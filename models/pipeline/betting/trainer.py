"""Train and calibrate the betting meta-model.

The test window is scored once for the report. It is not passed to
``fit``. Nothing in this module opens a database connection.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler

from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.config import BettingTrainingConfig
from models.pipeline.betting.dataset_builder import BettingDataset
from models.pipeline.betting.dataset_builder import TemporalSplit
from models.pipeline.betting.dataset_builder import build_walk_forward_splits
from models.pipeline.betting.evaluation import brier_score
from models.pipeline.betting.evaluation import log_loss_score
from models.pipeline.betting.evaluation import reliability_score
from models.pipeline.betting.evaluation import unit_stake_hit_rate
from models.pipeline.betting.evaluation import unit_stake_roi
from models.pipeline.betting.features import CATEGORICAL_FEATURE_COLUMNS
from models.pipeline.betting.features import NUMERIC_FEATURE_COLUMNS
from models.pipeline.betting.features import feature_schema_fingerprint
from models.pipeline.core.artifacts import ensure_artifact_dir
from models.pipeline.core.artifacts import load_feature_columns
from models.pipeline.core.artifacts import load_meta
from models.pipeline.core.artifacts import model_file_fingerprint
from models.pipeline.core.artifacts import save_feature_columns
from models.pipeline.core.artifacts import save_metrics
from models.pipeline.core.artifacts import save_meta
from models.pipeline.core.artifacts import save_model_artifact


_CALIBRATION_METHODS = ("sigmoid", "isotonic")
_MAX_ITER = 1000
_MISSING_CATEGORY = "missing"
_MISSING_SEGMENT = "missing"
_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class _Block:
    """One walk-forward block, copied off the caller's dataset."""

    features: pd.DataFrame
    labels: pd.Series
    match_id: pd.Series
    kickoff: pd.Series
    odds: pd.Series
    prediction_id: pd.Series
    odds_id: pd.Series


@dataclass(frozen=True)
class _Windows:
    """Train, calibration and test rows of one dataset.

    ``test_odds`` prices a bet. The price is not a model column.
    """

    train_features: pd.DataFrame
    train_labels: pd.Series
    calibration_features: pd.DataFrame
    calibration_labels: pd.Series
    calibration_match_id: pd.Series
    calibration_kickoff: pd.Series
    calibration_prediction_id: pd.Series
    calibration_odds_id: pd.Series
    test_features: pd.DataFrame
    test_labels: pd.Series
    test_odds: pd.Series
    test_prediction_id: pd.Series
    test_odds_id: pd.Series


@dataclass(frozen=True)
class SliceMetrics:
    """Scores for one slice of the untouched test window.

    Brier, log loss and reliability use every row. ``roi`` and
    ``hit_rate`` use rows whose calibrated probability is above the
    strategy threshold. A win pays ``odds - 1`` and a loss costs 1.
    Both are ``None`` when the slice has no bet. The threshold is not
    a fitting input.
    """

    brier: float
    log_loss: float
    reliability: float
    roi: float | None
    hit_rate: float | None
    row_count: int
    bet_count: int
    no_bet_count: int

    def __post_init__(self) -> None:
        _validate_slice(self)


@dataclass(frozen=True)
class SegmentMetrics:
    """One league or market slice of the test window."""

    name: str
    metrics: SliceMetrics

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("segment name must not be empty")
        if not isinstance(self.metrics, SliceMetrics):
            raise ValueError("segment metrics must be a SliceMetrics")


@dataclass(frozen=True)
class TrainingReport:
    """Fingerprints and the single out-of-sample score of one run."""

    feature_schema_fingerprint: str
    model_fingerprint: str
    calibration_method: str
    test: SliceMetrics
    by_league: tuple[SegmentMetrics, ...]
    by_market: tuple[SegmentMetrics, ...]

    def __post_init__(self) -> None:
        _validate_report(self)


class FittedBettingModel:
    """Fitted pipeline wrapped by a public probability calibrator.

    ``predict_proba`` returns columns for class 0 and class 1. Class 1
    is a winning candidate. Calling it does not fit the pipeline again.
    The saved calibrator is ``CalibratedClassifierCV`` around a frozen
    pipeline, so the artifact does not name a private Platt class.
    """

    def __init__(
            self,
            pipeline: Pipeline,
            calibrated: CalibratedClassifierCV,
            method: str) -> None:
        if method not in _CALIBRATION_METHODS:
            raise ValueError(
                f"unsupported calibration method: {method}")
        if not isinstance(calibrated, CalibratedClassifierCV):
            raise ValueError(
                "calibrated model must be a CalibratedClassifierCV")
        self.pipeline = pipeline
        self.calibrated = calibrated
        self.method = method

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Return calibrated probabilities for class 0 and class 1."""
        matrix = np.asarray(
            self.calibrated.predict_proba(features),
            dtype=float)
        if matrix.ndim != 2 or matrix.shape != (len(features), 2):
            raise ValueError(
                "calibrated probabilities must have two classes")
        column = _positive_class_column(self.calibrated.classes_)
        positive = np.clip(matrix[:, column], 0.0, 1.0)
        return np.column_stack((1.0 - positive, positive))


class BettingMetaTrainer:
    """Fit preprocessing, logistic regression and one calibrator.

    The test window is scored once for the report. It is not passed
    to ``fit``. Training does not open a database connection.
    """

    def train(
            self,
            dataset: BettingDataset,
            config: BettingTrainingConfig,
            artifact_dir: Path,
            *,
            strategy: BettingStrategyConfig) -> TrainingReport:
        """Fit on train, calibrate, then score the test window once."""
        _require_strategy(strategy)
        windows = _prepare(dataset, config)
        _require_both_classes(windows.train_labels, "training")
        _require_both_classes(
            windows.calibration_labels, "calibration")
        pipeline = _fit_base(windows, config)
        model, method, scores = _choose_calibrator(
            pipeline, windows, config)
        probabilities = _positive_probabilities(
            model, windows.test_features)
        # Próg strategii jest użyty dopiero tutaj. Nie wchodzi do fit.
        threshold = strategy.probability_threshold
        slices, bet_ids = _score_test(windows, probabilities, threshold)
        schema, digest = _write_artifacts(
            model,
            config,
            windows,
            method,
            scores,
            slices,
            bet_ids,
            threshold,
            artifact_dir)
        test, by_league, by_market = slices
        return TrainingReport(
            feature_schema_fingerprint=schema,
            model_fingerprint=digest,
            calibration_method=method,
            test=test,
            by_league=by_league,
            by_market=by_market)


def train_meta_model(
        dataset: BettingDataset,
        config: BettingTrainingConfig,
        artifact_dir: Path,
        *,
        strategy: BettingStrategyConfig) -> TrainingReport:
    """Fit the meta-model and write its artifact.

    ``dataset`` supplies features, labels, kickoff and prices. Splits
    are the walk-forward blocks of ``config``. Logistic regression is
    fit on the train block. Each map is compared on the later
    calibration matches, then only the chosen method is fit on the
    whole calibration block. A block that cannot be split uses the
    first configured method on every calibration row. The test block
    is scored once and does not change the fit. ``strategy`` supplies
    the bet threshold for that score only. No database connection is
    opened.
    """
    return BettingMetaTrainer().train(
        dataset,
        config,
        artifact_dir,
        strategy=strategy)


def require_feature_schema(
        artifact_dir: Path,
        columns: Sequence[str]) -> None:
    """Raise when columns disagree with the saved schema fingerprint.

    The digest is the sorted column-name hash stored in ``meta.json``.
    The saved feature-column file must carry that same digest.
    """
    digest = feature_schema_fingerprint(columns)
    stored = load_meta(artifact_dir).get("feature_schema_fingerprint")
    if stored != digest:
        raise ValueError(
            "feature schema fingerprint does not match the artifact")
    saved = load_feature_columns(artifact_dir)
    if feature_schema_fingerprint(saved) != stored:
        raise ValueError(
            "feature schema fingerprint does not match the artifact")


def _prepare(
        dataset: BettingDataset,
        config: BettingTrainingConfig) -> _Windows:
    """Cut the dataset into train, calibration and test."""
    _require_dataset(dataset)
    _require_config(config)
    splits = build_walk_forward_splits(dataset.split_frame(), config)
    return _windows_from(dataset, splits)


def _windows_from(
        dataset: BettingDataset,
        splits: Sequence[TemporalSplit]) -> _Windows:
    """Copy each block so later fitting cannot mutate the caller."""
    parts = {
        split.role: _indexed(dataset, split)
        for split in splits}
    train = parts["train"]
    calibration = parts["calibration"]
    test = parts["test"]
    return _Windows(
        train_features=train.features,
        train_labels=train.labels,
        calibration_features=calibration.features,
        calibration_labels=calibration.labels,
        calibration_match_id=calibration.match_id,
        calibration_kickoff=calibration.kickoff,
        calibration_prediction_id=calibration.prediction_id,
        calibration_odds_id=calibration.odds_id,
        test_features=test.features,
        test_labels=test.labels,
        test_odds=test.odds,
        test_prediction_id=test.prediction_id,
        test_odds_id=test.odds_id)


def _indexed(
        dataset: BettingDataset,
        split: TemporalSplit) -> _Block:
    """Return one block in its row order."""
    index = list(split.row_labels)
    return _Block(
        features=dataset.features.loc[index].copy(),
        labels=dataset.labels.loc[index].copy(),
        match_id=dataset.match_id.loc[index].copy(),
        kickoff=dataset.kickoff.loc[index].copy(),
        odds=dataset.odds.loc[index].copy(),
        prediction_id=dataset.prediction_id.loc[index].copy(),
        odds_id=dataset.odds_id.loc[index].copy())


def _require_both_classes(labels: pd.Series, role: str) -> None:
    """Reject a block that cannot teach a binary classifier."""
    # Jedna klasa nie daje logistic regression ani kalibratorowi
    # punktu odniesienia. To jest błąd danych, nie ostrzeżenie.
    values = {int(value) for value in labels.tolist()}
    if values != {0, 1}:
        raise ValueError(f"{role} split must contain both classes")


def _fit_base(
        windows: _Windows,
        config: BettingTrainingConfig) -> Pipeline:
    """Fit preprocessing and logistic regression on the train block."""
    # Puste de-vig nie może skasować kolumny, więc train dostaje 0.
    # Sam fit widzi tylko train. Kalibracja i test zostają na później.
    features = _fill_empty_numeric(windows.train_features)
    pipeline = _build_pipeline(config)
    pipeline.fit(features, windows.train_labels)
    return pipeline


def _fill_empty_numeric(features: pd.DataFrame) -> pd.DataFrame:
    """Give an all-missing numeric column a finite train value.

    Median imputation drops a column with no observed values. De-vig
    can be empty on every row, and the saved transformer must keep
    that column.
    """
    filled = features.copy()
    for name in NUMERIC_FEATURE_COLUMNS:
        observed = filled[name].map(_is_finite)
        if bool(observed.any()):
            continue
        filled[name] = 0.0
    return filled


def _build_pipeline(config: BettingTrainingConfig) -> Pipeline:
    """Return an unfitted preprocess-and-classify pipeline."""
    numeric = Pipeline(steps=[
        ("median", SimpleImputer(strategy="median")),
        ("scale", StandardScaler())])
    categorical = Pipeline(steps=[
        ("fill", SimpleImputer(
            strategy="constant",
            fill_value=_MISSING_CATEGORY)),
        ("encode", OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False))])
    preprocess = ColumnTransformer(
        transformers=[
            ("numeric", numeric, list(NUMERIC_FEATURE_COLUMNS)),
            (
                "categorical",
                categorical,
                list(CATEGORICAL_FEATURE_COLUMNS))],
        remainder="drop")
    classifier = LogisticRegression(
        class_weight=config.class_weight,
        random_state=config.random_state,
        max_iter=_MAX_ITER,
        solver="lbfgs")
    return Pipeline(steps=[
        ("preprocess", preprocess),
        ("classifier", classifier)])


def _choose_calibrator(
        pipeline: Pipeline,
        windows: _Windows,
        config: BettingTrainingConfig
        ) -> tuple[FittedBettingModel, str, dict[str, float]]:
    """Choose a map on a later slice, then fit it on every row.

    The comparison stays inside the calibration window. Only the
    winning method is fit again, on all of its rows. The test block
    is not read. A window that cannot be split uses the first
    configured method on the whole window.
    """
    # Wybór metody zostaje na późniejszej części. Zapisana mapa
    # widzi całe okno, a nie tylko wcześniejszą połowę.
    parts = _split_calibration(windows)
    if parts is None:
        method = _first_method(config)
        return _fit_window(pipeline, windows, method), method, {}
    earlier, later = parts
    method, scores = _method_by_later_brier(
        pipeline, earlier, later, config)
    return _fit_window(pipeline, windows, method), method, scores


def _fit_window(
        pipeline: Pipeline,
        windows: _Windows,
        method: str) -> FittedBettingModel:
    """Fit one method on every calibration row."""
    return _fit_calibrated(
        pipeline,
        method,
        windows.calibration_features,
        windows.calibration_labels)


def _first_method(config: BettingTrainingConfig) -> str:
    """Return the method used when the window cannot be compared."""
    if not config.calibration_methods:
        raise ValueError("calibration_methods must not be empty")
    return config.calibration_methods[0]


def _method_by_later_brier(
        pipeline: Pipeline,
        earlier: "_Rows",
        later: "_Rows",
        config: BettingTrainingConfig) -> tuple[str, dict[str, float]]:
    """Fit each map on the earlier matches and score the later ones.

    A tie keeps the earlier method in ``config.calibration_methods``.
    The models fit here are discarded after the comparison.
    """
    best_method: str | None = None
    best_brier: float | None = None
    scores: dict[str, float] = {}
    for method in config.calibration_methods:
        model = _fit_calibrated(
            pipeline, method, earlier.features, earlier.labels)
        chances = _positive_probabilities(model, later.features)
        brier = _brier_in_pair_order(later, chances)
        scores[method] = brier
        if best_brier is None or brier < best_brier:
            best_method = method
            best_brier = brier
    if best_method is None:
        raise ValueError("calibration_methods must not be empty")
    return best_method, scores


@dataclass(frozen=True)
class _Rows:
    """Features and labels of one calibration part."""

    features: pd.DataFrame
    labels: pd.Series
    prediction_id: pd.Series
    odds_id: pd.Series


def _split_calibration(
        windows: _Windows) -> tuple[_Rows, _Rows] | None:
    """Cut calibration matches into an earlier and a later part.

    ``None`` means the window cannot host a comparison. One match is
    a legal calibration block, and so is an earlier part that does
    not contain both classes.
    """
    order = _match_order(
        windows.calibration_match_id,
        windows.calibration_kickoff)
    if len(order) < 2:
        return None
    later_count = max(1, len(order) // 2)
    earlier_ids = set(order[:-later_count])
    fit_rows: list[object] = []
    select_rows: list[object] = []
    pairs = zip(
        windows.calibration_features.index,
        windows.calibration_match_id.tolist())
    for row_label, match_id in pairs:
        if int(match_id) in earlier_ids:
            fit_rows.append(row_label)
        else:
            select_rows.append(row_label)
    if not select_rows:
        return None
    earlier = _take_calibration(windows, fit_rows)
    if not _has_both_classes(earlier.labels):
        return None
    return earlier, _take_calibration(windows, select_rows)


def _match_order(
        match_ids: pd.Series,
        kickoffs: pd.Series) -> list[int]:
    """Return calibration matches sorted by kickoff, then id."""
    paired: dict[int, object] = {}
    for match_id, kickoff in zip(match_ids.tolist(), kickoffs.tolist()):
        parsed = int(match_id)
        if parsed not in paired:
            paired[parsed] = kickoff
    ordered = sorted(paired.items(), key=lambda item: (item[1], item[0]))
    return [match_id for match_id, _kickoff in ordered]


def _has_both_classes(labels: pd.Series) -> bool:
    """Return whether the rows contain a win and a loss."""
    return {int(value) for value in labels.tolist()} == {0, 1}


def _take_calibration(
        windows: _Windows,
        row_labels: list[object]) -> _Rows:
    """Copy the named calibration rows in the given order."""
    return _Rows(
        features=windows.calibration_features.loc[row_labels].copy(),
        labels=windows.calibration_labels.loc[row_labels].copy(),
        prediction_id=(
            windows.calibration_prediction_id.loc[row_labels].copy()),
        odds_id=windows.calibration_odds_id.loc[row_labels].copy())


class _FullWindowSplit:
    """Yield every supplied row once.

    The base model is already fitted. A k-fold split would mix
    kickoff order and demand more rows per class than a short
    calibration window has.
    """

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        """Return the single pass over the supplied rows."""
        return 1

    def split(self, X, y=None, groups=None):
        """Yield all row indexes as both train and test."""
        # Trening kalibratora ma zobaczyć całe podane okno.
        # Zamrożony model i tak nie jest tu uczony ponownie.
        count = len(X)
        index = np.arange(count)
        yield index, index


def _fit_calibrated(
        pipeline: Pipeline,
        method: str,
        features: pd.DataFrame,
        labels: pd.Series) -> FittedBettingModel:
    """Fit one public calibrator on the frozen pipeline."""
    if method not in _CALIBRATION_METHODS:
        raise ValueError(f"unsupported calibration method: {method}")
    # Publiczny kalibrator trzyma Platt albo izotonę u siebie.
    # cv=3 mieszałby kolejne mecze, a prefit znika w sklearn 1.8.
    calibrated = CalibratedClassifierCV(
        FrozenEstimator(pipeline),
        method=method,
        cv=_FullWindowSplit())
    calibrated.fit(features, labels)
    return FittedBettingModel(pipeline, calibrated, method)


def _positive_class_column(classes: np.ndarray) -> int:
    """Return the column that stores the probability of class 1."""
    labels = [int(label) for label in classes]
    if 1 not in labels:
        raise ValueError("calibrated model must predict class 1")
    return labels.index(1)


def _positive_probabilities(
        model: FittedBettingModel,
        features: pd.DataFrame) -> list[float]:
    """Return the calibrated probability of class 1 for each row."""
    matrix = model.predict_proba(features)
    if matrix.ndim != 2 or matrix.shape[1] != 2:
        raise ValueError(
            "calibrated probabilities must have two classes")
    if matrix.shape[0] != len(features):
        raise ValueError(
            "calibrated probabilities must cover every row")
    return [_require_probability(value) for value in matrix[:, 1]]


def _score_test(
        windows: _Windows,
        probabilities: Sequence[float],
        threshold: float
        ) -> tuple[
            tuple[
                SliceMetrics,
                tuple[SegmentMetrics, ...],
                tuple[SegmentMetrics, ...]],
            list[int]]:
    """Score the test block overall and by league and market."""
    labels = [int(value) for value in windows.test_labels.tolist()]
    odds = [float(value) for value in windows.test_odds.tolist()]
    chances = [float(value) for value in probabilities]
    prediction_ids = [
        int(value) for value in windows.test_prediction_id.tolist()]
    odds_ids = [int(value) for value in windows.test_odds_id.tolist()]
    overall = _slice_metrics(
        labels, chances, odds, prediction_ids, odds_ids, threshold)
    leagues = _segment_names(windows.test_features["league_id"])
    markets = _segment_names(windows.test_features["market_family"])
    slices = (
        overall,
        _grouped(
            leagues, labels, chances, odds,
            prediction_ids, odds_ids, threshold),
        _grouped(
            markets, labels, chances, odds,
            prediction_ids, odds_ids, threshold))
    return slices, _bet_prediction_ids(prediction_ids, chances, threshold)


def _grouped(
        names: Sequence[str],
        labels: Sequence[int],
        chances: Sequence[float],
        odds: Sequence[float],
        prediction_ids: Sequence[int],
        odds_ids: Sequence[int],
        threshold: float) -> tuple[SegmentMetrics, ...]:
    """Build one slice per distinct segment name."""
    segments: list[SegmentMetrics] = []
    for name in sorted(set(names)):
        chosen = [
            index for index, item in enumerate(names) if item == name]
        segments.append(SegmentMetrics(
            name=name,
            metrics=_slice_metrics(
                [labels[index] for index in chosen],
                [chances[index] for index in chosen],
                [odds[index] for index in chosen],
                [prediction_ids[index] for index in chosen],
                [odds_ids[index] for index in chosen],
                threshold)))
    return tuple(segments)


def _segment_names(values: pd.Series) -> list[str]:
    """Return a stable label for each categorical cell."""
    return [_segment_name(value) for value in values.tolist()]


def _segment_name(value: object) -> str:
    """Map a missing category to one shared segment name."""
    if _is_missing(value):
        return _MISSING_SEGMENT
    text = str(value).strip()
    if text == "":
        return _MISSING_SEGMENT
    return text


def _slice_metrics(
        labels: Sequence[int],
        chances: Sequence[float],
        odds: Sequence[float],
        prediction_ids: Sequence[int],
        odds_ids: Sequence[int],
        threshold: float) -> SliceMetrics:
    """Return probability scores and unit-stake ROI of the bets."""
    _require_alignment(labels, chances, odds)
    ordered_labels, ordered_chances, ordered_odds = _ordered_by_pair(
        prediction_ids, odds_ids, labels, chances, odds)
    bets = _bet_indexes(ordered_chances, threshold)
    bet_labels = [ordered_labels[index] for index in bets]
    bet_odds = [ordered_odds[index] for index in bets]
    return SliceMetrics(
        brier=brier_score(ordered_chances, ordered_labels),
        log_loss=log_loss_score(ordered_chances, ordered_labels),
        reliability=reliability_score(ordered_chances, ordered_labels),
        roi=unit_stake_roi(bet_labels, bet_odds),
        hit_rate=unit_stake_hit_rate(bet_labels),
        row_count=len(labels),
        bet_count=len(bets),
        no_bet_count=len(labels) - len(bets))


def _ordered_by_pair(
        prediction_ids: Sequence[int],
        odds_ids: Sequence[int],
        labels: Sequence[int],
        chances: Sequence[float],
        odds: Sequence[float]
        ) -> tuple[list[int], list[float], list[float]]:
    """Return labels, probabilities and prices in pair order.

    The order matches ``evaluate_selections``, so the float sums
    agree.
    """
    rows = list(zip(prediction_ids, odds_ids, labels, chances, odds))
    rows.sort(key=lambda item: (int(item[0]), int(item[1])))
    ordered_labels = [int(item[2]) for item in rows]
    ordered_chances = [float(item[3]) for item in rows]
    ordered_odds = [float(item[4]) for item in rows]
    return ordered_labels, ordered_chances, ordered_odds


def _brier_in_pair_order(
        rows: _Rows,
        chances: Sequence[float]) -> float:
    """Return Brier in evaluation pair order."""
    labels, ordered, _prices = _ordered_by_pair(
        [int(value) for value in rows.prediction_id.tolist()],
        [int(value) for value in rows.odds_id.tolist()],
        [int(value) for value in rows.labels.tolist()],
        [float(value) for value in chances],
        [0.0] * len(chances))
    return brier_score(ordered, labels)


def _bet_indexes(
        chances: Sequence[float],
        threshold: float) -> list[int]:
    """Return rows whose probability is above the strategy threshold."""
    # Sekcja 6.5 daje bet dopiero powyżej progu, nie przy równości.
    return [
        index for index, probability in enumerate(chances)
        if probability > threshold]


def _bet_prediction_ids(
        prediction_ids: Sequence[int],
        chances: Sequence[float],
        threshold: float) -> list[int]:
    """Return the sorted ids of rows marked bet."""
    chosen = [
        int(prediction_ids[index])
        for index in _bet_indexes(chances, threshold)]
    chosen.sort()
    return chosen


def _write_artifacts(
        model: FittedBettingModel,
        config: BettingTrainingConfig,
        windows: _Windows,
        method: str,
        scores: dict[str, float],
        slices: tuple[
            SliceMetrics,
            tuple[SegmentMetrics, ...],
            tuple[SegmentMetrics, ...]],
        bet_ids: list[int],
        threshold: float,
        artifact_dir: Path) -> tuple[str, str]:
    """Write the model, then the hashes that describe that file."""
    directory = ensure_artifact_dir(Path(artifact_dir))
    model_path = save_model_artifact(directory, model)
    # Skrót jest z bajtów już zapisanych, więc meta powstaje później.
    digest = model_file_fingerprint(model_path)
    columns = list(windows.train_features.columns)
    save_feature_columns(directory, columns)
    schema = feature_schema_fingerprint(columns)
    save_metrics(
        directory,
        _metrics_payload(
            slices, method, scores, windows, bet_ids, threshold))
    save_meta(directory, _meta_payload(config, method, schema, digest))
    return schema, digest


def _metrics_payload(
        slices: tuple[
            SliceMetrics,
            tuple[SegmentMetrics, ...],
            tuple[SegmentMetrics, ...]],
        method: str,
        scores: dict[str, float],
        windows: _Windows,
        bet_ids: list[int],
        threshold: float) -> dict[str, object]:
    """Return the JSON report for the test window."""
    test, by_league, by_market = slices
    return {
        "brier": test.brier,
        "log_loss": test.log_loss,
        "reliability": test.reliability,
        "roi": test.roi,
        "hit_rate": test.hit_rate,
        "row_count": test.row_count,
        "bet_count": test.bet_count,
        "no_bet_count": test.no_bet_count,
        "bet_prediction_ids": bet_ids,
        "probability_threshold": threshold,
        "by_league": _named_payload(by_league),
        "by_market": _named_payload(by_market),
        "calibration_method": method,
        "calibration_brier": scores,
        "split_rows": {
            "train": len(windows.train_labels),
            "calibration": len(windows.calibration_labels),
            "test": len(windows.test_labels)}}


def _named_payload(
        segments: tuple[SegmentMetrics, ...]) -> dict[str, dict[str, object]]:
    """Return segment slices keyed by name."""
    payload: dict[str, dict[str, object]] = {}
    for segment in segments:
        payload[segment.name] = _slice_payload(segment.metrics)
    return payload


def _slice_payload(metrics: SliceMetrics) -> dict[str, object]:
    """Return one slice as plain JSON values."""
    return {
        "brier": metrics.brier,
        "log_loss": metrics.log_loss,
        "reliability": metrics.reliability,
        "roi": metrics.roi,
        "hit_rate": metrics.hit_rate,
        "row_count": metrics.row_count,
        "bet_count": metrics.bet_count,
        "no_bet_count": metrics.no_bet_count}


def _meta_payload(
        config: BettingTrainingConfig,
        method: str,
        schema: str,
        digest: str) -> dict[str, str]:
    """Return run metadata, including both fingerprints."""
    return {
        "model_name": config.model_name,
        "algorithm": config.algorithm,
        "calibration_method": method,
        "feature_schema_fingerprint": schema,
        "model_fingerprint": digest}


def _require_alignment(
        labels: Sequence[int],
        chances: Sequence[float],
        odds: Sequence[float]) -> None:
    """Reject an empty slice or a trio of different lengths."""
    if not labels:
        raise ValueError("a scored slice must contain a row")
    if not (len(labels) == len(chances) == len(odds)):
        raise ValueError(
            "labels, probabilities and odds must align")


def _require_probability(value: object) -> float:
    """Reject a calibrated probability outside the unit interval."""
    if isinstance(value, bool):
        raise ValueError(
            "calibrated probability must be between 0 and 1")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "calibrated probability must be between 0 and 1") from exc
    if not math.isfinite(number) or number < 0.0 or number > 1.0:
        raise ValueError(
            "calibrated probability must be between 0 and 1")
    return number


def _require_dataset(dataset: object) -> None:
    """Reject a value that is not the betting dataset contract."""
    if not isinstance(dataset, BettingDataset):
        raise ValueError("dataset must be a BettingDataset")


def _require_config(config: object) -> None:
    """Reject a trainer config from outside the training contract."""
    if not isinstance(config, BettingTrainingConfig):
        raise ValueError("config must be a BettingTrainingConfig")


def _require_strategy(strategy: object) -> None:
    """Reject a threshold config from outside the strategy contract."""
    if not isinstance(strategy, BettingStrategyConfig):
        raise ValueError("strategy must be a BettingStrategyConfig")


def _validate_slice(metrics: SliceMetrics) -> None:
    """Reject a slice whose scores disagree with its row count."""
    _require_count(metrics.row_count)
    _require_tally("bet_count", metrics.bet_count)
    _require_tally("no_bet_count", metrics.no_bet_count)
    if metrics.bet_count + metrics.no_bet_count != metrics.row_count:
        raise ValueError(
            "bet_count and no_bet_count must cover the slice")
    _require_unit_interval("brier", metrics.brier)
    _require_non_negative("log_loss", metrics.log_loss)
    _require_unit_interval("reliability", metrics.reliability)
    _require_selection_scores(metrics)


def _validate_report(report: TrainingReport) -> None:
    """Reject a report whose fingerprints or slices disagree."""
    _require_fingerprint(
        "feature_schema_fingerprint",
        report.feature_schema_fingerprint)
    _require_fingerprint("model_fingerprint", report.model_fingerprint)
    if report.calibration_method not in _CALIBRATION_METHODS:
        raise ValueError(
            "calibration_method must be sigmoid or isotonic")
    if not isinstance(report.test, SliceMetrics):
        raise ValueError("test must be a SliceMetrics")
    _require_segments(
        "by_league",
        report.by_league,
        report.test.row_count,
        report.test.bet_count)
    _require_segments(
        "by_market",
        report.by_market,
        report.test.row_count,
        report.test.bet_count)


def _require_segments(
        name: str,
        segments: object,
        row_count: int,
        bet_count: int) -> None:
    """Require the named slices to cover each test row and bet once."""
    if not isinstance(segments, tuple) or not segments:
        raise ValueError(f"{name} must cover the test window")
    names: list[str] = []
    covered = 0
    bets = 0
    for segment in segments:
        if not isinstance(segment, SegmentMetrics):
            raise ValueError(f"{name} must contain SegmentMetrics values")
        names.append(segment.name)
        covered += segment.metrics.row_count
        bets += segment.metrics.bet_count
    if len(names) != len(set(names)):
        raise ValueError(f"{name} names must be unique")
    if covered != row_count:
        raise ValueError(f"{name} must cover the test window")
    if bets != bet_count:
        raise ValueError(f"{name} must cover the test bets")


def _require_fingerprint(name: str, value: object) -> None:
    """Reject a digest that is not lowercase SHA-256 hex."""
    if (
            not isinstance(value, str)
            or len(value) != _SHA256_HEX_LENGTH
            or any(char not in _HEX_DIGITS for char in value)):
        raise ValueError(f"{name} must be a SHA-256 hex digest")


def _require_selection_scores(metrics: SliceMetrics) -> None:
    """Require ROI and hit rate only when a row was bet."""
    if metrics.bet_count == 0:
        if metrics.roi is not None or metrics.hit_rate is not None:
            raise ValueError(
                "roi and hit_rate must be empty when nothing is bet")
        return
    if metrics.roi is None or metrics.hit_rate is None:
        raise ValueError(
            "roi and hit_rate are required when a row is bet")
    _require_roi(metrics.roi)
    _require_unit_interval("hit_rate", metrics.hit_rate)


def _require_count(value: int) -> None:
    """Reject a count that is not a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("row_count must be a positive integer")


def _require_tally(name: str, value: int) -> None:
    """Reject a count that is not a non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _require_unit_interval(name: str, value: float) -> None:
    """Reject a metric outside the closed unit interval."""
    if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0.0
            or value > 1.0):
        raise ValueError(f"{name} must be between 0 and 1")


def _require_non_negative(name: str, value: float) -> None:
    """Reject a missing or negative score."""
    if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0.0):
        raise ValueError(f"{name} must be a finite number >= 0")


def _require_roi(value: float) -> None:
    """Reject ROI below a total loss of the unit stake."""
    if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < -1.0):
        raise ValueError("roi must be a finite number >= -1")


def _is_missing(value: object) -> bool:
    """Return whether a categorical cell is null."""
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)


def _is_finite(value: object) -> bool:
    """Return whether the value is a finite int or float."""
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)
