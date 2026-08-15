"""Authentication endpoints: login, first-login, status, and current user."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user
from api.schemas.auth import (
    AuthStatusResponse,
    CompleteFirstLoginRequest,
    CompleteFirstLoginResponse,
    LoginRequest,
    TokenResponse,
    UserPublic)
from backend.config import get_settings
from backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Validate credentials and return a JWT access token."""
    try:
        result = auth_service.login(body.username, body.password)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc)) from exc
    public = auth_service.to_public_user(result["user"])
    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
        first_login=public["first_login"],
        username=public["username"])


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    """Return whether authentication is currently enforced."""
    settings = get_settings()
    return AuthStatusResponse(auth_enabled=settings.auth_enabled)


@router.get("/me", response_model=UserPublic)
async def me(
    user: Annotated[dict[str, Any], Depends(get_current_user)]
) -> UserPublic:
    """Return the public profile of the authenticated user."""
    public = auth_service.to_public_user(user)
    return UserPublic(**public)


@router.post(
    "/complete-first-login",
    response_model=CompleteFirstLoginResponse)
async def complete_first_login(
    body: CompleteFirstLoginRequest,
    user: Annotated[dict[str, Any], Depends(get_current_user)]
) -> CompleteFirstLoginResponse:
    """Save new credentials and clear the first-login flag."""
    try:
        updated = auth_service.complete_first_login(
            user,
            body.username,
            body.new_password,
            body.new_password_confirm,
            body.display_name)
    except auth_service.UsernameTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)) from exc
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)) from exc
    return CompleteFirstLoginResponse(
        ok=True,
        user=UserPublic(**auth_service.to_public_user(updated)))
