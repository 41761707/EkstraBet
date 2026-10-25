"""CLI actions for the betting meta-model.

Dataset, training, evaluation and backtest read finished pairs.
Prediction appends verdicts and does not train. Backtest does not
write ``model.joblib``, so a report cannot change its fingerprint.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from models.pipeline.betting.baselines import ConfidenceSingleStrategy
from models.pipeline.betting.baselines import NoBetStrategy
from models.pipeline.betting.baselines import PositiveEvSingleStrategy
from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.config import BettingTrainingConfig
from models.pipeline.betting.config import load_betting_strategy_config
from models.pipeline.betting.config import load_betting_training_config
from models.pipeline.betting.dataset_builder import BettingDataset
from models.pipeline.betting.dataset_builder import DatasetManifest
from models.pipeline.betting.dataset_builder import build_betting_dataset
from models.pipeline.betting.dataset_builder import build_dataset_manifest
from models.pipeline.betting.dataset_builder import build_walk_forward_splits
from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.evaluation import EvaluationReport
from models.pipeline.betting.evaluation import evaluate_selections
from models.pipeline.betting.features import feature_schema_fingerprint
from models.pipeline.betting.predictor import BettingMetaPredictor
from models.pipeline.betting.recommendation import PredictReport
from models.pipeline.betting.recommendation import run_betting_predict
from models.pipeline.betting.trainer import TrainingReport
from models.pipeline.betting.trainer import train_meta_model
from models.pipeline.core.artifacts import load_meta
from models.pipeline.data.betting_candidate_repository import (
    attach_settlement_columns)
from models.pipeline.data.betting_candidate_repository import (
    fetch_candidates)


# Predykcje nie mają znacznika kwotowania, a komendy historii nie biorą
# zakresu dat. Dolna granica obejmuje każdy zapisany kickoff.
_HISTORY_START = datetime(1970, 1, 1)
_NOT_READY = "betting artifact is not ready; wrote no recommendations"
_NO_FINISHED = "no finished betting candidates"
_BASELINES = (
    ("no_bet", NoBetStrategy()),
    ("confidence_single", ConfidenceSingleStrategy()),
    ("positive_ev_single", PositiveEvSingleStrategy()))


def finished_candidate_frame(
        strategy: BettingStrategyConfig,
        horizon_end: datetime | None = None) -> pd.DataFrame:
    """Return candidate rows kicked off before ``horizon_end``.

    The default end is the current naive time. Settlement columns are
    attached so the dataset builder can label finished matches.
    """
    if not isinstance(strategy, BettingStrategyConfig):
        raise ValueError("strategy must be a BettingStrategyConfig")
    end = _naive_now() if horizon_end is None else _naive(horizon_end)
    frame = fetch_candidates(_HISTORY_START, end, strategy)
    return attach_settlement_columns(frame)


def run_build_betting_dataset(args: object) -> dict[str, object]:
    """Build the finished dataset and its walk-forward manifest."""
    training, strategy = _configs(args)
    _source, dataset = _finished_dataset(strategy)
    manifest = _manifest(dataset, training)
    return _dataset_payload(dataset, manifest)


def run_train_betting_meta(args: object) -> TrainingReport:
    """Train on finished pairs and write the artifact. No verdicts."""
    training, strategy = _configs(args)
    _source, dataset = _finished_dataset(strategy)
    return train_meta_model(
        dataset,
        training,
        _artifact_dir(args),
        strategy=strategy)


def run_evaluate_betting_meta(args: object) -> dict[str, object]:
    """Score the saved model on the untouched test window."""
    training, strategy = _configs(args)
    source, dataset = _finished_dataset(strategy)
    frame, manifest = _test_frame(source, dataset, training)
    report = _score_saved(
        frame,
        dataset,
        _artifact_dir(args),
        strategy)
    return {
        "calibration_method": _saved_calibration_method(
            _artifact_dir(args)),
        "feature_schema_fingerprint": (
            manifest.feature_schema_fingerprint),
        "report": report}


def run_backtest_betting_strategy(args: object) -> dict[str, object]:
    """Compare baselines and the saved model on the same pairs.

    A split or a missing artifact leaves the baseline reports in place.
    This command does not fit a model and does not insert verdicts.
    """
    training, strategy = _configs(args)
    source, dataset = _finished_dataset(strategy)
    frame, split_error = _comparison_frame(source, dataset, training)
    payload: dict[str, object] = {
        "pair_role": "finished" if split_error else "test",
        "pair_count": len(frame),
        "feature_schema_fingerprint": _schema_fingerprint(dataset),
        "baselines": _baseline_reports(frame, dataset)}
    if split_error is not None:
        payload["meta_model"] = {"error": split_error}
        return payload
    payload["meta_model"] = _meta_or_error(
        frame, dataset, _artifact_dir(args), strategy)
    return payload


def run_predict_betting_meta(args: object) -> PredictReport:
    """Insert missing future verdicts. An unready artifact writes none."""
    strategy = load_betting_strategy_config(_strategy_path(args))
    artifact_dir = _artifact_dir(args)
    predictor = BettingMetaPredictor(artifact_dir, strategy)
    # Bramka jest przed zapisem. Sam raport zerowy kończyłby się kodem 0.
    if not predictor.check_model_ready():
        raise ValueError(_NOT_READY)
    return run_betting_predict(
        artifact_dir,
        _naive(getattr(args, "as_of")),
        strategy)


def _configs(
        args: object
        ) -> tuple[BettingTrainingConfig, BettingStrategyConfig]:
    """Load the two explicit JSON configs for one history command."""
    training = load_betting_training_config(_training_path(args))
    strategy = load_betting_strategy_config(_strategy_path(args))
    return training, strategy


def _finished_dataset(
        strategy: BettingStrategyConfig
        ) -> tuple[pd.DataFrame, BettingDataset]:
    """Return labeled pairs, or fail when none of them settled."""
    source = finished_candidate_frame(strategy)
    dataset = build_betting_dataset(source)
    if len(dataset.features) == 0:
        raise ValueError(_NO_FINISHED)
    return source, dataset


def _manifest(
        dataset: BettingDataset,
        training: BettingTrainingConfig) -> DatasetManifest:
    """Cut the dataset into train, calibration and test."""
    splits = build_walk_forward_splits(dataset.split_frame(), training)
    return build_dataset_manifest(dataset.features, splits)


def _test_frame(
        source: pd.DataFrame,
        dataset: BettingDataset,
        training: BettingTrainingConfig
        ) -> tuple[pd.DataFrame, DatasetManifest]:
    """Return the test-window rows and the manifest that names them."""
    manifest = _manifest(dataset, training)
    test = next(split for split in manifest.splits if split.role == "test")
    return source.loc[list(test.row_labels)], manifest


def _comparison_frame(
        source: pd.DataFrame,
        dataset: BettingDataset,
        training: BettingTrainingConfig
        ) -> tuple[pd.DataFrame, str | None]:
    """Use the test window, or every finished row when it cannot be cut."""
    try:
        frame, _manifest = _test_frame(source, dataset, training)
    except ValueError as exc:
        finished = source.loc[list(dataset.features.index)]
        return finished, str(exc)
    return frame, None


def _dataset_payload(
        dataset: BettingDataset,
        manifest: DatasetManifest) -> dict[str, object]:
    """Return counts and the split manifest. Not the feature matrix."""
    return {
        "row_count": len(dataset.features),
        "match_count": int(dataset.match_id.nunique()),
        "feature_schema_fingerprint": (
            manifest.feature_schema_fingerprint),
        "splits": manifest.splits}


def _baseline_reports(
        frame: pd.DataFrame,
        dataset: BettingDataset) -> dict[str, EvaluationReport]:
    """Score each reference strategy on one shared set of pairs."""
    candidates = _candidates(frame)
    outcomes = _outcomes(dataset, list(frame.index))
    fingerprint = _schema_fingerprint(dataset)
    reports: dict[str, EvaluationReport] = {}
    for name, strategy in _BASELINES:
        reports[name] = evaluate_selections(
            strategy.decide(candidates),
            outcomes,
            feature_schema_fingerprint=fingerprint)
    return reports


def _score_saved(
        frame: pd.DataFrame,
        dataset: BettingDataset,
        artifact_dir: Path,
        strategy: BettingStrategyConfig) -> EvaluationReport:
    """Decide with the saved model and score those decisions."""
    decisions = BettingMetaPredictor(artifact_dir, strategy).decide(frame)
    return evaluate_selections(
        decisions,
        _outcomes(dataset, list(frame.index)),
        feature_schema_fingerprint=_schema_fingerprint(dataset))


def _meta_or_error(
        frame: pd.DataFrame,
        dataset: BettingDataset,
        artifact_dir: Path,
        strategy: BettingStrategyConfig) -> object:
    """Return the meta-model report, or the error that blocked it."""
    try:
        return _score_saved(frame, dataset, artifact_dir, strategy)
    except (OSError, ValueError) as exc:
        return {"error": str(exc)}


def _saved_calibration_method(artifact_dir: Path) -> str | None:
    """Return the calibrator name stored beside the model."""
    method = load_meta(artifact_dir).get("calibration_method")
    if not isinstance(method, str) or not method.strip():
        return None
    return method


def _candidates(frame: pd.DataFrame) -> list[BettingCandidate]:
    """Rebuild domain rows for the baseline strategies."""
    return [
        BettingCandidate(
            prediction_id=int(row.prediction_id),
            odds_id=int(row.odds_id),
            match_id=int(row.match_id),
            event_id=int(row.event_id),
            model_id=int(row.model_id),
            bookmaker_id=int(row.bookmaker_id),
            league_id=_optional_league(row.league_id),
            kickoff=_kickoff(row.kickoff),
            value_pct=float(row.value_pct),
            odds=float(row.odds))
        for row in frame.itertuples(index=False)]


def _outcomes(
        dataset: BettingDataset,
        labels: list[object]) -> dict[tuple[int, int], int]:
    """Map each kept pair to the label already stored on the dataset."""
    outcomes: dict[tuple[int, int], int] = {}
    for label in labels:
        pair = (
            int(dataset.prediction_id.loc[label]),
            int(dataset.odds_id.loc[label]))
        outcomes[pair] = int(dataset.labels.loc[label])
    return outcomes


def _schema_fingerprint(dataset: BettingDataset) -> str:
    """Hash the feature columns of one dataset."""
    return feature_schema_fingerprint(list(dataset.features.columns))


def _training_path(args: object) -> Path:
    return Path(getattr(args, "training_config"))


def _strategy_path(args: object) -> Path:
    return Path(getattr(args, "strategy_config"))


def _artifact_dir(args: object) -> Path:
    return Path(getattr(args, "artifact_dir"))


def _naive_now() -> datetime:
    """Current local time without a timezone."""
    return datetime.now().replace(microsecond=0)


def _naive(value: object) -> datetime:
    """Reject an aware clock. Prediction kickoffs have no offset."""
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise ValueError("as_of must be a naive datetime")
    return value


def _kickoff(value: object) -> datetime:
    """Normalize one kickoff to a naive datetime."""
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = pd.Timestamp(value).to_pydatetime()
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _optional_league(value: object) -> int | None:
    """Return a league id, or none when the match has no league."""
    if _missing(value):
        return None
    return int(value)


def _missing(value: object) -> bool:
    """Return whether a cell is null."""
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)
