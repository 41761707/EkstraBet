"""Business logic for prediction read endpoints."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.repositories import match_repository, prediction_repository


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
        "value": float(row["value"])
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
        "value": _optional_float(row.get("value")),
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
            "value": _optional_float(row.get("value")),
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
