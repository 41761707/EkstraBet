"""API tests for prediction endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")

from api.main import create_app


class TestPredictionsRouter(unittest.TestCase):
    """HTTP contract tests for prediction endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    @patch(
        "api.routers.predictions.prediction_service.get_match_predictions",
        return_value=None)
    def test_get_match_predictions_returns_404_for_missing_match(
        self,
        _mock_get_predictions: unittest.mock.MagicMock) -> None:
        response = self.client.get("/predictions/match/999999")
        self.assertEqual(response.status_code, 404)

    @patch("api.routers.predictions.prediction_service.get_match_predictions")
    def test_get_match_predictions_returns_extended_payload(
        self,
        mock_get_predictions: unittest.mock.MagicMock) -> None:
        mock_get_predictions.return_value = {
            "match_predictions": [{
                "prediction_id": 10,
                "event_id": 5,
                "event_name": "1",
                "event_family": {"id": 2, "name": "REZULTAT"},
                "model_id": 3,
                "model_name": "Model A",
                "value": 0.55,
                "outcome": 1,
            }],
            "total_count": 1,
            "match_id": 100,
        }
        response = self.client.get("/predictions/match/100")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["match_predictions"][0]["event_family"]["name"],
                         "REZULTAT")

    def test_invalid_model_ids_format_returns_400(self) -> None:
        response = self.client.get("/predictions/match/100?model_ids=abc")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
