"""Authentication helpers: password hashing and JWT sessions."""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from mysql.connector.errors import IntegrityError

from backend.config import get_settings
from backend.repositories import user_repository


MIN_PASSWORD_LENGTH = 3
MAX_PASSWORD_LENGTH = 200
MIN_USERNAME_LENGTH = 1
MAX_USERNAME_LENGTH = 50
MIN_DISPLAY_NAME_LENGTH = 1
MAX_DISPLAY_NAME_LENGTH = 50


class AuthError(Exception):
    """Raised when login or token validation fails."""


class UsernameTakenError(AuthError):
    """Raised when the chosen username belongs to another user."""


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
    # jeden komunikat — bez ujawniania, czy konto istnieje / jest nieaktywne
    user = user_repository.fetch_user_by_username(username)
    if user is None or not user.get("is_active"):
        raise AuthError("Invalid username or password")
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
        "display_name": user.get("display_name"),
        "first_login": bool(user.get("first_login")),
        "is_admin": bool(user.get("is_admin"))
    }


def complete_first_login(
        user: dict[str, Any],
        username: str,
        new_password: str,
        new_password_confirm: str,
        display_name: str) -> dict[str, Any]:
    """Persist new credentials and clear the first-login flag."""
    if not user.get("first_login"):
        raise AuthError("First login already completed")
    normalized_username = _normalize_username(username)
    normalized_display_name = _normalize_display_name(display_name)
    _validate_new_password(new_password, new_password_confirm)
    user_id = int(user["id"])
    if user_repository.is_username_taken(normalized_username, user_id):
        raise UsernameTakenError("Username already taken")
    password_hash = hash_password(new_password)
    _persist_first_login_credentials(
        user_id,
        normalized_username,
        password_hash,
        normalized_display_name)
    updated = user_repository.fetch_user_by_id(user_id)
    if updated is None:
        raise AuthError("User not found")
    return updated


def _normalize_username(username: str) -> str:
    """Return a trimmed username or raise AuthError."""
    return _normalize_required_name(
        username,
        MIN_USERNAME_LENGTH,
        MAX_USERNAME_LENGTH,
        "Username")


def _normalize_display_name(display_name: str) -> str:
    """Return a trimmed display name or raise AuthError."""
    return _normalize_required_name(
        display_name,
        MIN_DISPLAY_NAME_LENGTH,
        MAX_DISPLAY_NAME_LENGTH,
        "Display name")


def _normalize_required_name(
        value: str,
        min_length: int,
        max_length: int,
        field_label: str) -> str:
    """Return a trimmed required name or raise AuthError."""
    normalized = value.strip()
    if not min_length <= len(normalized) <= max_length:
        raise AuthError(
            f"{field_label} must be between "
            f"{min_length} and {max_length} characters")
    return normalized


def _validate_new_password(
        new_password: str,
        new_password_confirm: str) -> None:
    """Raise AuthError when the new password is invalid."""
    if new_password != new_password_confirm:
        raise AuthError("Passwords do not match")
    password_length = len(new_password)
    if not MIN_PASSWORD_LENGTH <= password_length <= MAX_PASSWORD_LENGTH:
        raise AuthError(
            "Password must be between "
            f"{MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters")


def _persist_first_login_credentials(
        user_id: int,
        username: str,
        password_hash: str,
        display_name: str) -> None:
    """Write credentials; map DB conflicts to domain errors."""
    try:
        user_repository.update_user_credentials_after_first_login(
            user_id, username, password_hash, display_name)
    except ValueError as exc:
        raise AuthError("First login already completed") from exc
    except IntegrityError as exc:
        raise UsernameTakenError("Username already taken") from exc
