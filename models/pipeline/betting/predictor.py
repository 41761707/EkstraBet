"""Score stored candidates and mark each one bet or no-bet.

The artifact is loaded from disk. No verdict is written and no
database connection is opened.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from numbers import Integral
from pathlib import Path

import pandas as pd

from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.domain import DecisionKind
from models.pipeline.betting.domain import SelectionDecision
from models.pipeline.betting.features import build_candidate_features
from models.pipeline.betting.trainer import FittedBettingModel
from models.pipeline.betting.trainer import require_feature_schema
from models.pipeline.core.artifacts import ARTIFACT_MODEL_NAME
from models.pipeline.core.artifacts import load_feature_columns
from models.pipeline.core.artifacts import load_meta
from models.pipeline.core.artifacts import load_metrics
from models.pipeline.core.artifacts import load_model_artifact
from models.pipeline.core.artifacts import model_file_fingerprint


_CANDIDATE_COLUMNS = (
    "prediction_id",
    "odds_id",
    "match_id",
    "event_id",
    "model_id",
    "bookmaker_id",
    "league_id",
    "kickoff",
    "value_pct",
    "odds",
    "devig_probability")


@dataclass(frozen=True)
class ScoredCandidate:
    """One kept candidate and its calibrated hit probability.

    ``BettingCandidate`` has no place for that probability. The score
    stays beside the candidate until the threshold makes a decision.
    """

    candidate: BettingCandidate
    calibrated_probability: float

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, BettingCandidate):
            raise ValueError("candidate must be a BettingCandidate")
        _require_probability(self.calibrated_probability)


class BettingMetaPredictor:
    """Decide bet or no-bet for each candidate of one artifact.

    Scoring loads the artifact. ``check_model_ready`` only reads the
    saved report, so a failed gate does not by itself stop scoring.
    Writing a verdict is a later step.
    """

    def __init__(
            self,
            artifact_dir: Path,
            strategy: BettingStrategyConfig) -> None:
        if not isinstance(strategy, BettingStrategyConfig):
            raise ValueError("strategy must be a BettingStrategyConfig")
        self.artifact_dir = Path(artifact_dir)
        self.strategy = strategy

    def check_model_ready(self) -> bool:
        """Return whether the out-of-sample report passes the gate.

        The gate is ``brier`` at or below ``max_brier``, reliability
        at or below ``max_reliability_error``, and ``roi`` at or above
        ``min_roi``. A missing or non-numeric metric keeps the
        artifact unready. Candidates are not scored here.
        """
        return _report_passes_gate(self.artifact_dir, self.strategy)

    def decide(
            self,
            candidates: pd.DataFrame) -> list[SelectionDecision]:
        """Score the frame and apply this predictor's threshold."""
        scored = score_candidates(candidates, self.artifact_dir)
        return select_candidates(scored, self.strategy)


def score_candidates(
        candidates: pd.DataFrame,
        artifact_dir: Path) -> list[ScoredCandidate]:
    """Return a calibrated probability for each kept candidate.

    Column names are checked against ``meta.json`` before the model
    runs. The ``model.joblib`` digest must match that file too.
    Odds of 1 or less and a probability outside 0-100 are left out.
    """
    frame = _require_frame(candidates)
    features = build_candidate_features(frame)
    directory = Path(artifact_dir)
    columns = _require_scoring_schema(directory, features)
    model = _load_model(directory)
    if features.empty:
        return []
    ordered = features.loc[:, columns].copy()
    probabilities = _positive_probabilities(model, ordered)
    return _scored_rows(frame, ordered, probabilities)


def select_candidates(
        scored: Sequence[ScoredCandidate],
        config: BettingStrategyConfig) -> list[SelectionDecision]:
    """Mark bet only when the probability is above the threshold.

    A price below ``min_odds`` stays no-bet even when the probability
    clears the threshold. Equality on the threshold stays no-bet.
    A price equal to ``min_odds`` may still be a bet. Input order is
    preserved. Each candidate is decided on its own, with no stake.
    """
    if not isinstance(config, BettingStrategyConfig):
        raise ValueError("config must be a BettingStrategyConfig")
    _require_scored(scored)
    return [
        _decision(item, config.probability_threshold, config.min_odds)
        for item in scored]


def _report_passes_gate(
        artifact_dir: Path,
        strategy: BettingStrategyConfig) -> bool:
    """Return whether metrics.json meets the strategy caps."""
    # Bramka to pułap Brier, pułap błędu reliability i minimalne ROI.
    # Brak liczby zostawia artefakt niegotowy i nie jest wyjątkiem.
    metrics = load_metrics(artifact_dir)
    brier = _metric(metrics, "brier")
    reliability = _metric(metrics, "reliability")
    roi = _metric(metrics, "roi")
    if brier is None or reliability is None or roi is None:
        return False
    if brier < 0.0 or brier > 1.0:
        return False
    if reliability < 0.0 or reliability > 1.0:
        return False
    if roi < -1.0:
        return False
    if brier > strategy.max_brier:
        return False
    if reliability > strategy.max_reliability_error:
        return False
    return roi >= strategy.min_roi


def _metric(metrics: dict[str, object], name: str) -> float | None:
    """Return a finite number, or none when the metric is unusable."""
    if name not in metrics:
        return None
    value = metrics[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _require_frame(candidates: pd.DataFrame) -> pd.DataFrame:
    """Reject a frame that is not one candidate row per index."""
    if not isinstance(candidates, pd.DataFrame):
        raise ValueError("candidates must be a DataFrame")
    missing = [
        name for name in _CANDIDATE_COLUMNS
        if name not in candidates.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"candidates are missing columns: {joined}")
    if not candidates.index.is_unique:
        raise ValueError("candidate index must be unique")
    return candidates


def _require_scoring_schema(
        artifact_dir: Path,
        features: pd.DataFrame) -> list[str]:
    """Return saved columns once the matrix and the digest agree."""
    saved = load_feature_columns(artifact_dir)
    missing = [
        name for name in saved
        if name not in features.columns]
    if missing:
        # Brak kolumny ma własny błąd. Skrót i tak by się nie zgodził.
        raise ValueError(f"missing feature column: {missing[0]}")
    require_feature_schema(artifact_dir, saved)
    return saved


def _load_model(artifact_dir: Path) -> FittedBettingModel:
    """Load the calibrator after its file digest matches ``meta.json``."""
    # Inny skrót bajtów niż w meta.json zatrzymuje inferencję.
    directory = Path(artifact_dir)
    digest = model_file_fingerprint(directory / ARTIFACT_MODEL_NAME)
    stored = load_meta(directory).get("model_fingerprint")
    if stored != digest:
        raise ValueError(
            "model file fingerprint does not match the artifact")
    model = load_model_artifact(directory)
    if not isinstance(model, FittedBettingModel):
        raise ValueError("artifact model must be a FittedBettingModel")
    return model


def _positive_probabilities(
        model: FittedBettingModel,
        features: pd.DataFrame) -> list[float]:
    """Return the calibrated probability of class 1 for each row."""
    matrix = model.predict_proba(features)
    if matrix.ndim != 2 or matrix.shape != (len(features), 2):
        raise ValueError(
            "calibrated probabilities must have two classes")
    return [
        _require_probability(value)
        for value in matrix[:, 1]]


def _scored_rows(
        candidates: pd.DataFrame,
        features: pd.DataFrame,
        probabilities: Sequence[float]) -> list[ScoredCandidate]:
    """Attach each probability to the candidate that produced it."""
    if len(probabilities) != len(features):
        raise ValueError(
            "calibrated probabilities must cover every row")
    scored: list[ScoredCandidate] = []
    for label, probability in zip(features.index, probabilities):
        scored.append(ScoredCandidate(
            candidate=_candidate_from_row(candidates.loc[label]),
            calibrated_probability=probability))
    return scored


def _candidate_from_row(row: pd.Series) -> BettingCandidate:
    """Build the domain candidate stored on a scored row."""
    return BettingCandidate(
        prediction_id=_positive_int(
            "prediction_id", row["prediction_id"]),
        odds_id=_positive_int("odds_id", row["odds_id"]),
        match_id=_positive_int("match_id", row["match_id"]),
        event_id=_positive_int("event_id", row["event_id"]),
        model_id=_positive_int("model_id", row["model_id"]),
        bookmaker_id=_positive_int(
            "bookmaker_id", row["bookmaker_id"]),
        league_id=_optional_id(row["league_id"]),
        kickoff=_kickoff(row["kickoff"]),
        value_pct=_finite_float("value_pct", row["value_pct"]),
        odds=_finite_float("odds", row["odds"]))


def _decision(
        scored: ScoredCandidate,
        threshold: float,
        min_odds: float) -> SelectionDecision:
    """Apply the odds floor and the threshold, one row at a time."""
    # Sekcja 6.5: bet dopiero powyżej progu. Równość zostaje no_bet.
    # Kurs poniżej min_odds nie jest wyborem, niezależnie od progu.
    probability = scored.calibrated_probability
    if scored.candidate.odds < min_odds:
        kind: DecisionKind = "no_bet"
        reason = "odds below minimum"
    elif probability > threshold:
        kind = "bet"
        reason = "calibrated probability above threshold"
    else:
        kind = "no_bet"
        reason = "calibrated probability at or below threshold"
    return SelectionDecision(
        decision=kind,
        candidate=scored.candidate,
        calibrated_probability=probability,
        reason=reason)


def _require_scored(scored: Sequence[ScoredCandidate]) -> None:
    """Reject anything other than scored candidates."""
    if isinstance(scored, (str, bytes)) or not isinstance(scored, Sequence):
        raise ValueError("scored must be a sequence of ScoredCandidate")
    for item in scored:
        if not isinstance(item, ScoredCandidate):
            raise ValueError(
                "scored must contain ScoredCandidate values")


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


def _positive_int(name: str, value: object) -> int:
    """Return a positive int, including integral floats and numpy ints."""
    if isinstance(value, bool) or isinstance(value, str):
        raise ValueError(f"{name} must be a positive integer")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"{name} must be a positive integer")
        number = int(value)
    elif isinstance(value, Integral):
        number = int(value)
    else:
        raise ValueError(f"{name} must be a positive integer")
    if number <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return number


def _optional_id(value: object) -> int | None:
    """Return a league id, or none when the match has no league."""
    if _missing(value):
        return None
    return _positive_int("league_id", value)


def _kickoff(value: object) -> datetime:
    """Return the kickoff when it is already a datetime."""
    if isinstance(value, datetime):
        return value
    raise ValueError("kickoff must be a datetime")


def _finite_float(name: str, value: object) -> float:
    """Return a finite float and reject booleans."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _missing(value: object) -> bool:
    """Return whether a cell is null."""
    if value is None:
        return True
    try:
        missing = pd.isna(value)
        flag = bool(missing)
    except (TypeError, ValueError):
        return False
    return flag
