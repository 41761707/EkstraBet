"""Training artifacts, calibration and fingerprints without a DB write."""

from __future__ import annotations

import hashlib
import inspect
import json
import math
from collections.abc import Callable
from datetime import datetime

import pandas as pd
import pytest
from sklearn.calibration import CalibratedClassifierCV
from sklearn.calibration import _SigmoidCalibration
from sklearn.frozen import FrozenEstimator
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from models.pipeline.betting import trainer as trainer_module
from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.config import BettingTrainingConfig
from models.pipeline.betting.dataset_builder import BettingDataset
from models.pipeline.betting.dataset_builder import build_walk_forward_splits
from models.pipeline.betting.evaluation import brier_score
from models.pipeline.betting.evaluation import log_loss_score
from models.pipeline.betting.evaluation import reliability_score
from models.pipeline.betting.evaluation import unit_stake_hit_rate
from models.pipeline.betting.evaluation import unit_stake_roi
from models.pipeline.betting.features import FEATURE_COLUMNS
from models.pipeline.betting.features import NUMERIC_FEATURE_COLUMNS
from models.pipeline.betting.features import feature_schema_fingerprint
from models.pipeline.betting.trainer import BettingMetaTrainer
from models.pipeline.betting.trainer import require_feature_schema
from models.pipeline.betting.trainer import train_meta_model
from models.pipeline.core.artifacts import load_model_artifact
from models.pipeline.core.artifacts import model_file_fingerprint


_WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "to_sql",
    "get_db_connection",
    "betting_recommendations")


def _config(**overrides: object) -> BettingTrainingConfig:
    payload: dict[str, object] = {
        "model_name": "FOOTBALL_BETTING_META_V1",
        "algorithm": "LogisticRegression",
        "class_weight": "balanced",
        "calibration_methods": ("sigmoid", "isotonic"),
        "random_state": 42,
        "train_fraction": 0.6,
        "calibration_fraction": 0.2,
        "test_fraction": 0.2}
    payload.update(overrides)
    return BettingTrainingConfig(**payload)


def _strategy(**overrides: object) -> BettingStrategyConfig:
    payload: dict[str, object] = {
        "probability_threshold": 0.5,
        "football_sport_name": "Piłka nożna",
        "excluded_model_names": (
            "FOOTBALL_PLAYED_BETTER_V1",
            "FOOTBALL_PLAYED_BETTER_NOXG_V1"),
        "max_brier": 0.24,
        "max_reliability_error": 0.05,
        "min_roi": 0.0}
    payload.update(overrides)
    return BettingStrategyConfig(**payload)


def _default_label(match_id: int) -> int:
    return match_id % 2


def _default_league(match_id: int) -> object:
    if match_id == 1:
        return None
    return str((match_id % 3) + 1)


def _default_market(match_id: int) -> str:
    if match_id % 2 == 0:
        return "BTTS"
    return "RESULT"


def _dataset(
        count: int = 15,
        label_of: Callable[[int], int] | None = None,
        league_of: Callable[[int], object] | None = None,
        market_of: Callable[[int], str] | None = None) -> BettingDataset:
    """Return a finished dataset with one row per match."""
    label_for = _default_label if label_of is None else label_of
    league_for = _default_league if league_of is None else league_of
    market_for = _default_market if market_of is None else market_of
    rows: list[dict[str, object]] = []
    labels: list[int] = []
    for match_id in range(1, count + 1):
        label = label_for(match_id)
        probability = 0.8 if label == 1 else 0.25
        rows.append(_feature_row(
            probability,
            league_for(match_id),
            market_for(match_id)))
        labels.append(label)
    features = pd.DataFrame(rows).loc[:, list(FEATURE_COLUMNS)]
    for name in NUMERIC_FEATURE_COLUMNS:
        features[name] = features[name].astype("float64")
    index = features.index
    return BettingDataset(
        features=features,
        labels=pd.Series(labels, index=index, dtype="int64", name="label"),
        prediction_id=_ids(count, 1, index, "prediction_id"),
        odds_id=_ids(count, 1000, index, "odds_id"),
        match_id=_ids(count, 1, index, "match_id"),
        kickoff=_kickoffs(count, index),
        odds=pd.Series(
            [2.0] * count,
            index=index,
            dtype="float64",
            name="odds"))


def _feature_row(
        probability: float,
        league_id: object,
        market_family: str) -> dict[str, object]:
    implied = 0.5
    return {
        "model_probability": probability,
        "implied_probability": implied,
        "devig_probability": math.nan,
        "edge": probability - implied,
        "ev": probability * 2.0 - 1.0,
        "kickoff_weekday_sin": 0.0,
        "kickoff_weekday_cos": 1.0,
        "kickoff_hour_sin": 0.0,
        "kickoff_hour_cos": 1.0,
        "model_id": "8",
        "market_family": market_family,
        "league_id": league_id}


def _ids(
        count: int,
        start: int,
        index: pd.Index,
        name: str) -> pd.Series:
    values = [start + offset for offset in range(count)]
    return pd.Series(values, index=index, dtype="int64", name=name)


def _kickoffs(count: int, index: pd.Index) -> pd.Series:
    values = [
        datetime(2026, 1, match_id, 18, 0)
        for match_id in range(1, count + 1)]
    return pd.Series(values, index=index, dtype="object", name="kickoff")


def _labels_of(
        dataset: BettingDataset,
        row_labels: tuple[object, ...]) -> tuple[int, ...]:
    return tuple(int(dataset.labels.loc[label]) for label in row_labels)


def _read_json(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_training_writes_the_artifact_files(tmp_path) -> None:
    dataset = _dataset()
    config = _config()
    report = BettingMetaTrainer().train(
        dataset, config, tmp_path, strategy=_strategy())
    assert (tmp_path / "model.joblib").is_file()
    assert (tmp_path / "feature_columns.json").is_file()
    assert (tmp_path / "metrics.json").is_file()
    assert (tmp_path / "meta.json").is_file()
    meta = _read_json(tmp_path / "meta.json")
    assert meta["feature_schema_fingerprint"] == (
        report.feature_schema_fingerprint)
    assert meta["model_fingerprint"] == report.model_fingerprint
    assert meta["feature_schema_fingerprint"] == (
        feature_schema_fingerprint(FEATURE_COLUMNS))
    assert model_file_fingerprint(tmp_path / "model.joblib") == (
        report.model_fingerprint)
    assert len(report.model_fingerprint) == 64
    saved = _read_json(tmp_path / "feature_columns.json")
    assert saved["feature_columns"] == list(FEATURE_COLUMNS)
    metrics = _read_json(tmp_path / "metrics.json")
    methods = list(config.calibration_methods)
    scores = metrics["calibration_brier"]
    expected = min(
        methods,
        key=lambda method: (scores[method], methods.index(method)))
    assert report.calibration_method == expected
    assert set(scores) == {"sigmoid", "isotonic"}
    assert metrics["brier"] == report.test.brier
    assert metrics["log_loss"] == report.test.log_loss
    assert metrics["reliability"] == report.test.reliability
    assert metrics["roi"] == report.test.roi
    assert metrics["by_league"]
    assert metrics["by_market"]
    league_rows = sum(
        item.metrics.row_count for item in report.by_league)
    market_rows = sum(
        item.metrics.row_count for item in report.by_market)
    assert league_rows == report.test.row_count
    assert market_rows == report.test.row_count
    assert metrics["bet_count"] == report.test.bet_count
    assert metrics["no_bet_count"] == report.test.no_bet_count
    assert metrics["bet_count"] + metrics["no_bet_count"] == (
        metrics["row_count"])
    assert metrics["bet_prediction_ids"]
    league_bets = sum(
        item["bet_count"] for item in metrics["by_league"].values())
    assert league_bets == metrics["bet_count"]
    assert "label" not in saved["feature_columns"]
    assert "result" not in saved["feature_columns"]


def test_unknown_category_still_scores(tmp_path) -> None:
    def league_of(match_id: int) -> object:
        if match_id >= 13:
            return "999"
        return _default_league(match_id)

    dataset = _dataset(league_of=league_of)
    splits = build_walk_forward_splits(dataset.split_frame(), _config())
    assert splits[2].match_ids == (13, 14, 15)
    report = train_meta_model(
        dataset, _config(), tmp_path, strategy=_strategy())
    assert "999" in {item.name for item in report.by_league}
    assert 0.0 <= report.test.brier <= 1.0
    row = dataset.features.iloc[[0]].copy()
    row["league_id"] = "999"
    row["market_family"] = "NO_SUCH_FAMILY"
    row["model_id"] = "404"
    model = load_model_artifact(tmp_path)
    proba = model.predict_proba(row)
    assert proba.shape == (1, 2)
    assert 0.0 <= float(proba[0, 1]) <= 1.0


def test_one_training_class_raises(tmp_path) -> None:
    def early_losses(match_id: int) -> int:
        if match_id <= 9:
            return 0
        return 1

    dataset = _dataset(label_of=early_losses)
    splits = build_walk_forward_splits(dataset.split_frame(), _config())
    assert set(splits[0].match_ids) <= set(range(1, 10))
    with pytest.raises(
            ValueError,
            match="training split must contain both classes"):
        train_meta_model(
            dataset, _config(), tmp_path, strategy=_strategy())
    assert not (tmp_path / "model.joblib").exists()


def test_one_calibration_class_raises(tmp_path) -> None:
    def calibration_losses(match_id: int) -> int:
        if 10 <= match_id <= 12:
            return 0
        return match_id % 2

    dataset = _dataset(label_of=calibration_losses)
    splits = build_walk_forward_splits(dataset.split_frame(), _config())
    assert splits[1].match_ids == (10, 11, 12)
    with pytest.raises(
            ValueError,
            match="calibration split must contain both classes"):
        train_meta_model(
            dataset, _config(), tmp_path, strategy=_strategy())
    assert not (tmp_path / "model.joblib").exists()


def test_column_fingerprint_mismatch_raises(tmp_path) -> None:
    train_meta_model(
        _dataset(), _config(), tmp_path, strategy=_strategy())
    require_feature_schema(tmp_path, list(FEATURE_COLUMNS))
    with pytest.raises(ValueError, match="fingerprint"):
        require_feature_schema(tmp_path, ["edge", "ev"])
    feature_file = tmp_path / "feature_columns.json"
    feature_file.write_text(
        '{"feature_columns": ["edge"]}',
        encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        require_feature_schema(tmp_path, list(FEATURE_COLUMNS))


def test_changed_model_bytes_change_the_fingerprint(tmp_path) -> None:
    payload = b"not-a-real-model"
    loose = tmp_path / "loose.joblib"
    loose.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    assert model_file_fingerprint(loose) == digest
    loose.write_bytes(payload + b"x")
    assert model_file_fingerprint(loose) != digest
    trained = tmp_path / "trained"
    report = train_meta_model(
        _dataset(), _config(), trained, strategy=_strategy())
    model_path = trained / "model.joblib"
    assert model_file_fingerprint(model_path) == report.model_fingerprint
    model_path.write_bytes(model_path.read_bytes() + b"\n")
    assert model_file_fingerprint(model_path) != report.model_fingerprint
    meta = _read_json(trained / "meta.json")
    assert meta["model_fingerprint"] == report.model_fingerprint


def test_test_features_change_brier_and_the_bet_rows(tmp_path) -> None:
    config = _config()
    strategy = _strategy()
    original = _dataset()
    changed = _replace_test_features(original, config)
    first = tmp_path / "first"
    second = tmp_path / "second"
    train_meta_model(original, config, first, strategy=strategy)
    train_meta_model(changed, config, second, strategy=strategy)
    assert (first / "model.joblib").read_bytes() == (
        (second / "model.joblib").read_bytes())
    left = _read_json(first / "metrics.json")
    right = _read_json(second / "metrics.json")
    assert left["calibration_brier"] == right["calibration_brier"]
    assert left["calibration_method"] == right["calibration_method"]
    assert left["brier"] != right["brier"]
    assert left["bet_prediction_ids"] != right["bet_prediction_ids"]
    assert _roi_of(original, config, strategy, left) == left["roi"]
    assert _roi_of(changed, config, strategy, right) == right["roi"]


def test_sigmoid_uses_platt_and_class_weight_stays_on_train(
        tmp_path) -> None:
    config = _config(calibration_methods=("sigmoid",))
    train_meta_model(
        _dataset(), config, tmp_path, strategy=_strategy())
    model = load_model_artifact(tmp_path)
    classifier = model.pipeline.named_steps["classifier"]
    assert classifier.class_weight == "balanced"
    assert isinstance(model.calibrated, CalibratedClassifierCV)
    assert isinstance(model.calibrated.estimator, FrozenEstimator)
    assert model.calibrated.method == "sigmoid"
    assert type(model.calibrated.cv).__name__ == "_FullWindowSplit"
    assert not hasattr(model, "classes_")
    assert not isinstance(model.calibrated, LogisticRegression)
    assert "_SigmoidCalibration" not in inspect.getsource(trainer_module)


def test_no_bets_leave_roi_and_hit_rate_empty(tmp_path) -> None:
    report = train_meta_model(
        _dataset(),
        _config(calibration_methods=("sigmoid",)),
        tmp_path,
        strategy=_strategy(probability_threshold=1.0))
    assert report.test.bet_count == 0
    assert report.test.no_bet_count == report.test.row_count
    assert report.test.roi is None
    assert report.test.hit_rate is None
    metrics = _read_json(tmp_path / "metrics.json")
    assert metrics["roi"] is None
    assert metrics["hit_rate"] is None
    assert metrics["bet_prediction_ids"] == []


def test_saved_calibrator_is_fit_on_the_whole_calibration_window(
        tmp_path, monkeypatch) -> None:
    dataset = _dataset()
    config = _config()
    splits = build_walk_forward_splits(dataset.split_frame(), config)
    recorded: list[tuple[str, tuple[int, ...]]] = []
    indexes: list[tuple[object, ...]] = []
    _patch_fit(monkeypatch, recorded, indexes)
    train_meta_model(dataset, config, tmp_path, strategy=_strategy())
    train_labels = _labels_of(dataset, splits[0].row_labels)
    earlier_labels, later_labels = _calibration_label_parts(
        dataset, splits[1])
    calibration_labels = _labels_of(dataset, splits[1].row_labels)
    test_labels = _labels_of(dataset, splits[2].row_labels)
    fitted = [labels for _name, labels in recorded]
    method = _read_json(tmp_path / "metrics.json")["calibration_method"]
    assert indexes == [splits[0].row_labels]
    assert ("logistic", train_labels) in recorded
    assert ("sigmoid", earlier_labels) in recorded
    assert ("isotonic", earlier_labels) in recorded
    assert [
        name for name, labels in recorded
        if labels == calibration_labels] == [method]
    assert later_labels not in fitted
    assert test_labels not in fitted


def test_one_calibration_match_fits_without_a_holdout(tmp_path) -> None:
    report = train_meta_model(
        _one_calibration_match_dataset(),
        _config(),
        tmp_path,
        strategy=_strategy())
    metrics = _read_json(tmp_path / "metrics.json")
    assert report.calibration_method == "sigmoid"
    assert metrics["calibration_brier"] == {}
    assert metrics["split_rows"]["calibration"] == 2
    model = load_model_artifact(tmp_path)
    assert isinstance(model.calibrated, CalibratedClassifierCV)


def test_probability_equal_to_the_threshold_is_not_a_bet() -> None:
    assert trainer_module._bet_indexes([0.5, 0.51], 0.5) == [1]


def test_report_uses_the_shared_sorted_metrics(tmp_path) -> None:
    dataset = _dataset()
    config = _config()
    report = train_meta_model(
        dataset, config, tmp_path, strategy=_strategy())
    labels, chances, prices = _sorted_test_scores(dataset, config, tmp_path)
    assert report.test.brier == brier_score(chances, labels)
    assert report.test.log_loss == log_loss_score(chances, labels)
    assert report.test.reliability == reliability_score(chances, labels)
    bet_labels = []
    bet_prices = []
    for chance, label, price in zip(chances, labels, prices):
        if chance > _strategy().probability_threshold:
            bet_labels.append(label)
            bet_prices.append(price)
    assert report.test.roi == unit_stake_roi(bet_labels, bet_prices)
    assert report.test.hit_rate == unit_stake_hit_rate(bet_labels)


def test_too_few_matches_raise(tmp_path) -> None:
    with pytest.raises(ValueError, match="not enough matches"):
        train_meta_model(
            _dataset(count=3),
            _config(),
            tmp_path,
            strategy=_strategy())
    assert not (tmp_path / "model.joblib").exists()


def test_training_does_not_write_recommendations() -> None:
    source = inspect.getsource(trainer_module)
    for word in _WRITE_WORDS:
        assert word not in source


def _one_calibration_match_dataset() -> BettingDataset:
    """Return five matches and both classes on the calibration match."""
    base = _dataset(count=5)
    extra = base.features.iloc[[3]].copy()
    extra.loc[extra.index[0], "model_probability"] = 0.8
    extra.loc[extra.index[0], "edge"] = 0.3
    extra.loc[extra.index[0], "ev"] = 0.6
    features = pd.concat([base.features, extra], ignore_index=True)
    count = len(features)
    index = features.index
    kickoffs = list(base.kickoff.tolist()) + [base.kickoff.iloc[3]]
    return BettingDataset(
        features=features,
        labels=pd.Series(
            [int(value) for value in base.labels.tolist()] + [1],
            index=index,
            dtype="int64",
            name="label"),
        prediction_id=_ids(count, 1, index, "prediction_id"),
        odds_id=_ids(count, 1000, index, "odds_id"),
        match_id=pd.Series(
            [1, 2, 3, 4, 5, 4],
            index=index,
            dtype="int64",
            name="match_id"),
        kickoff=pd.Series(
            kickoffs, index=index, dtype="object", name="kickoff"),
        odds=pd.Series(
            [2.0] * count,
            index=index,
            dtype="float64",
            name="odds"))


def _sorted_test_scores(
        dataset: BettingDataset,
        config: BettingTrainingConfig,
        artifact_dir) -> tuple[list[int], list[float], list[float]]:
    """Return test labels, probabilities and prices in pair order."""
    splits = build_walk_forward_splits(dataset.split_frame(), config)
    index = list(splits[2].row_labels)
    model = load_model_artifact(artifact_dir)
    chances = model.predict_proba(dataset.features.loc[index])[:, 1]
    rows = list(zip(
        dataset.prediction_id.loc[index].tolist(),
        dataset.odds_id.loc[index].tolist(),
        dataset.labels.loc[index].tolist(),
        chances.tolist(),
        dataset.odds.loc[index].tolist()))
    rows.sort(key=lambda item: (int(item[0]), int(item[1])))
    return (
        [int(item[2]) for item in rows],
        [float(item[3]) for item in rows],
        [float(item[4]) for item in rows])


def _replace_test_features(
        dataset: BettingDataset,
        config: BettingTrainingConfig) -> BettingDataset:
    """Flip the test block's probability features. Prices stay put."""
    splits = build_walk_forward_splits(dataset.split_frame(), config)
    index = list(splits[2].row_labels)
    features = dataset.features.copy()
    probability = features.loc[index, "model_probability"].map(_flipped)
    features.loc[index, "model_probability"] = probability
    features.loc[index, "edge"] = probability - 0.5
    features.loc[index, "ev"] = probability * 2.0 - 1.0
    return BettingDataset(
        features=features,
        labels=dataset.labels.copy(),
        prediction_id=dataset.prediction_id.copy(),
        odds_id=dataset.odds_id.copy(),
        match_id=dataset.match_id.copy(),
        kickoff=dataset.kickoff.copy(),
        odds=dataset.odds.copy())


def _flipped(value: object) -> float:
    """Swap a high probability feature with a low one."""
    if float(value) >= 0.5:
        return 0.05
    return 0.95


def _calibration_label_parts(
        dataset: BettingDataset,
        split) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return labels of the earlier and later calibration matches."""
    later_count = max(1, len(split.match_ids) // 2)
    earlier_ids = set(split.match_ids[:-later_count])
    earlier: list[object] = []
    later: list[object] = []
    for row_label in split.row_labels:
        match_id = int(dataset.match_id.loc[row_label])
        if match_id in earlier_ids:
            earlier.append(row_label)
        else:
            later.append(row_label)
    return _labels_of(dataset, tuple(earlier)), _labels_of(
        dataset, tuple(later))


def _roi_of(
        dataset: BettingDataset,
        config: BettingTrainingConfig,
        strategy: BettingStrategyConfig,
        metrics: dict) -> float | None:
    """Recompute unit-stake ROI from the reported bet ids."""
    bet_ids = set(metrics["bet_prediction_ids"])
    if not bet_ids:
        return None
    splits = build_walk_forward_splits(dataset.split_frame(), config)
    profit = 0.0
    for row_label in splits[2].row_labels:
        prediction_id = int(dataset.prediction_id.loc[row_label])
        if prediction_id not in bet_ids:
            continue
        if int(dataset.labels.loc[row_label]) == 1:
            profit += float(dataset.odds.loc[row_label]) - 1.0
        else:
            profit -= 1.0
    return profit / len(bet_ids)


def _patch_fit(
        monkeypatch,
        recorded: list[tuple[str, tuple[int, ...]]],
        indexes: list) -> None:
    """Record the rows passed to fit without changing the estimators."""
    original_pipeline = Pipeline.fit
    original_logistic = LogisticRegression.fit
    original_isotonic = IsotonicRegression.fit
    original_sigmoid = _SigmoidCalibration.fit

    def pipeline_fit(self, X, y=None, **kwargs):
        indexes.append(tuple(X.index))
        return original_pipeline(self, X, y, **kwargs)

    def logistic_fit(self, X, y, *args, **kwargs):
        recorded.append(("logistic", _as_labels(y)))
        return original_logistic(self, X, y, *args, **kwargs)

    def isotonic_fit(self, X, y, *args, **kwargs):
        recorded.append(("isotonic", _as_labels(y)))
        return original_isotonic(self, X, y, *args, **kwargs)

    def sigmoid_fit(self, X, y, *args, **kwargs):
        recorded.append(("sigmoid", _as_labels(y)))
        return original_sigmoid(self, X, y, *args, **kwargs)

    monkeypatch.setattr(Pipeline, "fit", pipeline_fit)
    monkeypatch.setattr(LogisticRegression, "fit", logistic_fit)
    monkeypatch.setattr(IsotonicRegression, "fit", isotonic_fit)
    monkeypatch.setattr(_SigmoidCalibration, "fit", sigmoid_fit)


def _as_labels(values) -> tuple[int, ...]:
    return tuple(int(value) for value in list(values))
