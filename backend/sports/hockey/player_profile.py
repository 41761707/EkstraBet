"""Hockey constants for the shared player profile."""

from __future__ import annotations

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
    """Hockey profile source. Slice methods arrive in later tasks."""

    sport_id = HOCKEY_SPORT_ID
    stats_table = _HOCKEY_STATS_TABLE
