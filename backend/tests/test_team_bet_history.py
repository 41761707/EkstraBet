"""Unit tests for the team-bet history strip rules."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.repositories.team_bet_history_repository import (
    fetch_team_recent_matches)
from backend.sports.team_bet_history import (
    PastMatch,
    history_rule,
    history_stat_filter,
    is_history_hit,
    names_sampled_team,
    sample_team_id,
    sampled_teams,
    stat_value)


def _match(
        *,
        home_team_id: int,
        away_team_id: int,
        home_goals: int,
        away_goals: int,
        result: str,
        home_corners: int | None = None,
        away_corners: int | None = None,
        ot_winner: int | None = None,
        so_winner: int | None = None) -> PastMatch:
    """Build a finished match with empty non-goal counts unless set."""
    return PastMatch(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_goals=home_goals,
        away_goals=away_goals,
        result=result,
        home_corners=home_corners,
        away_corners=away_corners,
        home_fouls=None,
        away_fouls=None,
        home_yellows=None,
        away_yellows=None,
        home_offsides=None,
        away_offsides=None,
        ot_winner=ot_winner,
        so_winner=so_winner)


class TestTeamBetHistoryRules(unittest.TestCase):
    """Rules and bar values, without the database."""

    def test_home_win_follows_the_team_when_they_played_away(self) -> None:
        rule = history_rule(1, 1, "Zwycięstwo gospodarza")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(sample_team_id(rule, 11, 12), 11)
        away_win = _match(
            home_team_id=20,
            away_team_id=11,
            home_goals=0,
            away_goals=2,
            result="2")
        home_draw = _match(
            home_team_id=11,
            away_team_id=21,
            home_goals=1,
            away_goals=1,
            result="X")
        self.assertEqual(stat_value(rule, 11, away_win), 1.0)
        self.assertEqual(stat_value(rule, 11, home_draw), 0.0)
        self.assertTrue(is_history_hit(1.0, rule.line, rule.comparator))
        self.assertFalse(is_history_hit(0.0, rule.line, rule.comparator))

    def test_under_totals_sample_home_then_away(self) -> None:
        rule = history_rule(1, 12, "Poniżej 2.5 gola")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(rule.sample, "home")
        self.assertEqual(rule.line, 2.5)
        self.assertEqual(rule.comparator, "under")
        self.assertEqual(
            sampled_teams(rule, 11, 12),
            [("home", 11), ("away", 12)])

    def test_named_side_samples_one_team(self) -> None:
        home = history_rule(1, 1, "Zwycięstwo gospodarza")
        away = history_rule(1, 3, "Zwycięstwo gościa")
        self.assertIsNotNone(home)
        self.assertIsNotNone(away)
        assert home is not None
        assert away is not None
        self.assertEqual(sampled_teams(home, 11, 12), [("home", 11)])
        self.assertEqual(sampled_teams(away, 11, 12), [("away", 12)])

    def test_under_totals_use_the_home_teams_recent_matches(self) -> None:
        rule = history_rule(1, 12, "Poniżej 2.5 gola")
        self.assertIsNotNone(rule)
        assert rule is not None
        low = _match(
            home_team_id=11,
            away_team_id=12,
            home_goals=1,
            away_goals=0,
            result="1")
        self.assertEqual(stat_value(rule, 11, low), 1.0)
        self.assertTrue(is_history_hit(1.0, rule.line, rule.comparator))
        self.assertFalse(is_history_hit(5.0, rule.line, rule.comparator))

    def test_parsed_team_total_counts_goals_the_team_scored(self) -> None:
        rule = history_rule(1, 40, "Gospodarz powyżej 1.5 gola")
        self.assertIsNotNone(rule)
        assert rule is not None
        played_away = _match(
            home_team_id=30,
            away_team_id=11,
            home_goals=4,
            away_goals=2,
            result="1")
        self.assertEqual(stat_value(rule, 11, played_away), 2.0)

    def test_hockey_moneyline_is_the_goal_margin(self) -> None:
        rule = history_rule(2, 234, "Zwycięstwo gospodarza (OT/SO)")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(rule.stat, "margin")
        self.assertEqual(rule.line, 0.0)
        won = _match(
            home_team_id=11,
            away_team_id=12,
            home_goals=3,
            away_goals=1,
            result="1")
        self.assertEqual(stat_value(rule, 11, won), 2.0)
        self.assertTrue(is_history_hit(2.0, rule.line, rule.comparator))

    def test_hockey_overtime_goal_lifts_margin_and_total(self) -> None:
        margin = history_rule(2, 234, "Zwycięstwo gospodarza (OT/SO)")
        total = history_rule(2, 236, "Powyżej 5.5")
        self.assertIsNotNone(margin)
        self.assertIsNotNone(total)
        assert margin is not None
        assert total is not None
        tied = _match(
            home_team_id=11,
            away_team_id=12,
            home_goals=2,
            away_goals=2,
            result="X",
            ot_winner=1)
        self.assertEqual(stat_value(margin, 11, tied), 1.0)
        self.assertEqual(stat_value(total, 11, tied), 5.0)
        self.assertTrue(is_history_hit(1.0, margin.line, margin.comparator))

    def test_exact_score_is_a_hit_flag(self) -> None:
        rule = history_rule(1, 198, "1:0")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(rule.sample, "home")
        self.assertTrue(names_sampled_team(rule))
        hit = _match(
            home_team_id=11,
            away_team_id=12,
            home_goals=1,
            away_goals=0,
            result="1")
        miss = _match(
            home_team_id=11,
            away_team_id=12,
            home_goals=2,
            away_goals=0,
            result="1")
        away_hit = _match(
            home_team_id=20,
            away_team_id=11,
            home_goals=0,
            away_goals=1,
            result="2")
        away_loss = _match(
            home_team_id=20,
            away_team_id=11,
            home_goals=1,
            away_goals=0,
            result="1")
        self.assertEqual(stat_value(rule, 11, hit), 1.0)
        self.assertEqual(stat_value(rule, 11, miss), 0.0)
        self.assertEqual(stat_value(rule, 11, away_hit), 1.0)
        self.assertEqual(stat_value(rule, 11, away_loss), 0.0)
        self.assertIsNone(history_rule(1, 198, "not-a-score"))

    def test_corners_use_their_own_history_filter(self) -> None:
        rule = history_rule(1, 70, "Powyżej 8.5 rożnych")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(history_stat_filter(rule), "corners_total")
        self.assertTrue(names_sampled_team(rule))

    def test_missing_corners_are_skipped(self) -> None:
        rule = history_rule(1, 70, "Powyżej 8.5 rożnych")
        self.assertIsNotNone(rule)
        assert rule is not None
        missing = _match(
            home_team_id=11,
            away_team_id=12,
            home_goals=1,
            away_goals=0,
            result="1")
        counted = _match(
            home_team_id=11,
            away_team_id=12,
            home_goals=1,
            away_goals=0,
            result="1",
            home_corners=6,
            away_corners=4)
        self.assertIsNone(stat_value(rule, 11, missing))
        self.assertEqual(stat_value(rule, 11, counted), 10.0)


class TestTeamBetHistoryRepository(unittest.TestCase):
    """The history query stays parameterized."""

    @patch(
        "backend.repositories.team_bet_history_repository.get_db_connection")
    def test_empty_anchors_skip_the_database(
            self,
            mock_connection: MagicMock) -> None:
        frame = fetch_team_recent_matches([], 10)
        self.assertTrue(frame.empty)
        mock_connection.assert_not_called()

    @patch("backend.repositories.team_bet_history_repository.pd.read_sql")
    @patch(
        "backend.repositories.team_bet_history_repository.get_db_connection")
    def test_team_ids_stay_in_parameters(
            self,
            mock_connection: MagicMock,
            mock_read_sql: MagicMock) -> None:
        mock_connection.return_value.__enter__.return_value = object()
        mock_read_sql.return_value = pd.DataFrame()
        kickoff = datetime(2026, 11, 8, 1, 30)
        fetch_team_recent_matches([(11, 100, kickoff, 1, "goals")], 10)
        query = mock_read_sql.call_args.args[0]
        params = mock_read_sql.call_args.kwargs["params"]
        self.assertIn("JOIN LATERAL", query)
        self.assertIn("LEFT JOIN hockey_matches_add hma", query)
        self.assertIn("hma.OTwinner AS ot_winner", query)
        self.assertIn("hma.SOwinner AS so_winner", query)
        self.assertNotIn("home_team_ck IS NOT NULL", query)
        self.assertNotIn("11", query)
        self.assertEqual(params, (11, 100, kickoff, 1, 10))

    @patch("backend.repositories.team_bet_history_repository.pd.read_sql")
    @patch(
        "backend.repositories.team_bet_history_repository.get_db_connection")
    def test_count_stats_are_filtered_before_limit(
            self,
            mock_connection: MagicMock,
            mock_read_sql: MagicMock) -> None:
        mock_connection.return_value.__enter__.return_value = object()
        mock_read_sql.return_value = pd.DataFrame()
        kickoff = datetime(2026, 11, 8, 1, 30)
        fetch_team_recent_matches(
            [(11, 100, kickoff, 1, "corners_total")], 10)
        query = mock_read_sql.call_args.args[0]
        self.assertLess(
            query.index("m.home_team_ck IS NOT NULL"),
            query.index("LIMIT %s"))
        self.assertLess(
            query.index("m.away_team_ck IS NOT NULL"),
            query.index("LIMIT %s"))


if __name__ == "__main__":
    unittest.main()
