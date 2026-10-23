"""Unit tests for hockey rating rows and the fill entry points."""

from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from backend.services.hockey_game_rating_fill import fill_match
from backend.services.hockey_game_rating_fill import resolve_fill_target
from backend.sports.hockey.game_rating_rows import rows_from_rating


_FILL = "backend.services.hockey_game_rating_fill"


def _konecny_payload() -> dict:
    """Rating JSON from the design, with a decoy player team id."""
    return {
        "teams": [
            {
                "team_id": 10,
                "team_name": "Philadelphia Flyers",
                "players": [
                    {
                        "player_id": 1,
                        "player_name": "Konecny T.",
                        "team_id": 99,
                        "group": "forward",
                        "offense": 3.2,
                        "defense": -1.4,
                        "total": 1.8,
                        "parts": {
                            "production": 3.0,
                            "empty_net": 0.0,
                            "shots": 0.2,
                            "teammate_goals": 0.0,
                            "faceoffs": 0.0,
                            "goals_against": -1.4,
                            "penalties": 0.0,
                            "blocks": 0.0,
                            "goaltending": 0.0
                        }
                    }
                ]
            },
            {
                "team_id": 20,
                "team_name": "Ottawa Senators",
                "players": []
            }
        ]
    }


def _played_hockey_match() -> dict:
    """Sides of one finished hockey match."""
    return {
        "id": 44,
        "sport_id": 2,
        "result": "3:2",
        "home_team": 10,
        "away_team": 20,
        "home_team_name": "Philadelphia Flyers",
        "away_team_name": "Ottawa Senators"
    }


class TestRowsFromRating(unittest.TestCase):
    """Flattening the rating JSON into insert rows."""

    def test_three_point_json_becomes_one_row(self) -> None:
        rows = rows_from_rating(_konecny_payload())
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["team_id"], 10)
        self.assertEqual(row["player_id"], 1)
        self.assertEqual(row["player_group"], "forward")
        self.assertEqual(row["offense"], Decimal("3.2"))
        self.assertEqual(row["defense"], Decimal("-1.4"))
        self.assertEqual(row["total"], Decimal("1.8"))
        self.assertEqual(row["production"], Decimal("3.0"))
        self.assertEqual(row["shots"], Decimal("0.2"))
        self.assertEqual(row["goals_against"], Decimal("-1.4"))
        self.assertEqual(row["empty_net"], Decimal("0.0"))
        self.assertEqual(row["goaltending"], Decimal("0.0"))

    def test_empty_player_list_yields_no_rows(self) -> None:
        payload = {
            "teams": [
                {
                    "team_id": 10,
                    "team_name": "Philadelphia Flyers",
                    "players": []
                }
            ]
        }
        self.assertEqual(rows_from_rating(payload), [])

    def test_unknown_group_raises(self) -> None:
        payload = _konecny_payload()
        payload["teams"][0]["players"][0]["group"] = "wing"
        with self.assertRaises(ValueError):
            rows_from_rating(payload)

    def test_duplicate_player_id_raises(self) -> None:
        payload = _konecny_payload()
        payload["teams"][1]["players"].append(
            payload["teams"][0]["players"][0])
        with self.assertRaises(ValueError):
            rows_from_rating(payload)


class TestResolveFillTarget(unittest.TestCase):
    """The command accepts exactly one target."""

    def test_no_arguments_raise(self) -> None:
        with self.assertRaises(ValueError):
            resolve_fill_target(None, None)

    def test_both_arguments_raise(self) -> None:
        with self.assertRaises(ValueError):
            resolve_fill_target(44, 7)

    def test_one_argument_selects_that_target(self) -> None:
        self.assertEqual(resolve_fill_target(44, None), ("match", 44))
        self.assertEqual(resolve_fill_target(None, 7), ("season", 7))


class TestFillMatch(unittest.TestCase):
    """fill_match writes through the rating functions without a database."""

    @patch(f"{_FILL}.replace_match_ratings")
    @patch(f"{_FILL}.build_match_rating")
    @patch(f"{_FILL}.fetch_hockey_season_save_rate")
    @patch(f"{_FILL}.fetch_hockey_match_events")
    @patch(f"{_FILL}.fetch_hockey_game_rating_players")
    @patch(f"{_FILL}.fetch_hockey_rating_match")
    def test_played_match_replaces_one_row(
            self,
            fetch_match: unittest.mock.MagicMock,
            fetch_players: unittest.mock.MagicMock,
            fetch_events: unittest.mock.MagicMock,
            fetch_rate: unittest.mock.MagicMock,
            build: unittest.mock.MagicMock,
            replace: unittest.mock.MagicMock) -> None:
        fetch_match.return_value = _played_hockey_match()
        fetch_players.return_value = pd.DataFrame([{"player_id": 1}])
        fetch_events.return_value = pd.DataFrame()
        fetch_rate.return_value = 0.907
        build.return_value = _konecny_payload()
        replace.return_value = 1

        written = fill_match(44)

        self.assertEqual(written, 1)
        replace.assert_called_once()
        match_id, rows = replace.call_args.args
        self.assertEqual(match_id, 44)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["offense"], Decimal("3.2"))
        self.assertEqual(rows[0]["defense"], Decimal("-1.4"))
        self.assertEqual(rows[0]["total"], Decimal("1.8"))
        self.assertEqual(rows[0]["team_id"], 10)

    @patch(f"{_FILL}.replace_match_ratings")
    @patch(f"{_FILL}.build_match_rating")
    @patch(f"{_FILL}.fetch_hockey_season_save_rate")
    @patch(f"{_FILL}.fetch_hockey_match_events")
    @patch(f"{_FILL}.fetch_hockey_game_rating_players")
    @patch(f"{_FILL}.fetch_hockey_rating_match")
    def test_empty_player_frame_does_not_replace(
            self,
            fetch_match: unittest.mock.MagicMock,
            fetch_players: unittest.mock.MagicMock,
            _fetch_events: unittest.mock.MagicMock,
            _fetch_rate: unittest.mock.MagicMock,
            build: unittest.mock.MagicMock,
            replace: unittest.mock.MagicMock) -> None:
        fetch_match.return_value = _played_hockey_match()
        fetch_players.return_value = pd.DataFrame()

        with self.assertRaises(ValueError):
            fill_match(44)

        replace.assert_not_called()
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
