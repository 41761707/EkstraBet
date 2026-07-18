"""First-period goal counts for hockey match charts."""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection

GOAL_EVENT_ID = 181


def fetch_first_period_goals(match_ids: list[int]) -> dict[int, int]:
    """Return total first-period goals per match id."""
    if not match_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(match_ids))
    query = f"""
        SELECT
            hme.match_id,
            COUNT(*) AS first_period_goals
        FROM hockey_match_events hme
        WHERE hme.match_id IN ({placeholders})
            AND hme.period = 1
            AND hme.event_id = %s
        GROUP BY hme.match_id
    """
    params: tuple[object, ...] = (*match_ids, GOAL_EVENT_ID)
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=params)

    if frame.empty:
        return {}
    return {
        int(row["match_id"]): int(row["first_period_goals"])
        for _, row in frame.iterrows()
    }
