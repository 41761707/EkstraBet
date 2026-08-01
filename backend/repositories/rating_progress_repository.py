"""SQL context for seasonal football rating-progress calculations.

Loads league/season metadata, season participants and finished matches from
football leagues in the same country, ordered for ``compute_ratings_timeline``.
User values are bound as query parameters — never interpolated into SQL text.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from backend.database import get_db_connection

FOOTBALL_SPORT_ID = 1
_FINISHED_RESULTS = ("1", "X", "2")


@dataclass(frozen=True)
class RatingProgressContext:
    """Deterministic DB payload for seasonal rating progress.

    ``matches`` uses pipeline column names expected by
    ``compute_ratings_timeline`` (``home_team``, ``away_team``,
    ``game_date``, ``league``, ``season``, ``id``) plus ``tier`` and
    ``round``. ``participants`` lists every team that appears in any
    match of the target league/season (including unfinished fixtures).
    """

    league_id: int
    league_name: str
    country_id: int
    country_name: str | None
    sport_id: int
    tier: int | None
    season_id: int
    season_years: str
    participants: pd.DataFrame
    matches: pd.DataFrame
    last_played_match_id: int | None
    last_played_at: datetime | None


def fetch_rating_progress_context(
        league_id: int,
        season_id: int) -> RatingProgressContext | None:
    """Return rating-progress context or ``None`` when league/season is missing.

    When the league and season exist but the season has no finished matches,
    returns a context with empty ``matches`` / ``participants`` as needed and
    ``last_played_match_id`` set to ``None``. Callers distinguish non-football
    leagues via ``sport_id``.
    """
    league = _fetch_league_row(league_id)
    if league is None:
        return None
    season_years = _fetch_season_years(season_id)
    if season_years is None:
        return None

    participants = _fetch_season_participants(league_id, season_id)
    last_match = _fetch_last_finished_match(league_id, season_id)
    if last_match is None:
        matches = _empty_matches_frame()
        last_played_match_id = None
        last_played_at = None
    else:
        last_played_match_id, last_played_at = last_match
        matches = _fetch_country_finished_matches(
            country_id=int(league["country_id"]),
            sport_id=FOOTBALL_SPORT_ID,
            cutoff_at=last_played_at,
            cutoff_match_id=last_played_match_id)

    return RatingProgressContext(
        league_id=int(league["league_id"]),
        league_name=str(league["league_name"]),
        country_id=int(league["country_id"]),
        country_name=league["country_name"],
        sport_id=int(league["sport_id"]),
        tier=league["tier"],
        season_id=season_id,
        season_years=season_years,
        participants=participants,
        matches=matches,
        last_played_match_id=last_played_match_id,
        last_played_at=last_played_at)


def _fetch_league_row(league_id: int) -> dict[str, object] | None:
    """Return league metadata or ``None`` when the id is unknown."""
    query = """
        SELECT
            l.id AS league_id,
            l.name AS league_name,
            l.country AS country_id,
            c.name AS country_name,
            l.sport_id,
            l.tier
        FROM leagues l
        LEFT JOIN countries c ON l.country = c.id
        WHERE l.id = %s
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(league_id,))
    if frame.empty:
        return None
    row = frame.iloc[0]
    country_id = row["country_id"]
    if pd.isna(country_id):
        return None
    sport_id = row["sport_id"]
    if pd.isna(sport_id):
        return None
    country_name = row["country_name"]
    tier_value = row["tier"]
    return {
        "league_id": int(row["league_id"]),
        "league_name": str(row["league_name"]),
        "country_id": int(country_id),
        "country_name": (
            None if pd.isna(country_name) else str(country_name)),
        "sport_id": int(sport_id),
        "tier": None if pd.isna(tier_value) else int(tier_value)
    }


def _fetch_season_years(season_id: int) -> str | None:
    """Return season label or ``None`` when the season id is unknown."""
    query = "SELECT years FROM seasons WHERE id = %s"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(season_id,))
    if frame.empty:
        return None
    years = frame.iloc[0]["years"]
    if pd.isna(years):
        return None
    return str(years)


def _fetch_season_participants(
        league_id: int,
        season_id: int) -> pd.DataFrame:
    """Return distinct teams that appear in the league season fixtures."""
    query = """
        SELECT team_id, team_name, team_shortcut
        FROM (
            SELECT DISTINCT
                m.home_team AS team_id,
                t.name AS team_name,
                t.shortcut AS team_shortcut
            FROM matches m
            JOIN teams t ON m.home_team = t.id
            WHERE m.league = %s
                AND m.season = %s
                AND m.home_team IS NOT NULL
            UNION
            SELECT DISTINCT
                m.away_team AS team_id,
                t.name AS team_name,
                t.shortcut AS team_shortcut
            FROM matches m
            JOIN teams t ON m.away_team = t.id
            WHERE m.league = %s
                AND m.season = %s
                AND m.away_team IS NOT NULL
        ) AS season_teams
        ORDER BY team_name
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(league_id, season_id, league_id, season_id))


def _fetch_last_finished_match(
        league_id: int,
        season_id: int) -> tuple[int, datetime] | None:
    """Return id and kickoff of the latest finished target-season match."""
    result_placeholders = ", ".join(["%s"] * len(_FINISHED_RESULTS))
    query = f"""
        SELECT
            m.id,
            m.game_date
        FROM matches m
        WHERE m.league = %s
            AND m.season = %s
            AND m.result IN ({result_placeholders})
            AND m.home_team IS NOT NULL
            AND m.away_team IS NOT NULL
            AND m.home_team_goals IS NOT NULL
            AND m.away_team_goals IS NOT NULL
            AND m.game_date IS NOT NULL
        ORDER BY m.game_date DESC, m.id DESC
        LIMIT 1
    """
    params: tuple[object, ...] = (
        league_id,
        season_id,
        *_FINISHED_RESULTS)
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=params)
    if frame.empty:
        return None
    game_date = frame.iloc[0]["game_date"]
    if pd.isna(game_date):
        return None
    return int(frame.iloc[0]["id"]), pd.Timestamp(game_date).to_pydatetime()


def _fetch_country_finished_matches(
        *,
        country_id: int,
        sport_id: int,
        cutoff_at: datetime,
        cutoff_match_id: int) -> pd.DataFrame:
    """Return finished same-country football matches up to the cutoff.

    Includes matches strictly before ``cutoff_at`` and same-timestamp matches
    with ``id <= cutoff_match_id``, so the target season's last fixture is
    included without pulling later same-day games from other leagues.
    """
    result_placeholders = ", ".join(["%s"] * len(_FINISHED_RESULTS))
    query = f"""
        SELECT
            m.id,
            m.league,
            m.season,
            m.round,
            m.game_date,
            m.home_team,
            m.away_team,
            m.home_team_goals,
            m.away_team_goals,
            m.result,
            m.sport_id,
            l.tier
        FROM matches m
        JOIN leagues l ON m.league = l.id
        WHERE l.country = %s
            AND l.sport_id = %s
            AND m.sport_id = %s
            AND m.result IN ({result_placeholders})
            AND m.home_team IS NOT NULL
            AND m.away_team IS NOT NULL
            AND m.home_team_goals IS NOT NULL
            AND m.away_team_goals IS NOT NULL
            AND m.game_date IS NOT NULL
            AND (
                m.game_date < %s
                OR (m.game_date = %s AND m.id <= %s)
            )
        ORDER BY m.game_date ASC, m.id ASC
    """
    params: tuple[object, ...] = (
        country_id,
        sport_id,
        sport_id,
        *_FINISHED_RESULTS,
        cutoff_at,
        cutoff_at,
        cutoff_match_id)
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def _empty_matches_frame() -> pd.DataFrame:
    """Return an empty matches frame with the expected column set."""
    return pd.DataFrame(columns=[
        "id",
        "league",
        "season",
        "round",
        "game_date",
        "home_team",
        "away_team",
        "home_team_goals",
        "away_team_goals",
        "result",
        "sport_id",
        "tier"
    ])
