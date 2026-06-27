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
        frame = pd.DataFrame([
            {
                "event_id": 12,
                "pred_outcome": 1,
                "bet_event_id": 12,
                "bet_outcome": 1,
                "odds": 2.0,
            },
            {
                "event_id": 8,
                "pred_outcome": 0,
                "bet_event_id": 8,
                "bet_outcome": 0,
                "odds": 1.8,
            },
            {
                "event_id": 12,
                "pred_outcome": 1,
                "bet_event_id": 12,
                "bet_outcome": 0,
                "odds": 1.9,
            },
        ])
        stats = _generate_category_statistics(frame, "ou", False, 0.12)
        self.assertEqual(stats["predictions"]["total"], 3)
        self.assertEqual(stats["predictions"]["correct"], 2)
        self.assertEqual(stats["bets"]["total"], 3)
        self.assertEqual(stats["bets"]["correct"], 1)
        self.assertEqual(stats["bets"]["profit_total"], -1.0)
        self.assertEqual(
            stats["predictions"]["charts"]["distribution"]["labels"],
            ["Under 2.5", "Over 2.5"])

    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_prediction_bet_rows")
    def test_get_model_statistics_returns_requested_categories(
        self,
        mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = pd.DataFrame([
            {
                "event_id": 1,
                "pred_outcome": 1,
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
        mock_fetch.assert_called_once()

    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_prediction_bet_rows")
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
        mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = pd.DataFrame()
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


if __name__ == "__main__":
    unittest.main()
