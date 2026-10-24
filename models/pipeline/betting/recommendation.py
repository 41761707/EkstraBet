"""Write verdicts for future pairs without training again.

A ready artifact is scored once. Each new pair gets one INSERT.
A duplicate key is left as it is. Nothing is updated.
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from numbers import Integral
from numbers import Real
from pathlib import Path

import pandas as pd
from mysql.connector import IntegrityError

from backend.database import get_db_connection
from models.pipeline.betting.config import BettingStrategyConfig
from models.pipeline.betting.config import load_betting_strategy_config
from models.pipeline.betting.domain import BettingRecommendation
from models.pipeline.betting.domain import SelectionDecision
from models.pipeline.betting.predictor import BettingMetaPredictor
from models.pipeline.core.artifacts import ARTIFACT_MODEL_NAME
from models.pipeline.core.artifacts import load_meta
from models.pipeline.core.artifacts import (
    model_file_fingerprint as _artifact_fingerprint)
from models.pipeline.data.betting_candidate_repository import (
    BETTING_CANDIDATE_COLUMNS)
from models.pipeline.data.betting_candidate_repository import (
    fetch_candidates)


logger = logging.getLogger(__name__)

# Odczyt kandydatów jest przedziałem [od, do). Predykcja nie ma końca
# okna, więc górna data jest tylko granicą zapytania.
_OPEN_HORIZON = datetime(9999, 12, 31, 23, 59, 59)
_DUPLICATE_KEY = 1062
_FINGERPRINT_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
_STRATEGY_PATH = (
    Path(__file__).resolve().parents[2]
    / "configs"
    / "prediction"
    / "football_betting_strategy_v1.json")
_INSERT_SQL = """
INSERT INTO betting_recommendations (
    prediction_id,
    odds_id,
    decision,
    calibrated_probability,
    model_fingerprint
) VALUES (%s, %s, %s, %s, %s)
"""
_SCORED_PAIRS_SQL = """
SELECT prediction_id, odds_id
FROM betting_recommendations
WHERE model_fingerprint = %s
"""


@dataclass(frozen=True)
class PredictReport:
    """Counts from one prediction run that does not train.

    ``inserted_count`` is rows newly written. ``skipped_existing_count``
    is future pairs that already have this model file, plus rows a
    duplicate key refused. ``rejected_count`` is candidates dropped
    before a verdict because the pair is not usable.
    """

    inserted_count: int
    skipped_existing_count: int
    rejected_count: int

    def __post_init__(self) -> None:
        _require_count("inserted_count", self.inserted_count)
        _require_count(
            "skipped_existing_count",
            self.skipped_existing_count)
        _require_count("rejected_count", self.rejected_count)


def model_file_fingerprint(model_path: Path) -> str:
    """Return the SHA-256 hex digest of a model file's raw bytes.

    The digest identifies one saved training file. It is not a hash
    of the feature column names.
    """
    # Ten sam skrót zapisuje trening, bez drugiej implementacji.
    return _artifact_fingerprint(model_path)


def fetch_unscored_candidates(
        model_fingerprint: str,
        as_of: datetime) -> pd.DataFrame:
    """Return future pairs with no verdict for this model file.

    Kickoff is strictly later than ``as_of``. A row already stored
    for ``model_fingerprint`` is left out. The pool is the football
    strategy config. The read of stored pairs is one SELECT.
    """
    digest = _require_fingerprint(model_fingerprint)
    moment = _require_as_of(as_of)
    _future, unscored = _split_future(digest, moment, _load_strategy())
    return unscored


def write_recommendations(
        rows: Sequence[BettingRecommendation]) -> int:
    """Insert verdicts. A duplicate key is skipped and not updated.

    The statement lists the pair, the decision, the calibrated
    probability and the model file digest. It does not copy the
    base-model percentage or the bookmaker price. An empty sequence
    does not open a connection. Returns the number of new rows.
    """
    prepared = _require_recommendations(rows)
    if not prepared:
        return 0
    inserted = _insert_all(prepared)
    logger.info("Inserted %s betting recommendations", inserted)
    return inserted


def run_betting_predict(
        artifact_dir: Path,
        as_of: datetime) -> PredictReport:
    """Score missing future pairs and insert their verdicts.

    The artifact is not trained. When the report gate fails, the
    result is all zeros and no write connection is opened. A model
    file whose digest disagrees with ``meta.json`` stops the run
    before any read of pairs.
    """
    directory = Path(artifact_dir)
    moment = _require_as_of(as_of)
    strategy = _load_strategy()
    predictor = BettingMetaPredictor(directory, strategy)
    if not predictor.check_model_ready():
        logger.info(
            "Betting artifact is not ready; wrote no recommendations")
        return _empty_report()
    digest = _require_file_fingerprint(directory)
    report = _predict_ready(predictor, digest, moment, strategy)
    logger.info(
        "Betting predict inserted=%s skipped=%s rejected=%s",
        report.inserted_count,
        report.skipped_existing_count,
        report.rejected_count)
    return report


def _predict_ready(
        predictor: BettingMetaPredictor,
        digest: str,
        as_of: datetime,
        strategy: BettingStrategyConfig) -> PredictReport:
    """Score the unscored future pairs and insert what remains."""
    future, unscored = _split_future(digest, as_of, strategy)
    decisions = predictor.decide(unscored)
    rows = [_to_recommendation(item, digest) for item in decisions]
    inserted = write_recommendations(rows)
    skipped = len(future) - len(unscored)
    skipped += len(rows) - inserted
    return PredictReport(
        inserted_count=inserted,
        skipped_existing_count=skipped,
        rejected_count=len(unscored) - len(decisions))


def _split_future(
        model_fingerprint: str,
        as_of: datetime,
        strategy: BettingStrategyConfig
        ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return future pairs and the subset with no stored verdict."""
    future = _future_candidates(as_of, strategy)
    scored = _scored_pairs(model_fingerprint)
    return future, _without_scored(future, scored)


def _future_candidates(
        as_of: datetime,
        strategy: BettingStrategyConfig) -> pd.DataFrame:
    """Return pool pairs whose kickoff is later than ``as_of``."""
    if as_of >= _OPEN_HORIZON:
        raise ValueError("as_of must be earlier than the open horizon")
    frame = fetch_candidates(as_of, _OPEN_HORIZON, strategy)
    return _later_kickoffs(frame, as_of)


def _later_kickoffs(frame: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    """Drop pairs that are not strictly after ``as_of``."""
    _require_candidate_columns(frame)
    flags = [
        _kickoff_is_later(value, as_of)
        for value in frame["kickoff"].tolist()]
    mask = pd.Series(flags, index=frame.index)
    return frame.loc[mask].copy()


def _kickoff_is_later(value: object, as_of: datetime) -> bool:
    """Return whether this kickoff is strictly after ``as_of``."""
    if _is_missing(value):
        return False
    kickoff = _as_kickoff(value)
    if (kickoff.tzinfo is None) != (as_of.tzinfo is None):
        raise ValueError("as_of and kickoff timezones must match")
    return kickoff > as_of


def _as_kickoff(value: object) -> datetime:
    """Return a kickoff datetime or reject a value that is not one."""
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    raise ValueError("kickoff must be a datetime")


def _without_scored(
        frame: pd.DataFrame,
        scored: set[tuple[int, int]]) -> pd.DataFrame:
    """Drop pairs that already have a verdict for this file."""
    if frame.empty:
        return frame.copy()
    keep = [
        _pair_key(prediction_id, odds_id) not in scored
        for prediction_id, odds_id in zip(
            frame["prediction_id"].tolist(),
            frame["odds_id"].tolist())]
    mask = pd.Series(keep, index=frame.index)
    return frame.loc[mask].copy()


def _pair_key(prediction_id: object, odds_id: object) -> tuple[int, int]:
    """Return the stored pair identity used by the unique key."""
    return _pair_id(prediction_id), _pair_id(odds_id)


def _pair_id(value: object) -> int:
    """Return a positive pair id from a database cell."""
    if isinstance(value, bool) or isinstance(value, str):
        raise ValueError("pair id must be a positive integer")
    if isinstance(value, Integral):
        number = int(value)
    elif isinstance(value, Real):
        number = _integral_real(value)
    else:
        raise ValueError("pair id must be a positive integer")
    if number <= 0:
        raise ValueError("pair id must be a positive integer")
    return number


def _integral_real(value: Real) -> int:
    """Accept 10.0 from pandas and reject a fractional id."""
    number = float(value)
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError("pair id must be a positive integer")
    return int(number)


def _scored_pairs(model_fingerprint: str) -> set[tuple[int, int]]:
    """Return pairs already stored for this model file."""
    with get_db_connection() as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(_SCORED_PAIRS_SQL, (model_fingerprint,))
            fetched = cursor.fetchall()
        finally:
            cursor.close()
    return {_pair_key(row[0], row[1]) for row in fetched}


def _insert_all(rows: tuple[BettingRecommendation, ...]) -> int:
    """Insert every row and return how many were new."""
    inserted = 0
    with get_db_connection() as connection:
        cursor = connection.cursor()
        try:
            for row in rows:
                inserted += _insert_one(cursor, row)
            connection.commit()
        finally:
            cursor.close()
    return inserted


def _insert_one(cursor: Any, row: BettingRecommendation) -> int:
    """Insert one verdict. A duplicate key counts as zero."""
    try:
        cursor.execute(_INSERT_SQL, _insert_params(row))
    except IntegrityError as exc:
        if getattr(exc, "errno", None) != _DUPLICATE_KEY:
            raise
        # Duplikat klucza zostaje bez drugiego zapisu.
        return 0
    return 1


def _insert_params(
        row: BettingRecommendation) -> tuple[object, ...]:
    """Return the five stored fields and no source values."""
    return (
        row.prediction_id,
        row.odds_id,
        row.decision,
        row.calibrated_probability,
        row.model_fingerprint)


def _to_recommendation(
        decision: SelectionDecision,
        digest: str) -> BettingRecommendation:
    """Copy the verdict without the price or the base percentage."""
    return BettingRecommendation(
        prediction_id=decision.candidate.prediction_id,
        odds_id=decision.candidate.odds_id,
        decision=decision.decision,
        calibrated_probability=decision.calibrated_probability,
        model_fingerprint=digest)


def _require_file_fingerprint(artifact_dir: Path) -> str:
    """Return the model digest once it matches ``meta.json``."""
    digest = model_file_fingerprint(
        Path(artifact_dir) / ARTIFACT_MODEL_NAME)
    stored = load_meta(artifact_dir).get("model_fingerprint")
    if stored != digest:
        raise ValueError(
            "model file fingerprint does not match the artifact")
    return digest


def _load_strategy() -> BettingStrategyConfig:
    """Load the football selection config used by this prediction."""
    return load_betting_strategy_config(_STRATEGY_PATH)


def _empty_report() -> PredictReport:
    """Return a run that wrote nothing and scored nothing."""
    return PredictReport(
        inserted_count=0,
        skipped_existing_count=0,
        rejected_count=0)


def _require_candidate_columns(frame: pd.DataFrame) -> None:
    """Reject a frame that is not the candidate contract."""
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("candidates must be a DataFrame")
    missing = [
        name for name in BETTING_CANDIDATE_COLUMNS
        if name not in frame.columns]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"candidates are missing columns: {joined}")


def _require_recommendations(
        rows: Sequence[BettingRecommendation]
        ) -> tuple[BettingRecommendation, ...]:
    """Reject anything other than recommendation rows."""
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise ValueError(
            "rows must be a sequence of BettingRecommendation")
    prepared = tuple(rows)
    for row in prepared:
        if not isinstance(row, BettingRecommendation):
            raise ValueError(
                "rows must contain BettingRecommendation values")
    return prepared


def _require_fingerprint(value: object) -> str:
    """Reject anything other than a 64-character SHA-256 hex digest."""
    if (
            not isinstance(value, str)
            or _FINGERPRINT_HEX.fullmatch(value) is None):
        raise ValueError(
            "model_fingerprint must be a 64-character SHA-256 hex string")
    return value


def _require_as_of(value: object) -> datetime:
    """Reject a clock that is not a naive datetime."""
    # Kandydaci wracają ze strefą sesji bazy, bez offsetu.
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if not isinstance(value, datetime) or value.tzinfo is not None:
        raise ValueError("as_of must be a naive datetime")
    return value


def _require_count(name: str, value: int) -> None:
    """Reject a bool or a negative count."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _is_missing(value: object) -> bool:
    """Return whether a kickoff cell is null."""
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)
