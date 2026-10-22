"""Metrics for finished betting selections.

Unit stake is used only to turn bet outcomes into ROI. Nothing here
opens a database connection or writes a recommendation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from models.pipeline.betting.domain import SelectionDecision


_UNIT_STAKE = 1.0
_RELIABILITY_BINS = 5
_LOG_LOSS_CLIP = 1e-6
_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class _ScoredRow:
    decision: SelectionDecision
    outcome: int


@dataclass(frozen=True)
class EvaluationReport:
    """Walk-forward metrics for one set of finished selections.

    ``brier``, ``log_loss`` and ``reliability`` cover every row.
    ``reliability`` is the largest absolute gap between a bin's mean
    predicted probability and its observed win rate. ``roi`` and
    ``hit_rate`` cover rows marked ``bet``. Each of those rows stakes
    1 and wins ``odds - 1`` or loses 1. Both are ``None`` when no row
    was bet. ``kickoff_from`` and ``kickoff_to`` are the earliest and
    latest kickoff in the set.
    """

    brier: float | None
    log_loss: float | None
    reliability: float | None
    roi: float | None
    hit_rate: float | None
    bet_count: int
    no_bet_count: int
    kickoff_from: datetime | None
    kickoff_to: datetime | None
    feature_schema_fingerprint: str | None

    def __post_init__(self) -> None:
        _validate_report(self)


def evaluate_selections(
        decisions: Sequence[SelectionDecision],
        outcomes: Mapping[tuple[int, int], int],
        *,
        feature_schema_fingerprint: str | None = None
        ) -> EvaluationReport:
    """Return metrics for decisions paired with finished outcomes.

    ``outcomes`` maps ``(prediction_id, odds_id)`` to 1 when that
    candidate won and 0 otherwise. The coding matches the football
    outcome evaluator, but this function does not call it. The map
    must cover every decision and nothing else.
    ``feature_schema_fingerprint`` is stored as given. Columns are
    not hashed here. No database connection is opened.
    """
    rows = _aligned_rows(decisions, outcomes)
    fingerprint = _copy_fingerprint(feature_schema_fingerprint)
    if not rows:
        return _empty_report(fingerprint)
    kickoff_from, kickoff_to = _kickoff_bounds(rows)
    bets = _bets(rows)
    return EvaluationReport(
        brier=_brier(rows),
        log_loss=_log_loss(rows),
        reliability=_max_reliability_gap(rows),
        roi=_roi(bets),
        hit_rate=_hit_rate(bets),
        bet_count=len(bets),
        no_bet_count=len(rows) - len(bets),
        kickoff_from=kickoff_from,
        kickoff_to=kickoff_to,
        feature_schema_fingerprint=fingerprint)


def _validate_report(report: EvaluationReport) -> None:
    """Reject a report whose counts and metrics disagree."""
    _require_count("bet_count", report.bet_count)
    _require_count("no_bet_count", report.no_bet_count)
    total = report.bet_count + report.no_bet_count
    _require_probability_block(report, total == 0)
    _require_selection_block(report, report.bet_count == 0)
    _require_kickoffs(report, total == 0)
    _copy_fingerprint(report.feature_schema_fingerprint)


def _require_probability_block(
        report: EvaluationReport,
        empty: bool) -> None:
    """Require score metrics only when at least one row exists."""
    values = (report.brier, report.log_loss, report.reliability)
    if empty:
        _require_all_none("probability metrics", values)
        return
    _require_unit_interval("brier", report.brier)
    _require_non_negative("log_loss", report.log_loss)
    _require_unit_interval("reliability", report.reliability)


def _require_selection_block(
        report: EvaluationReport,
        no_bets: bool) -> None:
    """Require ROI and hit rate only when a bet was placed."""
    values = (report.roi, report.hit_rate)
    if no_bets:
        _require_all_none("roi and hit_rate", values)
        return
    _require_roi(report.roi)
    _require_unit_interval("hit_rate", report.hit_rate)


def _require_kickoffs(report: EvaluationReport, empty: bool) -> None:
    """Require a closed kickoff range exactly for a non-empty set."""
    if empty:
        if report.kickoff_from is not None or report.kickoff_to is not None:
            raise ValueError("empty report has no kickoff range")
        return
    if not isinstance(report.kickoff_from, datetime):
        raise ValueError("kickoff_from must be a datetime")
    if not isinstance(report.kickoff_to, datetime):
        raise ValueError("kickoff_to must be a datetime")
    try:
        ordered = report.kickoff_from <= report.kickoff_to
    except TypeError as exc:
        raise ValueError("kickoff values must be comparable") from exc
    if not ordered:
        raise ValueError("kickoff_from must not be after kickoff_to")


def _empty_report(fingerprint: str | None) -> EvaluationReport:
    """Return the report used when no finished row was supplied."""
    return EvaluationReport(
        brier=None,
        log_loss=None,
        reliability=None,
        roi=None,
        hit_rate=None,
        bet_count=0,
        no_bet_count=0,
        kickoff_from=None,
        kickoff_to=None,
        feature_schema_fingerprint=fingerprint)


def _aligned_rows(
        decisions: Sequence[SelectionDecision],
        outcomes: Mapping[tuple[int, int], int]) -> list[_ScoredRow]:
    """Pair each decision with its outcome, independent of list order."""
    _require_decisions(decisions)
    _require_outcomes(outcomes)
    rows: list[_ScoredRow] = []
    seen: set[tuple[int, int]] = set()
    for decision in decisions:
        key = (
            decision.candidate.prediction_id,
            decision.candidate.odds_id)
        if key in seen:
            raise ValueError(
                "decisions must contain each prediction-odds pair once")
        seen.add(key)
        if key not in outcomes:
            raise ValueError("every decision needs a finished outcome")
        rows.append(_ScoredRow(decision, outcomes[key]))
    if set(outcomes) != seen:
        raise ValueError("every outcome needs a decision")
    # Kolejność listy nie może zmieniać sumy zmiennoprzecinkowej.
    rows.sort(key=_pair_sort_key)
    return rows


def _pair_sort_key(row: _ScoredRow) -> tuple[int, int]:
    """Order rows by the prediction-odds pair."""
    return (
        row.decision.candidate.prediction_id,
        row.decision.candidate.odds_id)


def _require_decisions(decisions: Sequence[SelectionDecision]) -> None:
    """Reject anything that is not a pool of decisions."""
    if isinstance(decisions, (str, bytes)) or not isinstance(
            decisions, Sequence):
        raise ValueError("decisions must be a sequence")
    for decision in decisions:
        if not isinstance(decision, SelectionDecision):
            raise ValueError(
                "decisions must contain SelectionDecision values")


def _require_outcomes(outcomes: Mapping[tuple[int, int], int]) -> None:
    """Reject a map that is not pair keys to 0 or 1."""
    if isinstance(outcomes, (str, bytes)) or not isinstance(
            outcomes, Mapping):
        raise ValueError("outcomes must be a mapping")
    for key, value in outcomes.items():
        _require_pair_key(key)
        _require_outcome_bit(value)


def _require_pair_key(key: object) -> None:
    """Reject an outcome key that is not one stored pair."""
    if not isinstance(key, tuple) or len(key) != 2:
        raise ValueError(
            "outcome keys must be (prediction_id, odds_id)")
    prediction_id, odds_id = key
    _require_positive_id("prediction_id", prediction_id)
    _require_positive_id("odds_id", odds_id)


def _require_positive_id(name: str, value: object) -> None:
    """Reject ids that cannot point at an existing row."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _require_outcome_bit(value: object) -> None:
    """Reject labels other than a loss or a win."""
    if isinstance(value, bool) or value not in (0, 1):
        raise ValueError("outcome must be 0 or 1")


def _bets(rows: Sequence[_ScoredRow]) -> list[_ScoredRow]:
    """Keep rows the selector marked as a bet."""
    return [row for row in rows if row.decision.decision == "bet"]


def _brier(rows: Sequence[_ScoredRow]) -> float:
    """Return the mean squared error of the quoted probabilities."""
    total = 0.0
    for row in rows:
        gap = row.decision.calibrated_probability - float(row.outcome)
        total += gap * gap
    return total / len(rows)


def _log_loss(rows: Sequence[_ScoredRow]) -> float:
    """Return the mean binary log loss of the quoted probabilities."""
    # Decyzja dopuszcza 0 i 1, a logarytm zera nie jest liczbą.
    total = 0.0
    for row in rows:
        probability = _clip_probability(
            row.decision.calibrated_probability)
        outcome = float(row.outcome)
        total += -(
            outcome * math.log(probability)
            + (1.0 - outcome) * math.log(1.0 - probability))
    return total / len(rows)


def _clip_probability(probability: float) -> float:
    """Move 0 and 1 inside the open unit interval for log loss."""
    if probability < _LOG_LOSS_CLIP:
        return _LOG_LOSS_CLIP
    if probability > 1.0 - _LOG_LOSS_CLIP:
        return 1.0 - _LOG_LOSS_CLIP
    return probability


def _max_reliability_gap(rows: Sequence[_ScoredRow]) -> float:
    """Return the worst absolute calibration gap across equal bins."""
    # Bramka configu porównuje ten maksymalny błąd, nie średnią ważoną.
    worst = 0.0
    seen = False
    for index in range(_RELIABILITY_BINS):
        gap = _bin_gap(rows, index)
        if gap is None:
            continue
        seen = True
        if gap > worst:
            worst = gap
    if not seen:
        raise RuntimeError("reliability bins missed every probability")
    return worst


def _bin_gap(rows: Sequence[_ScoredRow], index: int) -> float | None:
    """Return one bin's absolute gap, or none when the bin is empty."""
    low = index / _RELIABILITY_BINS
    high = (index + 1) / _RELIABILITY_BINS
    chosen = [
        row for row in rows
        if _in_reliability_bin(
            row.decision.calibrated_probability,
            low,
            high,
            index)]
    if not chosen:
        return None
    predicted = _mean([
        row.decision.calibrated_probability for row in chosen])
    observed = _mean([float(row.outcome) for row in chosen])
    return abs(predicted - observed)


def _in_reliability_bin(
        probability: float,
        low: float,
        high: float,
        index: int) -> bool:
    """Assign a probability to one of the equal-width bins."""
    if index == _RELIABILITY_BINS - 1:
        return low <= probability <= high
    return low <= probability < high


def _roi(bets: Sequence[_ScoredRow]) -> float | None:
    """Return profit over stake, using stake 1 on every bet."""
    if not bets:
        return None
    # Stawka żyje tylko w tym ilorazie. To nie jest zapis salda.
    return _profit(bets) / (len(bets) * _UNIT_STAKE)


def _profit(bets: Sequence[_ScoredRow]) -> float:
    """Return the sum of unit-stake win and loss amounts."""
    total = 0.0
    for row in bets:
        if row.outcome == 1:
            total += float(row.decision.candidate.odds) - _UNIT_STAKE
        else:
            total -= _UNIT_STAKE
    return total


def _hit_rate(bets: Sequence[_ScoredRow]) -> float | None:
    """Return the share of bets that won."""
    if not bets:
        return None
    wins = sum(row.outcome for row in bets)
    return wins / len(bets)


def _kickoff_bounds(
        rows: Sequence[_ScoredRow]) -> tuple[datetime, datetime]:
    """Return the earliest and latest kickoff in the scored rows."""
    kickoffs = [row.decision.candidate.kickoff for row in rows]
    try:
        return min(kickoffs), max(kickoffs)
    except TypeError as exc:
        raise ValueError("kickoff values must be comparable") from exc


def _mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean of a non-empty sequence."""
    return sum(values) / len(values)


def _copy_fingerprint(value: str | None) -> str | None:
    """Accept a SHA-256 hex digest and reject every other string."""
    if value is None:
        return None
    if isinstance(value, str) and _is_sha256(value):
        return value
    raise ValueError(
        "feature_schema_fingerprint must be a SHA-256 hex digest")


def _is_sha256(value: str) -> bool:
    """Return whether the string is 64 lowercase hex characters."""
    if len(value) != _SHA256_HEX_LENGTH:
        return False
    return set(value) <= _HEX_DIGITS


def _require_count(name: str, value: int) -> None:
    """Reject a count that is not a non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _require_unit_interval(name: str, value: float | None) -> None:
    """Reject a metric outside the closed unit interval."""
    if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0.0
            or value > 1.0):
        raise ValueError(f"{name} must be between 0 and 1")


def _require_non_negative(name: str, value: float | None) -> None:
    """Reject a missing or negative score."""
    if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0.0):
        raise ValueError(f"{name} must be a finite number >= 0")


def _require_roi(value: float | None) -> None:
    """Reject ROI below a total loss of the unit stake."""
    if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < -1.0):
        raise ValueError("roi must be a finite number >= -1")


def _require_all_none(name: str, values: tuple[object, ...]) -> None:
    """Reject a block that should be empty."""
    if any(value is not None for value in values):
        raise ValueError(f"{name} must be empty")
