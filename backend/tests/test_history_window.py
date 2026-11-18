"""Hit rate shared by the team and player history strips."""

from __future__ import annotations

import unittest

from backend.sports.history_window import (
    history_hit_rate,
    page_by_history_rate)


class TestHistoryHitRate(unittest.TestCase):
    """Two strips add counts before the rate is divided."""

    def test_two_strips_rank_as_the_sum_of_counts(self) -> None:
        combined = {
            "series": [
                {"hits": 3, "played": 10},
                {"hits": 9, "played": 10}]}
        single = {"hits": 6, "played": 10}
        self.assertAlmostEqual(history_hit_rate(combined), 12 / 20)
        self.assertAlmostEqual(
            history_hit_rate(combined), history_hit_rate(single))

    def test_empty_strip_does_not_change_the_other(self) -> None:
        history = {
            "series": [
                {"hits": 3, "played": 10},
                {"hits": 0, "played": 0}]}
        self.assertAlmostEqual(history_hit_rate(history), 0.3)

    def test_no_played_matches_has_no_rate(self) -> None:
        self.assertIsNone(history_hit_rate(None))
        self.assertIsNone(history_hit_rate({"hits": 0, "played": 0}))
        self.assertIsNone(history_hit_rate({"series": []}))


class TestPageByHistoryRate(unittest.TestCase):
    """Missing rates stay last. Equal rates keep the smaller id."""

    def test_descending_pages_the_highest_rate_first(self) -> None:
        rows = [
            {"bet_id": 1, "history": {"hits": 1, "played": 2}},
            {"bet_id": 2, "history": {"hits": 2, "played": 2}},
            {"bet_id": 3, "history": None}]
        page = page_by_history_rate(rows, "desc", 1, 1, "bet_id")
        self.assertEqual(page[0]["bet_id"], 2)

    def test_ascending_keeps_a_missing_rate_last(self) -> None:
        rows = [
            {"bet_id": 3, "history": None},
            {"bet_id": 2, "history": {"hits": 2, "played": 2}},
            {"bet_id": 1, "history": {"hits": 1, "played": 2}}]
        ordered = page_by_history_rate(rows, "asc", 1, 10, "bet_id")
        self.assertEqual(
            [row["bet_id"] for row in ordered], [1, 2, 3])

    def test_equal_rates_keep_the_smaller_id_first(self) -> None:
        rows = [
            {"line_id": 8, "history": {"hits": 6, "played": 10}},
            {
                "line_id": 4,
                "history": {
                    "series": [
                        {"hits": 3, "played": 10},
                        {"hits": 9, "played": 10}]}}]
        ordered = page_by_history_rate(rows, "desc", 1, 10, "line_id")
        self.assertEqual(
            [row["line_id"] for row in ordered], [4, 8])


if __name__ == "__main__":
    unittest.main()
