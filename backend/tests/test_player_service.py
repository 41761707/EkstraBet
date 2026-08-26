"""Unit tests for player service mappings."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from api.schemas.player import (
    FootballPlayerMatchStat,
    HockeyPlayerMatchStat)
from backend.services import player_service


def _hockey_skater_row(
    match_id: int,
    home_team: str,
    away_team: str,
    opponent_shortcut: str,
    opponent_name: str) -> dict[str, object]:
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "match_date": "02.01",
        "opponent_shortcut": opponent_shortcut,
        "opponent_name": opponent_name,
        "toi": "20:30",
        "points": 2,
        "goals": 1,
        "assists": 1,
        "plus_minus": 1,
        "penalty_minutes": 2,
        "sog": 4
    }


def _football_stat_row(
    match_id: int,
    home_team: str,
    away_team: str,
    opponent_shortcut: str,
    opponent_name: str) -> dict[str, object]:
    return {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "match_date": "02.01",
        "opponent_shortcut": opponent_shortcut,
        "opponent_name": opponent_name,
        "goals": 1,
        "assists": 0,
        "shots": 3,
        "shots_on_target": 2,
        "fouls_conceded": 1,
        "yellow_cards": 0
    }


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
        mock_fetch_stats.return_value = pd.DataFrame([
            _hockey_skater_row(
                100,
                "Edmonton Oilers",
                "Calgary Flames",
                "CGY",
                "Calgary Flames")
        ])

        payload = player_service.get_hockey_player_match_stats(
            player_id=408,
            season_id=12,
            limit=10)

        assert payload is not None
        self.assertEqual(payload["summary"]["penalty_minutes"], 2)
        self.assertEqual(payload["summary"]["average_penalty_minutes"], 2.0)
        self.assertEqual(payload["matches"][0]["penalty_minutes"], 2)

    @patch(
        "backend.services.player_service.player_repository"
        ".fetch_player_position",
        return_value="C")
    @patch(
        "backend.services.player_service.player_repository"
        ".fetch_hockey_player_match_stats")
    def test_hockey_player_stats_include_opponent_name_home_and_away(
        self,
        mock_fetch_stats: unittest.mock.MagicMock,
        _mock_position: unittest.mock.MagicMock) -> None:
        """Map opponent_name for home and away hockey appearances."""
        mock_fetch_stats.return_value = pd.DataFrame([
            _hockey_skater_row(
                100,
                "Edmonton Oilers",
                "Calgary Flames",
                "CGY",
                "Calgary Flames"),
            _hockey_skater_row(
                101,
                "Toronto Maple Leafs",
                "Edmonton Oilers",
                "TOR",
                "Toronto Maple Leafs")
        ])

        payload = player_service.get_hockey_player_match_stats(
            player_id=408,
            season_id=12,
            limit=10)

        assert payload is not None
        home_game = payload["matches"][0]
        away_game = payload["matches"][1]
        self.assertEqual(home_game["opponent_shortcut"], "CGY")
        self.assertEqual(home_game["opponent_name"], "Calgary Flames")
        self.assertEqual(away_game["opponent_shortcut"], "TOR")
        self.assertEqual(away_game["opponent_name"], "Toronto Maple Leafs")
        HockeyPlayerMatchStat.model_validate(home_game)
        HockeyPlayerMatchStat.model_validate(away_game)

    @patch(
        "backend.services.player_service.player_repository"
        ".fetch_football_player_match_stats")
    def test_football_player_stats_include_opponent_name_home_and_away(
        self,
        mock_fetch_stats: unittest.mock.MagicMock) -> None:
        """Map opponent_name for home and away football appearances."""
        mock_fetch_stats.return_value = pd.DataFrame([
            _football_stat_row(
                200,
                "Legia Warszawa",
                "Lech Poznań",
                "LPO",
                "Lech Poznań"),
            _football_stat_row(
                201,
                "Cracovia",
                "Legia Warszawa",
                "CRA",
                "Cracovia")
        ])

        payload = player_service.get_football_player_match_stats(
            player_id=15,
            season_id=8,
            limit=10)

        assert payload is not None
        home_game = payload["matches"][0]
        away_game = payload["matches"][1]
        self.assertEqual(home_game["opponent_shortcut"], "LPO")
        self.assertEqual(home_game["opponent_name"], "Lech Poznań")
        self.assertEqual(away_game["opponent_shortcut"], "CRA")
        self.assertEqual(away_game["opponent_name"], "Cracovia")
        FootballPlayerMatchStat.model_validate(home_game)
        FootballPlayerMatchStat.model_validate(away_game)


if __name__ == "__main__":
    unittest.main()
