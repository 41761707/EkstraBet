"""Unit tests for basketball match lineup mapping."""

from __future__ import annotations

import unittest
from typing import Any

import pandas as pd

from api.schemas.match import BasketballMatchLineups
from backend.sports.basketball.lineups import map_basketball_lineups


HOME_TEAM_ID = 917
AWAY_TEAM_ID = 923
HOME_TEAM_NAME = "New Orleans Pelicans"
AWAY_TEAM_NAME = "Portland Trail Blazers"
FOREIGN_TEAM_ID = 999


def _player_row(
    *,
    player_id: int,
    player_name: str,
    team_id: int,
    team_name: str,
    number: object,
    starter: object) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "team_name": team_name,
        "number": number,
        "starter": starter
    }


def _map_lineups(frame: pd.DataFrame) -> dict[str, Any] | None:
    return map_basketball_lineups(
        frame,
        HOME_TEAM_ID,
        HOME_TEAM_NAME,
        AWAY_TEAM_ID,
        AWAY_TEAM_NAME)


class TestMapBasketballLineups(unittest.TestCase):
    """Tests for grouping basketball roster rows into home/away lineups."""

    def test_map_basketball_lineups_splits_home_away_and_starters(
        self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=1,
                player_name="Fears J.",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=0,
                starter=1),
            _player_row(
                player_id=2,
                player_name="Poole J.",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=13,
                starter=0),
            _player_row(
                player_id=3,
                player_name="Avdija D.",
                team_id=AWAY_TEAM_ID,
                team_name=AWAY_TEAM_NAME,
                number=8,
                starter=1)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        BasketballMatchLineups.model_validate(payload)

        home_players = payload["home"]["players"]
        away_players = payload["away"]["players"]
        self.assertEqual(payload["home"]["team_id"], HOME_TEAM_ID)
        self.assertEqual(payload["home"]["team_name"], HOME_TEAM_NAME)
        self.assertEqual(payload["away"]["team_id"], AWAY_TEAM_ID)
        self.assertEqual(len(home_players), 2)
        self.assertEqual(home_players[0]["player_name"], "Fears J.")
        self.assertTrue(home_players[0]["starter"])
        self.assertEqual(home_players[0]["number"], 0)
        self.assertEqual(home_players[1]["player_name"], "Poole J.")
        self.assertFalse(home_players[1]["starter"])
        self.assertEqual(len(away_players), 1)
        self.assertEqual(away_players[0]["player_name"], "Avdija D.")
        self.assertTrue(away_players[0]["starter"])

    def test_map_basketball_lineups_returns_none_for_empty_frame(
        self) -> None:
        self.assertIsNone(_map_lineups(pd.DataFrame()))

    def test_map_basketball_lineups_keeps_zero_and_maps_missing_number(
        self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=1,
                player_name="Fears J.",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=0,
                starter=1),
            _player_row(
                player_id=2,
                player_name="Unknown A.",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=-1,
                starter=0),
            _player_row(
                player_id=3,
                player_name="Unknown B.",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=float("nan"),
                starter=0)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        numbers = [player["number"] for player in payload["home"]["players"]]
        self.assertEqual(numbers, [0, None, None])

    def test_map_basketball_lineups_skips_foreign_team_and_keeps_empty_side(
        self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=1,
                player_name="Fears J.",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=0,
                starter=1),
            _player_row(
                player_id=99,
                player_name="Visitor X.",
                team_id=FOREIGN_TEAM_ID,
                team_name="Other",
                number=7,
                starter=1)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        self.assertEqual(len(payload["home"]["players"]), 1)
        self.assertEqual(payload["away"]["players"], [])
        self.assertEqual(payload["away"]["team_id"], AWAY_TEAM_ID)
        self.assertEqual(payload["away"]["team_name"], AWAY_TEAM_NAME)

    def test_map_basketball_lineups_maps_starter_flag(self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=1,
                player_name="Starter",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=1,
                starter=1),
            _player_row(
                player_id=2,
                player_name="Bench",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=2,
                starter=0),
            _player_row(
                player_id=3,
                player_name="Unknown",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=3,
                starter=-1),
            _player_row(
                player_id=4,
                player_name="Missing",
                team_id=HOME_TEAM_ID,
                team_name=HOME_TEAM_NAME,
                number=4,
                starter=None)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        starters = [
            player["starter"] for player in payload["home"]["players"]]
        self.assertEqual(starters, [True, False, False, False])


if __name__ == "__main__":
    unittest.main()
