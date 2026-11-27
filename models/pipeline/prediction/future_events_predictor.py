"""Artifact-backed prediction for future football matchups."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Protocol

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
from models.pipeline.data.shared_history_context import FeatureSignature
from models.pipeline.data.shared_history_context import SharedHistoryContext
from models.pipeline.data.shared_history_context import feature_signature
from models.pipeline.prediction.score_matrix import derive_goal_markets
from models.pipeline.prediction.score_matrix import score_matrix_from_lambdas
from models.pipeline.prediction.score_matrix import top_exact_scores
from models.pipeline.training.calibration import apply_calibration
from models.pipeline.training.model_inputs import model_inputs


# zgodne z SeasonSimulationConfig.inference_batch_size (bez importu simulation)
_DEFAULT_GOAL_RATE_BATCH_SIZE = 512


class FeatureProvider(Protocol):
    """Callable that builds one-row features for a matchup."""

    def __call__(
            self,
            matchup: MatchupInput,
            config: FutureEventsRunConfig,
            context: SharedHistoryContext | None = None
            ) -> SequenceBatch:
        ...


CacheKey = tuple[tuple[Any, ...], FeatureSignature]
FeatureCache = dict[CacheKey, SequenceBatch]
ProgressCallback = Callable[[int, int, MatchupInput], None]


@dataclass(frozen=True)
class LoadedFutureModels:
    """Loaded artifacts, scalers, league vocabularies and calibration."""

    result_model: Any | None = None
    btts_model: Any | None = None
    goals_model: Any | None = None
    result_scaler: Any | None = None
    btts_scaler: Any | None = None
    goals_scaler: Any | None = None
    result_league_vocab: list[int] | None = None
    btts_league_vocab: list[int] | None = None
    goals_league_vocab: list[int] | None = None
    result_meta: dict[str, Any] | None = None
    btts_meta: dict[str, Any] | None = None
    goals_meta: dict[str, Any] | None = None
    result_calibrator: Any | None = None
    btts_calibrator: Any | None = None
    goals_calibrator: Any | None = None


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


def _league_vocab_for(
        config: FutureEventsRunConfig | None) -> list[int] | None:
    """Load the league vocabulary when the family uses an embedding."""
    if config is None or config.league_embedding_dim <= 0:
        return None
    # Brak pliku przy embeddingu jest błędem artefaktu, nie cichym V2.
    return artifacts.load_league_vocab(config.artifact_dir)


def _family_calibration(
        config: FutureEventsRunConfig | None
) -> tuple[dict[str, Any] | None, Any | None]:
    """Load meta and, for BTTS isotonic, the calibrator file.

    ``calibration == none`` still returns meta so the artifact is
    visible, but prediction ignores it and keeps the raw network.
    """
    if config is None:
        return None, None
    meta = artifacts.load_meta(config.artifact_dir)
    if config.calibration == "none":
        return meta, None
    if (
            meta.get("calibration") != config.calibration
            or meta.get("temperature") is None):
        raise ValueError(
            "calibration artifact does not match the config "
            f"in {config.artifact_dir}")
    calibrator = None
    if config.calibration == "temperature_isotonic":
        calibrator = artifacts.load_calibrator(
            config.artifact_dir, required=True)
    return meta, calibrator


def load_future_models(
        result_config: FutureEventsRunConfig | None,
        btts_config: FutureEventsRunConfig | None,
        goals_config: FutureEventsRunConfig | None) -> LoadedFutureModels:
    """Load Keras artifacts for the provided future-event families."""
    _require_at_least_one_config(result_config, btts_config, goals_config)
    result_meta, result_calibrator = _family_calibration(result_config)
    btts_meta, btts_calibrator = _family_calibration(btts_config)
    goals_meta, goals_calibrator = _family_calibration(goals_config)
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
            if goals_config is not None else None),
        result_league_vocab=_league_vocab_for(result_config),
        btts_league_vocab=_league_vocab_for(btts_config),
        goals_league_vocab=_league_vocab_for(goals_config),
        result_meta=result_meta,
        btts_meta=btts_meta,
        goals_meta=goals_meta,
        result_calibrator=result_calibrator,
        btts_calibrator=btts_calibrator,
        goals_calibrator=goals_calibrator)


def matchup_cache_key(matchup: MatchupInput) -> tuple[Any, ...]:
    """Return a hashable identity for one matchup in the feature cache."""
    return (
        matchup.home_team_id,
        matchup.away_team_id,
        matchup.league_id,
        matchup.season_id,
        matchup.as_of_date,
        matchup.match_id)


def _accepts_history_context(target: Any) -> bool:
    """Return whether a callable accepts a ``context`` keyword argument."""
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return False
    if "context" in signature.parameters:
        return True
    for item in signature.parameters.values():
        if item.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False


def _call_with_optional_context(
        target: Any,
        matchup: MatchupInput,
        config: FutureEventsRunConfig,
        context: SharedHistoryContext | None) -> Any:
    """Invoke a provider or builder without assuming a context parameter."""
    if _accepts_history_context(target):
        return target(matchup, config, context=context)
    return target(matchup, config)


def _default_feature_provider(
        matchup: MatchupInput,
        config: FutureEventsRunConfig,
        context: SharedHistoryContext | None = None) -> SequenceBatch:
    builder = get_feature_builder(config.feature_builder)
    method = getattr(builder, "build_matchup_batch", None)
    if method is None:
        method = getattr(builder, "build_prediction_batch", None)
    if method is None:
        raise TypeError(
            f"{type(builder).__name__} must implement build_matchup_batch")
    batch = _call_with_optional_context(
        method, matchup, config, context)
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
        X_static=scaler.transform(batch.X_static),
        league_ids=batch.league_ids)


def _predict_array(
        model: Any,
        batch: SequenceBatch,
        config: FutureEventsRunConfig,
        league_vocab: list[int] | None = None) -> np.ndarray:
    values = model.predict(
        model_inputs(batch, config, league_vocab),
        verbose=0)
    return np.asarray(values, dtype=float)


def _slice_sequence_batch(
        batch: SequenceBatch,
        start: int,
        end: int) -> SequenceBatch:
    league_ids = None
    if batch.league_ids is not None:
        league_ids = batch.league_ids[start:end]
    return SequenceBatch(
        X_home=batch.X_home[start:end],
        X_away=batch.X_away[start:end],
        X_static=batch.X_static[start:end],
        league_ids=league_ids)


def _reshape_goal_rates(values: np.ndarray, batch_size: int) -> np.ndarray:
    rates = np.asarray(values, dtype=float)
    if rates.ndim == 1:
        rates = rates.reshape(1, -1)
    if rates.shape != (batch_size, 2):
        raise ValueError(
            f"Poisson model must output shape ({batch_size}, 2), "
            f"got {rates.shape}")
    if not np.all(np.isfinite(rates)):
        raise ValueError("Poisson model returned non-finite lambdas")
    # ujemne lambdy traktujemy jak w ścieżce pair prediction
    return np.maximum(rates, 0.0)


def _family_probabilities(
        values: np.ndarray,
        config: FutureEventsRunConfig,
        meta: dict[str, Any] | None,
        calibrator: Any | None,
        expected_size: int) -> np.ndarray:
    """Normalize one row, applying the artifact calibration when set."""
    raw = np.asarray(values, dtype=float).reshape(-1)
    if config.calibration == "none":
        calibrated = raw
    else:
        calibrated = apply_calibration(raw, meta or {}, calibrator)
    return _normalized_probabilities(calibrated, expected_size)


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
            matchup: MatchupInput,
            *,
            context: SharedHistoryContext | None = None,
            feature_cache: FeatureCache | None = None) -> dict[str, object]:
        """Predict configured result, BTTS, and/or goals families."""
        cache = feature_cache if feature_cache is not None else {}
        payload: dict[str, object] = {}
        if self.result_config is not None:
            payload["result"] = self._predict_result(
                matchup, cache=cache, context=context)
        if self.btts_config is not None:
            payload["btts"] = self._predict_btts(
                matchup, cache=cache, context=context)
        if self.goals_config is not None:
            payload["goals_poisson"] = self._predict_goals(
                matchup, cache=cache, context=context)
        return payload

    def predict_batch(
            self,
            matchups: Iterable[MatchupInput],
            *,
            context: SharedHistoryContext | None = None,
            progress: ProgressCallback | None = None
            ) -> list[dict[str, object]]:
        """Predict multiple pairs while reusing artifacts and feature batches."""
        matchup_list = list(matchups)
        total = len(matchup_list)
        feature_cache: FeatureCache = {}
        results: list[dict[str, object]] = []
        for index, matchup in enumerate(matchup_list, start=1):
            results.append(self.predict_pair(
                matchup, context=context, feature_cache=feature_cache))
            if progress is not None:
                progress(index, total, matchup)
        return results

    def _batch_for(
            self,
            matchup: MatchupInput,
            config: FutureEventsRunConfig,
            *,
            cache: FeatureCache,
            context: SharedHistoryContext | None) -> SequenceBatch:
        """Return a SequenceBatch, reusing one only for the same signature."""
        key = (matchup_cache_key(matchup), feature_signature(config))
        cached = cache.get(key)
        if cached is not None:
            return cached
        batch = _call_with_optional_context(
            self.feature_provider, matchup, config, context)
        cache[key] = batch
        return batch

    def predict_goal_rates(
            self,
            batch: SequenceBatch,
            batch_size: int = _DEFAULT_GOAL_RATE_BATCH_SIZE) -> np.ndarray:
        """Infer Poisson lambdas for a ready SequenceBatch (no DB access).

        Applies the goals scaler and runs one or chunked ``model.predict``
        calls. Returns shape ``(B, 2)`` with ``lambda_home``, ``lambda_away``.
        """
        if self.goals_config is None or self.models.goals_model is None:
            raise RuntimeError("Goals model is not configured")
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        scaled = _scaled_batch(batch, self.models.goals_scaler)
        total = scaled.X_home.shape[0]
        if total == 0:
            return np.zeros((0, 2), dtype=float)
        if total <= batch_size:
            return _reshape_goal_rates(
                _predict_array(
                    self.models.goals_model,
                    scaled,
                    self.goals_config,
                    self.models.goals_league_vocab),
                total)
        chunks: list[np.ndarray] = []
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            chunk = _slice_sequence_batch(scaled, start, end)
            chunk_rates = _reshape_goal_rates(
                _predict_array(
                    self.models.goals_model,
                    chunk,
                    self.goals_config,
                    self.models.goals_league_vocab),
                end - start)
            chunks.append(chunk_rates)
        return np.concatenate(chunks, axis=0)

    def _predict_result(
            self,
            matchup: MatchupInput,
            *,
            cache: FeatureCache,
            context: SharedHistoryContext | None) -> ResultPrediction:
        if self.result_config is None or self.models.result_model is None:
            raise RuntimeError("Result model is not configured")
        batch = self._batch_for(
            matchup, self.result_config, cache=cache, context=context)
        values = _family_probabilities(
            _predict_array(
                self.models.result_model,
                _scaled_batch(batch, self.models.result_scaler),
                self.result_config,
                self.models.result_league_vocab)[0],
            self.result_config,
            self.models.result_meta,
            self.models.result_calibrator,
            3)
        return ResultPrediction(
            p_home=float(values[0]),
            p_draw=float(values[1]),
            p_away=float(values[2]))

    def _predict_btts(
            self,
            matchup: MatchupInput,
            *,
            cache: FeatureCache,
            context: SharedHistoryContext | None) -> BttsPrediction:
        if self.btts_config is None or self.models.btts_model is None:
            raise RuntimeError("BTTS model is not configured")
        batch = self._batch_for(
            matchup, self.btts_config, cache=cache, context=context)
        values = _family_probabilities(
            _predict_array(
                self.models.btts_model,
                _scaled_batch(batch, self.models.btts_scaler),
                self.btts_config,
                self.models.btts_league_vocab)[0],
            self.btts_config,
            self.models.btts_meta,
            self.models.btts_calibrator,
            2)
        return BttsPrediction(
            p_yes=float(values[1]),
            p_no=float(values[0]))

    def _predict_goals(
            self,
            matchup: MatchupInput,
            *,
            cache: FeatureCache,
            context: SharedHistoryContext | None) -> GoalsPoissonPrediction:
        if self.goals_config is None:
            raise RuntimeError("Goals model is not configured")
        batch = self._batch_for(
            matchup, self.goals_config, cache=cache, context=context)
        rates = self.predict_goal_rates(batch)[0]
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
        models: FutureEventsPredictor,
        *,
        context: SharedHistoryContext | None = None,
        feature_cache: FeatureCache | None = None) -> dict[str, object]:
    """Module-level pair prediction API from the technical design."""
    return models.predict_pair(
        matchup, context=context, feature_cache=feature_cache)


def predict_batch(
        matchups: Iterable[MatchupInput],
        models: FutureEventsPredictor,
        *,
        context: SharedHistoryContext | None = None,
        progress: ProgressCallback | None = None
        ) -> list[dict[str, object]]:
    """Module-level batch prediction API reusing loaded artifacts."""
    return models.predict_batch(
        matchups, context=context, progress=progress)
