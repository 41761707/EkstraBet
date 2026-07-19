"""Configuration models for the shared ML pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


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
    events: dict[str, int] = Field(default_factory=dict)
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
        return Path(value)

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


def load_model_config(path: Path) -> ModelRunConfig:
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
    config = ModelRunConfig.model_validate(raw)
    config.config_path = config_path
    # sport_id modelu musi trafić do feature buildera (filtr wierszy)
    if config.feature_config.sport_id is None:
        config.feature_config = config.feature_config.model_copy(
            update={"sport_id": config.sport_id})
    return config
