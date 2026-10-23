"""Read and replace rows in hockey_player_game_ratings."""

from __future__ import annotations

import mysql.connector
import pandas as pd

from backend.database import get_db_connection
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID


_INSERT_RATING = """
    INSERT INTO hockey_player_game_ratings (
        match_id,
        player_id,
        team_id,
        player_group,
        offense,
        defense,
        total,
        production,
        empty_net,
        shots,
        teammate_goals,
        faceoffs,
        goals_against,
        penalties,
        blocks,
        goaltending
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s
    )
"""


def fetch_played_hockey_match_ids(season_id: int) -> list[int]:
    """Return played hockey matches that already have player stats."""
    # '0' i pusty result to mecz nierozegrany.
    query = """
        SELECT DISTINCT m.id
        FROM matches m
        JOIN hockey_match_player_stats box
            ON box.match_id = m.id
        WHERE m.sport_id = %s
            AND m.season = %s
            AND m.result IS NOT NULL
            AND m.result <> ''
            AND m.result <> '0'
        ORDER BY m.id
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, (HOCKEY_SPORT_ID, season_id))
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [int(row[0]) for row in rows]


def fetch_hockey_rating_match(match_id: int) -> dict | None:
    """Return sides of one match, or None when it does not exist."""
    query = """
        SELECT
            m.id,
            m.sport_id,
            m.result,
            m.home_team,
            m.away_team,
            home.name AS home_team_name,
            away.name AS away_team_name
        FROM matches m
        JOIN teams home ON home.id = m.home_team
        JOIN teams away ON away.id = m.away_team
        WHERE m.id = %s
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, (match_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        return None
    return dict(row)


def _rating_params(match_id: int, row: dict) -> tuple:
    """Map one rating row onto the insert placeholders.

    ``match_id`` is the function argument, not a key of the row.
    """
    return (
        match_id,
        row["player_id"],
        row["team_id"],
        row["player_group"],
        row["offense"],
        row["defense"],
        row["total"],
        row["production"],
        row["empty_net"],
        row["shots"],
        row["teammate_goals"],
        row["faceoffs"],
        row["goals_against"],
        row["penalties"],
        row["blocks"],
        row["goaltending"])


def replace_match_ratings(match_id: int, rows: list[dict]) -> int:
    """Delete this match's rating rows and insert the new set.

    An empty list still deletes. An insert error rolls the delete back.
    """
    delete_sql = """
        DELETE FROM hockey_player_game_ratings
        WHERE match_id = %s
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(delete_sql, (match_id,))
            for row in rows:
                cursor.execute(
                    _INSERT_RATING, _rating_params(match_id, row))
            # Bez commit close cofa DELETE i INSERT.
            conn.commit()
        except mysql.connector.Error:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return len(rows)


def fetch_hockey_rating_rows(season_id: int) -> pd.DataFrame:
    """Return one stored rating per player-night in a season."""
    query = """
        SELECT
            r.player_id,
            p.common_name AS player_name,
            t.name AS team_name,
            r.match_id,
            m.game_date,
            CASE
                WHEN m.home_team = r.team_id THEN away.name
                ELSE home.name
            END AS opponent_name,
            r.total
        FROM hockey_player_game_ratings r
        JOIN matches m ON m.id = r.match_id
        JOIN players p ON p.id = r.player_id
        JOIN teams t ON t.id = r.team_id
        JOIN teams home ON home.id = m.home_team
        JOIN teams away ON away.id = m.away_team
        WHERE m.season = %s
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(season_id,))
