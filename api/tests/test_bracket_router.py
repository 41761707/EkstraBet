"""API tests for the league knockout bracket endpoint."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app


_GET_BRACKET = (
    "api.routers.leagues.knockout_bracket_service"
    ".get_league_bracket")


class TestBracketRouter(unittest.TestCase):
    """HTTP contract tests. The service is mocked, so no database."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    @patch(_GET_BRACKET)
    def test_bracket_requires_season_id(
            self,
            mock_get_bracket: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/47/bracket")
        self.assertEqual(response.status_code, 422)
        mock_get_bracket.assert_not_called()

    @patch(_GET_BRACKET, return_value=None)
    def test_bracket_returns_404_for_missing_league(
            self,
            mock_get_bracket: unittest.mock.MagicMock) -> None:
        response = self.client.get("/leagues/999999/bracket?season_id=12")
        self.assertEqual(response.status_code, 404)
        mock_get_bracket.assert_called_once_with(999999, 12)

    @patch(_GET_BRACKET)
    def test_bracket_returns_empty_list(
            self,
            mock_get_bracket: unittest.mock.MagicMock) -> None:
        mock_get_bracket.return_value = {
            "league_id": 42,
            "season_id": 13,
            "consumed_round_numbers": [],
            "brackets": []}
        response = self.client.get("/leagues/42/bracket?season_id=13")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["league_id"], 42)
        self.assertEqual(payload["season_id"], 13)
        self.assertEqual(payload["brackets"], [])
        self.assertEqual(payload["consumed_round_numbers"], [])
        mock_get_bracket.assert_called_once_with(42, 13)

    @patch(_GET_BRACKET)
    def test_bracket_returns_one_column(
            self,
            mock_get_bracket: unittest.mock.MagicMock) -> None:
        mock_get_bracket.return_value = _one_column_payload()
        response = self.client.get("/leagues/47/bracket?season_id=12")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["consumed_round_numbers"], [970])
        bracket = payload["brackets"][0]
        self.assertEqual(bracket["bracket_id"], "cup")
        self.assertEqual(bracket["title"], "Drabinka")
        self.assertIsNone(bracket["third_place"])
        self.assertEqual(len(bracket["columns"]), 1)
        column = bracket["columns"][0]
        self.assertEqual(column["depth"], 1)
        self.assertEqual(column["stage_label"], "Finał")
        tie = column["ties"][0]
        self.assertEqual(tie["tie_id"], "cup-1-1-2")
        self.assertEqual(tie["advanced_team_id"], 1)
        self.assertIsNone(tie["aggregate"])
        self.assertIsNone(tie["series_wins"])
        played = tie["matches"][0]
        self.assertEqual(played["home_goals"], 0)
        self.assertEqual(played["home_extra_time_goals"], 1)
        self.assertEqual(played["decided_by"], "extra_time")
        self.assertEqual(played["game_date"], "2026-07-19T21:00:00")
        mock_get_bracket.assert_called_once_with(47, 12)


def _one_column_payload() -> dict[str, object]:
    """Service dictionary with a single final column."""
    return {
        "league_id": 47,
        "season_id": 12,
        "consumed_round_numbers": [970],
        "brackets": [{
            "bracket_id": "cup",
            "title": "Drabinka",
            "columns": [{
                "depth": 1,
                "stage_label": "Finał",
                "ties": [_final_tie()]}],
            "third_place": None}]}


def _final_tie() -> dict[str, object]:
    """One played final. Extra time is kept beside 0:0."""
    return {
        "tie_id": "cup-1-1-2",
        "teams": [{
            "team_id": 1,
            "name": "Hiszpania",
            "shortcut": "ESP"}, {
            "team_id": 2,
            "name": "Anglia",
            "shortcut": "ENG"}],
        "is_bye": False,
        "pending_opponent_label": None,
        "seed_position": None,
        "advanced_team_id": 1,
        "on_champion_path": True,
        "feeder_tie_ids": [],
        "aggregate": None,
        "series_wins": None,
        "matches": [{
            "match_id": 10,
            "game_date": "2026-07-19T21:00:00",
            "home_team_id": 1,
            "away_team_id": 2,
            "home_goals": 0,
            "away_goals": 0,
            "home_extra_time_goals": 1,
            "away_extra_time_goals": 0,
            "home_penalty_goals": None,
            "away_penalty_goals": None,
            "is_played": True,
            "decided_by": "extra_time"}]}


if __name__ == "__main__":
    unittest.main()
