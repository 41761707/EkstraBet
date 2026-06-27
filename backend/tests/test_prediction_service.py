"""Unit tests for prediction service helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.services.prediction_service import (
    get_match_predictions,
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
                "value": 0.55,
            }]),
            1)
        payload = search_predictions(match_id=100)
        self.assertEqual(payload["total_count"], 1)
        prediction = payload["predictions"][0]
        self.assertEqual(prediction["event_family"]["name"], "REZULTAT")
        self.assertEqual(prediction["model_name"], "Model A")

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
            "value": 0.55,
            "outcome": 1,
        }])
        payload = get_match_predictions(100)
        assert payload is not None
        prediction = payload["match_predictions"][0]
        self.assertEqual(prediction["prediction_id"], 10)
        self.assertEqual(prediction["value"], 0.55)
        self.assertEqual(prediction["outcome"], 1)


if __name__ == "__main__":
    unittest.main()
