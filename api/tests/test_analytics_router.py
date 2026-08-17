"""API tests for analytics endpoints."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")
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
                                "labels": ["Poniżej 2.5"],
                                "values": [2],
                                "percentages": [50.0],
                            },
                            "comparison": {
                                "labels": ["Poniżej 2.5"],
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
                                "labels": ["Poniżej 2.5"],
                                "values": [2],
                                "percentages": [100.0],
                            },
                            "comparison": {
                                "labels": ["Poniżej 2.5"],
                                "correct": [1],
                                "incorrect": [1],
                            },
                        },
                    },
                },
            },
            "aggregations": {},
            "league_comparisons": None,
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
        self.assertIsNone(payload["model_league_comparisons"])

    @patch("api.routers.analytics.analytics_service.get_model_statistics")
    def test_get_models_returns_model_league_comparisons(
        self,
        mock_get_statistics: unittest.mock.MagicMock) -> None:
        mock_get_statistics.return_value = {
            "categories": {},
            "aggregations": {},
            "league_comparisons": None,
            "model_league_comparisons": {
                "predictions": {
                    "ou": [{
                        "model_id": 2,
                        "model_name": "Alpha",
                        "leagues": [
                            {
                                "league_id": 1,
                                "league_name": "Ekstraklasa",
                                "total": 10,
                                "correct": 4,
                                "accuracy_pct": 40.0,
                            },
                            {
                                "league_id": 2,
                                "league_name": "Premier League",
                                "total": 20,
                                "correct": 12,
                                "accuracy_pct": 60.0,
                            },
                        ],
                        "average_accuracy_pct": 53.33,
                    }],
                    "btts": [],
                    "result": [],
                },
                "bet_profits": {
                    "ou": [{
                        "model_id": 2,
                        "model_name": "Alpha",
                        "leagues": [
                            {
                                "league_id": 1,
                                "league_name": "Ekstraklasa",
                                "total_bets": 4,
                                "profit": 1.2,
                            },
                            {
                                "league_id": 2,
                                "league_name": "Premier League",
                                "total_bets": 6,
                                "profit": -0.5,
                            },
                        ],
                        "total_profit": 0.7,
                    }],
                    "btts": [],
                    "result": [],
                },
            },
            "filters_applied": {
                "stat_type": "ou",
                "model_ou_ids": [2, 5],
                "league_ids": [1, 2],
                "season_id": 11,
                "settled_only": True,
                "positive_ev_only": True,
                "apply_tax": True,
            },
        }
        response = self.client.get(
            "/analytics/models",
            params={
                "stat_type": "ou",
                "model_ou_ids": "2,5",
                "league_ids": "1,2",
                "season_id": "11",
                "settled_only": "true",
                "positive_ev_only": "true",
                "apply_tax": "true",
            })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        comparisons = payload["model_league_comparisons"]
        self.assertEqual(len(comparisons["predictions"]["ou"]), 1)
        self.assertEqual(
            comparisons["predictions"]["ou"][0]["model_name"],
            "Alpha")
        self.assertEqual(
            comparisons["predictions"]["ou"][0]["average_accuracy_pct"],
            53.33)
        self.assertEqual(
            comparisons["bet_profits"]["ou"][0]["total_profit"],
            0.7)
        mock_get_statistics.assert_called_once()
        kwargs = mock_get_statistics.call_args.kwargs
        self.assertEqual(kwargs["model_ou_ids"], [2, 5])
        self.assertEqual(kwargs["league_ids"], [1, 2])
        self.assertEqual(kwargs["season_id"], 11)
        self.assertTrue(kwargs["settled_only"])
        self.assertTrue(kwargs["positive_ev_only"])
        self.assertTrue(kwargs["apply_tax"])

    @patch(
        "api.routers.analytics.analytics_service."
        "get_league_outcome_comparisons")
    def test_get_league_comparisons_returns_payload(
        self,
        mock_get_comparisons: unittest.mock.MagicMock) -> None:
        mock_get_comparisons.return_value = {
            "leagues": [{
                "league_id": 1,
                "league_name": "Ekstraklasa",
                "played_matches": 10,
                "btts_yes_pct": 50.0,
                "over_2_5_pct": 40.0,
                "home_win_pct": 45.0,
                "away_win_pct": 30.0
            }, {
                "league_id": 2,
                "league_name": "Premier League",
                "played_matches": 20,
                "btts_yes_pct": 55.0,
                "over_2_5_pct": 50.0,
                "home_win_pct": 40.0,
                "away_win_pct": 35.0
            }],
            "averages": {
                "btts_yes_pct": 53.33,
                "over_2_5_pct": 46.67,
                "home_win_pct": 41.67,
                "away_win_pct": 33.33
            }
        }
        response = self.client.get(
            "/analytics/league-comparisons",
            params={
                "league_ids": "1,2",
                "season_id": "11"
            })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["comparisons"]["leagues"]), 2)
        mock_get_comparisons.assert_called_once_with(
            league_ids=[1, 2],
            season_id=11)


if __name__ == "__main__":
    unittest.main()
