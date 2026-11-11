"""Hockey constants and profile source for the shared player profile."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import Any

import pandas as pd

from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from backend.services.player_service import _build_hockey_summary
from backend.services.player_service import _toi_to_minutes


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

    def build_body(
            self,
            player: dict[str, Any],
            frame: pd.DataFrame,
            event_frame: pd.DataFrame | None,
            truncated: bool) -> dict[str, Any]:
        """Build the hockey body placed in the profile envelope.

        ``truncated`` stays on the envelope. The body is the slice itself.
        """
        # Limit zostaje na kopercie. Ciało opisuje tylko zwrócone wiersze.
        del truncated
        is_goalie = player.get("position") == "G"
        if frame.empty:
            # Pusta seria nie ma średniej. Helper zwróciłby NaN.
            matches: list[dict[str, Any]] = []
            summary = _empty_hockey_summary(is_goalie)
        else:
            counts = _match_event_counts(event_frame)
            matches = [
                _slice_match(row, counts)
                for _, row in frame.iterrows()]
            summary = _build_hockey_summary(
                pd.DataFrame(matches),
                is_goalie)
        return {
            "sport_id": self.sport_id,
            "player_role": "goalie" if is_goalie else "skater",
            "summary": summary,
            "event_split": _event_split(event_frame),
            "matches": matches}


_SKATER_INT_COLUMNS = (
    "points",
    "goals",
    "assists",
    "plus_minus",
    "penalty_minutes",
    "sog")
_GOALIE_INT_COLUMNS = ("shots_against", "shots_saved")
_PENALTY_COUNT_KEYS = {
    MINOR_PENALTY_EVENT_ID: "minor_penalties",
    MAJOR_PENALTY_EVENT_ID: "major_penalties",
    MISCONDUCT_EVENT_ID: "misconduct_penalties",
    UNSPORTSMANLIKE_EVENT_ID: "unsportsmanlike_penalties",
    DISALLOWED_GOAL_EVENT_ID: "disallowed_goals"}
_PERIOD_GOAL_KEYS = {
    1: "goals_period_1",
    2: "goals_period_2",
    3: "goals_period_3",
    4: "goals_overtime",
    5: "shootout_goals"}


def _empty_hockey_summary(is_goalie: bool) -> dict[str, Any]:
    """Return zero box-score totals for a slice with no matches."""
    if is_goalie:
        return {
            "is_goalie": True,
            "average_toi": "0:00",
            "shots_against": 0.0,
            "shots_saved": 0.0,
            "saves_acc": 0.0}
    return {
        "is_goalie": False,
        "points": 0,
        "goals": 0,
        "assists": 0,
        "plus_minus": 0,
        "penalty_minutes": 0,
        "average_penalty_minutes": 0.0,
        "average_toi": "0:00",
        "average_sog": 0.0}


def _event_split(event_frame: pd.DataFrame | None) -> dict[str, int]:
    """Count hockey events in the slice. Missing facts are zeros."""
    counts = _zero_event_split()
    if event_frame is None or event_frame.empty:
        return counts
    for row in event_frame.itertuples(index=False):
        _add_event(counts, row)
    return counts


def _zero_event_split() -> dict[str, int]:
    """Return every hockey event counter set to zero."""
    return {
        "goals": 0,
        "power_play_goals": 0,
        "empty_net_goals": 0,
        "goals_period_1": 0,
        "goals_period_2": 0,
        "goals_period_3": 0,
        "goals_overtime": 0,
        "shootout_goals": 0,
        "minor_penalties": 0,
        "major_penalties": 0,
        "misconduct_penalties": 0,
        "unsportsmanlike_penalties": 0,
        "disallowed_goals": 0}


def _add_event(counts: dict[str, int], row: object) -> None:
    """Add one event row to the slice counters."""
    event_id = _as_int(getattr(row, "event_id", None))
    if event_id is None:
        return
    penalty_key = _PENALTY_COUNT_KEYS.get(event_id)
    if penalty_key is not None:
        counts[penalty_key] += 1
        return
    if event_id != GOAL_EVENT_ID:
        return
    counts["goals"] += 1
    if _flag_is_set(getattr(row, "pp_flag", None)):
        counts["power_play_goals"] += 1
    if _flag_is_set(getattr(row, "en_flag", None)):
        counts["empty_net_goals"] += 1
    period = _as_int(getattr(row, "period", None))
    period_key = _PERIOD_GOAL_KEYS.get(period) if period is not None else None
    if period_key is not None:
        counts[period_key] += 1


def _match_event_counts(
        event_frame: pd.DataFrame | None) -> dict[int, tuple[int, int]]:
    """Return match_id -> (power_play_goals, empty_net_goals)."""
    totals: dict[int, list[int]] = {}
    if event_frame is None or event_frame.empty:
        return {}
    for row in event_frame.itertuples(index=False):
        if _as_int(getattr(row, "event_id", None)) != GOAL_EVENT_ID:
            continue
        match_id = _as_int(getattr(row, "match_id", None))
        if match_id is None:
            continue
        pair = totals.setdefault(match_id, [0, 0])
        if _flag_is_set(getattr(row, "pp_flag", None)):
            pair[0] += 1
        if _flag_is_set(getattr(row, "en_flag", None)):
            pair[1] += 1
    return {
        match_id: (pair[0], pair[1])
        for match_id, pair in totals.items()}


def _slice_match(
        row: pd.Series,
        counts: dict[int, tuple[int, int]]) -> dict[str, Any]:
    """Map one slice row to a hockey match, plus situational goals."""
    match_id = int(row["match_id"])
    power_play_goals, empty_net_goals = counts.get(match_id, (0, 0))
    toi = _toi_text(_cell(row, "toi"))
    match: dict[str, Any] = {
        "match_id": match_id,
        "game_date": _game_date(_cell(row, "game_date")),
        "season_id": int(row["season_id"]),
        "season_years": _required_text(_cell(row, "season_years")),
        "own_team_id": int(row["own_team_id"]),
        "own_team_name": _required_text(_cell(row, "own_team_name")),
        "opponent_team_id": int(row["opponent_team_id"]),
        "opponent_name": _required_text(_cell(row, "opponent_name")),
        "opponent_shortcut": _required_text(
            _cell(row, "opponent_shortcut")),
        "venue": _required_text(_cell(row, "venue")),
        "home_goals": _as_int(_cell(row, "home_goals")),
        "away_goals": _as_int(_cell(row, "away_goals")),
        "result": _optional_text(_cell(row, "result")),
        "toi": toi,
        "toi_minutes": round(_toi_to_minutes(toi), 2),
        "power_play_goals": power_play_goals,
        "empty_net_goals": empty_net_goals}
    for column in _SKATER_INT_COLUMNS:
        match[column] = _stat_int(row, column)
    for column in _GOALIE_INT_COLUMNS:
        match[column] = _stat_int(row, column)
    match["saves_acc"] = _stat_float(row, "saves_acc")
    return match


def _stat_int(row: pd.Series, column: str) -> int | None:
    """Return 0 for SQL NULL. A missing column belongs to the other role."""
    if column not in row.index:
        return None
    value = row[column]
    if _is_na(value):
        return 0
    return int(value)


def _stat_float(row: pd.Series, column: str) -> float | None:
    """Return a one-decimal stat, or 0 when the stored value is NULL."""
    if column not in row.index:
        return None
    value = row[column]
    if _is_na(value):
        return 0.0
    return round(float(value), 1)


def _cell(row: pd.Series, column: str) -> object:
    if column not in row.index:
        return None
    return row[column]


def _toi_text(value: object) -> str:
    """Return ice time. NULL is no time, shown as 0:00."""
    if _is_na(value):
        return "0:00"
    return str(value)


def _game_date(value: object) -> str:
    """Return the match day as YYYY-MM-DD."""
    if _is_na(value):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _required_text(value: object) -> str:
    if _is_na(value):
        return ""
    return str(value)


def _optional_text(value: object) -> str | None:
    if _is_na(value):
        return None
    return str(value)


def _flag_is_set(value: object) -> bool:
    """True only for flag 1. Any other value stays out of the counter."""
    return _as_int(value) == 1


def _as_int(value: object) -> int | None:
    if _is_na(value):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _is_na(value: object) -> bool:
    if isinstance(value, (str, bytes)):
        return False
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
