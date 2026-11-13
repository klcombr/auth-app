"""
Models - Camada de dados do sistema de autenticação.
Utiliza SQLite com aiosqlite para operações assíncronas.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Pydantic Models ---

class UserBase(BaseModel):
    """Campos comuns do usuário."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Dados para criar um novo usuário."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Dados para atualizar o usuário."""
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Resposta da API com dados do usuário (sem senha)."""
    id: int
    is_active: bool
    is_verified: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Resposta com tokens de autenticação."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos


class TokenData(BaseModel):
    """Dados extraídos do JWT."""
    sub: Optional[int] = None
    type: Optional[str] = None  # "access" or "refresh"


class PasswordReset(BaseModel):
    """Solicitação de reset de senha."""
    email: EmailStr


class NewPassword(BaseModel):
    """Nova senha após reset."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


# --- Database Layer ---

DB_PATH = Path(__file__).parent.parent / "auth.db"


def init_db():
    """Inicializa o banco de dados e cria as tabelas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Banco inicializado em {DB_PATH}")


async def get_db_connection():
    """Retorna uma conexão assíncrona com o banco."""
    import aiosqlite
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def get_user_by_email(email: str) -> Optional[dict]:
    """Busca usuário por email."""
    conn = await get_db_connection()
    async with conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ) as cursor:
        row = await cursor.fetchone()
    await conn.close()
    return dict(row) if row else None


async def get_user_by_id(user_id: int) -> Optional[dict]:
    """Busca usuário por ID."""
    conn = await get_db_connection()
    async with conn.execute(
        "SELECT id, email, full_name, is_active, is_verified, created_at, updated_at FROM users WHERE id = ?",
        (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
    await conn.close()
    return dict(row) if row else None


async def create_user(
    email: str,
    hashed_password: str,
    full_name: Optional[str] = None
) -> int:
    """Cria um novo usuário e retorna o ID."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """INSERT INTO users (email, hashed_password, full_name)
               VALUES (?, ?, ?)""",
            (email, hashed_password, full_name)
        )
        await conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError("Email já cadastrado")
    finally:
        await conn.close()


async def add_refresh_token(user_id: int, token_hash: str, expires_at: datetime) -> int:
    """Adiciona um token de refresh ao banco."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
               VALUES (?, ?, ?)""",
            (user_id, token_hash, expires_at.isoformat())
        )
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def revoke_refresh_token(token_hash: str):
    """Revoga um token de refresh."""
    conn = await get_db_connection()
    await conn.execute("DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,))
    await conn.commit()
    await conn.close()


async def get_active_refresh_token(token_hash: str) -> Optional[dict]:
    """Busca token de refresh ativo e não revogado."""
    conn = await get_db_connection()
    async with conn.execute(
        """SELECT rt.*, u.id, u.email, u.full_name, u.is_active, u.is_verified
           FROM refresh_tokens rt
           JOIN users u ON rt.user_id = u.id
           WHERE rt.token_hash = ? AND rt.expires_at > datetime('now')""",
        (token_hash,)
    ) as cursor:
        row = await cursor.fetchone()
    await conn.close()
    return dict(row) if row else None


async def add_password_reset_token(user_id: int, token: str, expires_at: datetime) -> int:
    """Adiciona token de recuperação de senha."""
    conn = await get_db_connection()
    try:
        cursor = await conn.execute(
            """INSERT INTO password_resets (user_id, token, expires_at)
               VALUES (?, ?, ?)""",
            (user_id, token, expires_at.isoformat())
        )
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def get_valid_password_reset_token(token: str) -> Optional[dict]:
    """Busca token de reset válido e não usado."""
    conn = await get_db_connection()
    async with conn.execute(
        """SELECT pr.*, u.email FROM password_resets pr
           JOIN users u ON pr.user_id = u.id
           WHERE pr.token = ? AND pr.expires_at > datetime('now') AND pr.used = FALSE""",
        (token,)
    ) as cursor:
        row = await cursor.fetchone()
    await conn.close()
    return dict(row) if row else None


async def mark_password_reset_used(token_id: int):
    """Marca token de reset como usado."""
    conn = await get_db_connection()
    await conn.execute("UPDATE password_resets SET used = TRUE WHERE id = ?", (token_id,))
    await conn.commit()
    await conn.close()


async def update_user_password(user_id: int, hashed_password: str):
    """Atualiza a senha do usuário."""
    conn = await get_db_connection()
    await conn.execute(
        "UPDATE users SET hashed_password = ?, updated_at = datetime('now') WHERE id = ?",
        (hashed_password, user_id)
    )
    await conn.commit()
    await conn.close()


async def update_user(user_id: int, updates: dict):
    """Atualiza campos do usuário."""
    if not updates:
        return
    conn = await get_db_connection()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    await conn.execute(f"UPDATE users SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
    await conn.commit()
    await conn.close()


async def get_all_users(page: int = 1, limit: int = 20) -> dict:
    """Lista todos os usuários com paginação."""
    conn = await get_db_connection()
    offset = (page - 1) * limit
    async with conn.execute(
        "SELECT id, email, full_name, is_active, is_verified, created_at FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ) as cursor:
        users_list = [dict(row) for row in await cursor.fetchall()]
    async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
        total = (await cursor.fetchone())[0]
    await conn.close()
    return {"users": users_list, "total": total, "page": page, "limit": limit}
