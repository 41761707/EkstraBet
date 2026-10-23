"""Unit tests for the season hockey rating board."""

from __future__ import annotations

import unittest

import pandas as pd

from backend.sports.hockey.rating_board import build_hockey_rating_board


def _game(
    player_id: int,
    name: str,
    total: float,
    game_date: str,
    match_id: int,
    roster_position: str | None = None,
    player_position: str | None = None,
    shots_against: int | None = None) -> dict:
    """One stored rating row."""
    return {
        "player_id": player_id,
        "player_name": name,
        "team_name": "Los Angeles Kings",
        "match_id": match_id,
        "game_date": game_date,
        "opponent_name": "Ottawa Senators",
        "total": total,
        "roster_position": roster_position,
        "player_position": player_position,
        "shots_against": shots_against
    }


class TestHockeyRatingBoard(unittest.TestCase):
    """Averages need five games. Extremes ignore the window."""

    def test_five_game_window_skips_a_short_sample(self) -> None:
        rows = []
        match_id = 1
        for index in range(4):
            rows.append(_game(
                1, "Short S.", 9.0, f"2026-01-{index + 1:02d}", match_id))
            match_id += 1
        for index in range(5):
            rows.append(_game(
                2, "Low L.", 1.0, f"2026-02-{index + 1:02d}", match_id))
            match_id += 1
        for index in range(5):
            rows.append(_game(
                3, "High H.", 3.0, f"2026-03-{index + 1:02d}", match_id))
            match_id += 1

        board = build_hockey_rating_board(pd.DataFrame(rows), 5)

        names = [item["player_name"] for item in board["averages"]]
        worst_names = [
            item["player_name"] for item in board["worst_averages"]]
        self.assertEqual(names, ["High H.", "Low L."])
        self.assertEqual(worst_names, ["Low L.", "High H."])
        self.assertEqual(board["averages"][0]["games"], 5)
        self.assertEqual(board["averages"][0]["average"], 3.0)
        best = board["forward"]["best_games"]
        worst = board["forward"]["worst_games"]
        self.assertEqual(len(best), 10)
        self.assertEqual(len(worst), 10)
        self.assertEqual(best[0]["total"], 9.0)
        self.assertEqual(worst[0]["total"], 1.0)
        self.assertGreater(best[0]["total"], best[-1]["total"])
        self.assertLess(worst[0]["total"], worst[-1]["total"])
        self.assertEqual(board["defense"]["best_games"], [])
        self.assertEqual(board["goalie"]["best_games"], [])

    def test_equal_totals_keep_the_later_night_first(self) -> None:
        frame = pd.DataFrame([
            _game(2, "Later L.", 2.0, "2026-04-02", 20),
            _game(1, "Earlier E.", 2.0, "2026-04-01", 10)
        ])

        board = build_hockey_rating_board(frame, 0)

        self.assertEqual(board["averages"], [])
        self.assertEqual(board["worst_averages"], [])
        self.assertEqual(
            board["forward"]["best_games"][0]["player_id"],
            2)
        self.assertEqual(
            board["forward"]["worst_games"][0]["player_id"],
            2)

    def test_nights_stay_inside_their_position(self) -> None:
        frame = pd.DataFrame([
            _game(1, "Wing W.", 4.0, "2026-04-02", 1, roster_position="LW"),
            _game(2, "Def D.", 3.0, "2026-04-02", 2, roster_position="D"),
            _game(
                3,
                "Net N.",
                -2.0,
                "2026-04-02",
                3,
                shots_against=20)
        ])

        board = build_hockey_rating_board(frame, 0)

        self.assertEqual(
            board["forward"]["best_games"][0]["player_id"],
            1)
        self.assertEqual(
            board["defense"]["worst_games"][0]["player_id"],
            2)
        self.assertEqual(
            board["goalie"]["best_games"][0]["player_id"],
            3)
        self.assertEqual(board["goalie"]["best_games"][0]["total"], -2.0)
        self.assertEqual(len(board["forward"]["best_games"]), 1)
        self.assertEqual(board["defense"]["best_games"][0]["total"], 3.0)
