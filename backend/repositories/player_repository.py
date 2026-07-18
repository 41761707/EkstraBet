"""SQL queries for player statistics pages."""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection

FOOTBALL_SPORT_ID = 1
HOCKEY_SPORT_ID = 2


def fetch_football_player_countries() -> pd.DataFrame:
    """Return countries with football leagues that expose player stats."""
    query = """
        SELECT DISTINCT
            c.id AS country_id,
            c.name AS country_name,
            c.emoji AS country_emoji
        FROM teams t
        JOIN countries c ON t.country = c.id
        JOIN leagues l ON c.id = l.country
        WHERE t.sport_id = %s
            AND l.has_player_stats = 1
        ORDER BY c.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(FOOTBALL_SPORT_ID,))


def fetch_football_player_teams(country_id: int) -> pd.DataFrame:
    """Return football teams with Opta mapping for a given country."""
    query = """
        SELECT
            t.id AS team_id,
            t.name AS team_name,
            t.country AS country_id
        FROM teams t
        JOIN countries c ON t.country = c.id
        JOIN leagues l ON c.id = l.country
        WHERE t.sport_id = %s
            AND t.opta_name IS NOT NULL
            AND l.has_player_stats = 1
            AND t.country = %s
        ORDER BY t.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(FOOTBALL_SPORT_ID, country_id))


def fetch_football_player_seasons() -> pd.DataFrame:
    """Return seasons that contain football matches."""
    query = """
        SELECT DISTINCT
            s.id AS season_id,
            s.years AS years
        FROM matches m
        JOIN seasons s ON m.season = s.id
        WHERE m.sport_id = %s
        ORDER BY s.years DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(FOOTBALL_SPORT_ID,))


def fetch_hockey_player_teams() -> pd.DataFrame:
    """Return NHL teams for the players page."""
    query = """
        SELECT
            t.id AS team_id,
            t.name AS team_name,
            t.country AS country_id
        FROM teams t
        WHERE t.sport_id = %s
        ORDER BY t.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(HOCKEY_SPORT_ID,))


def fetch_hockey_player_seasons() -> pd.DataFrame:
    """Return seasons that contain hockey player stats."""
    query = """
        SELECT DISTINCT
            s.id AS season_id,
            s.years AS years
        FROM seasons s
        JOIN matches m ON s.id = m.season
        JOIN hockey_match_player_stats stat ON m.id = stat.match_id
        WHERE m.sport_id = %s
        ORDER BY s.years DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(HOCKEY_SPORT_ID,))


def fetch_football_players(
    season_id: int,
    team_id: int | None = None,
    search: str | None = None) -> pd.DataFrame:
    """Return football players for a season, optionally filtered by team or name."""
    conditions = [
        "m.season = %s",
        "p.common_name IS NOT NULL",
        "p.common_name != ''",
    ]
    params: list[object] = [season_id]

    if team_id is not None:
        conditions.append("fps.team_id = %s")
        params.append(team_id)

    if search:
        conditions.append("LOWER(p.common_name) LIKE %s")
        params.append(f"%{search.strip().lower()}%")

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT DISTINCT
            p.id AS player_id,
            p.common_name AS common_name,
            fps.team_id AS current_team_id
        FROM players p
        JOIN football_player_stats fps ON p.id = fps.player_id
        JOIN matches m ON fps.match_id = m.id
        WHERE {where_clause}
        ORDER BY p.common_name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def fetch_hockey_players(
    season_id: int,
    team_id: int | None = None,
    search: str | None = None) -> pd.DataFrame:
    """Return NHL players for a season, optionally filtered by team or name."""
    conditions = ["m.season = %s"]
    params: list[object] = [season_id]

    if team_id is not None:
        conditions.append("p.current_club = %s")
        params.append(team_id)

    if search:
        conditions.append(
            """
            LOWER(
                CONVERT(
                    CONCAT_WS(
                        ' ',
                        p.first_name,
                        p.last_name,
                        p.common_name
                    )
                    USING utf8mb4
                )
            ) COLLATE utf8mb4_unicode_ci LIKE %s
            """)
        params.append(f"%{search.strip().lower()}%")

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT DISTINCT
            p.id AS player_id,
            CONCAT_WS(' ', p.first_name, p.last_name) AS common_name,
            p.position AS position,
            p.current_club AS current_team_id
        FROM players p
        JOIN hockey_match_player_stats stat ON p.id = stat.player_id
        JOIN matches m ON stat.match_id = m.id
        WHERE {where_clause}
        ORDER BY common_name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def fetch_player_position(player_id: int) -> str | None:
    """Return player position for role-specific stat handling."""
    query = "SELECT position FROM players WHERE id = %s"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(player_id,))
    if frame.empty or pd.isna(frame.iloc[0]["position"]):
        return None
    return str(frame.iloc[0]["position"])


def fetch_football_player_match_stats(
    player_id: int,
    season_id: int,
    limit: int) -> pd.DataFrame:
    """Return per-match football stats for a player in a season."""
    query = """
        SELECT
            m.id AS match_id,
            t1.name AS home_team,
            t2.name AS away_team,
            DATE_FORMAT(CAST(m.game_date AS DATE), '%d.%m') AS match_date,
            stat.goals,
            stat.assists,
            stat.shots,
            stat.shots_on_target,
            stat.fouls_conceded,
            stat.yellow_cards,
            CASE
                WHEN t1.id = stat.team_id THEN t2.shortcut
                WHEN t2.id = stat.team_id THEN t1.shortcut
            END AS opponent_shortcut
        FROM football_player_stats stat
        JOIN matches m ON stat.match_id = m.id
        JOIN teams t1 ON t1.id = m.home_team
        JOIN teams t2 ON t2.id = m.away_team
        WHERE stat.player_id = %s
            AND m.season = %s
        ORDER BY m.game_date DESC
        LIMIT %s
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(
            query,
            conn,
            params=(player_id, season_id, limit))
    if frame.empty:
        return frame
    numeric_columns = [
        "goals",
        "assists",
        "shots",
        "shots_on_target",
        "fouls_conceded",
        "yellow_cards",
    ]
    for column in numeric_columns:
        frame[column] = frame[column].fillna(0).astype(int)
    return frame


def fetch_hockey_player_match_stats(
    player_id: int,
    season_id: int,
    limit: int,
    is_goalie: bool) -> pd.DataFrame:
    """Return per-match hockey stats for a player in a season."""
    if is_goalie:
        stat_columns = """
            stat.shots_against,
            stat.shots_saved,
            stat.saves_acc,
            stat.toi,
        """
    else:
        stat_columns = """
            stat.points,
            stat.goals,
            stat.assists,
            stat.plus_minus,
            stat.penalty_minutes,
            stat.sog,
            stat.toi,
        """

    query = f"""
        SELECT
            m.id AS match_id,
            t1.name AS home_team,
            t2.name AS away_team,
            DATE_FORMAT(CAST(m.game_date AS DATE), '%d.%m') AS match_date,
            {stat_columns}
            CASE
                WHEN t1.id = stat.team_id THEN t2.shortcut
                WHEN t2.id = stat.team_id THEN t1.shortcut
            END AS opponent_shortcut
        FROM hockey_match_player_stats stat
        JOIN matches m ON stat.match_id = m.id
        JOIN teams t1 ON t1.id = m.home_team
        JOIN teams t2 ON t2.id = m.away_team
        WHERE stat.player_id = %s
            AND m.season = %s
        ORDER BY m.game_date DESC
        LIMIT %s
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(
            query,
            conn,
            params=(player_id, season_id, limit))
    if frame.empty:
        return frame

    numeric_columns = (
        ["shots_against", "shots_saved", "saves_acc"]
        if is_goalie
        else [
            "points",
            "goals",
            "assists",
            "plus_minus",
            "penalty_minutes",
            "sog"])
    for column in numeric_columns:
        frame[column] = frame[column].fillna(0)
    frame["toi"] = frame["toi"].fillna("0:00")
    return frame
