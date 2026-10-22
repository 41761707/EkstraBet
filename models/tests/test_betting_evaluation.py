"""Walk-forward selection metrics without a bankroll write."""

from __future__ import annotations

import inspect
import math
from datetime import datetime
from datetime import timezone

import pytest

from models.pipeline.betting import evaluation as evaluation_module
from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.domain import SelectionDecision
from models.pipeline.betting.evaluation import EvaluationReport
from models.pipeline.betting.evaluation import evaluate_selections
from models.pipeline.betting.features import feature_schema_fingerprint


_WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "ALTER",
    "DROP",
    "TRUNCATE")


def _candidate(**overrides: object) -> BettingCandidate:
    payload = {
        "prediction_id": 10,
        "odds_id": 20,
        "match_id": 30,
        "event_id": 1,
        "model_id": 8,
        "bookmaker_id": 4,
        "league_id": 12,
        "kickoff": datetime(2026, 8, 1, 18, 0, tzinfo=timezone.utc),
        "value_pct": 55.0,
        "odds": 2.0
    }
    payload.update(overrides)
    return BettingCandidate(**payload)


def _decision(
        kind: str = "bet",
        probability: float = 0.6,
        **overrides: object) -> SelectionDecision:
    return SelectionDecision(
        decision=kind,
        candidate=_candidate(**overrides),
        calibrated_probability=probability,
        reason="evaluation fixture")


def _pair(decision: SelectionDecision) -> tuple[int, int]:
    return (
        decision.candidate.prediction_id,
        decision.candidate.odds_id)


def _report(
        rows: list[tuple[SelectionDecision, int]],
        fingerprint: str | None = None) -> EvaluationReport:
    decisions = [decision for decision, _outcome in rows]
    outcomes = {
        _pair(decision): outcome
        for decision, outcome in rows}
    return evaluate_selections(
        decisions,
        outcomes,
        feature_schema_fingerprint=fingerprint)


def test_winning_bet_uses_unit_stake() -> None:
    decision = _decision(probability=0.6, odds=2.0)
    report = _report([(decision, 1)])
    assert report.roi == pytest.approx(1.0)
    assert report.hit_rate == pytest.approx(1.0)
    assert report.bet_count == 1
    assert report.no_bet_count == 0
    assert report.brier == pytest.approx((0.6 - 1.0) ** 2)
    assert report.log_loss == pytest.approx(-math.log(0.6))
    assert report.reliability == pytest.approx(0.4)
    assert report.kickoff_from == decision.candidate.kickoff
    assert report.kickoff_to == decision.candidate.kickoff


def test_losing_bet_loses_the_unit_stake() -> None:
    decision = _decision(probability=0.25, odds=3.0)
    report = _report([(decision, 0)])
    assert report.roi == pytest.approx(-1.0)
    assert report.hit_rate == pytest.approx(0.0)
    assert report.bet_count == 1
    assert report.brier == pytest.approx(0.25 ** 2)
    assert report.log_loss == pytest.approx(-math.log(0.75))
    assert report.reliability == pytest.approx(0.25)


def test_two_bets_average_unit_profit_and_ignore_a_winning_no_bet() -> None:
    won = _decision(
        probability=0.7,
        prediction_id=1,
        odds_id=11,
        odds=3.0)
    lost = _decision(
        probability=0.4,
        prediction_id=2,
        odds_id=12,
        odds=2.0)
    ignored = _decision(
        "no_bet",
        probability=0.9,
        prediction_id=3,
        odds_id=13,
        odds=10.0)
    report = _report([(won, 1), (lost, 0), (ignored, 1)])
    assert report.roi == pytest.approx(0.5)
    assert report.hit_rate == pytest.approx(0.5)
    assert report.bet_count == 2
    assert report.no_bet_count == 1


def test_no_bet_only_has_scores_without_roi() -> None:
    missed = _decision(
        "no_bet",
        probability=0.2,
        prediction_id=1,
        odds_id=11,
        odds=4.0)
    skipped = _decision(
        "no_bet",
        probability=0.8,
        prediction_id=2,
        odds_id=12,
        odds=1.5)
    report = _report([(missed, 0), (skipped, 1)])
    assert report.bet_count == 0
    assert report.no_bet_count == 2
    assert report.roi is None
    assert report.hit_rate is None
    assert report.brier == pytest.approx(0.04)
    assert report.log_loss == pytest.approx(-math.log(0.8))
    assert report.reliability == pytest.approx(0.2)


def test_identical_input_returns_an_identical_report() -> None:
    later = _decision(
        probability=0.62,
        prediction_id=8,
        odds_id=80,
        odds=2.4,
        kickoff=datetime(2026, 8, 3, 20, 0, tzinfo=timezone.utc))
    earlier = _decision(
        "no_bet",
        probability=0.31,
        prediction_id=2,
        odds_id=20,
        odds=1.7,
        kickoff=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc))
    rows = [(later, 1), (earlier, 0)]
    digest = feature_schema_fingerprint(("league_id", "model_id"))
    first = _report(rows, digest)
    second = _report(rows, digest)
    reversed_rows = list(reversed(rows))
    assert first == second
    assert _report(reversed_rows, digest) == first
    assert first.feature_schema_fingerprint == digest
    assert first.kickoff_from == earlier.candidate.kickoff
    assert first.kickoff_to == later.candidate.kickoff


def test_shared_reliability_bin_uses_the_bin_mean() -> None:
    # Koszyki mają szerokość 0.2. 0.61 i 0.69 wpadają do jednego.
    low = _decision(probability=0.61, prediction_id=1, odds_id=1)
    high = _decision(probability=0.69, prediction_id=2, odds_id=2)
    report = _report([(low, 1), (high, 0)])
    assert report.reliability == pytest.approx(0.15)


def test_certain_loss_keeps_log_loss_finite() -> None:
    decision = _decision(probability=0.0, odds=2.0)
    report = _report([(decision, 0)])
    assert math.isfinite(report.log_loss)
    assert report.log_loss == pytest.approx(-math.log(1.0 - 1e-6))
    assert report.brier == pytest.approx(0.0)


def test_empty_input_returns_an_empty_report() -> None:
    report = evaluate_selections((), {})
    assert report == EvaluationReport(
        brier=None,
        log_loss=None,
        reliability=None,
        roi=None,
        hit_rate=None,
        bet_count=0,
        no_bet_count=0,
        kickoff_from=None,
        kickoff_to=None,
        feature_schema_fingerprint=None)


def test_report_has_no_stake_and_does_not_write() -> None:
    decision = _decision()
    caller = [decision]
    report = evaluate_selections(caller, {_pair(decision): 1})
    assert caller == [decision]
    assert "stake" not in EvaluationReport.__dataclass_fields__
    assert "stake" not in inspect.signature(evaluate_selections).parameters
    source = inspect.getsource(evaluation_module).upper()
    for word in _WRITE_WORDS:
        assert word not in source
    assert "BETTING_RECOMMENDATIONS" not in source
    assert "SQLALCHEMY" not in source
    assert "PYMYSQL" not in source
    assert "EVALUATE_FOOTBALL_OUTCOME" not in source
    assert report.bet_count == 1


def test_rejects_a_partial_outcome_map() -> None:
    decision = _decision()
    with pytest.raises(ValueError, match="finished outcome"):
        evaluate_selections([decision], {})
    with pytest.raises(ValueError, match="needs a decision"):
        evaluate_selections(
            [decision],
            {_pair(decision): 1, (99, 98): 0})


def test_rejects_bad_outcomes_and_duplicate_pairs() -> None:
    decision = _decision(prediction_id=1, odds_id=2)
    duplicate = _decision(prediction_id=1, odds_id=2, value_pct=40.0)
    with pytest.raises(ValueError, match="0 or 1"):
        evaluate_selections([decision], {_pair(decision): True})
    with pytest.raises(ValueError, match="once"):
        evaluate_selections(
            [decision, duplicate],
            {_pair(decision): 1})
    with pytest.raises(ValueError, match="sequence"):
        evaluate_selections(None, {})
    with pytest.raises(ValueError, match="mapping"):
        evaluate_selections((), [])
    with pytest.raises(ValueError, match="SelectionDecision"):
        evaluate_selections([object()], {})


def test_rejects_a_fingerprint_that_is_not_sha256() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        evaluate_selections((), {}, feature_schema_fingerprint="")
    with pytest.raises(ValueError, match="SHA-256"):
        evaluate_selections(
            (),
            {},
            feature_schema_fingerprint=("ab" * 32).upper())


def test_rejects_incomparable_kickoffs() -> None:
    aware = _decision(
        prediction_id=1,
        odds_id=1,
        kickoff=datetime(2026, 8, 1, tzinfo=timezone.utc))
    naive = _decision(
        prediction_id=2,
        odds_id=2,
        kickoff=datetime(2026, 8, 2))
    with pytest.raises(ValueError, match="comparable"):
        _report([(aware, 1), (naive, 0)])
