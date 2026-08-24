"""Business rules for a user's scalar UI preferences."""

from __future__ import annotations

from typing import Any

from backend.repositories import user_preferences_repository as repository

ALLOWED_THEMES = frozenset({"system", "dark", "light"})


class InvalidThemeError(ValueError):
    """Raised when a theme value is outside the allowlist."""


def _internal_user_id(user: dict[str, Any]) -> int:
    """Return the internal users.id used only inside the service layer."""
    return int(user["id"])


def get_preferences(user: dict[str, Any]) -> dict[str, str] | None:
    """Return stored preferences for the current user, or None if absent."""
    return repository.fetch_preferences(_internal_user_id(user))


def update_theme(user: dict[str, Any], theme: str) -> dict[str, str]:
    """Persist theme only; omitted future columns are left unchanged."""
    if theme not in ALLOWED_THEMES:
        raise InvalidThemeError("Invalid theme")
    return repository.upsert_theme(_internal_user_id(user), theme)
