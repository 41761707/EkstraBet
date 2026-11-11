"""Unit tests for hockey player prop hit and settlement rules."""

from __future__ import annotations

import unittest

from backend.sports.hockey.player_prop_history import (
    OVER_PROP_EVENT_IDS,
    format_prop_event_name,
    is_prop_hit,
    prop_stat_spec,
    settle_prop,
    settlement_case_sql)


class TestPlayerPropHit(unittest.TestCase):
    """Over clears the line strictly. A missing stat stays pending."""

    def test_shots_above_two_and_half_are_won(self) -> None:
        self.assertTrue(is_prop_hit(3, 2.5, "over"))
        self.assertEqual(settle_prop(3, 2.5, "over"), "won")

    def test_shots_below_two_and_half_are_lost(self) -> None:
        self.assertFalse(is_prop_hit(2, 2.5, "over"))
        self.assertEqual(settle_prop(2, 2.5, "over"), "lost")

    def test_missing_stat_is_pending(self) -> None:
        self.assertEqual(settle_prop(None, 2.5, "over"), "pending")

    def test_points_above_half_line_are_a_hit(self) -> None:
        spec = prop_stat_spec(192)
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.column, "points")
        self.assertEqual(spec.side, "over")
        self.assertTrue(is_prop_hit(1, 0.5, spec.side))

    def test_equality_is_not_a_hit_on_either_side(self) -> None:
        self.assertFalse(is_prop_hit(2, 2.0, "over"))
        self.assertFalse(is_prop_hit(2, 2.0, "under"))
        self.assertEqual(settle_prop(2, 2.0, "over"), "lost")
        self.assertEqual(settle_prop(2, 2.0, "under"), "lost")

    def test_under_hits_only_below_the_line(self) -> None:
        self.assertTrue(is_prop_hit(1, 2.5, "under"))
        self.assertEqual(settle_prop(1, 2.5, "under"), "won")


class TestFormatPropEventName(unittest.TestCase):
    """The first X token becomes the line. Other names stay as written."""

    def test_formats_shots_line(self) -> None:
        name = format_prop_event_name(
            "Powyżej X strzałów na bramkę (zawodnik)", 2.5)
        self.assertEqual(
            name, "Powyżej 2.5 strzałów na bramkę (zawodnik)")

    def test_formats_goals_line(self) -> None:
        name = format_prop_event_name("Powyżej X goli zawodnika", 0.5)
        self.assertEqual(name, "Powyżej 0.5 goli zawodnika")

    def test_keeps_name_without_token(self) -> None:
        self.assertEqual(
            format_prop_event_name("Gole zawodnika", 0.5),
            "Gole zawodnika")


class TestPropStatSpec(unittest.TestCase):
    """The catalog is the four over props and nothing else."""

    def test_unknown_event_returns_none(self) -> None:
        self.assertIsNone(prop_stat_spec(191))
        self.assertIsNone(prop_stat_spec(193))
        self.assertIsNone(prop_stat_spec(195))

    def test_catalog_maps_over_columns(self) -> None:
        expected = {
            190: "sog",
            192: "points",
            194: "assists",
            196: "goals"}
        self.assertEqual(OVER_PROP_EVENT_IDS, tuple(expected))
        for event_id, column in expected.items():
            spec = prop_stat_spec(event_id)
            assert spec is not None
            self.assertEqual(spec.event_id, event_id)
            self.assertEqual(spec.column, column)
            self.assertEqual(spec.side, "over")


class TestSettlementCaseSql(unittest.TestCase):
    """The CASE is built from the over catalog only."""

    def test_case_uses_over_stat_columns(self) -> None:
        sql = settlement_case_sql("hs", "ppl")
        self.assertIn("hs.sog", sql)
        self.assertIn("hs.points", sql)
        self.assertIn("hs.assists", sql)
        self.assertIn("hs.goals", sql)
        self.assertIn("> ppl.line", sql)
        self.assertNotIn("191", sql)
        self.assertNotIn("193", sql)
        self.assertNotIn("195", sql)
        self.assertLess(
            sql.index("hs.sog IS NULL"),
            sql.index("hs.sog > ppl.line"))
