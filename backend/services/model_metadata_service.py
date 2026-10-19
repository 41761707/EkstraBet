"""Business logic for prediction model metadata endpoints.

This service exposes database metadata about prediction models. It does not
load or run ML artifacts from the repository ``models/`` directory.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.repositories import model_metadata_repository


def _optional_str(value: object) -> str | None:
    """Convert nullable values to strings."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value)


def get_event_families(sport_id: int | None = None) -> list[dict[str, Any]]:
    """Return event families with optional sport filter."""
    frame = model_metadata_repository.fetch_event_families(sport_id)
    families = []
    for _, row in frame.iterrows():
        families.append({
            "id": int(row["id"]),
            "sport_id": int(row["sport_id"]),
            "name": str(row["name"]),
            "sport_name": _optional_str(row.get("sport_name")),
            "description": _optional_str(row.get("description"))
        })
    return families


def get_sport_market_families(sport_id: int) -> list[dict[str, Any]]:
    """Return event families of a sport with their events, in catalog order."""
    frame = model_metadata_repository.fetch_sport_family_events(sport_id)
    families: list[dict[str, Any]] = []
    current_id: int | None = None
    current: dict[str, Any] | None = None
    for _, row in frame.iterrows():
        family_id = int(row["family_id"])
        if family_id != current_id:
            current = {
                "id": family_id,
                "name": str(row["family_name"]),
                "description": _optional_str(row.get("description")),
                "events": []
            }
            families.append(current)
            current_id = family_id
        event_id = row.get("event_id")
        if current is None or event_id is None or pd.isna(event_id):
            continue
        event_name = row.get("event_name")
        current["events"].append({
            "event_id": int(event_id),
            "name": "" if event_name is None or pd.isna(event_name) else str(
                event_name)
        })
    return families


def get_family_events(family_id: int) -> list[dict[str, Any]]:
    """Return events mapped to an event family."""
    frame = model_metadata_repository.fetch_family_events(family_id)
    events = []
    for _, row in frame.iterrows():
        events.append({
            "id": int(row["id"]),
            "event_id": int(row["event_id"]),
            "event_family_id": int(row["event_family_id"]),
            "event_name": _optional_str(row.get("event_name")),
            "family_name": _optional_str(row.get("family_name"))
        })
    return events


def get_models() -> list[dict[str, Any]]:
    """Return all prediction models."""
    frame = model_metadata_repository.fetch_models()
    models = []
    for _, row in frame.iterrows():
        models.append({
            "id": int(row["id"]),
            "name": str(row["name"]),
            "active": int(row["active"]),
            "sport_id": int(row["sport_id"]),
            "sport_name": _optional_str(row.get("sport_name"))
        })
    return models


def get_model_details(model_id: int) -> dict[str, Any] | None:
    """Return model details or None when the model does not exist."""
    frame = model_metadata_repository.fetch_model_by_id(model_id)
    if frame.empty:
        return None

    row = frame.iloc[0]
    families_frame = model_metadata_repository.fetch_model_event_families(
        model_id)
    events_frame = model_metadata_repository.fetch_model_supported_events(
        model_id)

    event_families = []
    for _, family_row in families_frame.iterrows():
        event_families.append({
            "id": int(family_row["id"]),
            "sport_id": int(family_row["sport_id"]),
            "name": str(family_row["name"])
        })

    supported_events = []
    for _, event_row in events_frame.iterrows():
        supported_events.append({
            "id": int(event_row["id"]),
            "name": str(event_row["name"]),
            "family_id": int(event_row["family_id"]),
            "family_name": str(event_row["family_name"])
        })

    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "active": int(row["active"]),
        "sport_id": int(row["sport_id"]),
        "sport_name": _optional_str(row.get("sport_name")),
        "event_families": event_families,
        "supported_events": supported_events,
        "total_events": len(supported_events)
    }
