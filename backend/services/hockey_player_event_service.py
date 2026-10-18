"""Read upcoming NHL skater event rankings."""

from __future__ import annotations

from typing import Any

from backend.repositories import match_repository
from backend.sports.hockey.player_event_rankings import (
    build_hockey_player_event_rankings)


def get_hockey_player_event_rankings(limit: int | None) -> dict[str, Any]:
    """Return point, goal, assist and shot boards for unplayed matches."""
    frame = match_repository.fetch_upcoming_hockey_player_props()
    return build_hockey_player_event_rankings(frame, limit)
