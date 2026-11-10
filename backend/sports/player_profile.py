"""Shared player-profile limits, table whitelist and source registry."""

from __future__ import annotations

from typing import Any
from typing import Protocol

import pandas as pd

from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from backend.sports.hockey.player_profile import HockeyPlayerProfileSource


SLICE_MATCH_LIMIT = 1000
PLAYER_SEARCH_MIN_LENGTH = 2
PLAYER_SEARCH_LIMIT = 20

HOCKEY_STATS_TABLE = "hockey_match_player_stats"
# Dopisać źródło, nie zmieniać SQL wspólnego.
FOOTBALL_STATS_TABLE = "football_player_stats"
BASKETBALL_STATS_TABLE = "basketball_match_player_stats"
ALLOWED_PROFILE_STATS_TABLES = frozenset({
    HOCKEY_STATS_TABLE,
    FOOTBALL_STATS_TABLE,
    BASKETBALL_STATS_TABLE})


class PlayerProfileSource(Protocol):
    """Sport reader that fills one profile body.

    ``fetch_event_facts`` returns ``None`` when the sport has no events.
    """

    sport_id: int
    stats_table: str

    def fetch_slice(
            self,
            player_id: int,
            season_id: int | None,
            opponent_team_id: int | None,
            own_team_id: int | None,
            teammate_id: int | None,
            limit: int) -> pd.DataFrame:
        """Return one row per match in the requested slice."""
        ...

    def fetch_event_facts(
            self,
            player_id: int,
            match_ids: list[int]) -> pd.DataFrame | None:
        """Return event rows, or None when this sport has no events."""
        ...

    def build_body(
            self,
            player: dict[str, Any],
            frame: pd.DataFrame,
            event_frame: pd.DataFrame | None,
            truncated: bool) -> dict[str, Any]:
        """Build the sport-specific body placed in the envelope."""
        ...


PROFILE_SOURCES: dict[int, PlayerProfileSource] = {
    HOCKEY_SPORT_ID: HockeyPlayerProfileSource()}
