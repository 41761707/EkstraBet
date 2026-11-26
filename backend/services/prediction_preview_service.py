"""Adapter between the API and the optional future-events ML pipeline."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import is_dataclass
from datetime import date
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any
from typing import Mapping


# Kolejność zgodna z FutureEventsPredictor.from_config_paths.
_CHAMPION_CONFIG_SLOTS = ("result", "btts", "goals_poisson")


class PredictionPreviewHistoryError(Exception):
    """Raised when a team has too little history for a prediction."""


def _load_predictor_module() -> ModuleType:
    """Load the heavy prediction module only for an enabled preview request."""
    return import_module(
        "models.pipeline.prediction.future_events_predictor")


def _matchup_input_class(module: ModuleType) -> type[Any]:
    input_class = getattr(module, "MatchupInput", None)
    if input_class is not None:
        return input_class

    config_module = import_module("models.pipeline.core.config")
    return getattr(config_module, "MatchupInput")


def _champion_config_paths() -> tuple[Path | None, Path | None, Path | None]:
    """Return champion configs for the result, BTTS and goals slots.

    A missing champion leaves that slot empty. Two champions of one
    task type, or a task type outside those three slots, raise
    LineupError.
    """
    # Import dopiero przy podglądzie, tak jak ciężki moduł predykcji.
    from models.pipeline.core.model_lineup import LineupError
    from models.pipeline.core.model_lineup import resolve_lineup

    paths: list[Path | None] = [None, None, None]
    for entry in resolve_lineup().champion_entries():
        task_type = entry.config.task_type
        if task_type not in _CHAMPION_CONFIG_SLOTS:
            raise LineupError(
                f"Unsupported task_type {task_type!r} "
                f"for champion {entry.model_name}")
        index = _CHAMPION_CONFIG_SLOTS.index(task_type)
        if paths[index] is not None:
            raise LineupError(
                f"Multiple champions for task_type {task_type!r}")
        paths[index] = entry.config_path
    return (paths[0], paths[1], paths[2])


@lru_cache
def _load_predictor() -> Any:
    module = _load_predictor_module()
    predictor_class = getattr(module, "FutureEventsPredictor")
    return predictor_class.from_config_paths(*_champion_config_paths())


def _to_plain_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return {
            key: _to_plain_value(item)
            for key, item in value.model_dump().items()
        }
    if is_dataclass(value):
        return _to_plain_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _to_plain_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain_value(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            key: _to_plain_value(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _is_history_error(exc: Exception) -> bool:
    error_name = type(exc).__name__.lower()
    message = str(exc).lower()
    return (
        "history" in error_name
        or "sequence" in error_name
        or "history" in message
        or "historical match" in message
        or "sequence" in message
    )


def _normalize_top_scores(goals: dict[str, Any]) -> None:
    top_scores = goals.get("top_exact_scores")
    if isinstance(top_scores, Mapping):
        goals["top_exact_scores"] = [
            {"score": str(score), "probability": probability}
            for score, probability in top_scores.items()
        ]
        return
    if not isinstance(top_scores, list):
        return

    normalized = []
    for item in top_scores:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            normalized.append({
                "score": str(item[0]),
                "probability": item[1]
            })
        elif isinstance(item, (list, tuple)) and len(item) == 3:
            normalized.append({
                "score": f"{item[0]}:{item[1]}",
                "probability": item[2]
            })
        elif (
            isinstance(item, dict)
            and "score" not in item
            and {"home_goals", "away_goals", "probability"} <= item.keys()
        ):
            normalized.append({
                "score": f"{item['home_goals']}:{item['away_goals']}",
                "probability": item["probability"]
            })
        else:
            normalized.append(item)
    goals["top_exact_scores"] = normalized


def _normalize_prediction_sections(payload: dict[str, Any]) -> None:
    aliases = {
        "result": ("result_prediction",),
        "btts": ("btts_prediction",),
        "goals": ("goals_prediction", "goals_poisson")
    }
    for target, sources in aliases.items():
        if target in payload:
            continue
        for source in sources:
            if source in payload:
                payload[target] = payload.pop(source)
                break


def preview_prediction(
    home_team_id: int,
    away_team_id: int,
    league_id: int | None,
    as_of_date: date
) -> dict[str, Any]:
    """Run pair inference and return a serialization-friendly payload."""
    module = _load_predictor_module()
    matchup_input = _matchup_input_class(module)(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        league_id=league_id,
        season_id=None,
        as_of_date=as_of_date,
        match_id=None)

    try:
        prediction = _load_predictor().predict_pair(matchup_input)
    except Exception as exc:
        if _is_history_error(exc):
            raise PredictionPreviewHistoryError(
                "Insufficient match history for one or both teams") from exc
        raise

    payload = _to_plain_value(prediction)
    if not isinstance(payload, dict):
        raise TypeError("Prediction pipeline returned an invalid payload")
    _normalize_prediction_sections(payload)
    goals = payload.get("goals")
    if isinstance(goals, dict):
        _normalize_top_scores(goals)
    return payload
