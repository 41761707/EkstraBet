"""Configuration models for the shared ML pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.config import REPO_ROOT


def _resolve_artifact_dir(value: Any) -> Path:
    """Resolve relative artifact paths against the repository root."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


class FeatureConfig(BaseModel):
    """Feature extraction settings for a model run."""

    source_columns: list[str] = Field(default_factory=list)
    required_columns: list[str] = Field(default_factory=list)
    imputable_columns: list[str] = Field(default_factory=list)
    include_goals_as_features: bool = False
    missing_data_policy: str = "reject_required_impute_optional"
    sport_id: int | None = None
    # require/exclude_positive_xg: filtr zbioru treningowego, nie assess
    require_positive_xg: bool = False
    exclude_positive_xg: bool = False

    @model_validator(mode="after")
    def _validate_xg_flags(self) -> FeatureConfig:
        if self.require_positive_xg and self.exclude_positive_xg:
            raise ValueError(
                "require_positive_xg and exclude_positive_xg "
                "are mutually exclusive")
        return self


class TrainingConfig(BaseModel):
    """Training hyperparameters and split settings."""

    algorithm: str = "HistGradientBoostingClassifier"
    test_size: float = 0.2
    validation_size: float = 0.1
    random_state: int = 42
    calibration_method: str = "isotonic"
    class_thresholds: dict[str, float] = Field(
        default_factory=lambda: {"draw_abs_score": 0.15})


class LabelerConfig(BaseModel):
    """Weak-label formula parameters for played-better supervision."""

    temperature: float = 1.0
    draw_threshold: float = 0.15
    weights: dict[str, float] = Field(default_factory=dict)


class ModelRunConfig(BaseModel):
    """Validated runtime configuration for one model command."""

    model_name: str
    sport_id: int
    task_type: str
    artifact_dir: Path
    events: dict[str, int | str] = Field(default_factory=dict)
    feature_config: FeatureConfig
    training_config: TrainingConfig | None = None
    labeler_config: LabelerConfig = Field(default_factory=LabelerConfig)
    source_table: str = "matches"
    required_columns: list[str] = Field(default_factory=list)
    feature_builder: str
    labeler: str
    trainer: str = "SklearnTrainer"
    output_columns: list[str] = Field(default_factory=list)
    write_policy: str = "upsert"
    assessment_type: str = "PLAYED_BETTER"
    model_version: str = "1.0.0"
    config_path: Path | None = None

    @field_validator("artifact_dir", mode="before")
    @classmethod
    def _coerce_artifact_dir(cls, value: Any) -> Path:
        return _resolve_artifact_dir(value)

    @model_validator(mode="after")
    def _validate_required_fields(self) -> ModelRunConfig:
        if not self.output_columns:
            raise ValueError("output_columns must not be empty")
        if not str(self.artifact_dir):
            raise ValueError("artifact_path must not be empty")
        if not self.feature_builder:
            raise ValueError("feature_builder is required")
        if not self.labeler:
            raise ValueError("labeler is required")
        return self


class PredictionResult(BaseModel):
    """Assessment output for a single finished match."""

    match_id: int
    model_id: int
    probabilities: dict[str, float]
    final_event_key: str
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    dominance_score: float | None = None
    model_version: str = "1.0.0"
    assessment_type: str = "PLAYED_BETTER"
    sport_id: int = 1
    artifact_path: str | None = None


class TrainingReport(BaseModel):
    """Summary returned after a successful training run."""

    model_name: str
    model_version: str
    artifact_dir: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    feature_columns: list[str] = Field(default_factory=list)
    n_train: int = 0
    n_test: int = 0
    skipped_matches: int = 0


class EvaluationReport(BaseModel):
    """Summary returned after model evaluation."""

    model_name: str
    model_version: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    n_samples: int = 0
    skipped_matches: int = 0


class FutureEventsRunConfig(ModelRunConfig):
    """Configuration for result, BTTS, or Poisson future-event runs."""

    sport_id: int = 1
    task_type: Literal["result", "btts", "goals_poisson"]
    window_size: int = Field(default=8, ge=1)
    ratings: dict[str, Any] = Field(default_factory=dict)
    sequence_feature_columns: list[str] = Field(default_factory=list)
    static_feature_columns: list[str] = Field(default_factory=list)
    date_to: date | None = None
    batch_size: int = Field(default=64, ge=1)
    epochs: int = Field(default=50, ge=1)
    patience: int = Field(default=7, ge=1)
    learning_rate: float = Field(default=0.001, gt=0.0)
    lstm_units: int = Field(default=32, ge=1)
    dense_units: int = Field(default=32, ge=1)
    top_exact_scores: int = Field(default=5, ge=1)
    max_goals: int = Field(default=5, ge=1)


class MatchupInput(BaseModel):
    """Input identifying a future football matchup."""

    home_team_id: int
    away_team_id: int
    league_id: int | None = None
    season_id: int | None = None
    as_of_date: date
    match_id: int | None = None

    @field_validator("as_of_date", mode="before")
    @classmethod
    def _coerce_as_of_date(cls, value: Any) -> date:
        # game_date z MySQL ma godzinę kickoffu — bierzemy dzień kalendarzowy
        if isinstance(value, datetime):
            return value.date()
        if hasattr(value, "to_pydatetime"):
            return value.to_pydatetime().date()
        if hasattr(value, "date") and not isinstance(value, date):
            return value.date()
        return value

    @model_validator(mode="after")
    def _validate_team_pair(self) -> MatchupInput:
        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must differ")
        return self


@dataclass(frozen=True)
class SequenceBatch:
    """Dual team sequences and static matchup features."""

    X_home: np.ndarray
    X_away: np.ndarray
    X_static: np.ndarray

    def __post_init__(self) -> None:
        if self.X_home.ndim != 3 or self.X_away.ndim != 3:
            raise ValueError("Team sequence arrays must be three-dimensional")
        if self.X_static.ndim != 2:
            raise ValueError("Static feature array must be two-dimensional")
        batch_sizes = {
            self.X_home.shape[0],
            self.X_away.shape[0],
            self.X_static.shape[0]
        }
        if len(batch_sizes) != 1:
            raise ValueError("All sequence batch inputs must have equal size")


@dataclass(frozen=True)
class ResultPrediction:
    """Calibrated 1X2 probabilities from the result classifier."""

    p_home: float
    p_draw: float
    p_away: float


@dataclass(frozen=True)
class BttsPrediction:
    """Calibrated both-teams-to-score probabilities."""

    p_yes: float
    p_no: float


@dataclass(frozen=True)
class GoalsPoissonPrediction:
    """Poisson lambdas and derived score and goal markets."""

    lambda_home: float
    lambda_away: float
    score_matrix: np.ndarray
    total_buckets: dict[str, float]
    over_25: float
    under_25: float
    top_exact_scores: list[tuple[str, float]]


@dataclass(frozen=True)
class PredictionWriteRow:
    """One event probability prepared for prediction persistence."""

    match_id: int
    model_id: int
    event_id: int
    value: float
    is_final: bool = False


def load_model_config(path: Path) -> ModelRunConfig | FutureEventsRunConfig:
    """Load and validate a model config JSON file."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    if "artifact_path" in raw and "artifact_dir" not in raw:
        raw["artifact_dir"] = raw.pop("artifact_path")
    if "artifact_dir" not in raw or not raw["artifact_dir"]:
        raise ValueError("artifact_path must not be empty")
    if not raw.get("output_columns"):
        raise ValueError("output_columns must not be empty")
    future_tasks = {"result", "btts", "goals_poisson"}
    config_class = (
        FutureEventsRunConfig
        if raw.get("task_type") in future_tasks else ModelRunConfig)
    config = config_class.model_validate(raw)
    config.config_path = config_path
    # sport_id modelu musi trafić do feature buildera (filtr wierszy)
    if config.feature_config.sport_id is None:
        config.feature_config = config.feature_config.model_copy(
            update={"sport_id": config.sport_id})
    return config
