"""Authentication helpers: password hashing and JWT sessions."""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from backend.config import get_settings
from backend.repositories import user_repository


class AuthError(Exception):
    """Raised when login or token validation fails."""


def _normalize_password(plain_password: str) -> str:
    """Return NFC-normalized password for stable Unicode comparisons."""
    return unicodedata.normalize("NFC", plain_password)


def _password_to_bytes(plain_password: str) -> bytes:
    """Return a bcrypt-safe secret derived from a Unicode password.
    """
    normalized = _normalize_password(plain_password)
    return hashlib.sha256(normalized.encode("utf-8")).digest()


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for the given plain-text password."""
    hashed = bcrypt.hashpw(
        _password_to_bytes(plain_password),
        bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True when the plain password matches the stored hash."""
    try:
        return bcrypt.checkpw(
            _password_to_bytes(plain_password),
            password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_uuid: str) -> tuple[str, int]:
    """Create a JWT with ``sub`` = user UUID. Returns (token, expires_in)."""
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    expire_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "sub": user_uuid,
        "exp": expire_at
    }
    token = jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.auth_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> str:
    """Return the user UUID from a valid JWT, or raise AuthError."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.auth_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid or expired token") from exc

    user_uuid = payload.get("sub")
    if not isinstance(user_uuid, str) or not user_uuid:
        raise AuthError("Invalid token subject")
    return user_uuid


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    """Validate credentials and return the active user row."""
    user = user_repository.fetch_user_by_username(username)
    if user is None:
        raise AuthError("Invalid username or password")
    if not user.get("is_active"):
        raise AuthError("User account is inactive")
    password_hash = user.get("password_hash") or ""
    if not verify_password(password, str(password_hash)):
        raise AuthError("Invalid username or password")
    return user


def login(username: str, password: str) -> dict[str, Any]:
    """Authenticate and return token payload fields for the API response."""
    user = authenticate_user(username, password)
    token, expires_in = create_access_token(str(user["uuid"]))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user
    }


def resolve_user_from_token(token: str) -> dict[str, Any]:
    """Decode JWT and load an active user by public UUID."""
    user_uuid = decode_access_token(token)
    user = user_repository.fetch_user_by_uuid(user_uuid)
    if user is None:
        raise AuthError("User not found")
    if not user.get("is_active"):
        raise AuthError("User account is inactive")
    return user


def to_public_user(user: dict[str, Any]) -> dict[str, Any]:
    """Map a DB user row to the public API shape (no internal id)."""
    return {
        "uuid": str(user["uuid"]),
        "username": str(user["username"]),
        "display_name": user.get("display_name")
    }
