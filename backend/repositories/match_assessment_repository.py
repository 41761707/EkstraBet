"""SQL queries for match model assessments (post-match quality scores)."""

from __future__ import annotations

import pandas as pd

from backend.database import get_db_connection


def fetch_match_assessments(match_id: int) -> pd.DataFrame:
    """Return assessments for a match joined with model name.

    Rows are ordered by ``updated_at`` descending so callers can pick the
    newest assessment of a given type first.
    """
    query = """
        SELECT
            a.model_id,
            m.name AS model_name,
            a.model_version,
            a.assessment_type,
            a.home_played_better_probability,
            a.draw_probability,
            a.away_played_better_probability,
            a.final_assessment,
            a.confidence,
            a.dominance_score,
            a.feature_snapshot,
            a.updated_at
        FROM match_model_assessments a
        JOIN models m ON a.model_id = m.id
        WHERE a.match_id = %s
        ORDER BY a.updated_at DESC
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=(match_id,))
