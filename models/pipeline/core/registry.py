"""Component registry and model metadata resolution."""

from __future__ import annotations

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
    from models.pipeline.features import football_match_stats 
    from models.pipeline.labels import football_played_better
    from models.pipeline.training import sklearn_trainer


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
    for event_key, event_id in config.events.items():
        if not event_key or event_id is None:
            raise RegistryError(
                f"Invalid event mapping: {event_key!r} -> {event_id!r}")
