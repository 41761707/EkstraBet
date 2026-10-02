"""Four Poisson regressors for NHL skater props.

The trees are the same ``HistGradientBoostingRegressor(loss="poisson")``
fit used by ``HockeyGbmTrainer``. Targets are shots, goals, assists
and points. There is no overtime model: each mean becomes
``P(X > line)`` from a Poisson.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any

import numpy as np
import pandas as pd

from models.pipeline.core import artifacts
from models.pipeline.core.config import EvaluationReport
from models.pipeline.core.config import ModelRunConfig
from models.pipeline.core.config import TrainingReport
from models.pipeline.core.registry import register_trainer
from models.pipeline.data.hockey_history_repository import fetch_hockey_matches
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_match_rosters)
from models.pipeline.data.hockey_history_repository import (
    fetch_hockey_player_stats)
from models.pipeline.data.hockey_history_repository import fetch_team_arenas
from models.pipeline.features.hockey.player_features import (
    PLAYER_PROP_FEATURE_COLUMNS)
from models.pipeline.features.hockey.player_features import (
    build_hockey_player_features)
from models.pipeline.labels.hockey_player_props import TARGET_COLUMNS
from models.pipeline.labels.hockey_player_props import HockeyPlayerPropsLabeler
from models.pipeline.training.hockey_gbm_trainer import HockeyGbmSettings
from models.pipeline.training.hockey_gbm_trainer import fit_poisson_regressor
from models.pipeline.training.hockey_gbm_trainer import (
    gbm_settings_from_config)
from models.pipeline.training.hockey_gbm_trainer import (
    season_sample_weights)
from models.pipeline.training.trainer import Trainer


logger = logging.getLogger(__name__)

_RATE_FLOOR = 1e-3
_RATE_CAP = 40.0
TRAINER_NAME = "HockeyPlayerPropsTrainer"


@dataclass(frozen=True)
class PlayerPropsParams:
    """League, holdout season and the short-season weights."""

    league_id: int = 45
    test_season: int = 12
    low_weight_seasons: dict[int, float] | None = None

    def weights(self) -> dict[int, float]:
        """Return the season weights, defaulting 2020/21 to one half."""
        if self.low_weight_seasons is None:
            return {4: 0.5}
        return dict(self.low_weight_seasons)


@dataclass
class HockeyPlayerPropsModel:
    """One Poisson regressor for each skater counting stat."""

    models: dict[str, Any]
    feature_columns: list[str]

    def predict_rates(self, frame: pd.DataFrame) -> dict[str, np.ndarray]:
        """Return means for shots, goals, assists and points.

        The points mean is at least goals plus assists, so a point
        probability cannot fall below a goal or an assist.
        """
        matrix = _feature_matrix(frame, self.feature_columns)
        predicted: dict[str, np.ndarray] = {}
        for target in TARGET_COLUMNS:
            if target not in self.models:
                raise KeyError(f"Props model is missing target '{target}'")
            raw = self.models[target].predict(matrix)
            predicted[target] = np.clip(raw, _RATE_FLOOR, _RATE_CAP)
        return align_point_rates(predicted)


def align_point_rates(
        rates: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Keep the points mean at least as large as goals plus assists.

    A point is a goal or an assist. Separate Poisson means can
    otherwise make P(goal) or P(assist) larger than P(point).
    """
    goals = np.asarray(rates["goals"], dtype=float)
    assists = np.asarray(rates["assists"], dtype=float)
    points = np.asarray(rates["points"], dtype=float)
    aligned = dict(rates)
    # Suma, nie max(gol, asysta): punkt to gol albo asysta.
    aligned["points"] = np.maximum(points, goals + assists)
    return aligned


class _RatingsView:
    """Adapter so ``gbm_settings_from_config`` can read ``props.gbm``."""

    def __init__(self, ratings: dict[str, Any]) -> None:
        self.ratings = ratings


def props_settings_from_config(
        config: ModelRunConfig) -> tuple[HockeyGbmSettings, PlayerPropsParams]:
    """Read tree size and the holdout season from the config file."""
    raw = _config_object(config)
    props = raw.get("props", {})
    if not isinstance(props, dict):
        raise ValueError("props must be an object")
    gbm = props.get("gbm", {})
    if not isinstance(gbm, dict):
        raise ValueError("props.gbm must be an object")
    settings = gbm_settings_from_config(_RatingsView({"gbm": gbm}))
    return settings, PlayerPropsParams(
        league_id=int(props.get("league_id", 45)),
        test_season=int(props.get("test_season", 12)),
        low_weight_seasons=_low_weights(props))


def fit_player_prop_models(
        frame: pd.DataFrame,
        settings: HockeyGbmSettings,
        sample_weight: np.ndarray | None = None) -> HockeyPlayerPropsModel:
    """Fit four Poisson trees on a frame that already has labels."""
    labels = HockeyPlayerPropsLabeler().build_labels(frame)
    _require_finite_labels(labels)
    matrix = _feature_matrix(frame, PLAYER_PROP_FEATURE_COLUMNS)
    weights = sample_weight
    if weights is None:
        weights = np.ones(len(frame), dtype=float)
    if len(weights) != len(frame):
        raise ValueError("sample_weight length must match the frame")
    models = {
        target: fit_poisson_regressor(
            matrix,
            labels[target].to_numpy(dtype=float),
            weights,
            settings)
        for target in TARGET_COLUMNS}
    return HockeyPlayerPropsModel(
        models=models,
        feature_columns=list(PLAYER_PROP_FEATURE_COLUMNS))


def score_player_props_holdout(
        frame: pd.DataFrame,
        settings: HockeyGbmSettings,
        params: PlayerPropsParams) -> dict[str, Any]:
    """Fit before the test season and score mean absolute error there."""
    train, test = _split_season(frame, params.test_season)
    weights = season_sample_weights(train["season"], params.weights())
    model = fit_player_prop_models(train, settings, weights)
    return _holdout_metrics(model, train, test, params.test_season)


def load_player_prop_frame(league_id: int) -> pd.DataFrame:
    """Load history and build one row per skater appearance."""
    logger.info("Loading hockey player-prop history for league %s", league_id)
    frame = build_hockey_player_features(
        fetch_hockey_matches(league_id),
        fetch_hockey_match_rosters(league_id),
        fetch_hockey_player_stats(league_id),
        fetch_team_arenas())
    if frame.empty:
        raise ValueError("No skater appearances were loaded")
    logger.info("Built %s hockey skater rows", len(frame))
    return frame


@register_trainer(TRAINER_NAME)
class HockeyPlayerPropsTrainer(Trainer):
    """Train HOCKEY_PLAYER_PROPS_V1 and score the holdout season."""

    def train(self, config: ModelRunConfig) -> TrainingReport:
        """Fit the production artifact on every finished skater row."""
        started = datetime.now(timezone.utc)
        settings, params = props_settings_from_config(config)
        frame = load_player_prop_frame(params.league_id)
        metrics = score_player_props_holdout(frame, settings, params)
        weights = season_sample_weights(frame["season"], params.weights())
        model = fit_player_prop_models(frame, settings, weights)
        _save_run(config, model, metrics, started)
        return TrainingReport(
            model_name=config.model_name,
            model_version=config.model_version,
            artifact_dir=str(config.artifact_dir),
            metrics=metrics,
            feature_columns=list(model.feature_columns),
            n_train=int(metrics["n_train"]),
            n_test=int(metrics["n_test"]),
            skipped_matches=0)

    def evaluate(self, config: ModelRunConfig) -> EvaluationReport:
        """Recompute the pre-season holdout without writing artifacts."""
        settings, params = props_settings_from_config(config)
        frame = load_player_prop_frame(params.league_id)
        metrics = score_player_props_holdout(frame, settings, params)
        return EvaluationReport(
            model_name=config.model_name,
            model_version=config.model_version,
            metrics=metrics,
            n_samples=int(metrics["n_test"]),
            skipped_matches=0)

    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series,
            config: ModelRunConfig,
            sample_weight: pd.Series | None = None) -> HockeyPlayerPropsModel:
        """Fit the four regressors. ``labels`` must carry the four targets."""
        settings, _params = props_settings_from_config(config)
        frame = _with_labels(features, labels)
        weights = None
        if sample_weight is not None:
            weights = sample_weight.to_numpy(dtype=float)
        return fit_player_prop_models(frame, settings, weights)


def _holdout_metrics(
        model: HockeyPlayerPropsModel,
        train: pd.DataFrame,
        test: pd.DataFrame,
        test_season: int) -> dict[str, Any]:
    predicted = model.predict_rates(test)
    metrics: dict[str, Any] = {
        "test_season": int(test_season),
        "n_train": int(len(train)),
        "n_test": int(len(test))}
    for target in TARGET_COLUMNS:
        actual = test[target].to_numpy(dtype=float)
        rate = predicted[target]
        metrics[f"{target}_mae"] = float(np.mean(np.abs(actual - rate)))
        metrics[f"{target}_mean"] = float(np.mean(actual))
    return metrics


def _split_season(
        frame: pd.DataFrame,
        test_season: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "season" not in frame.columns:
        raise KeyError("Player-prop frame requires season")
    seasons = frame["season"].astype(int)
    train = frame.loc[seasons != int(test_season)]
    test = frame.loc[seasons == int(test_season)]
    if train.empty:
        raise ValueError("No skater rows before the test season")
    if test.empty:
        raise ValueError(
            f"No skater rows for test season {test_season}")
    return train, test


def _with_labels(
        features: pd.DataFrame,
        labels: pd.Series | pd.DataFrame) -> pd.DataFrame:
    if isinstance(labels, pd.DataFrame):
        goals = labels
    else:
        goals = labels.to_frame()
    missing = [
        column for column in TARGET_COLUMNS if column not in goals.columns]
    if missing:
        raise KeyError(f"Missing player-prop labels: {missing}")
    frame = features.copy()
    for column in TARGET_COLUMNS:
        frame[column] = goals[column].to_numpy()
    return frame


def _require_finite_labels(labels: pd.DataFrame) -> None:
    for column in TARGET_COLUMNS:
        values = labels[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(
                f"Player-prop target '{column}' must be finite and >= 0")


def _feature_matrix(
        frame: pd.DataFrame,
        feature_columns: list[str]) -> pd.DataFrame:
    missing = [
        column for column in feature_columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing player-prop features: {missing}")
    matrix = frame.loc[:, feature_columns].apply(
        pd.to_numeric, errors="coerce")
    return matrix.replace([np.inf, -np.inf], np.nan)


def _config_object(config: ModelRunConfig) -> dict[str, Any]:
    path = config.config_path
    if path is None or not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Player-prop config must be a JSON object")
    return raw


def _low_weights(props: dict[str, Any]) -> dict[int, float]:
    nested = props.get("low_weight_seasons", {"4": 0.5})
    if not isinstance(nested, dict):
        raise ValueError("low_weight_seasons must be an object")
    return {
        int(season): float(weight)
        for season, weight in nested.items()}


def _save_run(
        config: ModelRunConfig,
        model: HockeyPlayerPropsModel,
        metrics: dict[str, Any],
        started: datetime) -> None:
    artifacts.save_model_artifact(config.artifact_dir, model)
    artifacts.save_feature_columns(
        config.artifact_dir, list(model.feature_columns))
    artifacts.save_metrics(config.artifact_dir, metrics)
    artifacts.save_meta(config.artifact_dir, {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "task_type": config.task_type,
        "trainer": TRAINER_NAME,
        "feature_builder": config.feature_builder,
        "labeler": config.labeler,
        "targets": list(TARGET_COLUMNS),
        "lines_per_skater": 7,
        "loss": "poisson_hist_gradient_boosting",
        "training_started_at": started.isoformat(),
        "training_finished_at": datetime.now(timezone.utc).isoformat()})
