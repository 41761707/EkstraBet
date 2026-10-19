"""Unit tests for upcoming NHL skater event rankings."""

from __future__ import annotations

import math
import unittest
from datetime import datetime

import pandas as pd

from backend.sports.hockey.player_event_rankings import (
    build_hockey_player_event_rankings)


EARLY = datetime(2026, 10, 18, 1, 0)
LATER = datetime(2026, 10, 19, 1, 0)


class TestHockeyPlayerEventRankings(unittest.TestCase):
    """Sorting, dedupe and limit rules for the four boards."""

    def test_metric_order_and_empty_frame(self) -> None:
        payload = build_hockey_player_event_rankings(pd.DataFrame(), None)
        self.assertEqual(payload["match_count"], 0)
        self.assertEqual(
            [item["metric"] for item in payload["rankings"]],
            ["point", "goal", "assist", "shot"])
        for ranking in payload["rankings"]:
            self.assertEqual(ranking["rows"], [])

    def test_higher_probability_wins_and_name_breaks_ties(self) -> None:
        frame = pd.DataFrame([
            _line(1, "Zulu", 10, EARLY, 192, 0.5, 40.0),
            _line(2, "Adam", 10, EARLY, 192, 0.5, 40.0),
            _line(3, "Beata", 11, EARLY, 192, 0.5, 90.0)])
        rows = _rows(frame, "point")
        self.assertEqual(
            [row["player_name"] for row in rows],
            ["Beata", "Adam", "Zulu"])

    def test_player_on_two_matches_keeps_the_earlier_date(self) -> None:
        frame = pd.DataFrame([
            _line(5, "Nate", 21, LATER, 192, 0.5, 90.0),
            _line(5, "Nate", 20, EARLY, 192, 0.5, 10.0)])
        rows = _rows(frame, "point")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_id"], 20)
        self.assertEqual(rows[0]["probability"], 10.0)
        self.assertEqual(rows[0]["game_date"], EARLY)
        payload = build_hockey_player_event_rankings(frame, None)
        self.assertEqual(payload["match_count"], 1)

    def test_same_date_keeps_the_smaller_match_id(self) -> None:
        frame = pd.DataFrame([
            _line(5, "Nate", 30, EARLY, 192, 0.5, 99.0),
            _line(5, "Nate", 10, EARLY, 192, 0.5, 5.0)])
        rows = _rows(frame, "point")
        self.assertEqual(rows[0]["match_id"], 10)
        self.assertEqual(rows[0]["probability"], 5.0)

    def test_missing_shot_line_drops_only_the_shot_ranking(self) -> None:
        frame = pd.DataFrame([
            _line(8, "Only Skater", 10, EARLY, 192, 0.5, 55.0),
            _line(8, "Only Skater", 10, EARLY, 196, 0.5, 22.0),
            _line(8, "Only Skater", 10, EARLY, 194, 0.5, 33.0)])
        payload = build_hockey_player_event_rankings(frame, None)
        self.assertEqual(_names(payload, "point"), ["Only Skater"])
        self.assertEqual(_names(payload, "goal"), ["Only Skater"])
        self.assertEqual(_names(payload, "assist"), ["Only Skater"])
        self.assertEqual(_names(payload, "shot"), [])

    def test_limit_cuts_after_ranks_are_assigned(self) -> None:
        rows = [
            _line(
                index,
                f"Player {index:02d}",
                10,
                EARLY,
                192,
                0.5,
                float(index))
            for index in range(1, 12)]
        limited = build_hockey_player_event_rankings(pd.DataFrame(rows), 10)
        point_rows = _metric(limited, "point")["rows"]
        self.assertEqual(len(point_rows), 10)
        self.assertEqual(point_rows[0]["rank"], 1)
        self.assertEqual(point_rows[-1]["rank"], 10)
        self.assertNotIn(1.0, [row["probability"] for row in point_rows])
        full = build_hockey_player_event_rankings(pd.DataFrame(rows), None)
        full_rows = _metric(full, "point")["rows"]
        self.assertEqual(full_rows[-1]["rank"], 11)
        self.assertEqual(full_rows[-1]["probability"], 1.0)

    def test_invalid_probability_and_null_shortcut(self) -> None:
        frame = pd.DataFrame([
            _line(
                4,
                "Ghost",
                10,
                EARLY,
                192,
                0.5,
                140.0,
                team_shortcut=None),
            _line(
                4,
                "Ghost",
                10,
                EARLY,
                196,
                0.5,
                18.0,
                team_shortcut=None),
            _line(
                4,
                "Ghost",
                10,
                EARLY,
                190,
                2.5,
                math.nan,
                expected_value=3.5)])
        payload = build_hockey_player_event_rankings(frame, None)
        self.assertEqual(_names(payload, "point"), [])
        goal = _metric(payload, "goal")["rows"][0]
        self.assertIsNone(goal["team_shortcut"])
        self.assertEqual(goal["is_home"], True)
        self.assertEqual(goal["opponent_shortcut"], "DAL")
        self.assertEqual(_names(payload, "shot"), [])

    def test_shot_row_carries_expected_shots(self) -> None:
        frame = pd.DataFrame([
            _line(
                6,
                "Shooter",
                10,
                EARLY,
                190,
                2.5,
                71.0,
                expected_value=4.12)])
        row = _rows(frame, "shot")[0]
        self.assertEqual(row["probability"], 71.0)
        self.assertEqual(row["expected_shots"], 4.12)
        point = _rows(frame, "point")
        self.assertEqual(point, [])


def _rows(frame: pd.DataFrame, metric: str) -> list[dict]:
    """Return one metric from an unlimited build."""
    payload = build_hockey_player_event_rankings(frame, None)
    return _metric(payload, metric)["rows"]


def _metric(payload: dict, metric: str) -> dict:
    """Find one ranking board by its metric key."""
    for ranking in payload["rankings"]:
        if ranking["metric"] == metric:
            return ranking
    raise AssertionError(metric)


def _names(payload: dict, metric: str) -> list[str]:
    """Player names on one board."""
    return [row["player_name"] for row in _metric(payload, metric)["rows"]]


def _line(
        player_id: int,
        player_name: str,
        match_id: int,
        game_date: datetime,
        event_id: int,
        line: float,
        probability: float,
        expected_value: float = 1.0,
        team_shortcut: str | None = "COL") -> dict:
    """One stored prop line for a home skater."""
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": 10,
        "team_name": "Avalanche",
        "team_shortcut": team_shortcut,
        "match_id": match_id,
        "game_date": game_date,
        "home_team_id": 10,
        "away_team_id": 20,
        "home_name": "Avalanche",
        "home_shortcut": "COL",
        "away_name": "Stars",
        "away_shortcut": "DAL",
        "event_id": event_id,
        "line": line,
        "expected_value": expected_value,
        "probability": probability}
