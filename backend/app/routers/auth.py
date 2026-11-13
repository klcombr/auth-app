"""Router de autenticação - login, registro, refresh token, logout e reset de senha."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.models import (
    get_user_by_email, get_user_by_id, create_user,
    add_refresh_token, revoke_refresh_token, get_active_refresh_token,
    add_password_reset_token, get_valid_password_reset_token,
    mark_password_reset_used, update_user_password,
)
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, UserOut,
)
from app.utils import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, get_token_hash,
    validate_password_strength, ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependência que extrai o usuário atual do token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.type != "access":
        raise credentials_exception
    user = get_user_by_id(payload.sub)
    if user is None or not user.get("is_active"):
        raise credentials_exception
    return user


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    """Registra um novo usuário e retorna tokens de acesso."""
    # Verifica se email já existe
    existing = await get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    # Valida força da senha
    valid, msg = validate_password_strength(body.password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # Cria usuário
    hashed_pw = hash_password(body.password)
    user_id = await create_user(body.email, hashed_pw, body.full_name)

    # Gera tokens
    access_token = create_access_token({"sub": user_id})
    refresh_token_str = create_refresh_token({"sub": user_id})
    refresh_hash = get_token_hash(refresh_token_str)
    expires_at = datetime.utcnow() + timedelta(days=7)
    await add_refresh_token(user_id, refresh_hash, expires_at)

    user_data = {
        "id": user_id,
        "email": body.email,
        "full_name": body.full_name,
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.utcnow().isoformat(),
    }

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut(**user_data),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Autentica usuário com email e senha."""
    user = await get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Conta desativada")

    access_token = create_access_token({"sub": user["id"]})
    refresh_token_str = create_refresh_token({"sub": user["id"]})
    refresh_hash = get_token_hash(refresh_token_str)
    expires_at = datetime.utcnow() + timedelta(days=7)
    await add_refresh_token(user["id"], refresh_hash, expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut(
            id=user["id"], email=user["email"], full_name=user["full_name"],
            is_active=user["is_active"], is_verified=user["is_verified"],
            created_at=user["created_at"],
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """Renova os tokens usando o refresh token."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.type != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    token_hash = get_token_hash(body.refresh_token)
    stored = await get_active_refresh_token(token_hash)
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token inválido ou revogado")

    # Gera novos tokens
    new_access = create_access_token({"sub": stored["user_id"]})
    new_refresh_str = create_refresh_token({"sub": stored["user_id"]})
    new_refresh_hash = get_token_hash(new_refresh_str)
    expires_at = datetime.utcnow() + timedelta(days=7)
    await add_refresh_token(stored["user_id"], new_refresh_hash, expires_at)

    # Revoga o old refresh token (boa prática: rotate)
    await revoke_refresh_token(token_hash)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh_str,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut(
            id=stored["user_id"], email=stored["email"],
            full_name=stored["full_name"], is_active=stored["is_active"],
            is_verified=stored["is_verified"], created_at=stored["created_at"],
        ),
    )


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, current_user: dict = Depends(get_current_user)):
    """Logout - revoga o refresh token."""
    token_hash = get_token_hash(body.refresh_token)
    await revoke_refresh_token(token_hash)
    return


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Gera token de recuperação de senha (simulado - em produção enviaria email)."""
    user = await get_user_by_email(body.email)
    if not user:
        # Security: não informar se o email existe ou não
        return {"message": "Se o email estiver cadastrado, um link de recuperação foi enviado."}

    reset_token = create_reset_token(user["id"])
    expires_at = datetime.utcnow() + timedelta(hours=1)
    await add_password_reset_token(user["id"], reset_token, expires_at)

    # EM PRODUÇÃO: enviar email com o link de reset
    # Para demo, retornamos o token diretamente
    return {
        "message": "Token de recuperação gerado.",
        "reset_token": reset_token,  # REMOVER EM PRODUÇÃO
        "expires_in": "1 hora",
    }


@router.post("/reset-password", status_code=204)
async def reset_password(body: ResetPasswordRequest):
    """Reseta a senha usando o token de recuperação."""
    reset_record = await get_valid_password_reset_token(body.token)
    if not reset_record:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    # Valida força da nova senha
    valid, msg = validate_password_strength(body.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    hashed_pw = hash_password(body.new_password)
    await update_user_password(reset_record["user_id"], hashed_pw)
    await mark_password_reset_used(reset_record["id"])

    # Revoga todos os refresh tokens do usuário (segurança)
    # Em produção, faríamos uma query para revogar todos os tokens ativos
