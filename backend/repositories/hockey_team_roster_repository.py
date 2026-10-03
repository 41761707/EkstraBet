"""SQL reads for the current NHL roster and season player stats."""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection
from backend.repositories.sport_league_repository import REGULAR_SEASON_ROUND

_UNPLAYED_RESULT = "0"
_ROSTER_COLUMNS = [
    "player_id",
    "first_name",
    "last_name",
    "common_name",
    "country_name",
    "roster_position",
    "player_position",
    "roster_line",
    "roster_number",
    "is_injured",
    "injury_status",
    "injury_note"]
_MATCH_COLUMNS = [
    "match_id",
    "player_id",
    "team_id",
    "position",
    "line",
    "number",
    "toi"]
_STAT_COLUMNS = [
    "player_id",
    "goals",
    "assists",
    "points",
    "sog",
    "toi",
    "shots_against",
    "shots_saved"]


def fetch_current_roster(team_id: int) -> pd.DataFrame:
    """Return the current ``hockey_rosters`` rows for one team."""
    query = """
        SELECT
            hr.player_id,
            p.first_name,
            p.last_name,
            p.common_name,
            c.name AS country_name,
            hr.position AS roster_position,
            p.position AS player_position,
            hr.line AS roster_line,
            hr.number AS roster_number,
            hr.is_injured,
            hr.injury_status,
            hr.injury_note
        FROM hockey_rosters hr
        INNER JOIN players p ON p.id = hr.player_id
        LEFT JOIN countries c ON c.id = p.current_country
        WHERE hr.team_id = %s
        ORDER BY hr.id
    """
    frame = _read_sql(query, (team_id,))
    return frame.reindex(columns=_ROSTER_COLUMNS)


def fetch_last_match_roster(team_id: int) -> pd.DataFrame:
    """Return the roster of the latest played match that has rows.

    Time on ice comes from the box score. A result already stored
    in ``matches`` is skipped until ``hockey_match_rosters`` has
    that game.
    """
    match_id = _last_played_match_id(team_id)
    if match_id is None:
        return pd.DataFrame(columns=_MATCH_COLUMNS)
    query = """
        SELECT
            r.match_id,
            r.player_id,
            r.team_id,
            r.position,
            r.line,
            r.number,
            s.toi
        FROM hockey_match_rosters r
        LEFT JOIN hockey_match_player_stats s
            ON s.match_id = r.match_id
           AND s.player_id = r.player_id
        WHERE r.match_id = %s
          AND r.team_id = %s
        ORDER BY r.id
    """
    frame = _read_sql(query, (match_id, team_id))
    return frame.reindex(columns=_MATCH_COLUMNS)


def fetch_season_player_stats(
        team_id: int,
        season_id: int) -> pd.DataFrame:
    """Return regular-season box scores for one team in one season."""
    # Play-off zaczyna się od round >= 900 i nie wchodzi do GP składu.
    query = """
        SELECT
            s.player_id,
            s.goals,
            s.assists,
            s.points,
            s.sog,
            s.toi,
            s.shots_against,
            s.shots_saved
        FROM hockey_match_player_stats s
        INNER JOIN matches m ON m.id = s.match_id
        WHERE s.team_id = %s
          AND m.season = %s
          AND m.result <> %s
          AND m.round = %s
        ORDER BY s.id
    """
    frame = _read_sql(
        query,
        (team_id, season_id, _UNPLAYED_RESULT, REGULAR_SEASON_ROUND))
    return frame.reindex(columns=_STAT_COLUMNS)


def _last_played_match_id(team_id: int) -> int | None:
    query = """
        SELECT m.id
        FROM hockey_match_rosters r
        INNER JOIN matches m ON m.id = r.match_id
        WHERE r.team_id = %s
          AND m.result <> %s
        ORDER BY m.game_date DESC, m.id DESC
        LIMIT 1
    """
    frame = _read_sql(query, (team_id, _UNPLAYED_RESULT))
    if frame.empty:
        return None
    return int(frame.iloc[0]["id"])


def _read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)
