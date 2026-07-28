"""Unit tests for football outcome settlement rules."""

from __future__ import annotations

import unittest

from backend.sports.football.outcome_evaluator import (
    EventFamily,
    InvalidMatchResultError,
    SettlementCandidate,
    SettlementTarget,
    UnsupportedFootballEventError,
    evaluate_football_outcome)


def _candidate(
        *,
        event_id: int,
        event_name: str,
        family: EventFamily,
        result: str = "1",
        home_goals: int | None = 2,
        away_goals: int | None = 1,
        target: SettlementTarget = "final_prediction",
        record_id: int = 1
) -> SettlementCandidate:
    return SettlementCandidate(
        record_id=record_id,
        target=target,
        event_id=event_id,
        event_name=event_name,
        family=family,
        result=result,
        home_goals=home_goals,
        away_goals=away_goals)


class TestResultSettlement(unittest.TestCase):
    """1X2 settlement against finished match result codes."""

    def test_home_win_hit(self) -> None:
        candidate = _candidate(
            event_id=1,
            event_name="home",
            family="REZULTAT",
            result="1")
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_home_win_miss(self) -> None:
        candidate = _candidate(
            event_id=1,
            event_name="home",
            family="REZULTAT",
            result="X",
            home_goals=1,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_draw_hit(self) -> None:
        candidate = _candidate(
            event_id=2,
            event_name="draw",
            family="REZULTAT",
            result="X",
            home_goals=0,
            away_goals=0)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_away_win_hit(self) -> None:
        candidate = _candidate(
            event_id=3,
            event_name="away",
            family="REZULTAT",
            result="2",
            home_goals=0,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_away_win_miss(self) -> None:
        candidate = _candidate(
            event_id=3,
            event_name="away",
            family="REZULTAT",
            result="1")
        self.assertEqual(evaluate_football_outcome(candidate), 0)


class TestBttsSettlement(unittest.TestCase):
    """Both-teams-to-score yes/no markets."""

    def test_btts_yes_hit(self) -> None:
        candidate = _candidate(
            event_id=6,
            event_name="btts_yes",
            family="BTTS",
            home_goals=1,
            away_goals=2)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_btts_yes_miss(self) -> None:
        candidate = _candidate(
            event_id=6,
            event_name="btts_yes",
            family="BTTS",
            home_goals=2,
            away_goals=0)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_btts_no_hit(self) -> None:
        candidate = _candidate(
            event_id=172,
            event_name="btts_no",
            family="BTTS",
            home_goals=3,
            away_goals=0)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_btts_no_miss(self) -> None:
        candidate = _candidate(
            event_id=172,
            event_name="btts_no",
            family="BTTS",
            home_goals=1,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 0)


class TestOverUnderSettlement(unittest.TestCase):
    """Over/under 2.5 total goals markets."""

    def test_over_25_hit(self) -> None:
        candidate = _candidate(
            event_id=8,
            event_name="over_25",
            family="OU",
            home_goals=2,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_over_25_miss_on_boundary(self) -> None:
        candidate = _candidate(
            event_id=8,
            event_name="over_25",
            family="OU",
            home_goals=1,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_under_25_hit(self) -> None:
        candidate = _candidate(
            event_id=12,
            event_name="under_25",
            family="OU",
            home_goals=0,
            away_goals=2)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_under_25_miss(self) -> None:
        candidate = _candidate(
            event_id=12,
            event_name="under_25",
            family="OU",
            home_goals=3,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 0)


class TestGoalsSettlement(unittest.TestCase):
    """Exact total-goal buckets including the 6+ tail."""

    def test_zero_goals_hit(self) -> None:
        candidate = _candidate(
            event_id=174,
            event_name="goals_0",
            family="GOALS",
            result="X",
            home_goals=0,
            away_goals=0)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_three_goals_hit(self) -> None:
        candidate = _candidate(
            event_id=177,
            event_name="goals_3",
            family="GOALS",
            home_goals=2,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_five_goals_miss_when_six(self) -> None:
        candidate = _candidate(
            event_id=179,
            event_name="goals_5",
            family="GOALS",
            home_goals=4,
            away_goals=2)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_six_plus_hit(self) -> None:
        candidate = _candidate(
            event_id=180,
            event_name="goals_6_plus",
            family="GOALS",
            home_goals=4,
            away_goals=2)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_six_plus_miss_for_five(self) -> None:
        candidate = _candidate(
            event_id=180,
            event_name="goals_6_plus",
            family="GOALS",
            home_goals=3,
            away_goals=2)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_all_exact_goal_buckets(self) -> None:
        mapping = {
            174: 0,
            175: 1,
            176: 2,
            177: 3,
            178: 4,
            179: 5
        }
        for event_id, total in mapping.items():
            with self.subTest(event_id=event_id, total=total):
                home = total // 2
                away = total - home
                hit = _candidate(
                    event_id=event_id,
                    event_name=f"goals_{total}",
                    family="GOALS",
                    result="X" if home == away else "1",
                    home_goals=home,
                    away_goals=away)
                miss = _candidate(
                    event_id=event_id,
                    event_name=f"goals_{total}",
                    family="GOALS",
                    home_goals=home,
                    away_goals=away + 1)
                self.assertEqual(evaluate_football_outcome(hit), 1)
                self.assertEqual(evaluate_football_outcome(miss), 0)


class TestExactSettlement(unittest.TestCase):
    """Exact score labels including folded 5+ thresholds."""

    def test_plain_exact_score_hit(self) -> None:
        candidate = _candidate(
            event_id=212,
            event_name="2:2",
            family="EXACT",
            result="X",
            home_goals=2,
            away_goals=2)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_plain_exact_score_miss(self) -> None:
        candidate = _candidate(
            event_id=212,
            event_name="2:2",
            family="EXACT",
            home_goals=2,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_away_five_plus_hit(self) -> None:
        candidate = _candidate(
            event_id=209,
            event_name="1:5+",
            family="EXACT",
            result="2",
            home_goals=1,
            away_goals=6)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_away_five_plus_miss_below_threshold(self) -> None:
        candidate = _candidate(
            event_id=209,
            event_name="1:5+",
            family="EXACT",
            result="2",
            home_goals=1,
            away_goals=4)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_home_five_plus_hit(self) -> None:
        candidate = _candidate(
            event_id=228,
            event_name="5+:0",
            family="EXACT",
            home_goals=5,
            away_goals=0)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_both_five_plus_hit(self) -> None:
        candidate = _candidate(
            event_id=233,
            event_name="5+:5+",
            family="EXACT",
            result="X",
            home_goals=7,
            away_goals=5)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_both_five_plus_miss_when_one_side_low(self) -> None:
        candidate = _candidate(
            event_id=233,
            event_name="5+:5+",
            family="EXACT",
            home_goals=5,
            away_goals=4)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_invalid_exact_name_is_unsupported(self) -> None:
        candidate = _candidate(
            event_id=999,
            event_name="2-1",
            family="EXACT")
        with self.assertRaises(UnsupportedFootballEventError):
            evaluate_football_outcome(candidate)


class TestBetMarketGuard(unittest.TestCase):
    """Bet targets are limited to odds-backed event IDs."""

    def test_bet_target_allows_odds_markets(self) -> None:
        candidate = _candidate(
            event_id=8,
            event_name="over_25",
            family="OU",
            target="bet",
            home_goals=3,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_bet_target_rejects_goals_family(self) -> None:
        candidate = _candidate(
            event_id=174,
            event_name="goals_0",
            family="GOALS",
            target="bet",
            result="X",
            home_goals=0,
            away_goals=0)
        with self.assertRaises(UnsupportedFootballEventError):
            evaluate_football_outcome(candidate)

    def test_bet_target_rejects_exact_family(self) -> None:
        candidate = _candidate(
            event_id=198,
            event_name="0:0",
            family="EXACT",
            target="bet",
            result="X",
            home_goals=0,
            away_goals=0)
        with self.assertRaises(UnsupportedFootballEventError):
            evaluate_football_outcome(candidate)


class TestInvalidAndUnsupportedInputs(unittest.TestCase):
    """Domain errors must never collapse into a guessed loss."""

    def test_unknown_event_raises(self) -> None:
        candidate = _candidate(
            event_id=9999,
            event_name="unknown",
            family="REZULTAT")
        with self.assertRaises(UnsupportedFootballEventError):
            evaluate_football_outcome(candidate)

    def test_invalid_result_raises(self) -> None:
        candidate = _candidate(
            event_id=1,
            event_name="home",
            family="REZULTAT",
            result="0")
        with self.assertRaises(InvalidMatchResultError):
            evaluate_football_outcome(candidate)

    def test_missing_goals_raise(self) -> None:
        candidate = _candidate(
            event_id=6,
            event_name="btts_yes",
            family="BTTS",
            home_goals=None,
            away_goals=1)
        with self.assertRaises(InvalidMatchResultError):
            evaluate_football_outcome(candidate)

    def test_negative_goals_raise(self) -> None:
        candidate = _candidate(
            event_id=8,
            event_name="over_25",
            family="OU",
            home_goals=-1,
            away_goals=2)
        with self.assertRaises(InvalidMatchResultError):
            evaluate_football_outcome(candidate)


if __name__ == "__main__":
    unittest.main()
