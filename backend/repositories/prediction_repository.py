"""SQL queries for predictions and final predictions."""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection

_EVENT_FAMILY_JOIN = """
    LEFT JOIN (
        SELECT
            efm.event_id,
            MIN(efm.event_family_id) AS event_family_id
        FROM event_family_mappings efm
        GROUP BY efm.event_id
    ) efm_one ON e.id = efm_one.event_id
    LEFT JOIN event_families ef ON efm_one.event_family_id = ef.id
"""


def search_predictions(
    match_id: int | None = None,
    event_id: int | None = None,
    model_ids: list[int] | None = None,
    page: int = 1,
    page_size: int = 50) -> tuple[pd.DataFrame, int]:
    """Return paginated raw predictions and total count."""
    conditions: list[str] = []
    params: list[object] = []

    if match_id is not None:
        conditions.append("p.match_id = %s")
        params.append(match_id)

    if event_id is not None:
        conditions.append("p.event_id = %s")
        params.append(event_id)

    if model_ids:
        placeholders = ",".join(["%s"] * len(model_ids))
        conditions.append(f"p.model_id IN ({placeholders})")
        params.extend(model_ids)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    count_query = f"""
        SELECT COUNT(*) AS total
        FROM predictions p
        {where_clause}
    """
    offset = (page - 1) * page_size
    query = f"""
        SELECT
            p.id,
            p.match_id,
            p.event_id,
            e.name AS event_name,
            ef.id AS event_family_id,
            ef.name AS event_family_name,
            p.model_id,
            m.name AS model_name,
            p.value
        FROM predictions p
        JOIN events e ON p.event_id = e.id
        LEFT JOIN models m ON p.model_id = m.id
        {_EVENT_FAMILY_JOIN}
        {where_clause}
        ORDER BY p.match_id, p.event_id, p.model_id
        LIMIT %s OFFSET %s
    """
    query_params = params + [page_size, offset]

    with get_db_connection() as conn:
        count_frame = pd.read_sql(count_query, conn, params=tuple(params))
        frame = pd.read_sql(query, conn, params=tuple(query_params))

    total = int(count_frame.iloc[0]["total"])
    return frame, total


def fetch_team_final_predictions(
    team_id: int,
    season_id: int) -> pd.DataFrame:
    """Return evaluated final predictions for a team in a season."""
    query = f"""
        SELECT
            p.event_id,
            fp.outcome,
            e.name AS event_name,
            m.id AS match_id,
            ef.id AS event_family_id,
            ef.name AS event_family_name,
            p.model_id,
            md.name AS model_name,
            p.value
        FROM predictions p
        JOIN final_predictions fp ON p.id = fp.predictions_id
        JOIN matches m ON m.id = p.match_id
        JOIN events e ON e.id = p.event_id
        LEFT JOIN models md ON p.model_id = md.id
        {_EVENT_FAMILY_JOIN}
        WHERE (m.home_team = %s OR m.away_team = %s)
          AND m.season = %s
          AND m.result != '0'
        ORDER BY m.game_date DESC, p.event_id, p.model_id
    """
    with get_db_connection() as conn:
        return pd.read_sql(
            query,
            conn,
            params=(team_id, team_id, season_id))


def fetch_match_final_predictions(
    match_id: int,
    model_ids: list[int] | None = None) -> pd.DataFrame:
    """Return final predictions with event and model family metadata."""
    conditions = ["p.match_id = %s"]
    params: list[object] = [match_id]

    if model_ids:
        placeholders = ",".join(["%s"] * len(model_ids))
        conditions.append(f"p.model_id IN ({placeholders})")
        params.extend(model_ids)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            p.id AS prediction_id,
            p.event_id,
            e.name AS event_name,
            ef.id AS event_family_id,
            ef.name AS event_family_name,
            p.model_id,
            md.name AS model_name,
            p.value,
            fp.outcome
        FROM predictions p
        JOIN final_predictions fp ON p.id = fp.predictions_id
        JOIN events e ON p.event_id = e.id
        LEFT JOIN models md ON p.model_id = md.id
        {_EVENT_FAMILY_JOIN}
        WHERE {where_clause}
        ORDER BY ef.name, p.event_id, p.model_id
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def team_exists(team_id: int) -> bool:
    """Return True when the team id exists in the database."""
    query = "SELECT 1 FROM teams WHERE id = %s LIMIT 1"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(team_id,))
    return not frame.empty


def season_exists(season_id: int) -> bool:
    """Return True when the season id exists in the database."""
    query = "SELECT 1 FROM seasons WHERE id = %s LIMIT 1"
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(season_id,))
    return not frame.empty
