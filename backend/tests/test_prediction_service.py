"""Unit tests for prediction service helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.services.prediction_service import (
    get_hockey_score_charts,
    get_match_predictions,
    map_market_predictions_to_analysis,
    search_predictions)


class TestPredictionService(unittest.TestCase):
    """Tests for prediction service mapping."""

    @patch(
        "backend.services.prediction_service.prediction_repository"
        ".search_predictions")
    def test_search_predictions_maps_event_family(
        self,
        mock_search: unittest.mock.MagicMock) -> None:
        mock_search.return_value = (
            pd.DataFrame([{
                "id": 1,
                "match_id": 100,
                "event_id": 5,
                "event_name": "1",
                "event_family_id": 2,
                "event_family_name": "REZULTAT",
                "model_id": 3,
                "model_name": "Model A",
                "value": 55.0,
            }]),
            1)
        payload = search_predictions(match_id=100)
        self.assertEqual(payload["total_count"], 1)
        prediction = payload["predictions"][0]
        self.assertEqual(prediction["event_family"]["name"], "REZULTAT")
        self.assertEqual(prediction["model_name"], "Model A")
        self.assertAlmostEqual(prediction["value"], 0.55)

    @patch(
        "backend.services.prediction_service.match_repository.match_exists",
        return_value=False)
    def test_get_match_predictions_returns_none_for_missing_match(
        self,
        _mock_exists: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_match_predictions(999999))

    @patch(
        "backend.services.prediction_service.match_repository.match_exists",
        return_value=True)
    @patch(
        "backend.services.prediction_service.prediction_repository"
        ".fetch_match_final_predictions")
    def test_get_match_predictions_maps_extended_fields(
        self,
        mock_fetch: unittest.mock.MagicMock,
        _mock_exists: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = pd.DataFrame([{
            "prediction_id": 10,
            "event_id": 5,
            "event_name": "1",
            "event_family_id": 2,
            "event_family_name": "REZULTAT",
            "model_id": 3,
            "model_name": "Model A",
            "value": 55.0,
            "outcome": 1,
        }])
        payload = get_match_predictions(100)
        assert payload is not None
        prediction = payload["match_predictions"][0]
        self.assertEqual(prediction["prediction_id"], 10)
        self.assertAlmostEqual(prediction["value"], 0.55)
        self.assertEqual(prediction["outcome"], 1)

    def test_map_market_predictions_to_analysis_builds_preview_shape(
            self) -> None:
        frame = pd.DataFrame([
            {
                "prediction_id": 1,
                "event_id": 1,
                "event_name": "Zwycięstwo gospodarza",
                "model_id": 8,
                "model_name": "FOOTBALL_RESULT_V2",
                "value": 46.2109
            },
            {
                "prediction_id": 2,
                "event_id": 2,
                "event_name": "Remis",
                "model_id": 8,
                "model_name": "FOOTBALL_RESULT_V2",
                "value": 28.7455
            },
            {
                "prediction_id": 3,
                "event_id": 3,
                "event_name": "Zwycięstwo gościa",
                "model_id": 8,
                "model_name": "FOOTBALL_RESULT_V2",
                "value": 25.0436
            },
            {
                "prediction_id": 4,
                "event_id": 6,
                "event_name": "Obie drużyny strzelą",
                "model_id": 9,
                "model_name": "FOOTBALL_BTTS_V2",
                "value": 53.9821
            },
            {
                "prediction_id": 5,
                "event_id": 172,
                "event_name": "Obie drużyny nie strzelą",
                "model_id": 9,
                "model_name": "FOOTBALL_BTTS_V2",
                "value": 46.0179
            },
            {
                "prediction_id": 6,
                "event_id": 8,
                "event_name": "Powyżej 2.5 gola",
                "model_id": 10,
                "model_name": "FOOTBALL_GOALS_POISSON_V1",
                "value": 47.7496
            },
            {
                "prediction_id": 7,
                "event_id": 12,
                "event_name": "Poniżej 2.5 gola",
                "model_id": 10,
                "model_name": "FOOTBALL_GOALS_POISSON_V1",
                "value": 52.2504
            },
            {
                "prediction_id": 8,
                "event_id": 176,
                "event_name": "2 bramki w meczu",
                "model_id": 10,
                "model_name": "FOOTBALL_GOALS_POISSON_V1",
                "value": 25.1975
            },
            {
                "prediction_id": 9,
                "event_id": 205,
                "event_name": "1:1",
                "model_id": 10,
                "model_name": "FOOTBALL_GOALS_POISSON_V1",
                "value": 12.0297
            },
            {
                "prediction_id": 10,
                "event_id": 204,
                "event_name": "1:0",
                "model_id": 10,
                "model_name": "FOOTBALL_GOALS_POISSON_V1",
                "value": 11.8247
            },
            {
                "prediction_id": 11,
                "event_id": 224,
                "event_name": "4:2",
                "model_id": 10,
                "model_name": "FOOTBALL_GOALS_POISSON_V1",
                "value": 0.980033
            }
        ])
        analysis = map_market_predictions_to_analysis(frame)
        assert analysis is not None
        self.assertAlmostEqual(analysis["result"]["p_home"], 0.462109)
        self.assertAlmostEqual(analysis["btts"]["p_yes"], 0.539821)
        self.assertAlmostEqual(analysis["goals"]["under_25"], 0.522504)
        self.assertAlmostEqual(
            analysis["goals"]["total_buckets"]["2"],
            0.251975)
        self.assertEqual(analysis["goals"]["lambda_home"], 0.0)
        self.assertEqual(
            analysis["goals"]["top_exact_scores"][0]["score"],
            "1:1")
        self.assertAlmostEqual(
            analysis["goals"]["top_exact_scores"][0]["probability"],
            0.120297)
        # sub-1% w DB to procent, nie prawdopodobieństwo 0-1
        self.assertAlmostEqual(
            analysis["goals"]["top_exact_scores"][2]["probability"],
            0.00980033)

    def test_map_market_predictions_requires_full_result(self) -> None:
        frame = pd.DataFrame([{
            "prediction_id": 1,
            "event_id": 1,
            "event_name": "Zwycięstwo gospodarza",
            "model_id": 8,
            "model_name": "FOOTBALL_RESULT_V2",
            "value": 50.0
        }])
        self.assertIsNone(map_market_predictions_to_analysis(frame))

    @patch(
        "backend.services.prediction_service.prediction_repository"
        ".fetch_match_market_predictions")
    def test_get_hockey_score_charts_groups_one_model(
            self,
            mock_fetch: unittest.mock.MagicMock) -> None:
        rows = _hockey_bucket_rows(8, "HOCKEY_GOALS_GBM_V1", range(252, 258))
        rows.extend(_hockey_bucket_rows(
            8, "HOCKEY_GOALS_GBM_V1", range(264, 270)))
        rows.extend(_hockey_exact_rows(8))
        rows.extend(_hockey_bucket_rows(
            21, "HOCKEY_RATINGS_POISSON_V1", range(252, 258)))
        rows.extend(_hockey_bucket_rows(
            21, "HOCKEY_RATINGS_POISSON_V1", range(264, 269)))
        rows.extend(_hockey_exact_rows(21))
        rows.extend(_hockey_bucket_rows(30, "PARTIAL", range(252, 257)))
        mock_fetch.return_value = pd.DataFrame(rows)

        charts = get_hockey_score_charts(10)

        self.assertEqual([chart["model_id"] for chart in charts], [8, 21])
        first = charts[0]
        self.assertEqual(
            [bucket["label"] for bucket in first["home_goals"]],
            ["0", "1", "2", "3", "4", "5+"])
        self.assertEqual(
            [bucket["label"] for bucket in first["total_goals"]],
            ["≤3", "4", "5", "6", "7", "8+"])
        self.assertEqual(first["away_goals"], [])
        self.assertAlmostEqual(first["home_goals"][0]["probability"], 0.1)
        self.assertEqual(
            [item["score"] for item in first["exact_scores"]],
            ["3:2", "2:3", "4:3", "3:4", "1:2"])
        self.assertAlmostEqual(
            first["exact_scores"][0]["probability"], 0.3)
        self.assertEqual(charts[1]["total_goals"], [])
        self.assertEqual(len(charts[1]["home_goals"]), 6)
        mock_fetch.assert_called_once_with(10)


def _hockey_bucket_rows(
        model_id: int,
        model_name: str,
        event_ids: range) -> list[dict[str, object]]:
    return [
        {
            "prediction_id": event_id + model_id * 1000,
            "event_id": event_id,
            "event_name": "kubełek",
            "model_id": model_id,
            "model_name": model_name,
            "value": 10.0
        }
        for event_id in event_ids
    ]


def _hockey_exact_rows(model_id: int) -> list[dict[str, object]]:
    scores = (
        (280, "1:2 (OT/SO)", 8.0),
        (289, "2:3 (OT/SO)", 20.0),
        (296, "3:2 (OT/SO)", 30.0),
        (298, "3:4 (OT/SO)", 10.0),
        (305, "4:3 (OT/SO)", 15.0))
    return [
        {
            "prediction_id": event_id + model_id * 1000,
            "event_id": event_id,
            "event_name": name,
            "model_id": model_id,
            "model_name": "model",
            "value": value
        }
        for event_id, name, value in scores
    ]


if __name__ == "__main__":
    unittest.main()
