"""SQL queries for bookmaker odds."""

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


def fetch_match_odds(match_id: int) -> pd.DataFrame:
    """Return odds for a match joined with bookmakers and events."""
    query = f"""
        SELECT
            o.id,
            o.match_id,
            o.bookmaker AS bookmaker_id,
            b.name AS bookmaker_name,
            o.event AS event_id,
            e.name AS event_name,
            ef.id AS event_family_id,
            ef.name AS event_family_name,
            o.odds
        FROM odds o
        JOIN bookmakers b ON o.bookmaker = b.id
        JOIN events e ON o.event = e.id
        {_EVENT_FAMILY_JOIN}
        WHERE o.match_id = %s
        ORDER BY b.name, ef.name, e.name
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(match_id,))
