"""Unit tests for model analytics service helpers."""

from __future__ import annotations
import unittest
from unittest.mock import patch
import pandas as pd
from backend.services.analytics_service import (
    _generate_category_statistics,
    _safe_pct,
    get_model_statistics)


class TestAnalyticsService(unittest.TestCase):
    """Tests for analytics statistics computation."""

    def test_safe_pct_returns_none_for_zero_denominator(self) -> None:
        self.assertIsNone(_safe_pct(1, 0))

    def test_safe_pct_rounds_to_two_decimals(self) -> None:
        self.assertEqual(_safe_pct(1, 3), 33.33)

    def test_generate_ou_category_statistics(self) -> None:
        pred_frame = pd.DataFrame([
            {"event_id": 12, "pred_outcome": 1},
            {"event_id": 8, "pred_outcome": 0},
            {"event_id": 12, "pred_outcome": 1},
        ])
        bet_frame = pd.DataFrame([
            {
                "bet_event_id": 12,
                "bet_outcome": 1,
                "odds": 2.0,
            },
            {
                "bet_event_id": 8,
                "bet_outcome": 0,
                "odds": 1.8,
            },
            {
                "bet_event_id": 12,
                "bet_outcome": 0,
                "odds": 1.9,
            },
        ])
        stats = _generate_category_statistics(
            pred_frame, bet_frame, "ou", False, 0.12)
        self.assertEqual(stats["predictions"]["total"], 3)
        self.assertEqual(stats["predictions"]["correct"], 2)
        self.assertEqual(stats["bets"]["total"], 3)
        self.assertEqual(stats["bets"]["correct"], 1)
        self.assertEqual(stats["bets"]["profit_total"], -1.0)
        self.assertEqual(
            stats["predictions"]["charts"]["distribution"]["labels"],
            ["Poniżej 2.5", "Powyżej 2.5"])

    def test_predictions_do_not_require_matching_bets(self) -> None:
        pred_frame = pd.DataFrame([
            {"event_id": 12, "pred_outcome": 1},
            {"event_id": 8, "pred_outcome": 0},
        ])
        stats = _generate_category_statistics(
            pred_frame, pd.DataFrame(), "ou", False, 0.12)
        self.assertEqual(stats["predictions"]["total"], 2)
        self.assertEqual(stats["predictions"]["correct"], 1)
        self.assertEqual(stats["bets"]["total"], 0)

    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_bet_rows")
    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_prediction_rows")
    def test_get_model_statistics_returns_requested_categories(
        self,
        mock_pred_fetch: unittest.mock.MagicMock,
        mock_bet_fetch: unittest.mock.MagicMock) -> None:
        mock_pred_fetch.return_value = pd.DataFrame([
            {
                "event_id": 1,
                "pred_outcome": 1,
            },
        ])
        mock_bet_fetch.return_value = pd.DataFrame([
            {
                "bet_event_id": 1,
                "bet_outcome": 1,
                "odds": 2.5,
            },
        ])
        payload = get_model_statistics(
            stat_type="result",
            model_result_ids=[3],
            season_id=11,
            league_ids=[1])
        self.assertIn("result", payload["categories"])
        self.assertEqual(payload["filters_applied"]["season_id"], 11)
        mock_pred_fetch.assert_called_once()
        mock_bet_fetch.assert_called_once()

    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_bet_rows")
    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_prediction_rows")
    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_league_prediction_aggregation")
    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_league_average_prediction_stats")
    def test_get_model_statistics_builds_league_aggregation(
        self,
        mock_average: unittest.mock.MagicMock,
        mock_league_agg: unittest.mock.MagicMock,
        mock_pred_fetch: unittest.mock.MagicMock,
        mock_bet_fetch: unittest.mock.MagicMock) -> None:
        mock_pred_fetch.return_value = pd.DataFrame()
        mock_bet_fetch.return_value = pd.DataFrame()
        mock_league_agg.return_value = pd.DataFrame([{
            "entity_id": 1,
            "entity_name": "Ekstraklasa",
            "total_predictions": 10,
            "correct_predictions": 6,
        }])
        mock_average.return_value = (10, 6)
        payload = get_model_statistics(
            stat_type="ou",
            model_ou_ids=[2],
            season_id=11,
            group_by="league")
        by_league = payload["aggregations"]["by_league"]
        self.assertEqual(by_league["metric"], "accuracy")
        self.assertEqual(len(by_league["ou"]), 2)
        self.assertEqual(by_league["ou"][-1]["entity_name"], "AVERAGE")

    def test_build_league_outcome_comparison_requires_two_leagues(
        self) -> None:
        from backend.services.analytics_service import (
            _build_league_outcome_comparison)
        frame = pd.DataFrame([{
            "league_id": 1,
            "league_name": "Ekstraklasa",
            "played_matches": 10,
            "over_2_5_count": 4,
            "btts_yes_count": 5,
            "home_win_count": 4,
            "away_win_count": 3,
        }])
        self.assertIsNone(_build_league_outcome_comparison(frame))

    def test_build_league_outcome_comparison_weights_by_matches(
        self) -> None:
        from backend.services.analytics_service import (
            _build_league_outcome_comparison)
        frame = pd.DataFrame([
            {
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "played_matches": 10,
                "over_2_5_count": 5,
                "btts_yes_count": 6,
                "home_win_count": 4,
                "away_win_count": 3,
            },
            {
                "league_id": 2,
                "league_name": "Premier League",
                "played_matches": 20,
                "over_2_5_count": 10,
                "btts_yes_count": 8,
                "home_win_count": 8,
                "away_win_count": 6,
            },
        ])
        payload = _build_league_outcome_comparison(frame)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(len(payload["leagues"]), 2)
        self.assertEqual(payload["averages"]["btts_yes_pct"], 46.67)
        self.assertEqual(payload["averages"]["over_2_5_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()
