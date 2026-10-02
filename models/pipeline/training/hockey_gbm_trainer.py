"""Gradient-boosted NHL goal rates and an overtime home-win model.

Two Poisson regressors predict regulation goals. A logistic model
predicts who wins overtime given a tie. Trees are fit before the
validation window. ``tie_inflation`` is chosen only on that window.
The holdout is one fit before the test season. Activation compares
that moneyline log loss with a ratings model fit once on the same
cut. A lower loss turns the artifact on. Walk-forward ratings stay
in the report and do not decide. The saved artifact is refit on all
finished matches with the same split.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.config import REPO_ROOT
from models.pipeline.core import artifacts
from models.pipeline.core.config import EvaluationReport
from models.pipeline.core.config import ModelRunConfig
from models.pipeline.core.config import TrainingReport
from models.pipeline.core.registry import register_trainer
from models.pipeline.features.hockey.early_season import EarlySeasonConfig
from models.pipeline.features.hockey.ratings import HockeyRatingsConfig
from models.pipeline.features.hockey.team_features import (
    HOCKEY_GBM_FEATURE_COLUMNS)
from models.pipeline.features.hockey.team_features import (
    load_hockey_team_feature_frame)
from models.pipeline.prediction.hockey_markets import HockeyScoreDistribution
from models.pipeline.prediction.hockey_markets import build_score_distribution
from models.pipeline.prediction.hockey_markets import derive_hockey_markets
from models.pipeline.training.hockey_ratings_trainer import (
    HockeyDixonColesParams)
from models.pipeline.training.hockey_ratings_trainer import (
    calibrate_tie_inflation)
from models.pipeline.training.hockey_ratings_trainer import (
    hockey_params_from_config)
from models.pipeline.training.trainer import Trainer


logger = logging.getLogger(__name__)

_RATE_FLOOR = 1e-3
_PROBABILITY_FLOOR = 1e-6
_MIN_VALIDATION_ROWS = 30
_SINGLE_FIT_BASELINE_KEY = "single_fit_moneyline_log_loss"
_BASELINE_METRICS = (
    REPO_ROOT / "models" / "artifacts" / "release"
    / "hockey_ratings_poisson_v1" / "metrics.json")


@dataclass(frozen=True)
class HockeyGbmSettings:
    """Tree size and the random seed for both Poisson regressors."""

    learning_rate: float = 0.06
    max_iter: int = 200
    max_depth: int = 6
    min_samples_leaf: int = 20
    l2_regularization: float = 0.1
    random_state: int = 42

    def __post_init__(self) -> None:
        if not 0.0 < self.learning_rate < 1.0:
            raise ValueError("learning_rate must be in (0, 1)")
        if self.max_iter < 1:
            raise ValueError("max_iter must be positive")
        if self.max_depth < 1:
            raise ValueError("max_depth must be positive")
        if self.min_samples_leaf < 1:
            raise ValueError("min_samples_leaf must be positive")
        if self.l2_regularization < 0.0:
            raise ValueError("l2_regularization cannot be negative")


@dataclass
class HockeyGoalsGbmModel:
    """Poisson goal rates, per-match overtime probability and tie inflation."""

    home_model: HistGradientBoostingRegressor
    away_model: HistGradientBoostingRegressor
    overtime_model: Pipeline
    feature_columns: list[str]
    tie_inflation: float
    fallback_p_ot_home: float
    max_goals: int
    overtime_ready: bool = True

    def score_distribution(
            self,
            features: pd.Series) -> HockeyScoreDistribution:
        """Return the final-score grid for one pre-match feature row."""
        home, away, p_ot = self.predict_rates(features.to_frame().T)
        return build_score_distribution(
            float(home[0]),
            float(away[0]),
            self.tie_inflation,
            float(p_ot[0]),
            self.max_goals)

    def predict_rates(
            self,
            frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return regulation lambdas and P(home wins overtime | tie)."""
        matrix = _feature_matrix(frame, self.feature_columns)
        home = np.clip(
            self.home_model.predict(matrix), _RATE_FLOOR, self.max_goals)
        away = np.clip(
            self.away_model.predict(matrix), _RATE_FLOOR, self.max_goals)
        if self.overtime_ready:
            overtime = _overtime_probability(
                self.overtime_model, matrix, self.fallback_p_ot_home)
        else:
            overtime = np.full(len(matrix), self.fallback_p_ot_home)
        return home, away, overtime


def gbm_settings_from_config(config: ModelRunConfig) -> HockeyGbmSettings:
    """Read tree hyperparameters from ``ratings.gbm``."""
    raw = getattr(config, "ratings", None)
    if not isinstance(raw, dict):
        raw = {}
    nested = raw.get("gbm", {})
    if not isinstance(nested, dict):
        raise ValueError("ratings.gbm must be an object")
    return HockeyGbmSettings(
        learning_rate=float(nested.get("learning_rate", 0.06)),
        max_iter=int(nested.get("max_iter", 200)),
        max_depth=int(nested.get("max_depth", 6)),
        min_samples_leaf=int(nested.get("min_samples_leaf", 20)),
        l2_regularization=float(nested.get("l2_regularization", 0.1)),
        random_state=int(nested.get("random_state", 42)))


def ratings_config_from_params(
        params: HockeyDixonColesParams) -> HockeyRatingsConfig:
    """Early-season multiplier used while the feature table is built."""
    return HockeyRatingsConfig(early_season=EarlySeasonConfig(
        games=params.early_season.games,
        boost=params.early_season.boost))


def fit_hockey_gbm(
        frame: pd.DataFrame,
        feature_columns: list[str],
        settings: HockeyGbmSettings,
        params: HockeyDixonColesParams,
        as_of: pd.Timestamp) -> HockeyGoalsGbmModel:
    """Fit rates before the validation window and calibrate there.

    Trees do not see the last ``validation_days``. The diagonal
    multiplier is chosen only on predictions for that window.
    """
    prior, validation = _prior_and_validation(frame, as_of, params)
    train = _rows_before_validation(prior, validation)
    weights = _season_weights(train["season"], params.low_weight_seasons)
    matrix = _feature_matrix(train, feature_columns)
    home_model = _fit_poisson(
        matrix, train["goals_home"].to_numpy(dtype=float), weights, settings)
    away_model = _fit_poisson(
        matrix, train["goals_away"].to_numpy(dtype=float), weights, settings)
    overtime, fallback, overtime_ready = _fit_overtime(
        matrix, train, settings)
    lambda_home = np.clip(
        home_model.predict(_feature_matrix(validation, feature_columns)),
        _RATE_FLOOR,
        params.max_goals)
    lambda_away = np.clip(
        away_model.predict(_feature_matrix(validation, feature_columns)),
        _RATE_FLOOR,
        params.max_goals)
    inflation = calibrate_tie_inflation(
        lambda_home,
        lambda_away,
        validation["goals_home"].to_numpy(),
        validation["goals_away"].to_numpy(),
        params)
    return HockeyGoalsGbmModel(
        home_model=home_model,
        away_model=away_model,
        overtime_model=overtime,
        feature_columns=list(feature_columns),
        tie_inflation=float(inflation),
        fallback_p_ot_home=fallback,
        max_goals=params.max_goals,
        overtime_ready=overtime_ready)


def score_gbm_holdout(
        frame: pd.DataFrame,
        feature_columns: list[str],
        settings: HockeyGbmSettings,
        params: HockeyDixonColesParams) -> dict[str, Any]:
    """Fit before the test season and score that season once."""
    finished = _finished_rows(frame)
    test = finished.loc[
        finished["season"] == params.test_season].sort_values(
        ["game_date", "match_id"])
    if test.empty:
        raise ValueError(
            f"No finished matches for test season {params.test_season}")
    as_of = pd.Timestamp(test["game_date"].min())
    model = fit_hockey_gbm(
        finished, feature_columns, settings, params, as_of)
    metrics = _metrics_from_scores(model, test, finished, as_of, params)
    metrics["holdout_tie_inflation"] = float(model.tie_inflation)
    metrics["holdout_fallback_p_ot_home"] = float(
        model.fallback_p_ot_home)
    return metrics


@register_trainer("HockeyGbmTrainer")
class HockeyGbmTrainer(Trainer):
    """Train HOCKEY_GOALS_GBM_V1 and compare it with the ratings model."""

    def train(self, config: ModelRunConfig) -> TrainingReport:
        """Fit the production artifact and write the season holdout."""
        started = datetime.now(timezone.utc)
        settings = gbm_settings_from_config(config)
        params = hockey_params_from_config(config)
        frame = _load_frame(params)
        metrics = score_gbm_holdout(
            frame, HOCKEY_GBM_FEATURE_COLUMNS, settings, params)
        as_of = pd.Timestamp(frame["game_date"].max()) + pd.Timedelta(days=1)
        model = fit_hockey_gbm(
            _finished_rows(frame),
            HOCKEY_GBM_FEATURE_COLUMNS,
            settings,
            params,
            as_of)
        metrics["production_tie_inflation"] = float(model.tie_inflation)
        metrics["production_fallback_p_ot_home"] = float(
            model.fallback_p_ot_home)
        comparison = _baseline_comparison(metrics["moneyline_log_loss"])
        metrics.update(comparison)
        _save_run(config, model, metrics, started)
        _log_comparison(config.model_name, metrics)
        return TrainingReport(
            model_name=config.model_name,
            model_version=config.model_version,
            artifact_dir=str(config.artifact_dir),
            metrics=metrics,
            feature_columns=list(HOCKEY_GBM_FEATURE_COLUMNS),
            n_train=int(metrics["n_train"]),
            n_test=int(metrics["n_scored"]),
            skipped_matches=int(metrics["n_skipped"]))

    def evaluate(self, config: ModelRunConfig) -> EvaluationReport:
        """Recompute the pre-season holdout without writing artifacts."""
        settings = gbm_settings_from_config(config)
        params = hockey_params_from_config(config)
        frame = _load_frame(params)
        metrics = score_gbm_holdout(
            frame, HOCKEY_GBM_FEATURE_COLUMNS, settings, params)
        metrics.update(_baseline_comparison(metrics["moneyline_log_loss"]))
        return EvaluationReport(
            model_name=config.model_name,
            model_version=config.model_version,
            metrics=metrics,
            n_samples=int(metrics["n_scored"]),
            skipped_matches=int(metrics["n_skipped"]))

    def fit(
            self,
            features: pd.DataFrame,
            labels: pd.Series,
            config: ModelRunConfig,
            sample_weight: pd.Series | None = None) -> HockeyGoalsGbmModel:
        """Fit rates. ``labels`` must carry goals_home and goals_away."""
        del sample_weight
        settings = gbm_settings_from_config(config)
        params = hockey_params_from_config(config)
        labeled = _with_label_columns(features, labels)
        as_of = (
            pd.Timestamp(labeled["game_date"].max()) + pd.Timedelta(days=1))
        return fit_hockey_gbm(
            labeled,
            HOCKEY_GBM_FEATURE_COLUMNS,
            settings,
            params,
            as_of)


def _load_frame(params: HockeyDixonColesParams) -> pd.DataFrame:
    return load_hockey_team_feature_frame(
        params.league_id,
        baseline_games=params.lineup_baseline_games,
        ratings_config=ratings_config_from_params(params),
        goalie_half_life_days=params.goalie_half_life_days)


def _finished_rows(frame: pd.DataFrame) -> pd.DataFrame:
    ready = frame.loc[
        frame["goals_home"].notna() & frame["goals_away"].notna()].copy()
    if ready.empty:
        raise ValueError("No finished hockey matches were loaded")
    ready["game_date"] = pd.to_datetime(ready["game_date"])
    return ready.sort_values(
        ["game_date", "match_id"]).reset_index(drop=True)


def _prior_and_validation(
        frame: pd.DataFrame,
        as_of: pd.Timestamp,
        params: HockeyDixonColesParams
) -> tuple[pd.DataFrame, pd.DataFrame]:
    moment = pd.Timestamp(as_of)
    prior = frame.loc[frame["game_date"] < moment].copy()
    if prior.empty:
        raise ValueError("No finished matches before the fit date")
    start = moment - pd.Timedelta(days=params.validation_days)
    validation = prior.loc[prior["game_date"] >= start]
    if len(validation) < _MIN_VALIDATION_ROWS:
        validation = prior.tail(min(len(prior), _MIN_VALIDATION_ROWS))
    return prior, validation


def _rows_before_validation(
        prior: pd.DataFrame,
        validation: pd.DataFrame) -> pd.DataFrame:
    """Matches the trees may see. The calibration window is excluded."""
    train = prior.loc[~prior.index.isin(validation.index)]
    if train.empty:
        raise ValueError(
            "Validation window covers every match before the fit date")
    return train


def season_sample_weights(
        seasons: pd.Series,
        low_weight_seasons: dict[int, float]) -> np.ndarray:
    """Return row weights, lowering seasons listed in the map."""
    weights = np.ones(len(seasons), dtype=float)
    season_values = seasons.to_numpy()
    for season, weight in low_weight_seasons.items():
        weights[season_values == int(season)] = float(weight)
    return weights


def fit_poisson_regressor(
        matrix: pd.DataFrame,
        target: np.ndarray,
        weights: np.ndarray,
        settings: HockeyGbmSettings) -> HistGradientBoostingRegressor:
    """Fit one Poisson histogram gradient booster."""
    model = HistGradientBoostingRegressor(
        loss="poisson",
        learning_rate=settings.learning_rate,
        max_iter=settings.max_iter,
        max_depth=settings.max_depth,
        min_samples_leaf=settings.min_samples_leaf,
        l2_regularization=settings.l2_regularization,
        random_state=settings.random_state)
    model.fit(matrix, target, sample_weight=weights)
    return model


# Stare nazwy zostają, bo fit drużynowy i testy je podmieniają.
_season_weights = season_sample_weights
_fit_poisson = fit_poisson_regressor


def _fit_overtime(
        matrix: pd.DataFrame,
        prior: pd.DataFrame,
        settings: HockeyGbmSettings) -> tuple[Pipeline, float, bool]:
    tied = prior["goals_home"].to_numpy() == prior["goals_away"].to_numpy()
    labels = pd.to_numeric(prior["ot_home_win"], errors="coerce").to_numpy()
    known = tied & np.array([
        value is not None and not pd.isna(value) for value in labels])
    known_labels = labels[known]
    fallback = 0.5 if known_labels.size == 0 else float(
        np.nanmean(known_labels.astype(float)))
    pipeline = _overtime_pipeline(settings)
    ready = int(known.sum()) >= 2 and len(set(known_labels.tolist())) >= 2
    if not ready:
        # Za mało remisów. Zapisany pipeline nie jest używany.
        dummy = pd.concat(
            [matrix.iloc[:1], matrix.iloc[:1]], ignore_index=True)
        pipeline.fit(dummy, np.array([0, 1]))
        return pipeline, fallback, False
    pipeline.fit(matrix.iloc[np.flatnonzero(known)], known_labels.astype(int))
    return pipeline, fallback, True


def _overtime_pipeline(settings: HockeyGbmSettings) -> Pipeline:
    logistic = LogisticRegression(
        max_iter=1000,
        random_state=settings.random_state)
    return Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", logistic)])


def _overtime_probability(
        pipeline: Pipeline,
        matrix: pd.DataFrame,
        fallback: float) -> np.ndarray:
    try:
        probabilities = pipeline.predict_proba(matrix)
    except ValueError:
        return np.full(len(matrix), fallback, dtype=float)
    classes = list(pipeline.named_steps["model"].classes_)
    if 1 not in classes:
        return np.full(len(matrix), fallback, dtype=float)
    return probabilities[:, classes.index(1)].astype(float)


def _feature_matrix(
        frame: pd.DataFrame,
        feature_columns: list[str]) -> pd.DataFrame:
    missing = [
        column for column in feature_columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing hockey GBM features: {missing}")
    matrix = frame.loc[:, feature_columns].apply(
        pd.to_numeric, errors="coerce")
    return matrix.replace([np.inf, -np.inf], np.nan)


def _metrics_from_scores(
        model: HockeyGoalsGbmModel,
        test: pd.DataFrame,
        finished: pd.DataFrame,
        as_of: pd.Timestamp,
        params: HockeyDixonColesParams) -> dict[str, Any]:
    scored, skipped = _score_rows(model, test)
    if not scored:
        raise ValueError("Hockey GBM holdout produced no scored matches")
    table = pd.DataFrame(scored)
    naive = _naive_home_rate(finished, as_of)
    moneyline = _log_loss(table["y_home"], table["p_home"])
    home_brier = _brier(table["y_home"], table["p_home"])
    over = _log_loss(table["y_over"], table["p_over"])
    puck = _log_loss(table["y_puck"], table["p_puck"])
    naive_loss = _log_loss(
        table["y_home"], np.full(len(table), naive))
    return {
        "test_season": int(params.test_season),
        "n_scored": int(len(table)),
        "n_skipped": int(skipped),
        "n_train": int((finished["season"] != params.test_season).sum()),
        "moneyline_log_loss": moneyline,
        "moneyline_brier": home_brier,
        "score_matrix_rps": float(table["rps"].mean()),
        "naive_home_log_loss": naive_loss,
        "beats_naive_moneyline": bool(moneyline < naive_loss),
        "over_55_log_loss": over,
        "over_55_brier": _brier(table["y_over"], table["p_over"]),
        "puck_line_home_minus_15_log_loss": puck,
        "puck_line_home_minus_15_brier": _brier(
            table["y_puck"], table["p_puck"]),
        "moneyline_reliability": _reliability(
            table["y_home"].to_numpy(), table["p_home"].to_numpy())}


def _score_rows(
        model: HockeyGoalsGbmModel,
        test: pd.DataFrame) -> tuple[list[dict[str, float]], int]:
    home, away, p_ot = model.predict_rates(test)
    scored: list[dict[str, float]] = []
    skipped = 0
    goals_home = test["goals_home"].to_numpy()
    goals_away = test["goals_away"].to_numpy()
    ot_home = test["ot_home_win"].tolist()
    for index in range(len(test)):
        markets = _markets_or_none(
            float(home[index]),
            float(away[index]),
            float(p_ot[index]),
            model)
        target = _market_targets(
            goals_home[index], goals_away[index], ot_home[index])
        if markets is None or target is None:
            skipped += 1
            continue
        scored.append({
            "y_home": target[0],
            "p_home": markets["ml_home"] / 100.0,
            "y_over": target[1],
            "p_over": markets["over_55"] / 100.0,
            "y_puck": target[2],
            "p_puck": markets["pl_home_minus_15"] / 100.0,
            "rps": _matrix_rps(markets["matrix"], target[3], target[4])})
    return scored, skipped


def _markets_or_none(
        lambda_home: float,
        lambda_away: float,
        p_ot_home: float,
        model: HockeyGoalsGbmModel) -> dict[str, Any] | None:
    try:
        distribution = build_score_distribution(
            lambda_home,
            lambda_away,
            model.tie_inflation,
            p_ot_home,
            model.max_goals)
    except ValueError:
        return None
    markets = derive_hockey_markets(distribution)
    markets["matrix"] = distribution.final_matrix
    return markets


def _market_targets(
        goals_home: object,
        goals_away: object,
        ot_home_win: object) -> tuple[float, float, float, int, int] | None:
    home = _whole_number(goals_home)
    away = _whole_number(goals_away)
    if home is None or away is None:
        return None
    winner = _final_winner(home, away, ot_home_win)
    if winner is None:
        return None
    final_home, final_away = _final_totals(home, away, winner)
    return (
        float(winner),
        1.0 if final_home + final_away > 5.5 else 0.0,
        1.0 if final_home - final_away > 1.5 else 0.0,
        final_home,
        final_away)


def _matrix_rps(matrix: np.ndarray, home_goals: int, away_goals: int) -> float:
    """Ranked probability score of one final-score grid.

    The score is the mean squared gap between the predicted and
    observed cumulative distributions. A point mass on the actual
    score is 0. Moneyline Brier is a different number.
    """
    home = min(max(int(home_goals), 0), matrix.shape[0] - 1)
    away = min(max(int(away_goals), 0), matrix.shape[1] - 1)
    observed = np.zeros(matrix.shape, dtype=float)
    # CDF obserwacji jest 1 dopiero od prawdziwego wyniku w górę.
    observed[home:, away:] = 1.0
    cumulative = np.cumsum(np.cumsum(matrix, axis=0), axis=1)
    gaps = (cumulative - observed) ** 2
    gaps[-1, -1] = 0.0
    return float(gaps.sum() / (matrix.size - 1))


def _final_winner(home: int, away: int, ot_home_win: object) -> int | None:
    if home > away:
        return 1
    if home < away:
        return 0
    decided = _whole_number(ot_home_win)
    if decided not in (0, 1):
        return None
    return decided


def _final_totals(home: int, away: int, winner: int) -> tuple[int, int]:
    if home != away:
        return home, away
    if winner == 1:
        return home + 1, away
    return home, away + 1


def _naive_home_rate(frame: pd.DataFrame, as_of: pd.Timestamp) -> float:
    prior = frame.loc[frame["game_date"] < as_of]
    wins = [
        _final_winner(
            int(row.goals_home), int(row.goals_away), row.ot_home_win)
        for row in prior.itertuples(index=False)]
    known = [float(item) for item in wins if item is not None]
    if not known:
        return 0.5
    return float(np.mean(known))


def _baseline_comparison(moneyline_log_loss: float) -> dict[str, Any]:
    single_fit, walk_forward, refit_count = _baseline_moneyline_report()
    report: dict[str, Any] = {
        "baseline_single_fit_moneyline_log_loss": single_fit,
        "baseline_walk_forward_moneyline_log_loss": walk_forward,
        "baseline_refit_count": refit_count,
        "comparison_protocol": "single_preseason_fit",
        "beats_baseline_moneyline": None,
        "recommended_active": 0}
    if single_fit is None:
        return report
    beats = bool(moneyline_log_loss < single_fit)
    report["beats_baseline_moneyline"] = beats
    report["recommended_active"] = 1 if beats else 0
    return report


def _baseline_moneyline_report() -> tuple[
        float | None, float | None, int | None]:
    payload = _read_baseline_metrics()
    if payload is None:
        return None, None, None
    return (
        _optional_finite(payload.get(_SINGLE_FIT_BASELINE_KEY)),
        _optional_finite(payload.get("moneyline_log_loss")),
        _optional_count(payload.get("refit_count")))


def _read_baseline_metrics() -> dict[str, Any] | None:
    if not _BASELINE_METRICS.is_file():
        return None
    try:
        with _BASELINE_METRICS.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _optional_finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _optional_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def _log_loss(target: pd.Series, probability: np.ndarray) -> float:
    clipped = np.clip(
        probability, _PROBABILITY_FLOOR, 1.0 - _PROBABILITY_FLOOR)
    actual = target.to_numpy(dtype=float)
    loss = -(
        actual * np.log(clipped) + (1.0 - actual) * np.log(1.0 - clipped))
    return float(np.mean(loss))


def _brier(target: pd.Series, probability: np.ndarray) -> float:
    actual = target.to_numpy(dtype=float)
    return float(np.mean((probability - actual) ** 2))


def _reliability(
        target: np.ndarray,
        probability: np.ndarray,
        bins: int = 5) -> list[dict[str, float | int]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict[str, float | int]] = []
    for index in range(bins):
        low = float(edges[index])
        high = float(edges[index + 1])
        if index == bins - 1:
            mask = (probability >= low) & (probability <= high)
        else:
            mask = (probability >= low) & (probability < high)
        count = int(mask.sum())
        if count == 0:
            continue
        rows.append({
            "lower": low,
            "upper": high,
            "n": count,
            "p_mean": float(probability[mask].mean()),
            "y_rate": float(target[mask].mean())})
    return rows


def _with_label_columns(
        features: pd.DataFrame,
        labels: pd.Series | pd.DataFrame) -> pd.DataFrame:
    if isinstance(labels, pd.DataFrame):
        goals = labels
    else:
        goals = labels.to_frame()
    required = ["goals_home", "goals_away"]
    missing = [column for column in required if column not in goals.columns]
    if missing:
        raise KeyError(f"Missing hockey GBM labels: {missing}")
    labeled = features.copy()
    for column in ("goals_home", "goals_away", "ot_home_win"):
        if column in goals.columns:
            labeled[column] = goals[column].to_numpy()
    if "game_date" not in labeled.columns:
        raise KeyError("GBM fit requires game_date on the feature frame")
    return labeled


def _whole_number(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not number.is_integer():
        return None
    return int(number)


def _save_run(
        config: ModelRunConfig,
        model: HockeyGoalsGbmModel,
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
        "trainer": "HockeyGbmTrainer",
        "feature_builder": config.feature_builder,
        "labeler": config.labeler,
        "tie_inflation": model.tie_inflation,
        "fallback_p_ot_home": model.fallback_p_ot_home,
        "max_goals": model.max_goals,
        "loss": "poisson_hist_gradient_boosting",
        "overtime": "logistic_regression",
        "holdout": "single_fit_before_test_season",
        "comparison_protocol": "single_preseason_fit",
        "baseline_refit_count": metrics.get("baseline_refit_count"),
        "recommended_active": metrics.get("recommended_active"),
        "training_started_at": started.isoformat(),
        "training_finished_at": datetime.now(timezone.utc).isoformat()})


def _log_comparison(model_name: str, metrics: dict[str, Any]) -> None:
    single_fit = metrics.get("baseline_single_fit_moneyline_log_loss")
    logger.info(
        "%s moneyline log loss %.4f, single-fit baseline %s, "
        "naive %.4f on %s matches",
        model_name,
        metrics["moneyline_log_loss"],
        single_fit,
        metrics["naive_home_log_loss"],
        metrics["n_scored"])
    active = 1 if metrics.get("recommended_active") == 1 else 0
    logger.info(
        "UPDATE models SET active = %s WHERE name = '%s';",
        active,
        model_name)
    if single_fit is None:
        logger.warning(
            "%s has no single-fit ratings moneyline to beat; "
            "leave models.active at 0",
            model_name)
        return
    if active == 1:
        logger.info(
            "%s beat the single-fit ratings moneyline", model_name)
        return
    logger.warning(
        "%s did not beat the single-fit ratings moneyline; "
        "leave models.active at 0",
        model_name)
