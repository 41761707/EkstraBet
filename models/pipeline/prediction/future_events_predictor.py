"""Artifact-backed prediction for future football matchups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterable

import numpy as np

from models.pipeline.core import artifacts
from models.pipeline.core.config import BttsPrediction
from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.core.config import GoalsPoissonPrediction
from models.pipeline.core.config import MatchupInput
from models.pipeline.core.config import ResultPrediction
from models.pipeline.core.config import SequenceBatch
from models.pipeline.core.config import load_model_config
from models.pipeline.core.registry import get_feature_builder
from models.pipeline.prediction.score_matrix import derive_goal_markets
from models.pipeline.prediction.score_matrix import score_matrix_from_lambdas
from models.pipeline.prediction.score_matrix import top_exact_scores


FeatureProvider = Callable[[MatchupInput, FutureEventsRunConfig], SequenceBatch]


@dataclass(frozen=True)
class LoadedFutureModels:
    """Loaded model artifacts and optional static feature scalers."""

    result_model: Any | None = None
    btts_model: Any | None = None
    goals_model: Any | None = None
    result_scaler: Any | None = None
    btts_scaler: Any | None = None
    goals_scaler: Any | None = None


def _future_config(path: Path) -> FutureEventsRunConfig:
    config = load_model_config(path)
    if not isinstance(config, FutureEventsRunConfig):
        raise TypeError(f"Config is not a future-event config: {path}")
    return config


def _optional_future_config(
        path: Path | None) -> FutureEventsRunConfig | None:
    if path is None:
        return None
    return _future_config(path)


def _require_at_least_one_config(
        result_config: FutureEventsRunConfig | None,
        btts_config: FutureEventsRunConfig | None,
        goals_config: FutureEventsRunConfig | None) -> None:
    if result_config is None and btts_config is None and goals_config is None:
        raise ValueError(
            "At least one of result, BTTS, or goals config is required")


def load_future_models(
        result_config: FutureEventsRunConfig | None,
        btts_config: FutureEventsRunConfig | None,
        goals_config: FutureEventsRunConfig | None) -> LoadedFutureModels:
    """Load Keras artifacts for the provided future-event families."""
    _require_at_least_one_config(result_config, btts_config, goals_config)
    return LoadedFutureModels(
        result_model=(
            artifacts.load_keras_model_artifact(result_config.artifact_dir)
            if result_config is not None else None),
        btts_model=(
            artifacts.load_keras_model_artifact(btts_config.artifact_dir)
            if btts_config is not None else None),
        goals_model=(
            artifacts.load_keras_model_artifact(goals_config.artifact_dir)
            if goals_config is not None else None),
        result_scaler=(
            artifacts.load_scaler_artifact(result_config.artifact_dir)
            if result_config is not None else None),
        btts_scaler=(
            artifacts.load_scaler_artifact(btts_config.artifact_dir)
            if btts_config is not None else None),
        goals_scaler=(
            artifacts.load_scaler_artifact(goals_config.artifact_dir)
            if goals_config is not None else None))


def _default_feature_provider(
        matchup: MatchupInput,
        config: FutureEventsRunConfig) -> SequenceBatch:
    builder = get_feature_builder(config.feature_builder)
    method = getattr(builder, "build_matchup_batch", None)
    if method is None:
        method = getattr(builder, "build_prediction_batch", None)
    if method is None:
        raise TypeError(
            f"{type(builder).__name__} must implement build_matchup_batch")
    batch = method(matchup, config)
    if not isinstance(batch, SequenceBatch):
        raise TypeError("Future feature builder did not return SequenceBatch")
    if batch.X_home.shape[0] != 1:
        raise ValueError("Pair prediction requires a one-row SequenceBatch")
    return batch


def _scaled_batch(batch: SequenceBatch, scaler: Any | None) -> SequenceBatch:
    if scaler is None:
        return batch
    return SequenceBatch(
        X_home=batch.X_home,
        X_away=batch.X_away,
        X_static=scaler.transform(batch.X_static))


def _predict_array(
        model: Any,
        batch: SequenceBatch) -> np.ndarray:
    values = model.predict(
        [batch.X_home, batch.X_away, batch.X_static],
        verbose=0)
    return np.asarray(values, dtype=float)


def _normalized_probabilities(
        values: np.ndarray,
        expected_size: int) -> np.ndarray:
    row = np.asarray(values, dtype=float).reshape(-1)
    if row.size != expected_size:
        raise ValueError(
            f"Expected {expected_size} probabilities, got {row.size}")
    row = np.clip(row, 0.0, None)
    total = float(row.sum())
    if total <= 0.0:
        raise ValueError("Model returned no positive probability mass")
    return row / total


class FutureEventsPredictor:
    """Load and run selected result, BTTS, and Poisson artifact families."""

    def __init__(
            self,
            result_config: FutureEventsRunConfig | None = None,
            btts_config: FutureEventsRunConfig | None = None,
            goals_config: FutureEventsRunConfig | None = None,
            models: LoadedFutureModels | None = None,
            feature_provider: FeatureProvider | None = None) -> None:
        _require_at_least_one_config(
            result_config, btts_config, goals_config)
        self.result_config = result_config
        self.btts_config = btts_config
        self.goals_config = goals_config
        self.models = models or load_future_models(
            result_config, btts_config, goals_config)
        self.feature_provider = feature_provider or _default_feature_provider

    @classmethod
    def from_config_paths(
            cls,
            result_config_path: Path | None = None,
            btts_config_path: Path | None = None,
            goals_config_path: Path | None = None) -> FutureEventsPredictor:
        """Construct a predictor for any non-empty subset of families."""
        return cls(
            _optional_future_config(result_config_path),
            _optional_future_config(btts_config_path),
            _optional_future_config(goals_config_path))

    def predict_pair(
            self,
            matchup: MatchupInput) -> dict[str, object]:
        """Predict configured result, BTTS, and/or goals families."""
        payload: dict[str, object] = {}
        if self.result_config is not None:
            payload["result"] = self._predict_result(matchup)
        if self.btts_config is not None:
            payload["btts"] = self._predict_btts(matchup)
        if self.goals_config is not None:
            payload["goals_poisson"] = self._predict_goals(matchup)
        return payload

    def predict_batch(
            self,
            matchups: Iterable[MatchupInput]
    ) -> list[dict[str, object]]:
        """Predict multiple pairs while reusing all loaded artifacts."""
        return [self.predict_pair(matchup) for matchup in matchups]

    def _predict_result(self, matchup: MatchupInput) -> ResultPrediction:
        if self.result_config is None or self.models.result_model is None:
            raise RuntimeError("Result model is not configured")
        batch = self.feature_provider(matchup, self.result_config)
        values = _normalized_probabilities(
            _predict_array(
                self.models.result_model,
                _scaled_batch(batch, self.models.result_scaler))[0],
            3)
        return ResultPrediction(
            p_home=float(values[0]),
            p_draw=float(values[1]),
            p_away=float(values[2]))

    def _predict_btts(self, matchup: MatchupInput) -> BttsPrediction:
        if self.btts_config is None or self.models.btts_model is None:
            raise RuntimeError("BTTS model is not configured")
        batch = self.feature_provider(matchup, self.btts_config)
        values = _normalized_probabilities(
            _predict_array(
                self.models.btts_model,
                _scaled_batch(batch, self.models.btts_scaler))[0],
            2)
        return BttsPrediction(
            p_yes=float(values[1]),
            p_no=float(values[0]))

    def _predict_goals(
            self, matchup: MatchupInput) -> GoalsPoissonPrediction:
        if self.goals_config is None or self.models.goals_model is None:
            raise RuntimeError("Goals model is not configured")
        batch = self.feature_provider(matchup, self.goals_config)
        rates = _predict_array(
            self.models.goals_model,
            _scaled_batch(batch, self.models.goals_scaler))[0]
        return _goals_prediction(rates, self.goals_config)


def _goals_prediction(
        rates: np.ndarray,
        config: FutureEventsRunConfig) -> GoalsPoissonPrediction:
    flattened = np.asarray(rates, dtype=float).reshape(-1)
    if flattened.size != 2:
        raise ValueError("Poisson model must output two lambdas")
    lambda_home = max(float(flattened[0]), 0.0)
    lambda_away = max(float(flattened[1]), 0.0)
    matrix = score_matrix_from_lambdas(
        lambda_home, lambda_away, config.max_goals)
    markets = derive_goal_markets(
        matrix, lambda_home, lambda_away)
    return GoalsPoissonPrediction(
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        score_matrix=matrix,
        total_buckets=markets["total_buckets"],
        over_25=float(markets["over_25"]),
        under_25=float(markets["under_25"]),
        top_exact_scores=top_exact_scores(
            matrix,
            config.top_exact_scores,
            config.max_goals))


def predict_pair(
        matchup: MatchupInput,
        models: FutureEventsPredictor) -> dict[str, object]:
    """Module-level pair prediction API from the technical design."""
    return models.predict_pair(matchup)


def predict_batch(
        matchups: Iterable[MatchupInput],
        models: FutureEventsPredictor) -> list[dict[str, object]]:
    """Module-level batch prediction API reusing loaded artifacts."""
    return models.predict_batch(matchups)
