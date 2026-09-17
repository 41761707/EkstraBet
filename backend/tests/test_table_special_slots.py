"""Unit tests for football table special-slot probability aggregation."""

from __future__ import annotations

import unittest

from backend.sports.football.table_special_slots import (
    outcome_probabilities,
    sum_position_slice)


class TestSumPositionSlice(unittest.TestCase):
    """Slice sums used by champion / top / bot aggregation."""

    def test_sums_inclusive_start_exclusive_end(self) -> None:
        self.assertAlmostEqual(
            sum_position_slice([0.5, 0.3, 0.15, 0.05], 0, 4),
            1.0)

    def test_empty_or_out_of_range_returns_zero(self) -> None:
        self.assertEqual(sum_position_slice([], 0, 1), 0.0)
        self.assertEqual(sum_position_slice([0.4, 0.6], 2, 5), 0.0)
        self.assertEqual(sum_position_slice([0.4, 0.6], -1, 1), 0.0)
        self.assertEqual(sum_position_slice([0.4, 0.6], 1, 1), 0.0)


class TestOutcomeProbabilities(unittest.TestCase):
    """Champion, top-N and bottom-N probabilities from a position vector."""

    def test_top_four_bot_three_on_eighteen_teams(self) -> None:
        probabilities = [1.0 / 18] * 18
        result = outcome_probabilities(probabilities, 4, 3)
        self.assertAlmostEqual(result.champion, probabilities[0])
        self.assertAlmostEqual(result.top, sum(probabilities[:4]))
        self.assertAlmostEqual(result.bot, sum(probabilities[-3:]))
        # TOP zawiera miejsce 1 (indeks 0)
        assert result.top is not None
        self.assertAlmostEqual(
            result.top,
            result.champion + sum(probabilities[1:4]))

    def test_clamps_top_when_vector_shorter_than_top_slots(self) -> None:
        probabilities = [0.5, 0.3, 0.2]
        result = outcome_probabilities(probabilities, 4, 1)
        self.assertAlmostEqual(result.champion, 0.5)
        self.assertAlmostEqual(result.top, 1.0)

    def test_zero_bot_slots_yield_none_bot(self) -> None:
        result = outcome_probabilities([0.7, 0.3], 2, 0)
        self.assertAlmostEqual(result.champion, 0.7)
        self.assertAlmostEqual(result.top, 1.0)
        self.assertIsNone(result.bot)

    def test_zero_top_slots_yield_none_top(self) -> None:
        result = outcome_probabilities([0.7, 0.3], 0, 2)
        self.assertAlmostEqual(result.champion, 0.7)
        self.assertIsNone(result.top)
        self.assertAlmostEqual(result.bot, 1.0)

    def test_empty_vector_champion_is_zero(self) -> None:
        result = outcome_probabilities([], 4, 3)
        self.assertEqual(result.champion, 0.0)
        self.assertIsNone(result.top)
        self.assertIsNone(result.bot)

    def test_four_team_example_from_spec(self) -> None:
        probabilities = [0.5, 0.3, 0.15, 0.05]
        result = outcome_probabilities(probabilities, 4, 3)
        self.assertAlmostEqual(result.champion, 0.5)
        self.assertAlmostEqual(result.top, 1.0)
        self.assertAlmostEqual(result.bot, 0.5)


if __name__ == "__main__":
    unittest.main()
