"""Unit tests for settleable football event catalog rules."""

from __future__ import annotations

import unittest

from backend.sports.football.event_settlement_registry import (
    is_settleable_event,
    parse_line_market)


class TestIsSettleableEvent(unittest.TestCase):
    """Settleable iff the evaluator can return 0/1 from a full boxscore."""

    def test_corners_fouls_yellows_offsides_are_settleable(self) -> None:
        cases = [
            (33, "Powyżej 8.5 rożnych"),
            (105, "Gospodarz powyżej 2.5 rożnych"),
            (53, "Powyżej 20.5 fauli"),
            (71, "Gospodarz powyżej 7.5 fauli"),
            (133, "Powyżej 2.5 żółtej kartki"),
            (146, "Gospodarz powyżej 0.5 żółtej kartki"),
            (164, "Powyżej 2.5 spalonych"),
            (167, "Poniżej 0.5 spalonych")
        ]
        for event_id, name in cases:
            with self.subTest(event_id=event_id, name=name):
                self.assertTrue(is_settleable_event(event_id, name))

    def test_double_chance_and_handicap_are_settleable_by_id(self) -> None:
        cases = [
            (4, "Gospodarz nie przegra"),
            (5, "Gość nie przegra"),
            (49, "Handicap -1.5 dla gospodarza"),
            (50, "Handicap +1.5 dla gospodarza"),
            (51, "Handicap -1.5 dla gościa"),
            (52, "Handicap +1.5 dla gościa")
        ]
        for event_id, name in cases:
            with self.subTest(event_id=event_id):
                self.assertTrue(is_settleable_event(event_id, name))

    def test_rejects_parent_goals_and_player_props(self) -> None:
        self.assertFalse(
            is_settleable_event(173, "Dokładna liczba goli"))
        self.assertFalse(is_settleable_event(181, "Strzelec bramki"))
        self.assertFalse(
            is_settleable_event(
                190, "Powyżej X strzałów na bramkę (zawodnik)"))

    def test_rejects_unknown_name_without_explicit_id(self) -> None:
        self.assertFalse(
            is_settleable_event(9999, "Rożne w 1. połowie"))
        self.assertFalse(
            is_settleable_event(9999, "Powyżej 2.5 strzałów"))


class TestParseLineMarket(unittest.TestCase):
    """Polish over/under catalog names map to a typed line rule."""

    def test_home_over_corners(self) -> None:
        rule = parse_line_market("Gospodarz powyżej 2.5 rożnych")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(rule.stat, "corners")
        self.assertEqual(rule.side, "home")
        self.assertEqual(rule.comparator, "over")
        self.assertEqual(rule.line, 2.5)

    def test_total_over_corners(self) -> None:
        rule = parse_line_market("Powyżej 8.5 rożnych")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(rule.stat, "corners")
        self.assertEqual(rule.side, "total")
        self.assertEqual(rule.comparator, "over")
        self.assertEqual(rule.line, 8.5)

    def test_away_under_fouls(self) -> None:
        rule = parse_line_market("Gość poniżej 10.5 fauli")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertEqual(rule.stat, "fouls")
        self.assertEqual(rule.side, "away")
        self.assertEqual(rule.comparator, "under")
        self.assertEqual(rule.line, 10.5)

    def test_yellows_and_offsides_and_goals(self) -> None:
        yellows = parse_line_market("Powyżej 3.5 żółtej kartki")
        offsides = parse_line_market("Poniżej 1.5 spalonych")
        goals = parse_line_market("Powyżej 1.5 gola")
        home_goals = parse_line_market("Gospodarz powyżej 0.5 gola")
        self.assertIsNotNone(yellows)
        self.assertIsNotNone(offsides)
        self.assertIsNotNone(goals)
        self.assertIsNotNone(home_goals)
        assert yellows is not None
        assert offsides is not None
        assert goals is not None
        assert home_goals is not None
        self.assertEqual(yellows.stat, "yellows")
        self.assertEqual(offsides.stat, "offsides")
        self.assertEqual(goals.stat, "goals")
        self.assertEqual(home_goals.side, "home")

    def test_unknown_tail_is_not_a_line_market(self) -> None:
        self.assertIsNone(parse_line_market("Powyżej 2.5 strzałów"))
        self.assertIsNone(parse_line_market("Handicap -1.5 dla gospodarza"))
        self.assertIsNone(parse_line_market("Zwycięstwo gospodarza"))


if __name__ == "__main__":
    unittest.main()
