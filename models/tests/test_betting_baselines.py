"""Reference selectors: no-bet, confidence, and positive expected value."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone

import pytest

from models.pipeline.betting.baselines import ConfidenceSingleStrategy
from models.pipeline.betting.baselines import NoBetStrategy
from models.pipeline.betting.baselines import PositiveEvSingleStrategy
from models.pipeline.betting.baselines import SelectionStrategy
from models.pipeline.betting.domain import BettingCandidate
from models.pipeline.betting.domain import SelectionDecision


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
        "odds": 1.9
    }
    payload.update(overrides)
    return BettingCandidate(**payload)


def _strategies() -> tuple[SelectionStrategy, ...]:
    return (
        NoBetStrategy(),
        ConfidenceSingleStrategy(),
        PositiveEvSingleStrategy())


def _bet_ids(decisions: list[SelectionDecision]) -> list[int]:
    return [
        decision.candidate.prediction_id
        for decision in decisions
        if decision.decision == "bet"]


def _max_bets_in_one_match(decisions: list[SelectionDecision]) -> int:
    counts: dict[int, int] = {}
    for decision in decisions:
        if decision.decision != "bet":
            continue
        match_id = decision.candidate.match_id
        counts[match_id] = counts.get(match_id, 0) + 1
    if not counts:
        return 0
    return max(counts.values())


def test_empty_pool_returns_no_decisions() -> None:
    for strategy in _strategies():
        assert strategy.decide(()) == []


def test_no_bet_marks_every_candidate() -> None:
    pool = (
        _candidate(prediction_id=1, value_pct=80.0, odds=2.0),
        _candidate(prediction_id=2, value_pct=20.0, odds=3.0))
    decisions = NoBetStrategy().decide(pool)
    assert _bet_ids(decisions) == []
    assert [decision.decision for decision in decisions] == [
        "no_bet",
        "no_bet"]
    assert [decision.reason for decision in decisions] == [
        "no-bet baseline",
        "no-bet baseline"]


def test_confidence_picks_the_highest_probability() -> None:
    low = _candidate(prediction_id=1, value_pct=40.0, odds=3.0)
    high = _candidate(prediction_id=2, value_pct=70.0, odds=1.2)
    decisions = ConfidenceSingleStrategy().decide((low, high))
    assert _bet_ids(decisions) == [2]
    assert decisions[0].reason == "lower model probability"
    assert decisions[1].reason == "highest model probability"
    assert decisions[1].calibrated_probability == pytest.approx(0.7)


def test_confidence_ignores_a_negative_expected_value() -> None:
    # 90% przy cenie 1.05 ma ujemne EV, ale najwyższą pewność modelu.
    confident = _candidate(prediction_id=1, value_pct=90.0, odds=1.05)
    value = _candidate(prediction_id=2, value_pct=60.0, odds=2.0)
    decisions = ConfidenceSingleStrategy().decide((confident, value))
    assert _bet_ids(decisions) == [1]


def test_positive_ev_rejects_a_negative_pool() -> None:
    pool = (
        _candidate(prediction_id=1, value_pct=40.0, odds=2.0),
        _candidate(prediction_id=2, value_pct=50.0, odds=2.0))
    decisions = PositiveEvSingleStrategy().decide(pool)
    assert _bet_ids(decisions) == []
    assert {decision.reason for decision in decisions} == {
        "non-positive expected value"}


def test_positive_ev_picks_the_highest_positive_value() -> None:
    negative = _candidate(prediction_id=1, value_pct=40.0, odds=2.0)
    smaller = _candidate(prediction_id=2, value_pct=60.0, odds=2.0)
    larger = _candidate(prediction_id=3, value_pct=70.0, odds=2.0)
    decisions = PositiveEvSingleStrategy().decide((negative, smaller, larger))
    assert _bet_ids(decisions) == [3]
    assert [decision.reason for decision in decisions] == [
        "non-positive expected value",
        "lower expected value",
        "highest positive expected value"]
    assert decisions[2].calibrated_probability == pytest.approx(0.7)


def test_confidence_tie_keeps_the_lower_prediction_id() -> None:
    later = _candidate(prediction_id=5, odds_id=2, value_pct=70.0, odds=1.5)
    earlier = _candidate(prediction_id=3, odds_id=9, value_pct=70.0, odds=2.4)
    decisions = ConfidenceSingleStrategy().decide((later, earlier))
    assert _bet_ids(decisions) == [3]
    assert decisions[0].reason == "tied model probability"
    assert decisions[1].reason == "highest model probability"


def test_expected_value_tie_keeps_the_lower_prediction_id() -> None:
    later = _candidate(prediction_id=8, value_pct=60.0, odds=2.0)
    earlier = _candidate(prediction_id=4, value_pct=60.0, odds=2.0)
    decisions = PositiveEvSingleStrategy().decide((later, earlier))
    assert _bet_ids(decisions) == [4]
    assert decisions[0].reason == "tied expected value"
    assert decisions[1].reason == "highest positive expected value"


def test_selection_does_not_follow_input_order() -> None:
    first = _candidate(prediction_id=2, value_pct=80.0, odds=2.0)
    second = _candidate(prediction_id=1, value_pct=80.0, odds=2.0)
    third = _candidate(prediction_id=3, value_pct=55.0, odds=1.5)
    forward = (first, second, third)
    backward = (third, second, first)
    confidence = ConfidenceSingleStrategy()
    positive_ev = PositiveEvSingleStrategy()
    assert _bet_ids(confidence.decide(forward)) == [1]
    assert _bet_ids(confidence.decide(backward)) == [1]
    assert _bet_ids(positive_ev.decide(forward)) == [1]
    assert _bet_ids(positive_ev.decide(backward)) == [1]
    repeated = confidence.decide(forward)
    assert confidence.decide(forward) == repeated


def test_decisions_keep_input_order_and_have_no_stake() -> None:
    pool = (
        _candidate(prediction_id=3, value_pct=40.0, odds=2.2),
        _candidate(prediction_id=1, value_pct=65.0, odds=2.0))
    decisions = PositiveEvSingleStrategy().decide(pool)
    assert [decision.candidate.prediction_id for decision in decisions] == [
        3,
        1]
    assert decisions[0].candidate is pool[0]
    assert decisions[1].candidate is pool[1]
    for decision in decisions:
        assert decision.decision in ("bet", "no_bet")
        assert decision.reason.strip()
        assert not hasattr(decision, "stake")
        assert 0.0 <= decision.calibrated_probability <= 1.0


def test_each_strategy_returns_at_most_one_bet_per_match() -> None:
    pool = (
        _candidate(prediction_id=1, value_pct=61.0, odds=2.0),
        _candidate(prediction_id=2, value_pct=72.0, odds=1.8),
        _candidate(prediction_id=3, value_pct=55.0, odds=2.4))
    for strategy in _strategies():
        decisions = strategy.decide(pool)
        assert len(decisions) == len(pool)
        assert _max_bets_in_one_match(decisions) <= 1


def test_two_matches_each_keep_one_single() -> None:
    tied_later = _candidate(
        match_id=101,
        prediction_id=5,
        value_pct=70.0,
        odds=2.0)
    tied_earlier = _candidate(
        match_id=101,
        prediction_id=3,
        value_pct=70.0,
        odds=2.0)
    weaker = _candidate(
        match_id=101,
        prediction_id=9,
        value_pct=40.0,
        odds=2.0)
    second_low = _candidate(
        match_id=202,
        prediction_id=8,
        value_pct=55.0,
        odds=2.0)
    second_high = _candidate(
        match_id=202,
        prediction_id=4,
        value_pct=80.0,
        odds=2.0)
    pool = (second_low, tied_later, second_high, tied_earlier, weaker)
    confidence = ConfidenceSingleStrategy().decide(pool)
    positive_ev = PositiveEvSingleStrategy().decide(pool)
    assert _bet_ids(confidence) == [4, 3]
    assert _bet_ids(positive_ev) == [4, 3]
    assert _max_bets_in_one_match(confidence) == 1
    assert _max_bets_in_one_match(positive_ev) == 1
    assert [decision.candidate.prediction_id for decision in confidence] == [
        8, 5, 4, 3, 9]
    assert confidence[1].reason == "tied model probability"
    assert confidence[3].reason == "highest model probability"
    assert positive_ev[1].reason == "tied expected value"
    assert positive_ev[3].reason == "highest positive expected value"
    assert _bet_ids(NoBetStrategy().decide(pool)) == []
    reversed_pool = tuple(reversed(pool))
    assert set(_bet_ids(
        ConfidenceSingleStrategy().decide(reversed_pool))) == {4, 3}
    assert set(_bet_ids(
        PositiveEvSingleStrategy().decide(reversed_pool))) == {4, 3}


def test_rejects_a_pool_that_is_not_candidates() -> None:
    strategy = NoBetStrategy()
    with pytest.raises(ValueError, match="sequence"):
        strategy.decide(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="BettingCandidate"):
        strategy.decide([object()])  # type: ignore[list-item]
