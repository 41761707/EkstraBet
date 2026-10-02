"""Map and upsert future-event probabilities into prediction tables."""

from __future__ import annotations

import math
from contextlib import nullcontext
from typing import Any
from typing import Iterable

from backend.database import get_db_connection
from models.pipeline.core.config import BttsPrediction
from models.pipeline.core.config import GoalsPoissonPrediction
from models.pipeline.core.config import PredictionWriteRow
from models.pipeline.core.config import ResultPrediction
from models.pipeline.prediction.hockey_markets import HOCKEY_MARKET_FAMILIES
from models.pipeline.prediction.hockey_markets import HOCKEY_MARKET_KEYS
from models.pipeline.prediction.hockey_markets import select_hockey_finals
from models.pipeline.prediction.score_matrix import exact_score_probabilities


_PREDICTION_UPSERT_SQL = """
INSERT INTO predictions (match_id, event_id, model_id, value)
VALUES (%s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    id = LAST_INSERT_ID(id),
    value = VALUES(value)
"""

_FINAL_UPSERT_SQL = """
INSERT INTO final_predictions (predictions_id)
VALUES (%s)
ON DUPLICATE KEY UPDATE
    predictions_id = VALUES(predictions_id)
"""

_PREDICTION_ID_SQL = """
SELECT id
FROM predictions
WHERE match_id = %s AND event_id = %s AND model_id = %s
LIMIT 1
"""

_CLEAR_FAMILY_FINALS_SQL = """
DELETE fp
FROM final_predictions fp
INNER JOIN predictions p ON p.id = fp.predictions_id
WHERE p.match_id = %s
  AND p.model_id = %s
  AND p.event_id IN ({placeholders})
"""


def _db_percentage(
        value: float,
        values_are_percent: bool = False) -> float:
    probability = float(value)
    if (
            not math.isfinite(probability)
            or probability < 0.0
            or probability > 100.0):
        raise ValueError("Prediction value must be between 0 and 100")
    # Wartości NHL są już w procentach; ułamek <= 1 nie może być mnożony.
    if values_are_percent:
        return probability
    if probability <= 1.0:
        return probability * 100.0
    return probability


def _prediction_id(cursor: Any, row: PredictionWriteRow) -> int:
    prediction_id = int(cursor.lastrowid or 0)
    if prediction_id > 0:
        return prediction_id
    cursor.execute(
        _PREDICTION_ID_SQL,
        (row.match_id, row.event_id, row.model_id))
    result = cursor.fetchone()
    if result is None:
        raise RuntimeError("Upserted prediction ID could not be retrieved")
    if isinstance(result, dict):
        return int(result["id"])
    return int(result[0])


def _family_event_ids(
        rows: list[PredictionWriteRow],
        match_id: int,
        model_id: int) -> list[int]:
    return sorted({
        row.event_id
        for row in rows
        if row.match_id == match_id and row.model_id == model_id
    })


def _clear_family_finals(
        cursor: Any,
        match_id: int,
        model_id: int,
        event_ids: list[int]) -> None:
    """Remove stale finals for a match/model family before selecting new ones."""
    if not event_ids:
        return
    placeholders = ", ".join(["%s"] * len(event_ids))
    sql = _CLEAR_FAMILY_FINALS_SQL.format(placeholders=placeholders)
    cursor.execute(sql, (match_id, model_id, *event_ids))


_PREDICTION_IDS_SQL = """
SELECT id, event_id
FROM predictions
WHERE match_id = %s
  AND model_id = %s
  AND event_id IN ({placeholders})
"""


def lookup_prediction_ids(
        match_id: int,
        model_id: int,
        event_ids: list[int],
        conn: Any | None = None) -> dict[int, int]:
    """Return existing ``predictions.id`` values keyed by event id."""
    unique_ids = list(dict.fromkeys(int(event_id) for event_id in event_ids))
    if not unique_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(unique_ids))
    sql = _PREDICTION_IDS_SQL.format(placeholders=placeholders)
    connection_context = (
        nullcontext(conn) if conn is not None else get_db_connection())
    with connection_context as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(sql, (int(match_id), int(model_id), *unique_ids))
            rows = cursor.fetchall() or []
        finally:
            cursor.close()
    found: dict[int, int] = {}
    for row in rows:
        prediction_id, event_id = _prediction_id_and_event(row)
        found[event_id] = prediction_id
    return found


def _prediction_id_and_event(row: Any) -> tuple[int, int]:
    """Read ``(predictions.id, event_id)`` from a tuple or dictionary row."""
    if isinstance(row, dict):
        return int(row["id"]), int(row["event_id"])
    return int(row[0]), int(row[1])


def write_predictions(
        rows: Iterable[PredictionWriteRow],
        conn: Any | None = None,
        *,
        values_are_percent: bool = False) -> int:
    """Upsert prediction rows and selected final prediction references.

    Football callers pass probabilities on a 0-1 scale. NHL markets
    are already 0-100, so they set ``values_are_percent`` and a
    sub-percent probability is stored unchanged. A supplied
    connection is left uncommitted for the caller.
    """
    prepared_rows = list(rows)
    if not prepared_rows:
        return 0
    owns_connection = conn is None
    connection_context = (
        nullcontext(conn) if conn is not None else get_db_connection())
    with connection_context as connection:
        cursor = connection.cursor()
        try:
            prediction_ids: list[int] = []
            for row in prepared_rows:
                cursor.execute(_PREDICTION_UPSERT_SQL, (
                    row.match_id,
                    row.event_id,
                    row.model_id,
                    _db_percentage(row.value, values_are_percent)))
                prediction_ids.append(_prediction_id(cursor, row))
            cleared_families: set[tuple[int, int]] = set()
            paired = zip(prepared_rows, prediction_ids, strict=True)
            for row, prediction_id in paired:
                if not row.is_final:
                    continue
                family_key = (row.match_id, row.model_id)
                if family_key not in cleared_families:
                    # argmax może się zmienić — stary finał rodziny nie może zostać
                    event_ids = _family_event_ids(
                        prepared_rows, row.match_id, row.model_id)
                    _clear_family_finals(
                        cursor, row.match_id, row.model_id, event_ids)
                    cleared_families.add(family_key)
                cursor.execute(_FINAL_UPSERT_SQL, (prediction_id,))
            if owns_connection:
                connection.commit()
        except Exception:
            if owns_connection:
                connection.rollback()
            raise
        finally:
            cursor.close()
    return len(prepared_rows)


def _event_row(
        match_id: int,
        model_id: int,
        event_ids: dict[str, int],
        event_key: str,
        value: float,
        final_key: str | None) -> PredictionWriteRow:
    if event_key not in event_ids:
        raise KeyError(f"Missing event mapping for '{event_key}'")
    return PredictionWriteRow(
        match_id=match_id,
        model_id=model_id,
        event_id=event_ids[event_key],
        value=float(value),
        is_final=event_key == final_key)


def _highest_key(values: dict[str, float], enabled: bool) -> str | None:
    if not enabled:
        return None
    return max(values.items(), key=lambda item: item[1])[0]


def map_predictions_to_rows(
        match_id: int,
        prediction: dict[str, object],
        model_ids: dict[str, int],
        event_ids: dict[str, int],
        select_finals: bool = False) -> list[PredictionWriteRow]:
    """Map present families to rows, selecting finals within each family."""
    rows: list[PredictionWriteRow] = []
    result = prediction.get("result")
    if result is not None:
        if not isinstance(result, ResultPrediction):
            raise TypeError("Prediction output has invalid ResultPrediction")
        rows.extend(_map_result_rows(
            match_id, result, model_ids["result"], event_ids, select_finals))
    btts = prediction.get("btts")
    if btts is not None:
        if not isinstance(btts, BttsPrediction):
            raise TypeError("Prediction output has invalid BttsPrediction")
        rows.extend(_map_btts_rows(
            match_id, btts, model_ids["btts"], event_ids, select_finals))
    goals = prediction.get("goals_poisson")
    if goals is not None:
        if not isinstance(goals, GoalsPoissonPrediction):
            raise TypeError(
                "Prediction output has invalid GoalsPoissonPrediction")
        rows.extend(_map_goals_rows(
            match_id,
            goals,
            model_ids["goals_poisson"],
            event_ids,
            select_finals))
    if not rows:
        raise ValueError("Prediction output contains no supported families")
    return rows


def map_hockey_markets_to_rows(
        match_id: int,
        model_id: int,
        market_probs: dict[str, float],
        event_ids: dict[str, int],
        select_finals: bool = False) -> list[PredictionWriteRow]:
    """Map NHL market percents to rows, one final per binary family.

    Probabilities stay on the 0-100 scale. ``select_finals`` marks the
    higher side of each family; a tie keeps the first listed key.
    """
    missing = [
        key for key in HOCKEY_MARKET_KEYS if key not in market_probs]
    if missing:
        raise KeyError(f"Missing hockey market probabilities: {missing}")
    final_keys: set[str] = set()
    if select_finals:
        final_keys = set(select_hockey_finals(
            market_probs, HOCKEY_MARKET_FAMILIES))
    return [
        _event_row(
            match_id,
            model_id,
            event_ids,
            key,
            _hockey_percent(market_probs[key]),
            key if key in final_keys else None)
        for key in HOCKEY_MARKET_KEYS]


def _hockey_percent(value: float) -> float:
    """Clip a market percent that drifted off 0-100 by rounding error."""
    percent = float(value)
    out_of_range = percent < -1e-6 or percent > 100.0 + 1e-6
    if not math.isfinite(percent) or out_of_range:
        raise ValueError(
            "Hockey market probability must be between 0 and 100")
    if percent < 0.0:
        return 0.0
    if percent > 100.0:
        return 100.0
    return percent


def _map_result_rows(
        match_id: int,
        prediction: ResultPrediction,
        model_id: int,
        event_ids: dict[str, int],
        select_finals: bool) -> list[PredictionWriteRow]:
    values = {
        "result_home": prediction.p_home,
        "result_draw": prediction.p_draw,
        "result_away": prediction.p_away
    }
    final_key = _highest_key(values, select_finals)
    return [
        _event_row(
            match_id, model_id, event_ids, key, value, final_key)
        for key, value in values.items()
    ]


def _map_btts_rows(
        match_id: int,
        prediction: BttsPrediction,
        model_id: int,
        event_ids: dict[str, int],
        select_finals: bool) -> list[PredictionWriteRow]:
    values = {
        "btts_yes": prediction.p_yes,
        "btts_no": prediction.p_no
    }
    final_key = _highest_key(values, select_finals)
    return [
        _event_row(
            match_id, model_id, event_ids, key, value, final_key)
        for key, value in values.items()
    ]


def _map_goals_rows(
        match_id: int,
        prediction: GoalsPoissonPrediction,
        model_id: int,
        event_ids: dict[str, int],
        select_finals: bool) -> list[PredictionWriteRow]:
    bucket_values = {
        f"goals_{key.replace('+', '_plus')}": value
        for key, value in prediction.total_buckets.items()
    }
    ou_values = {
        "over_25": prediction.over_25,
        "under_25": prediction.under_25
    }
    exact_values = {
        f"exact:{score}": value
        for score, value in exact_score_probabilities(
            prediction.score_matrix).items()
    }
    final_keys = {
        _highest_key(bucket_values, select_finals),
        _highest_key(ou_values, select_finals),
        _highest_key(exact_values, select_finals)
    }
    all_values = {**bucket_values, **ou_values, **exact_values}
    return [
        _event_row(
            match_id,
            model_id,
            event_ids,
            key,
            value,
            key if key in final_keys else None)
        for key, value in all_values.items()
    ]
