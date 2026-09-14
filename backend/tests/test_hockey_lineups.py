"""Unit tests for hockey match lineup mapping."""

from __future__ import annotations

import unittest

import pandas as pd

from api.schemas.match import HockeyMatchLineups
from backend.sports.hockey.lineups import HOCKEY_LINE_COUNT, map_hockey_lineups


HOME_TEAM_ID = 10
AWAY_TEAM_ID = 20
HOME_TEAM_NAME = "Columbus Blue Jackets"
AWAY_TEAM_NAME = "Philadelphia Flyers"


def _player_row(
    *,
    player_id: int,
    player_name: str,
    team_id: int,
    position: str = "C",
    number: object = 19,
    line: object = 1) -> dict[str, object]:
    """Build one roster row as returned by the repository query."""
    team_name = HOME_TEAM_NAME
    if team_id != HOME_TEAM_ID:
        team_name = AWAY_TEAM_NAME
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "team_name": team_name,
        "position": position,
        "number": number,
        "line": line
    }


def _map_lineups(frame: pd.DataFrame) -> dict[str, object] | None:
    """Map roster rows with the default home/away teams."""
    return map_hockey_lineups(
        frame,
        HOME_TEAM_ID,
        HOME_TEAM_NAME,
        AWAY_TEAM_ID,
        AWAY_TEAM_NAME)


class TestHockeyLineups(unittest.TestCase):
    """Tests for grouping hockey roster rows into match lineups."""

    def test_map_hockey_lineups_splits_home_away_and_has_four_lines(
        self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=101,
                player_name="Fantilli",
                team_id=HOME_TEAM_ID,
                position="C",
                number=19,
                line=1),
            _player_row(
                player_id=102,
                player_name="Marchment",
                team_id=HOME_TEAM_ID,
                position="LW",
                number=17,
                line=1),
            _player_row(
                player_id=201,
                player_name="Konecny",
                team_id=AWAY_TEAM_ID,
                position="RW",
                number=11,
                line=2)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        HockeyMatchLineups.model_validate(payload)

        home = payload["home"]
        away = payload["away"]
        self.assertEqual(home["team_id"], HOME_TEAM_ID)
        self.assertEqual(home["team_name"], HOME_TEAM_NAME)
        self.assertEqual(away["team_id"], AWAY_TEAM_ID)
        self.assertEqual(away["team_name"], AWAY_TEAM_NAME)

        self.assertEqual(len(home["lines"]), HOCKEY_LINE_COUNT)
        self.assertEqual(len(away["lines"]), HOCKEY_LINE_COUNT)
        self.assertEqual(
            [item["line"] for item in home["lines"]],
            [1, 2, 3, 4])
        self.assertEqual(
            [item["line"] for item in away["lines"]],
            [1, 2, 3, 4])

        home_line_1 = home["lines"][0]["players"]
        self.assertEqual(len(home_line_1), 2)
        self.assertEqual(home_line_1[0]["player_name"], "Fantilli")
        self.assertEqual(home_line_1[1]["player_name"], "Marchment")
        self.assertEqual(home["lines"][1]["players"], [])
        self.assertEqual(home["lines"][2]["players"], [])
        self.assertEqual(home["lines"][3]["players"], [])

        away_line_2 = away["lines"][1]["players"]
        self.assertEqual(len(away_line_2), 1)
        self.assertEqual(away_line_2[0]["player_name"], "Konecny")
        self.assertEqual(away["lines"][0]["players"], [])

    def test_map_hockey_lineups_returns_none_for_empty_frame(self) -> None:
        self.assertIsNone(_map_lineups(pd.DataFrame()))

    def test_map_hockey_lineups_keeps_partial_fourth_line(self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=301,
                player_name="Defender A",
                team_id=HOME_TEAM_ID,
                position="D",
                number=2,
                line=4),
            _player_row(
                player_id=302,
                player_name="Defender B",
                team_id=HOME_TEAM_ID,
                position="D",
                number=8,
                line=4),
            _player_row(
                player_id=303,
                player_name="Winger",
                team_id=HOME_TEAM_ID,
                position="RW",
                number=21,
                line=4)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        line_4_players = payload["home"]["lines"][3]["players"]
        self.assertEqual(len(line_4_players), 3)
        self.assertEqual(
            [player["player_name"] for player in line_4_players],
            ["Defender A", "Defender B", "Winger"])
        self.assertEqual(payload["home"]["lines"][0]["players"], [])
        self.assertEqual(payload["away"]["lines"][3]["players"], [])

    def test_map_hockey_lineups_skips_invalid_line_and_foreign_team(
        self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=101,
                player_name="Fantilli",
                team_id=HOME_TEAM_ID,
                position="C",
                number=19,
                line=1),
            _player_row(
                player_id=401,
                player_name="Skipped Line",
                team_id=HOME_TEAM_ID,
                position="C",
                number=99,
                line=5),
            _player_row(
                player_id=402,
                player_name="Foreign Team",
                team_id=999,
                position="LW",
                number=13,
                line=1)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        home_players = [
            player
            for line in payload["home"]["lines"]
            for player in line["players"]
        ]
        away_players = [
            player
            for line in payload["away"]["lines"]
            for player in line["players"]
        ]
        self.assertEqual(len(home_players), 1)
        self.assertEqual(home_players[0]["player_name"], "Fantilli")
        self.assertEqual(away_players, [])

    def test_map_hockey_lineups_maps_nan_number_to_none(self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=101,
                player_name="Fantilli",
                team_id=HOME_TEAM_ID,
                position="C",
                number=float("nan"),
                line=1)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        HockeyMatchLineups.model_validate(payload)
        player = payload["home"]["lines"][0]["players"][0]
        self.assertIsNone(player["number"])
        self.assertEqual(player["player_id"], 101)
        self.assertEqual(player["position"], "C")
        self.assertEqual(player["line"], 1)

    def test_map_hockey_lineups_skips_nan_line_and_maps_missing_position(
        self) -> None:
        frame = pd.DataFrame([
            _player_row(
                player_id=401,
                player_name="No Line",
                team_id=HOME_TEAM_ID,
                position="C",
                number=99,
                line=float("nan")),
            _player_row(
                player_id=102,
                player_name="No Position",
                team_id=HOME_TEAM_ID,
                position=float("nan"),
                number=17,
                line=1)
        ])

        payload = _map_lineups(frame)
        assert payload is not None
        home_players = [
            player
            for line in payload["home"]["lines"]
            for player in line["players"]
        ]
        self.assertEqual(len(home_players), 1)
        self.assertEqual(home_players[0]["player_name"], "No Position")
        self.assertEqual(home_players[0]["position"], "")


if __name__ == "__main__":
    unittest.main()
