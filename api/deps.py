"""Wspólne zależności FastAPI, w tym bramki autoryzacji."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import get_settings
from backend.services import auth_service

_bearer_scheme = HTTPBearer(auto_error=False)

# ścieżki dostępne bez JWT (gdy auth włączony)
_PUBLIC_PATHS = frozenset({
    "/",
    "/health",
    "/auth/login",
    "/auth/status"
})
_PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def _is_public_path(path: str) -> bool:
    """Sprawdza, czy ścieżka jest publiczna."""
    if path in _PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


def _extract_bearer_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None) -> str | None:
    """Wyciąga token z nagłówka lub ciasteczka."""
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    settings = get_settings()
    cookie_token = request.cookies.get(settings.auth_cookie_name)
    if cookie_token:
        return cookie_token
    return None


async def require_auth(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme)]
) -> dict[str, Any] | None:
    """Wymusza autoryzację JWT, gdy jest włączona; pomija publiczne ścieżki i kill-switch."""
    settings = get_settings()
    if not settings.auth_enabled:
        return None
    if _is_public_path(request.url.path):
        return None
    token = _extract_bearer_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"})
    try:
        return auth_service.resolve_user_from_token(token)
    except auth_service.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"}) from exc


async def get_current_user(
    user: Annotated[dict[str, Any] | None, Depends(require_auth)]
) -> dict[str, Any]:
    """Zwraca uwierzytelnionego użytkownika; 401 gdy brak użytkownika lub autoryzacja jest włączona."""
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authentication is disabled")
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"})
    return user
