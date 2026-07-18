"""Unit tests for player service mappings."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.services import player_service


class TestPlayerService(unittest.TestCase):
    """Tests for player match log payloads."""

    @patch(
        "backend.services.player_service.player_repository"
        ".fetch_player_position",
        return_value="C")
    @patch(
        "backend.services.player_service.player_repository"
        ".fetch_hockey_player_match_stats")
    def test_hockey_player_stats_include_penalty_minutes(
        self,
        mock_fetch_stats: unittest.mock.MagicMock,
        _mock_position: unittest.mock.MagicMock) -> None:
        """Ensure skater penalty minutes are exposed in match and summary."""
        mock_fetch_stats.return_value = pd.DataFrame([{
            "match_id": 100,
            "home_team": "Edmonton Oilers",
            "away_team": "Calgary Flames",
            "match_date": "02.01",
            "opponent_shortcut": "CGY",
            "toi": "20:30",
            "points": 2,
            "goals": 1,
            "assists": 1,
            "plus_minus": 1,
            "penalty_minutes": 2,
            "sog": 4
        }])

        payload = player_service.get_hockey_player_match_stats(
            player_id=408,
            season_id=12,
            limit=10)

        assert payload is not None
        self.assertEqual(payload["summary"]["penalty_minutes"], 2)
        self.assertEqual(payload["summary"]["average_penalty_minutes"], 2.0)
        self.assertEqual(payload["matches"][0]["penalty_minutes"], 2)


if __name__ == "__main__":
    unittest.main()
