"""Unit tests for shared probability conversion."""

from __future__ import annotations

import unittest

from backend.services.probability_service import to_unit_probability


class TestProbabilityService(unittest.TestCase):
    """Tests for DB percentage to unit probability conversion."""

    def test_converts_typical_percentage(self) -> None:
        self.assertAlmostEqual(to_unit_probability(55.0), 0.55)

    def test_converts_sub_one_percent_without_heuristic(self) -> None:
        self.assertAlmostEqual(to_unit_probability(0.98), 0.0098)

    def test_converts_tiny_percentage(self) -> None:
        self.assertAlmostEqual(to_unit_probability(0.00456585), 0.0000456585)

    def test_clamps_negative_values(self) -> None:
        self.assertEqual(to_unit_probability(-5.0), 0.0)

    def test_clamps_values_above_one_hundred(self) -> None:
        self.assertEqual(to_unit_probability(150.0), 1.0)


if __name__ == "__main__":
    unittest.main()
