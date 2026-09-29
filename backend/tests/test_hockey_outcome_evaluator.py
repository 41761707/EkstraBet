"""Unit tests for hockey outcome settlement including overtime."""

from __future__ import annotations

import unittest

from backend.sports.hockey.markets import HOCKEY_BET_MARKET_EVENT_IDS
from backend.sports.hockey.markets import HOCKEY_MARKET_RULES
from backend.sports.hockey.outcome_evaluator import HockeyEventFamily
from backend.sports.hockey.outcome_evaluator import HockeySettlementCandidate
from backend.sports.hockey.outcome_evaluator import InvalidMatchResultError
from backend.sports.hockey.outcome_evaluator import UnsupportedHockeyEventError
from backend.sports.hockey.outcome_evaluator import evaluate_hockey_outcome
from backend.sports.hockey.outcome_evaluator import final_score


_EVENT_FAMILY: dict[int, HockeyEventFamily] = {
    234: "HOCKEY_ML",
    235: "HOCKEY_ML",
    236: "HOCKEY_OU_55",
    237: "HOCKEY_OU_55",
    238: "HOCKEY_OU_65",
    239: "HOCKEY_OU_65",
    240: "HOCKEY_PL_HOME",
    241: "HOCKEY_PL_AWAY",
    242: "HOCKEY_PL_AWAY",
    243: "HOCKEY_PL_HOME",
    244: "HOCKEY_HOME_TT_25",
    245: "HOCKEY_HOME_TT_25",
    246: "HOCKEY_HOME_TT_35",
    247: "HOCKEY_HOME_TT_35",
    248: "HOCKEY_AWAY_TT_25",
    249: "HOCKEY_AWAY_TT_25",
    250: "HOCKEY_AWAY_TT_35",
    251: "HOCKEY_AWAY_TT_35"}


def _candidate(
    *,
    event_id: int,
    result: str = "1",
    home_goals: int | None = 2,
    away_goals: int | None = 1,
    ot_winner: int | None = None,
    so_winner: int | None = None,
    family: HockeyEventFamily | None = None,
    event_name: str = "hockey") -> HockeySettlementCandidate:
    resolved_family = family or _EVENT_FAMILY.get(event_id, "HOCKEY_ML")
    return HockeySettlementCandidate(
        record_id=1,
        target="final_prediction",
        event_id=event_id,
        event_name=event_name,
        family=resolved_family,
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        ot_winner=ot_winner,
        so_winner=so_winner,
        match_id=10)


class TestHockeyMarketCatalog(unittest.TestCase):
    """The bet catalog is exactly events 234-251."""

    def test_catalog_covers_every_hockey_bet_event(self) -> None:
        self.assertEqual(
            HOCKEY_BET_MARKET_EVENT_IDS,
            frozenset(range(234, 252)))
        self.assertEqual(set(HOCKEY_MARKET_RULES), set(range(234, 252)))


class TestFinalScore(unittest.TestCase):
    """Regulation ties gain one goal; decided games stay unchanged."""

    def test_regulation_win_ignores_overtime_fields(self) -> None:
        self.assertEqual(final_score(4, 1, 2, None), (4, 1))

    def test_overtime_home_win_adds_one_goal(self) -> None:
        self.assertEqual(final_score(2, 2, 1, None), (3, 2))

    def test_shootout_away_win_adds_one_goal(self) -> None:
        self.assertEqual(final_score(1, 1, 3, 2), (1, 2))

    def test_shootout_home_win_is_four_three(self) -> None:
        self.assertEqual(final_score(3, 3, 3, 1), (4, 3))


class TestMoneylineSettlement(unittest.TestCase):
    """Moneyline follows the winner after overtime and shootouts."""

    def test_regulation_home_win(self) -> None:
        home = _candidate(
            event_id=234, result="1", home_goals=3, away_goals=1)
        away = _candidate(
            event_id=235, result="1", home_goals=3, away_goals=1)
        self.assertEqual(evaluate_hockey_outcome(home), 1)
        self.assertEqual(evaluate_hockey_outcome(away), 0)

    def test_overtime_home_win(self) -> None:
        home = _candidate(
            event_id=234,
            result="X",
            home_goals=2,
            away_goals=2,
            ot_winner=1)
        away = _candidate(
            event_id=235,
            result="X",
            home_goals=2,
            away_goals=2,
            ot_winner=1)
        self.assertEqual(evaluate_hockey_outcome(home), 1)
        self.assertEqual(evaluate_hockey_outcome(away), 0)

    def test_shootout_away_win(self) -> None:
        home = _candidate(
            event_id=234,
            result="X",
            home_goals=2,
            away_goals=2,
            ot_winner=3,
            so_winner=2)
        away = _candidate(
            event_id=235,
            result="X",
            home_goals=2,
            away_goals=2,
            ot_winner=3,
            so_winner=2)
        self.assertEqual(evaluate_hockey_outcome(home), 0)
        self.assertEqual(evaluate_hockey_outcome(away), 1)


class TestPuckLineSettlement(unittest.TestCase):
    """Winning by one goal in overtime does not cover -1.5."""

    def test_one_goal_overtime_win_misses_minus_one_and_half(self) -> None:
        home_minus = _candidate(
            event_id=240,
            result="X",
            home_goals=2,
            away_goals=2,
            ot_winner=1)
        home_plus = _candidate(
            event_id=241,
            result="X",
            home_goals=2,
            away_goals=2,
            ot_winner=1)
        away_plus = _candidate(
            event_id=243,
            result="X",
            home_goals=2,
            away_goals=2,
            ot_winner=1)
        self.assertEqual(evaluate_hockey_outcome(home_minus), 0)
        self.assertEqual(evaluate_hockey_outcome(home_plus), 1)
        self.assertEqual(evaluate_hockey_outcome(away_plus), 1)

    def test_two_goal_regulation_win_covers_minus_one_and_half(self) -> None:
        candidate = _candidate(
            event_id=240, result="1", home_goals=3, away_goals=1)
        self.assertEqual(evaluate_hockey_outcome(candidate), 1)


class TestTotalAndTeamGoals(unittest.TestCase):
    """A shootout goal counts in totals and team goals."""

    def test_shootout_makes_over_six_and_half_win(self) -> None:
        over = _candidate(
            event_id=238,
            result="X",
            home_goals=3,
            away_goals=3,
            ot_winner=3,
            so_winner=1)
        under = _candidate(
            event_id=239,
            result="X",
            home_goals=3,
            away_goals=3,
            ot_winner=3,
            so_winner=1)
        self.assertEqual(evaluate_hockey_outcome(over), 1)
        self.assertEqual(evaluate_hockey_outcome(under), 0)

    def test_same_match_splits_team_totals_at_three_and_half(self) -> None:
        home_over = _candidate(
            event_id=246,
            result="X",
            home_goals=3,
            away_goals=3,
            ot_winner=3,
            so_winner=1)
        away_over = _candidate(
            event_id=250,
            result="X",
            home_goals=3,
            away_goals=3,
            ot_winner=3,
            so_winner=1)
        self.assertEqual(evaluate_hockey_outcome(home_over), 1)
        self.assertEqual(evaluate_hockey_outcome(away_over), 0)


class TestAllHockeyBetMarkets(unittest.TestCase):
    """Every event 234-251 settles on a 4-3 shootout final."""

    def test_four_three_shootout_settles_all_eighteen_events(self) -> None:
        expected = {
            234: 1,
            235: 0,
            236: 1,
            237: 0,
            238: 1,
            239: 0,
            240: 0,
            241: 1,
            242: 0,
            243: 1,
            244: 1,
            245: 0,
            246: 1,
            247: 0,
            248: 1,
            249: 0,
            250: 0,
            251: 1}
        self.assertEqual(set(expected), set(range(234, 252)))
        for event_id, outcome in expected.items():
            candidate = _candidate(
                event_id=event_id,
                result="X",
                home_goals=3,
                away_goals=3,
                ot_winner=3,
                so_winner=1)
            self.assertEqual(
                evaluate_hockey_outcome(candidate),
                outcome,
                msg=f"event_id={event_id}")


class TestInvalidHockeyPayloads(unittest.TestCase):
    """Invalid payloads stay pending instead of a guessed loss."""

    def test_tied_goals_without_overtime_winner_raise(self) -> None:
        candidate = _candidate(
            event_id=234,
            result="X",
            home_goals=3,
            away_goals=3,
            ot_winner=None)
        with self.assertRaises(InvalidMatchResultError):
            evaluate_hockey_outcome(candidate)

    def test_shootout_without_winner_raises(self) -> None:
        candidate = _candidate(
            event_id=234,
            result="X",
            home_goals=3,
            away_goals=3,
            ot_winner=3,
            so_winner=None)
        with self.assertRaises(InvalidMatchResultError):
            evaluate_hockey_outcome(candidate)

    def test_unknown_overtime_winner_raises(self) -> None:
        with self.assertRaises(InvalidMatchResultError):
            final_score(2, 2, 9, None)

    def test_unknown_event_raises(self) -> None:
        candidate = _candidate(event_id=999, event_name="unknown")
        with self.assertRaises(UnsupportedHockeyEventError):
            evaluate_hockey_outcome(candidate)

    def test_unfinished_result_raises(self) -> None:
        candidate = _candidate(
            event_id=234, result="0", home_goals=0, away_goals=0)
        with self.assertRaises(InvalidMatchResultError):
            evaluate_hockey_outcome(candidate)

    def test_missing_goals_raise(self) -> None:
        candidate = _candidate(
            event_id=234, result="1", home_goals=None, away_goals=1)
        with self.assertRaises(InvalidMatchResultError):
            evaluate_hockey_outcome(candidate)

    def test_negative_goals_raise(self) -> None:
        with self.assertRaises(InvalidMatchResultError):
            final_score(-1, 2, None, None)
