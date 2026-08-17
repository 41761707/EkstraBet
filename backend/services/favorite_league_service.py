"""Business rules for a user's favorite leagues."""

from __future__ import annotations

from typing import Any

from backend.repositories import user_favorite_league_repository as repository
from backend.services import league_service


class LeagueNotAvailableError(Exception):
    """Raised when a league cannot be added to favorites."""


def _internal_user_id(user: dict[str, Any]) -> int:
    """Return the internal users.id used only inside the service layer."""
    return int(user["id"])


def get_favorite_league_ids(user: dict[str, Any]) -> list[int]:
    """Return favorite league IDs for the current user."""
    return repository.fetch_favorite_league_ids(_internal_user_id(user))


def add_favorite_league(user: dict[str, Any], league_id: int) -> None:
    """Add an active league to favorites; unavailable leagues are rejected."""
    summary = league_service.get_league_summary(league_id)
    # brak ligi i active=0 to ten sam błąd domenowy — HTTP mapuje go na 404
    if summary is None or not summary["active"]:
        raise LeagueNotAvailableError("League not available")
    repository.add_favorite_league(_internal_user_id(user), league_id)


def remove_favorite_league(user: dict[str, Any], league_id: int) -> None:
    """Remove a favorite relation; missing or inactive leagues still succeed."""
    # DELETE jest idempotentny; nie wymagamy aktywności ani istnienia ligi
    repository.remove_favorite_league(_internal_user_id(user), league_id)
