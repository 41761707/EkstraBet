"""Unit tests for knockout round classification."""

from __future__ import annotations

import unittest

from backend.services.knockout_stages import RoundClass
from backend.services.knockout_stages import classify_round
from backend.services.knockout_stages import stage_label


class TestClassifyRound(unittest.TestCase):
    """Round numbers from the cup and relegation tables."""

    def test_single_and_series_share_round_of_16_depth(self) -> None:
        self.assertEqual(
            classify_round(974),
            RoundClass("cup", 16, None, "tie"))
        self.assertEqual(
            classify_round(920),
            RoundClass("cup", 16, 1, "tie"))

    def test_first_round_series_legs(self) -> None:
        self.assertEqual(
            classify_round(930),
            RoundClass("cup", 8, 1, "tie"))
        self.assertEqual(
            classify_round(936),
            RoundClass("cup", 8, 7, "tie"))

    def test_cup_series_band_edges(self) -> None:
        expected = (
            (900, 64, 1),
            (906, 64, 7),
            (910, 32, 1),
            (916, 32, 7),
            (926, 16, 7),
            (940, 4, 1),
            (946, 4, 7),
            (950, 2, 1),
            (956, 2, 7),
            (960, 1, 1),
            (966, 1, 7))
        for round_number, depth, leg in expected:
            with self.subTest(round_number=round_number):
                self.assertEqual(
                    classify_round(round_number),
                    RoundClass("cup", depth, leg, "tie"))

    def test_single_cup_rounds(self) -> None:
        expected = (
            (976, 64),
            (975, 32),
            (973, 8),
            (972, 4),
            (971, 2),
            (970, 1))
        for round_number, depth in expected:
            with self.subTest(round_number=round_number):
                self.assertEqual(
                    classify_round(round_number),
                    RoundClass("cup", depth, None, "tie"))

    def test_third_place_has_no_depth(self) -> None:
        self.assertEqual(
            classify_round(969),
            RoundClass("cup", None, None, "third_place"))

    def test_relegation_final_first_leg(self) -> None:
        self.assertEqual(
            classify_round(1005),
            RoundClass("relegation", 1, 1, "tie"))

    def test_relegation_pairs(self) -> None:
        expected = (
            (1001, 4, 1),
            (1002, 4, 2),
            (1003, 2, 1),
            (1004, 2, 2),
            (1006, 1, 2))
        for round_number, depth, leg in expected:
            with self.subTest(round_number=round_number):
                self.assertEqual(
                    classify_round(round_number),
                    RoundClass("relegation", depth, leg, "tie"))

    def test_numbers_outside_the_table_are_none(self) -> None:
        outside = (
            8,
            100,
            444,
            555,
            899,
            907,
            909,
            917,
            967,
            968,
            977,
            1000,
            1007)
        for round_number in outside:
            with self.subTest(round_number=round_number):
                self.assertIsNone(classify_round(round_number))


class TestStageLabel(unittest.TestCase):
    """Polish column titles for the seven knockout depths."""

    def test_known_depths(self) -> None:
        self.assertEqual(stage_label(64), "1/64 finału")
        self.assertEqual(stage_label(32), "1/32 finału")
        self.assertEqual(stage_label(16), "1/16 finału")
        self.assertEqual(stage_label(8), "1/8 finału")
        self.assertEqual(stage_label(4), "Ćwierćfinał")
        self.assertEqual(stage_label(2), "Półfinał")
        self.assertEqual(stage_label(1), "Finał")


if __name__ == "__main__":
    unittest.main()
