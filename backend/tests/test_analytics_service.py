"""Unit tests for model analytics service helpers."""

from __future__ import annotations
import unittest
from unittest.mock import patch
import pandas as pd
from backend.services.analytics_service import (
    _build_model_bet_profit_league_comparisons,
    _build_model_league_comparisons,
    _build_model_prediction_league_comparisons,
    _generate_category_statistics,
    _safe_pct,
    get_league_outcome_comparisons,
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

    def test_get_league_outcome_comparisons_requires_two_leagues(
        self) -> None:
        self.assertIsNone(get_league_outcome_comparisons([1], 11))
        self.assertIsNone(get_league_outcome_comparisons(None, 11))

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

    def test_prediction_comparisons_keep_models_separate(self) -> None:
        frame = pd.DataFrame([
            *_prediction_rows(1, "Alpha", 1, "Ekstraklasa", 10, 1),
            *_prediction_rows(1, "Alpha", 2, "Premier League", 20, 9),
            *_prediction_rows(2, "Beta", 1, "Ekstraklasa", 10, 8),
            *_prediction_rows(2, "Beta", 2, "Premier League", 10, 2),
        ])
        payload = _build_model_prediction_league_comparisons(frame)
        self.assertEqual(len(payload), 2)
        alpha = payload[0]
        beta = payload[1]
        self.assertEqual(alpha["model_name"], "Alpha")
        self.assertEqual(beta["model_name"], "Beta")
        self.assertEqual(alpha["average_accuracy_pct"], 33.33)
        self.assertEqual(beta["average_accuracy_pct"], 50.0)
        self.assertEqual(alpha["leagues"][0]["correct"], 1)
        self.assertEqual(beta["leagues"][0]["correct"], 8)

    def test_prediction_comparisons_weight_accuracy_by_totals(self) -> None:
        frame = pd.DataFrame([
            *_prediction_rows(1, "Alpha", 1, "Ekstraklasa", 10, 1),
            *_prediction_rows(1, "Alpha", 2, "Premier League", 20, 9),
        ])
        payload = _build_model_prediction_league_comparisons(frame)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["average_accuracy_pct"], 33.33)
        self.assertNotEqual(payload[0]["average_accuracy_pct"], 27.5)

    def test_prediction_comparisons_skip_single_league_and_empty(
        self) -> None:
        single_league = pd.DataFrame(
            _prediction_rows(1, "Alpha", 1, "Ekstraklasa", 5, 5))
        self.assertEqual(
            _build_model_prediction_league_comparisons(single_league),
            [])
        self.assertEqual(
            _build_model_prediction_league_comparisons(pd.DataFrame()),
            [])

    def test_bet_profit_comparisons_apply_odds_and_tax(self) -> None:
        frame = pd.DataFrame([
            {
                "model_id": 1,
                "model_name": "Alpha",
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "bet_event_id": 8,
                "odds": 2.0,
                "bet_outcome": 1,
            },
            {
                "model_id": 1,
                "model_name": "Alpha",
                "league_id": 2,
                "league_name": "Premier League",
                "bet_event_id": 8,
                "odds": 1.8,
                "bet_outcome": 0,
            },
        ])
        without_tax = _build_model_bet_profit_league_comparisons(
            frame, False, 0.12)
        with_tax = _build_model_bet_profit_league_comparisons(
            frame, True, 0.12)
        self.assertEqual(len(without_tax), 1)
        self.assertEqual(without_tax[0]["leagues"][0]["profit"], 1.0)
        self.assertEqual(without_tax[0]["leagues"][1]["profit"], -1.0)
        self.assertEqual(without_tax[0]["total_profit"], 0.0)
        self.assertEqual(with_tax[0]["leagues"][0]["profit"], 0.76)
        self.assertEqual(with_tax[0]["total_profit"], -0.24)

    def test_bet_profit_comparisons_skip_single_league(self) -> None:
        frame = pd.DataFrame([{
            "model_id": 1,
            "model_name": "Alpha",
            "league_id": 1,
            "league_name": "Ekstraklasa",
            "bet_event_id": 8,
            "odds": 2.0,
            "bet_outcome": 1,
        }])
        self.assertEqual(
            _build_model_bet_profit_league_comparisons(frame, False, 0.12),
            [])

    def test_model_league_comparisons_are_null_when_empty(self) -> None:
        payload = _build_model_league_comparisons({}, False, 0.12)
        self.assertIsNone(payload)

    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_bet_rows")
    @patch(
        "backend.services.analytics_service.analytics_repository."
        "fetch_prediction_rows")
    def test_get_model_statistics_returns_separate_model_league_sets(
        self,
        mock_pred_fetch: unittest.mock.MagicMock,
        mock_bet_fetch: unittest.mock.MagicMock) -> None:
        mock_pred_fetch.return_value = pd.DataFrame([
            *_prediction_rows(1, "Alpha", 1, "Ekstraklasa", 10, 1),
            *_prediction_rows(1, "Alpha", 2, "Premier League", 20, 9),
            *_prediction_rows(2, "Beta", 1, "Ekstraklasa", 10, 8),
            *_prediction_rows(2, "Beta", 2, "Premier League", 10, 2),
        ])
        mock_bet_fetch.return_value = pd.DataFrame([
            {
                "model_id": 1,
                "model_name": "Alpha",
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "bet_event_id": 8,
                "odds": 2.0,
                "bet_outcome": 1,
            },
            {
                "model_id": 1,
                "model_name": "Alpha",
                "league_id": 2,
                "league_name": "Premier League",
                "bet_event_id": 8,
                "odds": 1.8,
                "bet_outcome": 0,
            },
            {
                "model_id": 2,
                "model_name": "Beta",
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "bet_event_id": 8,
                "odds": 3.0,
                "bet_outcome": 1,
            },
            {
                "model_id": 2,
                "model_name": "Beta",
                "league_id": 2,
                "league_name": "Premier League",
                "bet_event_id": 12,
                "odds": 1.5,
                "bet_outcome": 1,
            },
        ])
        payload = get_model_statistics(
            stat_type="ou",
            model_ou_ids=[1, 2])
        comparisons = payload["model_league_comparisons"]
        self.assertIsNotNone(comparisons)
        assert comparisons is not None
        ou_predictions = comparisons["predictions"]["ou"]
        ou_profits = comparisons["bet_profits"]["ou"]
        self.assertEqual(len(ou_predictions), 2)
        self.assertEqual(len(ou_profits), 2)
        self.assertEqual(ou_predictions[0]["model_id"], 1)
        self.assertEqual(ou_predictions[1]["model_id"], 2)
        self.assertEqual(ou_predictions[0]["average_accuracy_pct"], 33.33)
        self.assertEqual(ou_profits[1]["total_profit"], 2.5)
        self.assertEqual(comparisons["predictions"]["btts"], [])
        self.assertEqual(comparisons["bet_profits"]["result"], [])


def _prediction_rows(
    model_id: int,
    model_name: str,
    league_id: int,
    league_name: str,
    total: int,
    correct: int) -> list[dict[str, object]]:
    """Build prediction rows for one model and league."""
    rows: list[dict[str, object]] = []
    for index in range(total):
        rows.append({
            "event_id": 8,
            "pred_outcome": 1 if index < correct else 0,
            "model_id": model_id,
            "model_name": model_name,
            "league_id": league_id,
            "league_name": league_name
        })
    return rows


if __name__ == "__main__":
    unittest.main()
