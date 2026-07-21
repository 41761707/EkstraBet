"""HTTP contract tests for prediction preview."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app
from backend.services.prediction_preview_service import (
    PredictionPreviewHistoryError)


PREVIEW_PAYLOAD = {
    "result": {"p_home": 0.5, "p_draw": 0.3, "p_away": 0.2},
    "btts": {"p_yes": 0.6, "p_no": 0.4},
    "goals": {
        "lambda_home": 1.7,
        "lambda_away": 1.1,
        "total_buckets": {"0": 0.05, "1": 0.15, "2": 0.25, "3": 0.2},
        "over_25": 0.55,
        "under_25": 0.45,
        "top_exact_scores": [
            {"score": "1:1", "probability": 0.12}
        ]
    }
}


class TestPredictionsPreviewRouter(unittest.TestCase):
    """HTTP contract tests for POST /predictions/preview."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    @patch("api.routers.predictions.prediction_preview_service.preview_prediction")
    @patch("api.routers.predictions.get_settings")
    def test_valid_body_delegates_to_preview_service(
        self,
        mock_get_settings: unittest.mock.MagicMock,
        mock_preview: unittest.mock.MagicMock
    ) -> None:
        mock_get_settings.return_value = SimpleNamespace(
            ekstrabet_ml_preview=True)
        mock_preview.return_value = PREVIEW_PAYLOAD

        response = self.client.post(
            "/predictions/preview",
            json={
                "home_team_id": 15,
                "away_team_id": 22,
                "league_id": 3,
                "as_of_date": "2026-07-21"
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), PREVIEW_PAYLOAD)
        mock_preview.assert_called_once()
        call = mock_preview.call_args.kwargs
        self.assertEqual(call["home_team_id"], 15)
        self.assertEqual(call["away_team_id"], 22)
        self.assertEqual(call["league_id"], 3)
        self.assertEqual(call["as_of_date"].isoformat(), "2026-07-21")

    @patch("api.routers.predictions.prediction_preview_service.preview_prediction")
    @patch("api.routers.predictions.get_settings")
    def test_disabled_preview_returns_503_without_loading_predictor(
        self,
        mock_get_settings: unittest.mock.MagicMock,
        mock_preview: unittest.mock.MagicMock
    ) -> None:
        mock_get_settings.return_value = SimpleNamespace(
            ekstrabet_ml_preview=False)

        response = self.client.post(
            "/predictions/preview",
            json={"home_team_id": 15, "away_team_id": 22})

        self.assertEqual(response.status_code, 503)
        self.assertIn("EKSTRABET_ML_PREVIEW=1", response.json()["detail"])
        mock_preview.assert_not_called()

    @patch("api.routers.predictions.prediction_preview_service.preview_prediction")
    def test_invalid_body_returns_422_without_delegation(
        self,
        mock_preview: unittest.mock.MagicMock
    ) -> None:
        response = self.client.post(
            "/predictions/preview",
            json={"home_team_id": 15, "away_team_id": 15})

        self.assertEqual(response.status_code, 422)
        mock_preview.assert_not_called()

    @patch("api.routers.predictions.prediction_preview_service.preview_prediction")
    @patch("api.routers.predictions.get_settings")
    def test_insufficient_history_returns_409(
        self,
        mock_get_settings: unittest.mock.MagicMock,
        mock_preview: unittest.mock.MagicMock
    ) -> None:
        mock_get_settings.return_value = SimpleNamespace(
            ekstrabet_ml_preview=True)
        mock_preview.side_effect = PredictionPreviewHistoryError(
            "Insufficient match history for one or both teams")

        response = self.client.post(
            "/predictions/preview",
            json={"home_team_id": 15, "away_team_id": 22})

        self.assertEqual(response.status_code, 409)
        self.assertIn("Insufficient match history", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
