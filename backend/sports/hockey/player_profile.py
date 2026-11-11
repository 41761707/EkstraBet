"""Hockey constants and profile source for the shared player profile."""

from __future__ import annotations

import pandas as pd

from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID


GOAL_EVENT_ID = 181
MINOR_PENALTY_EVENT_ID = 183
DISALLOWED_GOAL_EVENT_ID = 184
MAJOR_PENALTY_EVENT_ID = 185
MISCONDUCT_EVENT_ID = 186
UNSPORTSMANLIKE_EVENT_ID = 189
INCLUDED_EVENT_IDS = (
    GOAL_EVENT_ID,
    MINOR_PENALTY_EVENT_ID,
    DISALLOWED_GOAL_EVENT_ID,
    MAJOR_PENALTY_EVENT_ID,
    MISCONDUCT_EVENT_ID,
    UNSPORTSMANLIKE_EVENT_ID)
HOCKEY_SKATER_STAT_SQL = (
    "stat.points, stat.goals, stat.assists, stat.plus_minus, "
    "stat.penalty_minutes, stat.sog, stat.toi")
HOCKEY_GOALIE_STAT_SQL = (
    "stat.shots_against, stat.shots_saved, stat.saves_acc, stat.toi")
# Ta sama nazwa co HOCKEY_STATS_TABLE na białej liście wspólnego SQL.
_HOCKEY_STATS_TABLE = "hockey_match_player_stats"


class HockeyPlayerProfileSource:
    """Hockey profile source. Reads the slice and hockey event facts."""

    sport_id = HOCKEY_SPORT_ID
    stats_table = _HOCKEY_STATS_TABLE

    def fetch_slice(
            self,
            player_id: int,
            season_id: int | None,
            opponent_team_id: int | None,
            own_team_id: int | None,
            teammate_id: int | None,
            limit: int) -> pd.DataFrame:
        """Return one hockey row per match for the requested slice."""
        # Import lokalny: rejestr źródeł ładuje tę klasę, a repozytorium
        # białą listę z modułu rejestru. Import na górze zamyka cykl.
        from backend.repositories import player_profile_repository as repo

        player = repo.fetch_player(player_id)
        position = None if player is None else player.get("position")
        stat_sql = (
            HOCKEY_GOALIE_STAT_SQL
            if position == "G"
            else HOCKEY_SKATER_STAT_SQL)
        return repo.fetch_profile_slice(
            self.stats_table,
            stat_sql,
            player_id,
            self.sport_id,
            season_id,
            opponent_team_id,
            own_team_id,
            teammate_id,
            limit)

    def fetch_event_facts(
            self,
            player_id: int,
            match_ids: list[int]) -> pd.DataFrame:
        """Return hockey event rows. This sport always has events."""
        # Ten sam import lokalny co w fetch_slice: górny import zamyka cykl.
        from backend.repositories import player_profile_repository as repo

        return repo.fetch_hockey_event_facts(player_id, match_ids)
