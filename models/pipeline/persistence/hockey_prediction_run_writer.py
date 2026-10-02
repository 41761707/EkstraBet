"""Upsert one NHL team-model snapshot per match, model and stage."""

from __future__ import annotations

import json
import math
from contextlib import nullcontext
from typing import Any

from backend.database import get_db_connection


INITIAL_STAGE = "initial"
FINAL_STAGE = "final"
_ALLOWED_STAGES = frozenset({INITIAL_STAGE, FINAL_STAGE})

_UPSERT_SQL = """
INSERT INTO hockey_prediction_runs (
    match_id,
    model_id,
    stage,
    market_probabilities)
VALUES (%s, %s, %s, CAST(%s AS JSON))
ON DUPLICATE KEY UPDATE
    market_probabilities = VALUES(market_probabilities),
    created_at = CURRENT_TIMESTAMP
"""


def write_prediction_run(
        match_id: int,
        model_id: int,
        stage: str,
        market_probs: dict[str, float],
        conn: Any | None = None) -> None:
    """Upsert the market snapshot for one stage.

    The unique key is ``(match_id, model_id, stage)``, so a later
    final run leaves the initial row in place. Saving the same stage
    again replaces the probabilities and the snapshot time. A
    supplied connection is left uncommitted for the caller.
    """
    if stage not in _ALLOWED_STAGES:
        raise ValueError("stage must be 'initial' or 'final'")
    payload = _snapshot_json(market_probs)
    owns_connection = conn is None
    context = nullcontext(conn) if conn is not None else get_db_connection()
    with context as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(_UPSERT_SQL, (
                int(match_id),
                int(model_id),
                stage,
                payload))
            if owns_connection:
                connection.commit()
        except Exception:
            if owns_connection:
                connection.rollback()
            raise
        finally:
            cursor.close()


def _snapshot_json(market_probs: dict[str, float]) -> str:
    """Return a stable JSON object of 0-100 market probabilities."""
    if not market_probs:
        raise ValueError("market_probs must not be empty")
    clean: dict[str, float] = {}
    for key, value in market_probs.items():
        clean[str(key)] = _bounded_percent(value)
    return json.dumps(clean, sort_keys=True)


def _bounded_percent(value: float) -> float:
    """Clip a rounding error, and reject a probability outside 0-100."""
    probability = float(value)
    out_of_range = probability < -1e-6 or probability > 100.0 + 1e-6
    if not math.isfinite(probability) or out_of_range:
        raise ValueError(
            "Market probability must be between 0 and 100")
    if probability < 0.0:
        return 0.0
    if probability > 100.0:
        return 100.0
    return probability
