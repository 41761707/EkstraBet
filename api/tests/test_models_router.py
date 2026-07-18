"""API tests for model metadata endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app


class TestModelsRouter(unittest.TestCase):
    """HTTP contract tests for model metadata endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_model_metadata_info_mentions_ml_separation(self) -> None:
        response = self.client.get("/models/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("models/ directory", payload["description"])

    @patch(
        "api.routers.models.model_metadata_service.get_model_details",
        return_value=None)
    def test_get_model_details_returns_404_for_missing_model(
        self,
        _mock_get_details: unittest.mock.MagicMock) -> None:
        response = self.client.get("/models/models/999999/details")
        self.assertEqual(response.status_code, 404)

    @patch("api.routers.models.model_metadata_service.get_models")
    def test_get_models_returns_list(
        self,
        mock_get_models: unittest.mock.MagicMock) -> None:
        mock_get_models.return_value = [{
            "id": 3,
            "name": "Model A",
            "active": 1,
            "sport_id": 1,
            "sport_name": "Football",
        }]
        response = self.client.get("/models/models")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_models"], 1)


if __name__ == "__main__":
    unittest.main()
