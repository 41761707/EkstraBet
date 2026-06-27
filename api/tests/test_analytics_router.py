"""API tests for analytics endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
from api.main import create_app


class TestAnalyticsRouter(unittest.TestCase):
    """HTTP contract tests for analytics endpoints."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_get_models_rejects_invalid_date_range(self) -> None:
        response = self.client.get(
            "/analytics/models",
            params={
                "date_from": "2026-06-10",
                "date_to": "2026-06-01",
            })
        self.assertEqual(response.status_code, 422)

    def test_get_models_requires_season_for_group_by(self) -> None:
        response = self.client.get(
            "/analytics/models",
            params={"group_by": "league"})
        self.assertEqual(response.status_code, 422)

    def test_get_models_requires_single_league_for_team_group(self) -> None:
        response = self.client.get(
            "/analytics/models",
            params={
                "group_by": "team",
                "season_id": 11,
                "league_ids": "1,2",
            })
        self.assertEqual(response.status_code, 422)

    @patch("api.routers.analytics.analytics_service.get_model_statistics")
    def test_get_models_returns_payload(
        self,
        mock_get_statistics: unittest.mock.MagicMock) -> None:
        mock_get_statistics.return_value = {
            "categories": {
                "ou": {
                    "predictions": {
                        "total": 4,
                        "correct": 3,
                        "accuracy_pct": 75.0,
                        "profit_total": None,
                        "by_type": [{
                            "key": "under_2_5",
                            "total": 2,
                            "correct": 2,
                            "accuracy_pct": 100.0,
                            "share_pct": 50.0,
                            "profit": None,
                        }],
                        "charts": {
                            "distribution": {
                                "labels": ["Under 2.5"],
                                "values": [2],
                                "percentages": [50.0],
                            },
                            "comparison": {
                                "labels": ["Under 2.5"],
                                "correct": [2],
                                "incorrect": [0],
                            },
                        },
                    },
                    "bets": {
                        "total": 2,
                        "correct": 1,
                        "accuracy_pct": 50.0,
                        "profit_total": 0.5,
                        "by_type": [{
                            "key": "under_2_5",
                            "total": 2,
                            "correct": 1,
                            "accuracy_pct": 50.0,
                            "share_pct": 100.0,
                            "profit": 0.5,
                        }],
                        "charts": {
                            "distribution": {
                                "labels": ["Under 2.5"],
                                "values": [2],
                                "percentages": [100.0],
                            },
                            "comparison": {
                                "labels": ["Under 2.5"],
                                "correct": [1],
                                "incorrect": [1],
                            },
                        },
                    },
                },
            },
            "aggregations": {},
            "league_characteristics": None,
            "filters_applied": {
                "stat_type": "ou",
                "model_ou_ids": [2],
                "season_id": 11,
            },
        }
        response = self.client.get(
            "/analytics/models",
            params={
                "stat_type": "ou",
                "model_ou_ids": "2",
                "season_id": "11",
            })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("ou", payload["categories"])
        self.assertEqual(payload["categories"]["ou"]["predictions"]["total"], 4)


if __name__ == "__main__":
    unittest.main()
