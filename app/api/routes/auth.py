"""
Authentication endpoints — login, register, user management.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_auth, require_admin
from app.core.models import TokenPayload, TokenResponse, UserCreate, UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class PermissionsUpdate(BaseModel):
    allowed_skills: list[str]


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, auth: AuthService = Depends(get_auth)):
    result = auth.authenticate(body.username, body.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return result


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    body: UserCreate,
    auth: AuthService = Depends(get_auth),
    _admin: TokenPayload = Depends(require_admin),
):
    return auth.register(body)


@router.get("/users", response_model=list[UserRead])
def list_users(
    auth: AuthService = Depends(get_auth),
    _admin: TokenPayload = Depends(require_admin),
):
    return auth.list_users()


@router.put("/users/{username}/permissions")
def update_permissions(
    username: str,
    body: PermissionsUpdate,
    auth: AuthService = Depends(get_auth),
    _admin: TokenPayload = Depends(require_admin),
):
    if not auth.update_permissions(username, body.allowed_skills):
        raise HTTPException(404, "User not found")
    return {"status": "updated"}


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    username: str,
    auth: AuthService = Depends(get_auth),
    _admin: TokenPayload = Depends(require_admin),
):
    if not auth.delete_user(username):
        raise HTTPException(404, "User not found")
