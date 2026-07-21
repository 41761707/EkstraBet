"""Component registry and model metadata resolution."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable

import pandas as pd

from backend.database import get_db_connection
from models.pipeline.core.config import ModelRunConfig


class RegistryError(Exception):
    """Raised when a registered component or model cannot be resolved."""


_FEATURE_BUILDERS: dict[str, Callable[..., Any]] = {}
_LABELERS: dict[str, Callable[..., Any]] = {}
_TRAINERS: dict[str, Callable[..., Any]] = {}


def register_feature_builder(name: str) -> Callable[[type], type]:
    """Decorator that registers a feature builder class by name."""

    def decorator(cls: type) -> type:
        _FEATURE_BUILDERS[name] = cls
        return cls

    return decorator


def register_labeler(name: str) -> Callable[[type], type]:
    """Decorator that registers a labeler class by name."""

    def decorator(cls: type) -> type:
        _LABELERS[name] = cls
        return cls

    return decorator


def register_trainer(name: str) -> Callable[[type], type]:
    """Decorator that registers a trainer class by name."""

    def decorator(cls: type) -> type:
        _TRAINERS[name] = cls
        return cls

    return decorator


def _ensure_components_loaded() -> None:
    """Import concrete components so registration decorators run."""
    module_names = [
        "models.pipeline.features.football_match_stats",
        "models.pipeline.features.sequence_builder",
        "models.pipeline.labels.football_played_better",
        "models.pipeline.labels.football_result",
        "models.pipeline.labels.football_btts",
        "models.pipeline.labels.football_goals_poisson",
        "models.pipeline.training.lstm_trainer",
        "models.pipeline.training.poisson_trainer",
        "models.pipeline.training.sklearn_trainer"
    ]
    for module_name in module_names:
        import_module(module_name)


def get_feature_builder(name: str) -> Any:
    """Return a feature builder instance for the given registry name."""
    _ensure_components_loaded()
    if name not in _FEATURE_BUILDERS:
        raise RegistryError(f"Unknown feature builder: {name}")
    return _FEATURE_BUILDERS[name]()


def get_labeler(name: str, config: ModelRunConfig | None = None) -> Any:
    """Return a labeler instance for the given registry name."""
    _ensure_components_loaded()
    if name not in _LABELERS:
        raise RegistryError(f"Unknown labeler: {name}")
    cls = _LABELERS[name]
    if config is None:
        return cls()
    return cls(config.labeler_config)


def get_trainer(name: str) -> Any:
    """Return a trainer instance for the given registry name."""
    _ensure_components_loaded()
    if name not in _TRAINERS:
        raise RegistryError(f"Unknown trainer: {name}")
    return _TRAINERS[name]()


def resolve_model_id(model_name: str) -> int:
    """Resolve active model_id from the models table by name."""
    query = """
        SELECT id
        FROM models
        WHERE name = %s AND active = 1
        LIMIT 1
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(model_name,))
    if frame.empty:
        raise RegistryError(
            f"Model '{model_name}' is missing or inactive in models table")
    return int(frame.iloc[0]["id"])


def validate_events(config: ModelRunConfig) -> None:
    """Validate optional event mappings when a model declares them."""
    if not config.events:
        return
    for event_key, event_reference in config.events.items():
        if not event_key or event_reference is None:
            raise RegistryError(
                f"Invalid event mapping: "
                f"{event_key!r} -> {event_reference!r}")
        if isinstance(event_reference, str) and not event_reference.strip():
            raise RegistryError(
                f"Invalid event mapping: "
                f"{event_key!r} -> {event_reference!r}")


def resolve_event_id(
        event_reference: int | str,
        connection: Any | None = None) -> int:
    """Resolve an event ID, accepting either an ID or an exact event name."""
    if isinstance(event_reference, int):
        return event_reference
    query = "SELECT id FROM events WHERE name = %s ORDER BY id LIMIT 1"
    if connection is not None:
        return _resolve_event_with_connection(
            connection, query, event_reference)
    with get_db_connection() as conn:
        return _resolve_event_with_connection(conn, query, event_reference)


def _resolve_event_with_connection(
        connection: Any,
        query: str,
        event_name: str) -> int:
    cursor = connection.cursor()
    try:
        cursor.execute(query, (event_name,))
        row = cursor.fetchone()
    finally:
        cursor.close()
    if row is None:
        raise RegistryError(f"Event '{event_name}' is missing")
    if isinstance(row, dict):
        return int(row["id"])
    return int(row[0])


def resolve_event_map(
        events: dict[str, int | str],
        connection: Any | None = None) -> dict[str, int]:
    """Resolve every configured event reference to its database ID."""
    return {
        key: resolve_event_id(reference, connection)
        for key, reference in events.items()
    }
