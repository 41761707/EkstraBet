"""Administrative user operations: listing, creation and flag toggles."""

from __future__ import annotations

import uuid
from typing import Any, NoReturn

from mysql.connector.errors import IntegrityError

from backend.repositories import user_repository
from backend.services import auth_service
from backend.services.admin_errors import AdminConflictError
from backend.services.admin_errors import AdminForbiddenError
from backend.services.admin_errors import AdminNotFoundError
from backend.services.admin_errors import AdminValidationError


_MYSQL_DUPLICATE_ENTRY = 1062
# users.id zaczyna się od 1 — 0 nie wyklucza żadnego istniejącego wiersza
_NO_EXISTING_USER_ID = 0


def list_users() -> list[dict[str, Any]]:
    """Return all users as admin DTOs without password hashes."""
    return [_to_admin_user(row) for row in user_repository.fetch_all_users()]


def create_user(
        username: str,
        temporary_password: str,
        display_name: str | None = None,
        is_admin: bool = False) -> dict[str, Any]:
    """Create an active first-login account with an admin-supplied password."""
    normalized_username = _normalize_username(username)
    _validate_temporary_password(temporary_password)
    normalized_display_name = _normalize_optional_display_name(display_name)
    if user_repository.is_username_taken(
            normalized_username, _NO_EXISTING_USER_ID):
        raise AdminConflictError("Username already taken")
    user_uuid = str(uuid.uuid4())
    # plaintext zostaje u admina; DTO i logi go nie powielają
    password_hash = auth_service.hash_password(temporary_password)
    try:
        created = user_repository.create_user(
            user_uuid,
            normalized_username,
            password_hash,
            normalized_display_name,
            is_admin=is_admin,
            is_active=True,
            first_login=True)
    except IntegrityError as exc:
        _raise_user_integrity_error(exc)
    return _to_admin_user(created)


def set_user_active(
        actor: dict[str, Any],
        user_uuid: str,
        is_active: bool) -> dict[str, Any]:
    """Set is_active, rejecting self-deactivation."""
    target_uuid = _parse_user_uuid(user_uuid)
    _reject_self_demotion(
        actor,
        target_uuid,
        is_enabling=is_active,
        message="Cannot deactivate your own account")
    updated = user_repository.set_user_active(str(target_uuid), is_active)
    return _to_admin_user(_require_user_row(updated))


def set_user_admin(
        actor: dict[str, Any],
        user_uuid: str,
        is_admin: bool) -> dict[str, Any]:
    """Set is_admin, rejecting self-revocation of the admin role."""
    target_uuid = _parse_user_uuid(user_uuid)
    _reject_self_demotion(
        actor,
        target_uuid,
        is_enabling=is_admin,
        message="Cannot revoke your own admin role")
    updated = user_repository.set_user_admin(str(target_uuid), is_admin)
    return _to_admin_user(_require_user_row(updated))


def _to_admin_user(row: dict[str, Any]) -> dict[str, Any]:
    """Map a repository row to a public admin DTO."""
    # świadomie pomijamy id i password_hash — nie mogą wyciec do API
    return {"uuid": str(row["uuid"]),
        "username": str(row["username"]),
        "display_name": row.get("display_name"),
        "is_active": bool(row.get("is_active")),
        "is_admin": bool(row.get("is_admin")),
        "first_login": bool(row.get("first_login")),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at")}


def _require_user_row(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        raise AdminNotFoundError("User not found")
    return row


def _parse_user_uuid(user_uuid: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(user_uuid))
    except (ValueError, AttributeError, TypeError) as exc:
        raise AdminValidationError("Invalid user uuid") from exc


def _reject_self_demotion(
        actor: dict[str, Any],
        target_uuid: uuid.UUID,
        is_enabling: bool,
        message: str) -> None:
    if is_enabling:
        return
    # collation uuid jest case-insensitive — porównujemy kanoniczny UUID
    if _parse_user_uuid(str(actor["uuid"])) != target_uuid:
        return
    raise AdminForbiddenError(message)


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not (
            auth_service.MIN_USERNAME_LENGTH
            <= len(normalized)
            <= auth_service.MAX_USERNAME_LENGTH):
        raise AdminValidationError(
            "Username must be between "
            f"{auth_service.MIN_USERNAME_LENGTH} and "
            f"{auth_service.MAX_USERNAME_LENGTH} characters")
    return normalized


def _validate_temporary_password(password: str) -> None:
    if not (
            auth_service.MIN_PASSWORD_LENGTH
            <= len(password)
            <= auth_service.MAX_PASSWORD_LENGTH):
        raise AdminValidationError(
            "Password must be between "
            f"{auth_service.MIN_PASSWORD_LENGTH} and "
            f"{auth_service.MAX_PASSWORD_LENGTH} characters")


def _normalize_optional_display_name(
        display_name: str | None) -> str | None:
    if display_name is None:
        return None
    normalized = display_name.strip()
    if not normalized:
        return None
    if not (
            auth_service.MIN_DISPLAY_NAME_LENGTH
            <= len(normalized)
            <= auth_service.MAX_DISPLAY_NAME_LENGTH):
        raise AdminValidationError(
            "Display name must be between "
            f"{auth_service.MIN_DISPLAY_NAME_LENGTH} and "
            f"{auth_service.MAX_DISPLAY_NAME_LENGTH} characters")
    return normalized


def _raise_user_integrity_error(exc: IntegrityError) -> NoReturn:
    errno = getattr(exc, "errno", None)
    if errno != _MYSQL_DUPLICATE_ENTRY:
        raise AdminValidationError("Invalid user record") from exc
    message = str(exc).lower()
    if "username" in message:
        raise AdminConflictError("Username already taken") from exc
    raise AdminConflictError("User already exists") from exc
