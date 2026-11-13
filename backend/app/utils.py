"""
Utils - Funções utilitárias para segurança, JWT e hashing de senhas.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.models import TokenData
from dotenv import load_dotenv
import os

load_dotenv()

# --- Configurações ---

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE", "7"))
RESET_TOKEN_EXPIRE_HOURS = int(os.getenv("RESET_TOKEN_EXPIRE", "1"))

# --- Password Hashing ---

def hash_password(password: str) -> str:
    """Hash de senha usando bcrypt diretamente."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# --- JWT Tokens ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token de acesso JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Cria um token de refresh JWT."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_reset_token(user_id: int) -> str:
    """Cria um token de recuperação de senha."""
    return secrets.urlsafe_b64encode(secrets.token_bytes(32)).decode()


def decode_token(token: str) -> Optional[TokenData]:
    """Decodifica e valida um token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None or token_type is None:
            return None
        return TokenData(sub=int(user_id), type=token_type)
    except JWTError:
        return None


def get_token_hash(token: str) -> str:
    """Gera hash do token para armazenamento seguro no banco."""
    return hashlib.sha256(token.encode()).hexdigest()


# --- Validation ---

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Valida a força da senha. Retorna (valido, mensagem)."""
    if len(password) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres"
    if not any(c.isupper() for c in password):
        return False, "A senha deve conter pelo menos uma letra maiúscula"
    if not any(c.islower() for c in password):
        return False, "A senha deve conter pelo menos uma letra minúscula"
    if not any(c.isdigit() for c in password):
        return False, "A senha deve conter pelo menos um número"
    if not any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?/" for c in password):
        return False, "A senha deve conter pelo menos um caractere especial"
    return True, "Senha forte!"
