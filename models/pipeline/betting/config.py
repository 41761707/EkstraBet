"""Validated training and selection configs for the betting meta-model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_validator
from pydantic import model_validator


_FRACTION_SUM_TOLERANCE = 1e-9
CalibrationMethod = Literal["sigmoid", "isotonic"]


class BettingTrainingConfig(BaseModel):
    """Chronological split and trainer settings. No stake policy."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False)

    model_name: str
    algorithm: Literal["LogisticRegression"]
    class_weight: Literal["balanced"]
    calibration_methods: tuple[CalibrationMethod, ...]
    random_state: int
    train_fraction: float
    calibration_fraction: float
    test_fraction: float

    @field_validator("model_name")
    @classmethod
    def _validate_model_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model_name must not be empty")
        return value

    @field_validator("calibration_methods")
    @classmethod
    def _validate_calibration_methods(
            cls,
            value: tuple[CalibrationMethod, ...]
            ) -> tuple[CalibrationMethod, ...]:
        if not value:
            raise ValueError("calibration_methods must not be empty")
        if len(value) != len(set(value)):
            raise ValueError("calibration_methods must be unique")
        return value

    @field_validator("random_state", mode="before")
    @classmethod
    def _validate_random_state(cls, value: object) -> object:
        _reject_bool(value)
        if isinstance(value, int) and value < 0:
            raise ValueError("random_state must be >= 0")
        return value

    @field_validator(
        "train_fraction",
        "calibration_fraction",
        "test_fraction",
        mode="before")
    @classmethod
    def _validate_fraction(cls, value: object) -> object:
        _reject_bool(value)
        if isinstance(value, (int, float)) and (
                value <= 0.0 or value >= 1.0):
            raise ValueError("split fractions must be between 0 and 1")
        return value

    @model_validator(mode="after")
    def _validate_fraction_sum(self) -> BettingTrainingConfig:
        total = (
            self.train_fraction
            + self.calibration_fraction
            + self.test_fraction)
        if abs(total - 1.0) > _FRACTION_SUM_TOLERANCE:
            raise ValueError("split fractions must sum to 1")
        return self


class BettingStrategyConfig(BaseModel):
    """Selection threshold, model pool, and report gate.

    The gate is read when a later task decides whether the artifact is
    ready. Calibration is the maximum absolute reliability error,
    ``max_reliability_error``, and ROI is ``min_roi``. ``max_brier``
    stays a separate proper-score cap. This config does not size a
    stake.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False)

    probability_threshold: float
    football_sport_name: str
    excluded_model_names: tuple[str, ...]
    max_brier: float
    # Brier nie mierzy kalibracji. Próg reliability jest osobną bramką.
    max_reliability_error: float
    min_roi: float

    @field_validator("probability_threshold", mode="before")
    @classmethod
    def _validate_threshold(cls, value: object) -> object:
        _reject_bool(value)
        if isinstance(value, (int, float)) and (
                value < 0.0 or value > 1.0):
            raise ValueError(
                "probability_threshold must be between 0 and 1")
        return value

    @field_validator("football_sport_name")
    @classmethod
    def _validate_sport_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("football_sport_name must not be empty")
        return stripped

    @field_validator("excluded_model_names")
    @classmethod
    def _validate_excluded_names(
            cls,
            value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("excluded_model_names must not be empty")
        if not _names_are_non_empty(value):
            raise ValueError(
                "excluded_model_names must be non-empty strings")
        stripped = tuple(name.strip() for name in value)
        if len(stripped) != len(set(stripped)):
            raise ValueError("excluded_model_names must be unique")
        return stripped

    @field_validator("max_brier", mode="before")
    @classmethod
    def _validate_max_brier(cls, value: object) -> object:
        _reject_bool(value)
        if isinstance(value, (int, float)) and (
                value <= 0.0 or value > 1.0):
            raise ValueError("max_brier must be in the interval (0, 1]")
        return value

    @field_validator("max_reliability_error", mode="before")
    @classmethod
    def _validate_max_reliability_error(cls, value: object) -> object:
        _reject_bool(value)
        if isinstance(value, (int, float)) and (
                value <= 0.0 or value > 1.0):
            raise ValueError(
                "max_reliability_error must be in the interval (0, 1]")
        return value

    @field_validator("min_roi", mode="before")
    @classmethod
    def _validate_min_roi(cls, value: object) -> object:
        _reject_bool(value)
        if isinstance(value, (int, float)) and (
                value != value or value in (float("inf"), float("-inf"))):
            raise ValueError("min_roi must be finite")
        if isinstance(value, (int, float)) and value < -1.0:
            raise ValueError("min_roi must be >= -1")
        return value


def load_betting_training_config(path: Path) -> BettingTrainingConfig:
    """Load a training config and reject unknown or missing fields."""
    return BettingTrainingConfig.model_validate(_read_json_object(path))


def load_betting_strategy_config(path: Path) -> BettingStrategyConfig:
    """Load a selection config and reject unknown or missing fields."""
    return BettingStrategyConfig.model_validate(_read_json_object(path))


def _reject_bool(value: object) -> None:
    """Reject JSON booleans before they coerce to 0 or 1."""
    # bool jest podklasą int, więc Pydantic zamieniłby go na liczbę
    if isinstance(value, bool):
        raise ValueError("value must be a number, not a boolean")


def _names_are_non_empty(names: tuple[str, ...]) -> bool:
    """Return whether every name is a non-blank string."""
    for name in names:
        if not isinstance(name, str) or not name.strip():
            return False
    return True


def _read_json_object(path: Path) -> object:
    """Read one JSON value from a config file."""
    return json.loads(path.read_text(encoding="utf-8"))
