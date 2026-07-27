"""Unit tests for model statistics maintenance repository SQL contracts."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.repositories.model_statistics_maintenance_repository import (
    BetGenerationScope,
    GeneratedBet,
    _UPSERT_GENERATED_BET_SQL,
    fetch_bet_generation_candidates,
    fetch_pending_bets,
    fetch_pending_final_predictions,
    write_bet_outcomes,
    write_final_prediction_outcomes,
    write_generated_bets)
from backend.sports.football.outcome_evaluator import BET_MARKET_EVENT_IDS


class TestBetGenerationScope(unittest.TestCase):
    """Scope validation for bet generation filters."""

    def test_rejects_inverted_date_range(self) -> None:
        with self.assertRaises(ValueError):
            BetGenerationScope(
                date_from=date(2026, 7, 28),
                date_to=date(2026, 7, 27))

    def test_accepts_equal_date_bounds(self) -> None:
        scope = BetGenerationScope(
            date_from=date(2026, 7, 27),
            date_to=date(2026, 7, 27))
        self.assertEqual(scope.date_from, date(2026, 7, 27))


class TestFetchPendingFinalPredictions(unittest.TestCase):
    """Keyset reads for unsettled final predictions."""

    @patch(
        "backend.repositories.model_statistics_maintenance_repository"
        "._fetch_dicts")
    def test_query_uses_outcome_null_and_parameters(
            self,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{
            "record_id": 10,
            "event_id": 1,
            "event_name": "home",
            "family": "REZULTAT",
            "result": "1",
            "home_goals": 2,
            "away_goals": 1}]
        candidates = fetch_pending_final_predictions(after_id=5, limit=50)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].record_id, 10)
        self.assertEqual(candidates[0].target, "final_prediction")
        query, params = mock_fetch.call_args.args
        self.assertIn("fp.outcome IS NULL", query)
        self.assertIn("fp.ID > %s", query)
        self.assertEqual(params[0], 5)
        self.assertEqual(params[-1], 50)
        self.assertIn("REZULTAT", params)
        self.assertIn("EXACT", params)
        self.assertIn("GOALS", params)

    @patch(
        "backend.repositories.model_statistics_maintenance_repository"
        "._fetch_dicts")
    def test_empty_limit_skips_query(
            self,
            mock_fetch: MagicMock) -> None:
        self.assertEqual(
            fetch_pending_final_predictions(after_id=0, limit=0),
            [])
        mock_fetch.assert_not_called()


class TestFetchPendingBets(unittest.TestCase):
    """Keyset reads for priced bet markets only."""

    @patch(
        "backend.repositories.model_statistics_maintenance_repository"
        "._fetch_dicts")
    def test_filters_seven_bet_market_events(
            self,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{
            "record_id": 3,
            "event_id": 8,
            "event_name": "over",
            "family": "OU",
            "result": "1",
            "home_goals": 3,
            "away_goals": 1}]
        candidates = fetch_pending_bets(after_id=1, limit=20)
        self.assertEqual(candidates[0].target, "bet")
        query, params = mock_fetch.call_args.args
        self.assertIn("b.outcome IS NULL", query)
        self.assertIn("b.event_id IN (", query)
        for event_id in sorted(BET_MARKET_EVENT_IDS):
            self.assertIn(event_id, params)
        self.assertNotIn(174, params)
        self.assertNotIn(198, params)

    @patch(
        "backend.repositories.model_statistics_maintenance_repository"
        "._fetch_dicts")
    def test_sql_has_no_user_value_interpolation(
            self,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = []
        fetch_pending_bets(after_id=99, limit=10)
        query, params = mock_fetch.call_args.args
        self.assertNotIn("99", query)
        self.assertNotIn("10", query)
        self.assertEqual(params[0], 99)
        self.assertEqual(params[-1], 10)


class TestFetchBetGenerationCandidates(unittest.TestCase):
    """Deterministic best-odds selection for bet generation."""

    @patch(
        "backend.repositories.model_statistics_maintenance_repository"
        "._fetch_dicts")
    def test_orders_best_odds_desc_then_id_asc(
            self,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = [{
            "match_id": 1,
            "event_id": 1,
            "model_id": 2,
            "bookmaker_id": 4,
            "odds": 2.1,
            "ev": 0.05}]
        scope = BetGenerationScope(league_id=1, match_id=100)
        rows = fetch_bet_generation_candidates(scope)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].bookmaker_id, 4)
        query, params = mock_fetch.call_args.args
        self.assertIn("ORDER BY o.odds DESC, o.id ASC", query)
        self.assertIn("ml.active = 1", query)
        self.assertIn("o.odds > 0", query)
        self.assertIn("ROUND((p.value / 100.0) * bo.odds - 1, 4)", query)
        self.assertIn(1, params)
        self.assertIn(100, params)
        self.assertIn("m.league = %s", query)
        self.assertIn("m.id = %s", query)

    @patch(
        "backend.repositories.model_statistics_maintenance_repository"
        "._fetch_dicts")
    def test_scope_date_filters_are_parameterized(
            self,
            mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = []
        scope = BetGenerationScope(
            season_id=7,
            date_from=date(2026, 7, 27),
            date_to=date(2026, 7, 28))
        fetch_bet_generation_candidates(scope)
        query, params = mock_fetch.call_args.args
        self.assertIn("m.season = %s", query)
        self.assertIn("CAST(m.game_date AS DATE) >= %s", query)
        self.assertIn("CAST(m.game_date AS DATE) <= %s", query)
        self.assertIn(7, params)
        self.assertIn(date(2026, 7, 27), params)
        self.assertIn(date(2026, 7, 28), params)


class TestWriteGeneratedBets(unittest.TestCase):
    """Upsert contract for automatic model bets."""

    def test_upsert_updates_odds_and_ev_not_outcome(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        rows = [
            GeneratedBet(
                match_id=1,
                event_id=1,
                model_id=2,
                bookmaker_id=3,
                odds=2.5,
                ev=0.125)]
        written = write_generated_bets(rows, conn)
        self.assertEqual(written, 1)
        sql, params_seq = cursor.executemany.call_args.args
        self.assertEqual(sql, _UPSERT_GENERATED_BET_SQL)
        self.assertNotIn("outcome", sql.lower().split("update", 1)[-1])
        self.assertIn("odds = VALUES(odds)", sql)
        self.assertIn("EV = VALUES(EV)", sql)
        self.assertEqual(
            list(params_seq),
            [(1, 1, 2.5, 3, 0.125, 2)])
        cursor.close.assert_called_once()

    def test_upsert_does_not_commit(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        write_generated_bets([
            GeneratedBet(
                match_id=1,
                event_id=1,
                model_id=2,
                bookmaker_id=3,
                odds=2.0,
                ev=0.0)], conn)
        conn.commit.assert_not_called()
        conn.rollback.assert_not_called()

    def test_empty_rows_skip_cursor(self) -> None:
        conn = MagicMock()
        self.assertEqual(write_generated_bets([], conn), 0)
        conn.cursor.assert_not_called()


class TestWriteOutcomes(unittest.TestCase):
    """Outcome writes only touch still-pending rows."""

    def test_final_prediction_update_requires_null_outcome(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        cursor.rowcount = 1
        conn.cursor.return_value = cursor
        updated = write_final_prediction_outcomes([(10, 1), (11, 0)], conn)
        self.assertEqual(updated, 2)
        first_sql, first_params = cursor.execute.call_args_list[0].args
        self.assertIn("outcome IS NULL", first_sql)
        self.assertEqual(first_params, (1, 10))
        second_params = cursor.execute.call_args_list[1].args[1]
        self.assertEqual(second_params, (0, 11))

    def test_bet_update_requires_null_outcome(self) -> None:
        conn = MagicMock()
        cursor = MagicMock()
        cursor.rowcount = 0
        conn.cursor.return_value = cursor
        updated = write_bet_outcomes([(5, 1)], conn)
        self.assertEqual(updated, 0)
        sql, params = cursor.execute.call_args.args
        self.assertIn("UPDATE bets", sql)
        self.assertIn("outcome IS NULL", sql)
        self.assertEqual(params, (1, 5))

    def test_empty_outcome_rows_skip_cursor(self) -> None:
        conn = MagicMock()
        self.assertEqual(write_final_prediction_outcomes([], conn), 0)
        self.assertEqual(write_bet_outcomes([], conn), 0)
        conn.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
