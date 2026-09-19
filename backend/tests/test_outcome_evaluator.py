"""Unit tests for football outcome settlement rules."""

from __future__ import annotations

import unittest

from backend.sports.football.event_settlement_registry import MatchBoxscore
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
        record_id: int = 1,
        boxscore: MatchBoxscore | None = None
) -> SettlementCandidate:
    return SettlementCandidate(
        record_id=record_id,
        target=target,
        event_id=event_id,
        event_name=event_name,
        family=family,
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        boxscore=boxscore)


def _boxscore(
        *,
        result: str = "1",
        home_goals: int | None = 2,
        away_goals: int | None = 1,
        home_ck: int | None = 5,
        away_ck: int | None = 4,
        home_fouls: int | None = 12,
        away_fouls: int | None = 10,
        home_yc: int | None = 2,
        away_yc: int | None = 1,
        home_rc: int | None = 0,
        away_rc: int | None = 0,
        home_off: int | None = 2,
        away_off: int | None = 1
) -> MatchBoxscore:
    return MatchBoxscore(
        result=result,
        home_goals=home_goals,
        away_goals=away_goals,
        home_ck=home_ck,
        away_ck=away_ck,
        home_fouls=home_fouls,
        away_fouls=away_fouls,
        home_yc=home_yc,
        away_yc=away_yc,
        home_rc=home_rc,
        away_rc=away_rc,
        home_off=home_off,
        away_off=away_off)


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

    def test_bet_target_rejects_corners(self) -> None:
        candidate = _candidate(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family="OU",
            target="bet",
            boxscore=_boxscore())
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

    def test_final_prediction_still_rejects_corners(self) -> None:
        candidate = _candidate(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family="OU",
            boxscore=_boxscore())
        with self.assertRaises(UnsupportedFootballEventError):
            evaluate_football_outcome(candidate)


class TestTipsterLegSettlement(unittest.TestCase):
    """Tipster legs use goal markets plus registry lines vs boxscore."""

    def test_over_25_at_two_one_is_a_hit(self) -> None:
        # 2:1 = 3 gole; Over 2.5 wygrywa (plan mylnie podał outcome 0).
        candidate = _candidate(
            event_id=8,
            event_name="Powyżej 2.5 gola",
            family="OU",
            target="tipster_leg",
            home_goals=2,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_over_25_at_one_zero_is_a_miss(self) -> None:
        candidate = _candidate(
            event_id=8,
            event_name="Powyżej 2.5 gola",
            family="OU",
            target="tipster_leg",
            home_goals=1,
            away_goals=0)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_over_85_corners_hits_when_ck_is_five_plus_four(self) -> None:
        candidate = _candidate(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family="OU",
            target="tipster_leg",
            boxscore=_boxscore(home_ck=5, away_ck=4))
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_over_85_corners_misses_when_total_is_eight(self) -> None:
        candidate = _candidate(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family="OU",
            target="tipster_leg",
            boxscore=_boxscore(home_ck=4, away_ck=4))
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_missing_home_ck_stays_open(self) -> None:
        candidate = _candidate(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family="OU",
            target="tipster_leg",
            boxscore=_boxscore(home_ck=None, away_ck=4))
        with self.assertRaises(InvalidMatchResultError):
            evaluate_football_outcome(candidate)

    def test_missing_boxscore_for_corners_stays_open(self) -> None:
        candidate = _candidate(
            event_id=33,
            event_name="Powyżej 8.5 rożnych",
            family="OU",
            target="tipster_leg")
        with self.assertRaises(InvalidMatchResultError):
            evaluate_football_outcome(candidate)

    def test_double_chance_home_hits_on_draw(self) -> None:
        candidate = _candidate(
            event_id=4,
            event_name="Gospodarz nie przegra",
            family="REZULTAT",
            target="tipster_leg",
            result="X",
            home_goals=1,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_double_chance_home_misses_on_away_win(self) -> None:
        candidate = _candidate(
            event_id=4,
            event_name="Gospodarz nie przegra",
            family="REZULTAT",
            target="tipster_leg",
            result="2",
            home_goals=0,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 0)

    def test_handicap_home_minus_15_needs_two_goal_margin(self) -> None:
        win = _candidate(
            event_id=49,
            event_name="Handicap -1.5 dla gospodarza",
            family="REZULTAT",
            target="tipster_leg",
            home_goals=2,
            away_goals=0)
        miss = _candidate(
            event_id=49,
            event_name="Handicap -1.5 dla gospodarza",
            family="REZULTAT",
            target="tipster_leg",
            home_goals=2,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(win), 1)
        self.assertEqual(evaluate_football_outcome(miss), 0)

    def test_home_over_15_goals_line_from_registry(self) -> None:
        candidate = _candidate(
            event_id=16,
            event_name="Gospodarz powyżej 1.5 gola",
            family="OU",
            target="tipster_leg",
            home_goals=2,
            away_goals=0)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_exact_score_by_id_without_exact_family(self) -> None:
        candidate = _candidate(
            event_id=211,
            event_name="2:1",
            family="OU",
            target="tipster_leg",
            home_goals=2,
            away_goals=1)
        self.assertEqual(evaluate_football_outcome(candidate), 1)

    def test_unsupported_parent_goals_event_raises(self) -> None:
        candidate = _candidate(
            event_id=173,
            event_name="Dokładna liczba goli",
            family="GOALS",
            target="tipster_leg")
        with self.assertRaises(UnsupportedFootballEventError):
            evaluate_football_outcome(candidate)


if __name__ == "__main__":
    unittest.main()
