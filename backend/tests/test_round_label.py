"""Unit tests for round label resolution."""

from __future__ import annotations

import unittest

from backend.services.round_label import resolve_round_label


class TestRoundLabel(unittest.TestCase):
    """Tests for special round label mapping."""

    def test_resolve_round_label_returns_none_for_missing_round(self) -> None:
        self.assertIsNone(resolve_round_label(None, {}))

    def test_resolve_round_label_returns_number_for_regular_round(self) -> None:
        self.assertEqual(resolve_round_label(12, {}), "12")

    def test_resolve_round_label_resolves_special_round_name(self) -> None:
        special_rounds = {973: "Quarter-final"}
        self.assertEqual(
            resolve_round_label(973, special_rounds),
            "Quarter-final")

    def test_resolve_round_label_resolves_phase_round_from_dictionary(
        self) -> None:
        special_rounds = {100: "Sezon zasadniczy", 200: "Playoffy"}
        self.assertEqual(
            resolve_round_label(100, special_rounds),
            "Sezon zasadniczy")

    def test_resolve_round_label_falls_back_to_id_for_unknown_special_round(
        self) -> None:
        self.assertEqual(resolve_round_label(973, {}), "973")


if __name__ == "__main__":
    unittest.main()
