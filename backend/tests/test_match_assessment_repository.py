"""Unit tests for match assessment repository mapping helpers."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from backend.services.match_service import _map_match_assessments


class TestMatchAssessmentMapping(unittest.TestCase):
    """Mapper tests used when SQL repository mocks are not wired."""

    def test_map_match_assessments_returns_empty_for_empty_frame(self) -> None:
        self.assertEqual(_map_match_assessments(pd.DataFrame()), [])

    def test_map_match_assessments_parses_json_snapshot(self) -> None:
        frame = pd.DataFrame([{
            "model_id": 6,
            "model_name": "FOOTBALL_PLAYED_BETTER_V1",
            "model_version": "1.0.0",
            "assessment_type": "PLAYED_BETTER",
            "home_played_better_probability": 0.4,
            "draw_probability": 0.3,
            "away_played_better_probability": 0.3,
            "final_assessment": "HOME_PLAYED_BETTER",
            "confidence": 0.1,
            "dominance_score": None,
            "feature_snapshot": {"xg_diff": 0.5, "shots_diff": 2},
            "updated_at": datetime(2025, 3, 16, 12, 0),
        }])
        mapped = _map_match_assessments(frame)
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["model_name"], "FOOTBALL_PLAYED_BETTER_V1")
        self.assertEqual(mapped[0]["feature_snapshot"]["shots_diff"], 2.0)
        self.assertIsNone(mapped[0]["dominance_score"])

    def test_map_match_assessments_skips_invalid_final_assessment(
        self) -> None:
        frame = pd.DataFrame([
            {
                "model_id": 6,
                "model_name": "FOOTBALL_PLAYED_BETTER_V1",
                "model_version": "1.0.0",
                "assessment_type": "PLAYED_BETTER",
                "home_played_better_probability": 0.4,
                "draw_probability": 0.3,
                "away_played_better_probability": 0.3,
                "final_assessment": "HOME_PLAYED_BETTER",
                "confidence": 0.1,
                "dominance_score": None,
                "feature_snapshot": {"xg_diff": 0.5},
                "updated_at": datetime(2025, 3, 16, 12, 0)
            },
            {
                "model_id": 7,
                "model_name": "FOOTBALL_PLAYED_BETTER_NOXG_V1",
                "model_version": "1.0.0",
                "assessment_type": "PLAYED_BETTER",
                "home_played_better_probability": 0.2,
                "draw_probability": 0.3,
                "away_played_better_probability": 0.5,
                "final_assessment": "NOT_A_VALID_LABEL",
                "confidence": 0.2,
                "dominance_score": None,
                "feature_snapshot": None,
                "updated_at": datetime(2025, 3, 16, 13, 0)
            }
        ])
        mapped = _map_match_assessments(frame)
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["model_id"], 6)

    def test_map_match_assessments_skips_malformed_probability_row(
        self) -> None:
        frame = pd.DataFrame([{
            "model_id": 6,
            "model_name": "FOOTBALL_PLAYED_BETTER_V1",
            "model_version": "1.0.0",
            "assessment_type": "PLAYED_BETTER",
            "home_played_better_probability": "not-a-float",
            "draw_probability": 0.3,
            "away_played_better_probability": 0.3,
            "final_assessment": "HOME_PLAYED_BETTER",
            "confidence": 0.1,
            "dominance_score": None,
            "feature_snapshot": None,
            "updated_at": datetime(2025, 3, 16, 12, 0)
        }])
        self.assertEqual(_map_match_assessments(frame), [])


class TestFetchMatchAssessments(unittest.TestCase):
    """SQL fetch smoke test with mocked DB connection."""

    @patch("backend.repositories.match_assessment_repository.pd.read_sql")
    @patch(
        "backend.repositories.match_assessment_repository.get_db_connection")
    def test_fetch_match_assessments_queries_by_match_id(
        self,
        mock_get_conn: MagicMock,
        mock_read_sql: MagicMock) -> None:
        from backend.repositories import match_assessment_repository

        mock_conn = MagicMock()
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        mock_get_conn.return_value = mock_cm
        mock_read_sql.return_value = pd.DataFrame()

        frame = match_assessment_repository.fetch_match_assessments(101)
        self.assertTrue(frame.empty)
        args = mock_read_sql.call_args
        self.assertIn("match_model_assessments", args.args[0])
        self.assertEqual(args.kwargs["params"], (101,))


if __name__ == "__main__":
    unittest.main()
