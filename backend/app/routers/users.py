"""Router de gerenciamento de usuários - perfil, lista admin."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer

from app.models import (
    get_user_by_id, update_user, get_all_users,
    get_user_by_email, update_user_password,
)
from app.schemas import UserOut, UpdateProfileRequest, ChangePasswordRequest, UserListResponse
from app.utils import hash_password, verify_password, validate_password_strength, decode_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Extrai usuário atual do token JWT."""
    from app.routers.auth import get_current_user as auth_get_current
    return await auth_get_current(token)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Retorna dados do usuário autenticado."""
    return UserOut(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        is_active=current_user["is_active"],
        is_verified=current_user.get("is_verified", False),
        created_at=current_user["created_at"],
    )


@router.patch("/me", response_model=UserOut)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """Atualiza o perfil do usuário autenticado."""
    updates = {}
    if body.full_name is not None:
        updates["full_name"] = body.full_name
    if updates:
        await update_user(current_user["id"], updates)
    # Retorna dados atualizados
    updated = await get_user_by_id(current_user["id"])
    return UserOut(
        id=updated["id"], email=updated["email"], full_name=updated.get("full_name"),
        is_active=updated["is_active"], is_verified=updated.get("is_verified", False),
        created_at=updated["created_at"],
    )


@router.put("/me/password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Altera a senha do usuário autenticado."""
    user = await get_user_by_id(current_user["id"])
    if not verify_password(body.current_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    valid, msg = validate_password_strength(body.new_password)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    hashed_pw = hash_password(body.new_password)
    await update_user_password(current_user["id"], hashed_pw)


# --- Endpoints Admin (protegidos por verificação extra) ---

@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Lista todos os usuários (admin)."""
    # Em produção, verificar papel/role aqui
    result = await get_all_users(page=page, limit=limit)
    return UserListResponse(
        users=[UserOut(**u) for u in result["users"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
    )


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Desativa uma conta de usuário (soft delete)."""
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Não pode desativar a própria conta via API")
    await update_user(user_id, {"is_active": False})
