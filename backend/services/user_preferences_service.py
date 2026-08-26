"""Business rules for a user's scalar UI preferences."""

from __future__ import annotations

from typing import Any

from backend.repositories import user_preferences_repository as repository

ALLOWED_THEMES = frozenset({"system", "dark", "light"})
ALLOWED_TEAM_NAME_DISPLAYS = frozenset({"full", "shortcut"})


class InvalidThemeError(ValueError):
    """Raised when a theme value is outside the allowlist."""


class InvalidTeamNameDisplayError(ValueError):
    """Raised when a team-name display value is outside the allowlist."""


class EmptyPreferencesPatchError(ValueError):
    """Raised when an update provides no preference fields."""


def _internal_user_id(user: dict[str, Any]) -> int:
    """Return the internal users.id used only inside the service layer."""
    return int(user["id"])


def get_preferences(user: dict[str, Any]) -> dict[str, str] | None:
    """Return stored preferences for the current user, or None if absent."""
    return repository.fetch_preferences(_internal_user_id(user))


def update_preferences(
        user: dict[str, Any],
        theme: str | None = None,
        team_name_display: str | None = None) -> dict[str, str]:
    """Validate provided fields, reject an empty patch, then upsert once."""
    if theme is None and team_name_display is None:
        raise EmptyPreferencesPatchError(
            "At least one preference field is required")
    if theme is not None and theme not in ALLOWED_THEMES:
        raise InvalidThemeError("Invalid theme")
    if (
            team_name_display is not None
            and team_name_display not in ALLOWED_TEAM_NAME_DISPLAYS):
        raise InvalidTeamNameDisplayError("Invalid team_name_display")
    return repository.upsert_preferences(
        _internal_user_id(user),
        theme=theme,
        team_name_display=team_name_display)
