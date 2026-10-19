"""Business logic for prediction read endpoints."""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from backend.repositories import match_repository, prediction_repository
from backend.services.probability_service import to_unit_probability

# mapowanie event_id z konfiguracji football_*_v* (wynik / BTTS / gole)
_RESULT_HOME_EVENT_ID = 1
_RESULT_DRAW_EVENT_ID = 2
_RESULT_AWAY_EVENT_ID = 3
_BTTS_YES_EVENT_ID = 6
_BTTS_NO_EVENT_ID = 172
_OVER_25_EVENT_ID = 8
_UNDER_25_EVENT_ID = 12
_GOAL_BUCKET_EVENT_IDS = {
    174: "0",
    175: "1",
    176: "2",
    177: "3",
    178: "4",
    179: "5",
    180: "6+"
}
_TOP_EXACT_SCORES = 5
_EXACT_SCORE_NAME_RE = re.compile(r"^(?:\d+|5\+):(?:\d+|5\+)$")
_HOCKEY_EXACT_MIN_ID = 270
_HOCKEY_EXACT_MAX_ID = 333
_HOCKEY_EXACT_LIMIT = 5
_HOCKEY_OT_SUFFIX = " (OT/SO)"
_HOME_GOAL_BUCKETS = (
    (252, "0"),
    (253, "1"),
    (254, "2"),
    (255, "3"),
    (256, "4"),
    (257, "5+"))
_AWAY_GOAL_BUCKETS = (
    (258, "0"),
    (259, "1"),
    (260, "2"),
    (261, "3"),
    (262, "4"),
    (263, "5+"))
_TOTAL_GOAL_BUCKETS = (
    (264, "≤3"),
    (265, "4"),
    (266, "5"),
    (267, "6"),
    (268, "7"),
    (269, "8+"))


def _optional_int(value: object) -> int | None:
    """Convert nullable numeric values to integers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _optional_float(value: object) -> float | None:
    """Convert nullable numeric values to floats."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _map_event_family(row: pd.Series) -> dict[str, Any] | None:
    """Map event family columns when present on a dataframe row."""
    family_id = _optional_int(row.get("event_family_id"))
    family_name = row.get("event_family_name")
    if family_id is None or family_name is None or pd.isna(family_name):
        return None
    return {
        "id": family_id,
        "name": str(family_name)
    }


def _map_prediction_value(value: object) -> float | None:
    """Map DB percentage to API unit probability [0, 1]."""
    raw_value = _optional_float(value)
    if raw_value is None:
        return None
    return to_unit_probability(raw_value)


def _map_prediction_row(row: pd.Series) -> dict[str, Any]:
    """Map a raw prediction dataframe row."""
    return {
        "id": int(row["id"]),
        "match_id": int(row["match_id"]),
        "event_id": int(row["event_id"]),
        "event_name": str(row["event_name"]),
        "event_family": _map_event_family(row),
        "model_id": int(row["model_id"]),
        "model_name": (
            str(row["model_name"])
            if pd.notna(row.get("model_name")) else None),
        "value": to_unit_probability(float(row["value"]))
    }


def _map_final_prediction_row(row: pd.Series) -> dict[str, Any]:
    """Map a final prediction dataframe row."""
    outcome = row.get("outcome")
    model_name = row.get("model_name")
    return {
        "prediction_id": int(row["prediction_id"]),
        "event_id": int(row["event_id"]),
        "event_name": str(row["event_name"]),
        "event_family": _map_event_family(row),
        "model_id": int(row["model_id"]),
        "model_name": str(model_name) if pd.notna(model_name) else None,
        "value": _map_prediction_value(row.get("value")),
        "outcome": (
            int(outcome)
            if outcome is not None and pd.notna(outcome) else None)
    }


def search_predictions(
    match_id: int | None = None,
    event_id: int | None = None,
    model_ids: list[int] | None = None,
    page: int = 1,
    page_size: int = 50) -> dict[str, Any]:
    """Return paginated predictions with applied filters."""
    frame, total = prediction_repository.search_predictions(
        match_id=match_id,
        event_id=event_id,
        model_ids=model_ids,
        page=page,
        page_size=page_size)
    predictions = [
        _map_prediction_row(row)
        for _, row in frame.iterrows()
    ]
    return {
        "predictions": predictions,
        "total_count": total,
        "filters_applied": {
            "match_id": match_id,
            "event_id": event_id,
            "model_ids": model_ids,
            "page": page,
            "page_size": page_size
        }
    }


def get_team_predictions(
    team_id: int,
    season_id: int) -> dict[str, Any] | None:
    """Return team predictions or None when team/season is missing."""
    if not prediction_repository.team_exists(team_id):
        return None
    if not prediction_repository.season_exists(season_id):
        return None

    frame = prediction_repository.fetch_team_final_predictions(
        team_id,
        season_id)
    predictions = []
    for _, row in frame.iterrows():
        outcome = row.get("outcome")
        predictions.append({
            "event_id": int(row["event_id"]),
            "event_name": str(row["event_name"]),
            "event_family": _map_event_family(row),
            "match_id": int(row["match_id"]),
            "model_id": int(row["model_id"]),
            "model_name": (
                str(row["model_name"])
                if pd.notna(row.get("model_name")) else None),
            "value": _map_prediction_value(row.get("value")),
            "outcome": (
                int(outcome)
                if outcome is not None and pd.notna(outcome) else None)
        })
    return {
        "team_predictions": predictions,
        "total_count": len(predictions),
        "team_id": team_id,
        "season_id": season_id
    }


def get_match_predictions(
    match_id: int,
    model_ids: list[int] | None = None) -> dict[str, Any] | None:
    """Return match predictions or None when the match does not exist."""
    if not match_repository.match_exists(match_id):
        return None

    frame = prediction_repository.fetch_match_final_predictions(
        match_id,
        model_ids=model_ids)
    predictions = [
        _map_final_prediction_row(row)
        for _, row in frame.iterrows()
    ]
    return {
        "match_predictions": predictions,
        "total_count": len(predictions),
        "match_id": match_id
    }


def get_match_final_predictions(
    match_id: int,
    model_ids: list[int] | None = None) -> list[dict[str, Any]]:
    """Return final predictions for embedding in match details."""
    frame = prediction_repository.fetch_match_final_predictions(
        match_id,
        model_ids=model_ids)
    return [
        _map_final_prediction_row(row)
        for _, row in frame.iterrows()
    ]


def _dedupe_latest_by_event(
        frame: pd.DataFrame) -> dict[int, dict[str, Any]]:
    """Keep the newest prediction row per event_id."""
    by_event: dict[int, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        event_id = int(row["event_id"])
        if event_id in by_event:
            continue
        by_event[event_id] = {
            "event_id": event_id,
            "event_name": str(row["event_name"]),
            "value": to_unit_probability(float(row["value"]))
        }
    return by_event


def _probability_for(
        by_event: dict[int, dict[str, Any]],
        event_id: int) -> float | None:
    row = by_event.get(event_id)
    if row is None:
        return None
    return float(row["value"])


def _build_top_exact_scores(
        by_event: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for row in by_event.values():
        event_name = str(row["event_name"]).strip()
        if not _EXACT_SCORE_NAME_RE.match(event_name):
            continue
        scores.append({
            "score": event_name,
            "probability": float(row["value"])
        })
    scores.sort(key=lambda item: item["probability"], reverse=True)
    return scores[:_TOP_EXACT_SCORES]


def map_market_predictions_to_analysis(
        frame: pd.DataFrame) -> dict[str, Any] | None:
    """Map stored market rows into PredictionPreviewResponse shape."""
    if frame.empty:
        return None

    by_event = _dedupe_latest_by_event(frame)
    p_home = _probability_for(by_event, _RESULT_HOME_EVENT_ID)
    p_draw = _probability_for(by_event, _RESULT_DRAW_EVENT_ID)
    p_away = _probability_for(by_event, _RESULT_AWAY_EVENT_ID)
    # bez pełnego 1X2 nie ma sensu budować analizy jak na simulate
    if p_home is None or p_draw is None or p_away is None:
        return None

    p_yes = _probability_for(by_event, _BTTS_YES_EVENT_ID) or 0.0
    p_no = _probability_for(by_event, _BTTS_NO_EVENT_ID) or 0.0
    over_25 = _probability_for(by_event, _OVER_25_EVENT_ID) or 0.0
    under_25 = _probability_for(by_event, _UNDER_25_EVENT_ID) or 0.0
    total_buckets = {
        label: (_probability_for(by_event, event_id) or 0.0)
        for event_id, label in _GOAL_BUCKET_EVENT_IDS.items()
    }

    return {
        "result": {
            "p_home": p_home,
            "p_draw": p_draw,
            "p_away": p_away
        },
        "btts": {
            "p_yes": p_yes,
            "p_no": p_no
        },
        "goals": {
            # lambdy nie są persystowane w predictions — UI ukryje stopkę
            "lambda_home": 0.0,
            "lambda_away": 0.0,
            "total_buckets": total_buckets,
            "over_25": over_25,
            "under_25": under_25,
            "top_exact_scores": _build_top_exact_scores(by_event)
        }
    }


def get_match_prediction_analysis(
    match_id: int,
    model_ids: list[int] | None = None) -> dict[str, Any] | None:
    """Return chart-ready analysis from stored market predictions."""
    frame = prediction_repository.fetch_match_market_predictions(
        match_id,
        model_ids=model_ids)
    return map_market_predictions_to_analysis(frame)


def get_hockey_score_charts(match_id: int) -> list[dict[str, Any]]:
    """Return goal buckets and top scores stored for one match.

    Probabilities are on the 0-1 scale. A series missing any of its
    six ids is returned empty. A model with no full series and fewer
    than five exact scores is omitted.
    """
    frame = prediction_repository.fetch_match_market_predictions(match_id)
    return _map_hockey_score_charts(frame)


def _map_hockey_score_charts(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    grouped = _rows_by_model(frame)
    charts: list[dict[str, Any]] = []
    for model_id in sorted(grouped):
        chart = _chart_for_model(model_id, grouped[model_id])
        if chart is not None:
            charts.append(chart)
    return charts


def _rows_by_model(
        frame: pd.DataFrame) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for record in frame.to_dict(orient="records"):
        model_id = int(record["model_id"])
        grouped.setdefault(model_id, []).append(record)
    return grouped


def _chart_for_model(
        model_id: int,
        rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    by_event = _first_row_by_event(rows)
    home_goals = _bucket_series(by_event, _HOME_GOAL_BUCKETS)
    away_goals = _bucket_series(by_event, _AWAY_GOAL_BUCKETS)
    total_goals = _bucket_series(by_event, _TOTAL_GOAL_BUCKETS)
    exact_scores = _exact_score_chances(by_event)
    has_series = bool(home_goals or away_goals or total_goals)
    if not has_series and len(exact_scores) < _HOCKEY_EXACT_LIMIT:
        return None
    return {
        "model_id": model_id,
        "model_name": _model_name(rows, model_id),
        "home_goals": home_goals,
        "away_goals": away_goals,
        "total_goals": total_goals,
        "exact_scores": exact_scores}


def _first_row_by_event(
        rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    by_event: dict[int, dict[str, Any]] = {}
    for row in rows:
        event_id = int(row["event_id"])
        if event_id not in by_event:
            by_event[event_id] = row
    return by_event


def _bucket_series(
        by_event: dict[int, dict[str, Any]],
        spec: tuple[tuple[int, str], ...]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for event_id, label in spec:
        row = by_event.get(event_id)
        if row is None or not _finite_number(row.get("value")):
            return []
        series.append({
            "label": label,
            "probability": to_unit_probability(float(row["value"]))})
    return series


def _exact_score_chances(
        by_event: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    chances: list[dict[str, Any]] = []
    for event_id, row in by_event.items():
        if event_id < _HOCKEY_EXACT_MIN_ID or event_id > _HOCKEY_EXACT_MAX_ID:
            continue
        if not _finite_number(row.get("value")):
            continue
        chances.append({
            "score": _exact_score_label(row.get("event_name")),
            "probability": to_unit_probability(float(row["value"]))})
    chances.sort(key=lambda item: float(item["probability"]), reverse=True)
    return chances[:_HOCKEY_EXACT_LIMIT]


def _exact_score_label(name: object) -> str:
    text = "" if name is None or _is_missing(name) else str(name).strip()
    if text.endswith(_HOCKEY_OT_SUFFIX):
        return text[: -len(_HOCKEY_OT_SUFFIX)]
    return text


def _model_name(rows: list[dict[str, Any]], model_id: int) -> str:
    for row in rows:
        name = row.get("model_name")
        if _is_missing(name):
            continue
        text = str(name).strip()
        if text:
            return text
    return f"Model {model_id}"


def _finite_number(value: object) -> bool:
    if _is_missing(value) or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, float) and pd.isna(value)