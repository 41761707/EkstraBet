"""Unit tests for hockey match play-by-play mapping."""

from __future__ import annotations

import unittest

import pandas as pd

from backend.sports.hockey.events import map_hockey_match_events


HOME_TEAM_ID = 10
AWAY_TEAM_ID = 20


def _event_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": 1,
        "team_id": HOME_TEAM_ID,
        "team_name": "Tampa Bay Lightning",
        "player_id": 100,
        "player_name": "Kucherov N.",
        "event_id": 181,
        "event_name": "Strzelec bramki",
        "period": 1,
        "event_time": "05:12",
        "description": "Point B. + Hedman V.",
        "pp_flag": 0,
        "en_flag": 0
    }
    row.update(overrides)
    return row


class TestHockeyMatchEvents(unittest.TestCase):
    """Tests for hockey play-by-play event mapping."""

    def test_map_hockey_match_events_returns_none_for_empty_frame(
            self) -> None:
        self.assertIsNone(
            map_hockey_match_events(pd.DataFrame(), HOME_TEAM_ID))

    def test_map_hockey_match_events_sets_home_and_away_sides(self) -> None:
        frame = pd.DataFrame([
            _event_row(),
            _event_row(
                id=2,
                team_id=AWAY_TEAM_ID,
                team_name="Winnipeg Jets",
                player_id=200,
                player_name="Scheifele M.",
                event_id=183,
                event_name="Kara mniejsza",
                period=2,
                event_time="01:04",
                description="Zahaczanie")
        ])

        payload = map_hockey_match_events(frame, HOME_TEAM_ID)

        assert payload is not None
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["side"], "home")
        self.assertEqual(payload[0]["player_name"], "Kucherov N.")
        self.assertEqual(payload[1]["side"], "away")
        self.assertEqual(payload[1]["event_name"], "Kara mniejsza")

    def test_map_hockey_match_events_maps_power_play_and_empty_net(
            self) -> None:
        frame = pd.DataFrame([
            _event_row(pp_flag=1, en_flag=0),
            _event_row(
                id=2,
                pp_flag=0,
                en_flag=1,
                description="Do pustej bramki")
        ])

        payload = map_hockey_match_events(frame, HOME_TEAM_ID)

        assert payload is not None
        self.assertTrue(payload[0]["is_power_play"])
        self.assertFalse(payload[0]["is_empty_net"])
        self.assertFalse(payload[1]["is_power_play"])
        self.assertTrue(payload[1]["is_empty_net"])

    def test_map_hockey_match_events_skips_invalid_period_and_missing_team(
            self) -> None:
        frame = pd.DataFrame([
            _event_row(id=1, period=6),
            _event_row(id=2, team_id=None),
            _event_row(id=3, period=4, event_time="02:11")
        ])

        payload = map_hockey_match_events(frame, HOME_TEAM_ID)

        assert payload is not None
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], 3)
        self.assertEqual(payload[0]["period"], 4)

    def test_map_hockey_match_events_maps_missing_description_to_none(
            self) -> None:
        frame = pd.DataFrame([_event_row(description=float("nan"))])

        payload = map_hockey_match_events(frame, HOME_TEAM_ID)

        assert payload is not None
        self.assertIsNone(payload[0]["description"])
        self.assertEqual(payload[0]["event_time"], "05:12")


if __name__ == "__main__":
    unittest.main()
