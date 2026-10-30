"""Selector score, odds ceiling and deterministic leg choice."""

from __future__ import annotations

import inspect
import math
import unittest
from datetime import datetime, timedelta

from backend.services.coupon_agent_config import SelectorConfig
from backend.services.coupon_agent_selector import (
    AgentCandidate,
    score_candidate,
    select_coupon)
from backend.services import coupon_agent_selector as selector


_CFG = SelectorConfig()


def _candidate(
        *,
        match_id: int,
        odds: float,
        model_probability: float,
        event_id: int = 1,
        model_id: int = 1,
        bookmaker_id: int = 1,
        implied_probability: float | None = None,
        value_edge_pp: float | None = None,
        kickoff: datetime | None = None) -> AgentCandidate:
    if implied_probability is None:
        implied = 1.0 / odds
    else:
        implied = implied_probability
    if value_edge_pp is None:
        edge = (model_probability - implied) * 100.0
    else:
        edge = value_edge_pp
    if kickoff is None:
        when = datetime(2026, 10, 26, 12, 0)
        when = when + timedelta(minutes=match_id)
    else:
        when = kickoff
    return AgentCandidate(
        match_id=match_id,
        event_id=event_id,
        model_id=model_id,
        bookmaker_id=bookmaker_id,
        odds=odds,
        model_probability=model_probability,
        implied_probability=implied,
        value_edge_pp=edge,
        kickoff=when,
        league_id=1,
        league_tier=1,
        event_family="REZULTAT")


def _ids(selection) -> list[int]:
    return [leg.match_id for leg in selection.legs]


class TestScoreCandidate(unittest.TestCase):
    """Leg score prefers a small gap over a large edge."""

    def test_formula_uses_confidence_gap_and_longshot(self) -> None:
        candidate = _candidate(
            match_id=1,
            odds=1.0 / 0.52,
            model_probability=0.55,
            implied_probability=0.52,
            value_edge_pp=3.0)
        expected = 1.0 * 0.55 - 1.5 * abs(0.55 - 0.52) - 0.75 * 3.0 / 100.0
        self.assertAlmostEqual(score_candidate(candidate, _CFG), expected)

    def test_large_edge_scores_below_a_small_disagreement(self) -> None:
        close = _candidate(
            match_id=1,
            odds=1.0 / 0.52,
            model_probability=0.55,
            implied_probability=0.52,
            value_edge_pp=3.0)
        longshot = _candidate(
            match_id=2,
            odds=3.5,
            model_probability=0.40)
        close_score = score_candidate(close, _CFG)
        long_score = score_candidate(longshot, _CFG)
        close_ev = close.model_probability * close.odds - 1.0
        long_ev = longshot.model_probability * longshot.odds - 1.0
        self.assertGreater(close_score, long_score)
        self.assertGreater(long_ev, close_ev)
        selection = select_coupon([longshot, close], _CFG)
        self.assertEqual(selection.reason, "published")
        self.assertEqual(_ids(selection), [1])

    def test_edge_past_the_cap_is_rejected(self) -> None:
        candidate = _candidate(
            match_id=1,
            odds=2.0,
            model_probability=0.55,
            value_edge_pp=25.0)
        legal = _candidate(
            match_id=2,
            odds=1.8,
            model_probability=0.58)
        self.assertEqual(score_candidate(candidate, _CFG), float("-inf"))
        selection = select_coupon([candidate, legal], _CFG)
        self.assertEqual(_ids(selection), [2])

    def test_edge_equal_to_the_cap_stays_on_a_slip_at_odds_five(self) -> None:
        candidate = _candidate(
            match_id=1,
            odds=5.0,
            model_probability=0.35,
            implied_probability=0.20,
            value_edge_pp=15.0)
        self.assertTrue(math.isfinite(score_candidate(candidate, _CFG)))
        selection = select_coupon([candidate], _CFG)
        self.assertEqual(selection.reason, "published")
        self.assertAlmostEqual(selection.combined_odds, 5.0)

    def test_drops_probability_outside_unit_interval(self) -> None:
        zero = _candidate(match_id=1, odds=1.5, model_probability=0.0)
        full = _candidate(match_id=2, odds=1.5, model_probability=1.0)
        legal = _candidate(match_id=3, odds=1.5, model_probability=0.70)
        selection = select_coupon([zero, full, legal], _CFG)
        self.assertEqual(_ids(selection), [3])


class TestCombinedOddsCeiling(unittest.TestCase):
    """The product of prices is a hard ceiling of 6."""

    def test_two_prices_at_two_fit_under_the_ceiling(self) -> None:
        first = _candidate(match_id=1, odds=2.0, model_probability=0.55)
        second = _candidate(match_id=2, odds=2.0, model_probability=0.55)
        selection = select_coupon([second, first], _CFG)
        self.assertEqual(selection.reason, "published")
        self.assertEqual(_ids(selection), [1, 2])
        self.assertAlmostEqual(selection.combined_odds, 4.0)

    def test_two_prices_at_two_point_four_fit_under_six(self) -> None:
        first = _candidate(match_id=1, odds=2.4, model_probability=0.45)
        second = _candidate(match_id=2, odds=2.4, model_probability=0.45)
        selection = select_coupon([second, first], _CFG)
        self.assertEqual(selection.reason, "published")
        self.assertEqual(_ids(selection), [1, 2])
        self.assertAlmostEqual(selection.combined_odds, 5.76)

    def test_two_prices_at_three_do_not_combine(self) -> None:
        first = _candidate(match_id=1, odds=3.0, model_probability=0.40)
        second = _candidate(match_id=2, odds=3.0, model_probability=0.40)
        selection = select_coupon([first, second], _CFG)
        self.assertEqual(len(selection.legs), 1)
        self.assertAlmostEqual(selection.combined_odds, 3.0)
        self.assertEqual(_ids(selection), [1])

    def test_price_three_can_pair_with_one_and_a_half(self) -> None:
        price_three = _candidate(
            match_id=1,
            odds=3.0,
            model_probability=0.38)
        other_three = _candidate(
            match_id=2,
            odds=3.0,
            model_probability=0.42)
        short = _candidate(
            match_id=3,
            odds=1.5,
            model_probability=0.70)
        selection = select_coupon(
            [other_three, short, price_three],
            _CFG)
        self.assertEqual(_ids(selection), [1, 3])
        self.assertAlmostEqual(selection.combined_odds, 4.5)
        self.assertNotIn(2, _ids(selection))

    def test_single_price_at_six_stays_on_the_slip(self) -> None:
        cfg = SelectorConfig(min_probability=0.10, max_abs_edge_pp=50.0)
        candidate = _candidate(
            match_id=1,
            odds=6.0,
            model_probability=0.20)
        selection = select_coupon([candidate], cfg)
        self.assertEqual(selection.reason, "published")
        self.assertAlmostEqual(selection.combined_odds, 6.0)

    def test_single_price_above_six_is_no_bet(self) -> None:
        cfg = SelectorConfig(min_probability=0.10, max_abs_edge_pp=50.0)
        candidate = _candidate(
            match_id=1,
            odds=6.01,
            model_probability=0.20)
        self.assertGreater(score_candidate(candidate, cfg), float("-inf"))
        selection = select_coupon([candidate], cfg)
        self.assertEqual(selection.reason, "no_bet")
        self.assertEqual(selection.legs, [])
        self.assertIsNone(selection.combined_odds)

    def test_price_below_one_and_a_half_is_no_bet(self) -> None:
        cfg = SelectorConfig(min_probability=0.10, max_abs_edge_pp=50.0)
        short = _candidate(
            match_id=1,
            odds=1.49,
            model_probability=0.70)
        self.assertGreater(score_candidate(short, cfg), float("-inf"))
        rejected = select_coupon([short], cfg)
        self.assertEqual(rejected.reason, "no_bet")
        boundary = _candidate(
            match_id=2,
            odds=1.5,
            model_probability=0.70)
        kept = select_coupon([boundary], cfg)
        self.assertEqual(kept.reason, "published")
        self.assertAlmostEqual(kept.combined_odds, 1.5)

    def test_penalty_drops_a_weak_leg_that_still_fits(self) -> None:
        strong = _candidate(match_id=1, odds=1.5, model_probability=0.70)
        weak = _candidate(match_id=2, odds=4.0, model_probability=0.40)
        weak_score = score_candidate(weak, _CFG)
        self.assertLess(weak_score, _CFG.leg_penalty)
        self.assertLessEqual(strong.odds * weak.odds, _CFG.max_combined_odds)
        selection = select_coupon([weak, strong], _CFG)
        self.assertEqual(_ids(selection), [1])


class TestCouponShape(unittest.TestCase):
    """One leg per match, at most max_legs, stable across input order."""

    def test_empty_pool_is_no_bet(self) -> None:
        selection = select_coupon([], _CFG)
        self.assertEqual(selection.reason, "no_bet")
        self.assertEqual(selection.legs, [])
        self.assertIsNone(selection.score)
        self.assertIsNone(selection.combined_odds)

    def test_one_leg_per_match_keeps_the_higher_score(self) -> None:
        weak = _candidate(
            match_id=7,
            event_id=1,
            odds=2.2,
            model_probability=0.40)
        strong = _candidate(
            match_id=7,
            event_id=2,
            odds=1.7,
            model_probability=0.62)
        other = _candidate(match_id=8, odds=1.6, model_probability=0.66)
        self.assertGreater(
            score_candidate(strong, _CFG),
            score_candidate(weak, _CFG))
        selection = select_coupon([weak, other, strong], _CFG)
        on_match = [
            leg for leg in selection.legs if leg.match_id == 7]
        self.assertEqual(len(on_match), 1)
        self.assertEqual(on_match[0].event_id, 2)
        self.assertIn(8, _ids(selection))

    def test_same_input_returns_the_same_legs(self) -> None:
        legs = [
            _candidate(match_id=index, odds=1.8, model_probability=0.58)
            for index in range(1, 5)]
        forward = select_coupon(legs, _CFG)
        backward = select_coupon(list(reversed(legs)), _CFG)
        self.assertEqual(_ids(forward), _ids(backward))
        self.assertAlmostEqual(forward.score, backward.score)
        self.assertAlmostEqual(forward.combined_odds, backward.combined_odds)

    def test_max_legs_stops_at_the_cap_even_when_odds_still_fit(self) -> None:
        legs = [
            _candidate(match_id=index, odds=1.50, model_probability=0.70)
            for index in range(1, 11)]
        selection = select_coupon(list(reversed(legs)), _CFG)
        self.assertEqual(
            _ids(selection),
            list(range(1, _CFG.max_legs + 1)))
        self.assertEqual(len(selection.legs), _CFG.max_legs)
        self.assertLessEqual(selection.combined_odds, _CFG.max_combined_odds)

    def test_selector_module_has_no_io(self) -> None:
        source = inspect.getsource(selector)
        self.assertNotIn("get_db_connection", source)
        self.assertNotIn("read_sql", source)
        self.assertNotIn("pandas", source)
        self.assertNotIn("model.joblib", source)


if __name__ == "__main__":
    unittest.main()
