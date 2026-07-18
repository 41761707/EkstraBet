"""Authentication endpoints: login, session status, and current user."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user
from api.schemas.auth import (
    AuthStatusResponse,
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
    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"])


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
