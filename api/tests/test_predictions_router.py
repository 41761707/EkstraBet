"""API tests for prediction endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

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

    @patch(
        "api.routers.predictions.hockey_player_event_service"
        ".get_hockey_player_event_rankings")
    def test_hockey_player_events_passes_limit(
        self,
        mock_rankings: unittest.mock.MagicMock) -> None:
        mock_rankings.return_value = _hockey_rankings_payload()
        response = self.client.get(
            "/predictions/hockey/player-events?limit=10")
        self.assertEqual(response.status_code, 200)
        mock_rankings.assert_called_once_with(10)
        metrics = [
            item["metric"]
            for item in response.json()["rankings"]]
        self.assertEqual(metrics, ["point", "goal", "assist", "shot"])

    @patch(
        "api.routers.predictions.hockey_player_event_service"
        ".get_hockey_player_event_rankings")
    def test_hockey_player_events_without_limit(
        self,
        mock_rankings: unittest.mock.MagicMock) -> None:
        mock_rankings.return_value = _hockey_rankings_payload()
        response = self.client.get("/predictions/hockey/player-events")
        self.assertEqual(response.status_code, 200)
        mock_rankings.assert_called_once_with(None)

    def test_hockey_player_events_rejects_limit_outside_range(self) -> None:
        low = self.client.get("/predictions/hockey/player-events?limit=0")
        high = self.client.get("/predictions/hockey/player-events?limit=51")
        self.assertEqual(low.status_code, 422)
        self.assertEqual(high.status_code, 422)


def _hockey_rankings_payload() -> dict:
    """Four empty boards that still satisfy the response model."""
    specs = (
        ("point", "Punkt", "P(punkt)"),
        ("goal", "Gol", "P(gol)"),
        ("assist", "Asysta", "P(asysta)"),
        ("shot", "Strzał", "P(SOG > 2.5)"))
    return {
        "match_count": 0,
        "rankings": [
            {
                "metric": metric,
                "label": label,
                "hint": hint,
                "rows": []}
            for metric, label, hint in specs]}


if __name__ == "__main__":
    unittest.main()
