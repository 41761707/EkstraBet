"""Unit tests for grouping knockout matches into ties."""

from __future__ import annotations

import unittest
from datetime import datetime

from backend.services.knockout_stages import stage_label
from backend.services.knockout_ties import THIRD_PLACE_LABEL
from backend.services.knockout_ties import BracketTie
from backend.services.knockout_ties import GroupedTies
from backend.services.knockout_ties import TieMatch
from backend.services.knockout_ties import group_ties


def _match(
        match_id: int,
        round_number: int,
        home_team_id: int,
        away_team_id: int,
        game_date: datetime | None = None) -> TieMatch:
    """Build a match with only the fields grouping reads."""
    return TieMatch(
        match_id=match_id,
        round_number=round_number,
        leg_index=None,
        game_date=game_date,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_team_name=f"Team {home_team_id}",
        away_team_name=f"Team {away_team_id}",
        home_team_shortcut=None,
        away_team_shortcut=None,
        home_goals=None,
        away_goals=None,
        result=None,
        is_played=False)


class TestGroupTies(unittest.TestCase):
    """Pairs of the same two teams inside one phase."""

    def test_same_round_splits_into_two_two_legged_ties(self) -> None:
        grouped = group_ties([
            _match(11, 971, 2, 1, datetime(2026, 5, 8)),
            _match(21, 971, 4, 3, datetime(2026, 5, 9)),
            _match(10, 971, 1, 2, datetime(2026, 5, 1)),
            _match(20, 971, 3, 4, datetime(2026, 5, 2))])
        self.assertEqual(grouped.third_place, [])
        self.assertEqual(
            [tie.tie_id for tie in grouped.ties],
            ["cup-2-1-2", "cup-2-3-4"])
        self.assertEqual(
            [match.match_id for match in grouped.ties[0].matches],
            [10, 11])
        self.assertEqual(
            [match.match_id for match in grouped.ties[1].matches],
            [20, 21])
        first = grouped.ties[0]
        self.assertEqual(first.family, "cup")
        self.assertEqual(first.depth, 2)
        self.assertEqual(first.stage_label, stage_label(2))
        self.assertEqual(first.team_ids, (1, 2))
        self.assertEqual(first.source_round_numbers, (971,))
        self.assertIsNone(first.matches[0].leg_index)
        self._assert_unset(first)

    def test_home_away_swap_stays_one_tie(self) -> None:
        grouped = group_ties([
            _match(2, 971, 20, 10, datetime(2026, 5, 1)),
            _match(1, 971, 10, 20, datetime(2026, 5, 8))])
        self.assertEqual(len(grouped.ties), 1)
        tie = grouped.ties[0]
        self.assertEqual(tie.tie_id, "cup-2-10-20")
        self.assertEqual(tie.team_ids, (10, 20))
        self.assertEqual(
            [match.match_id for match in tie.matches],
            [2, 1])

    def test_same_date_orders_by_match_id(self) -> None:
        day = datetime(2026, 5, 1)
        grouped = group_ties([
            _match(30, 971, 1, 2, day),
            _match(10, 971, 2, 1, day)])
        self.assertEqual(
            [match.match_id for match in grouped.ties[0].matches],
            [10, 30])

    def test_missing_date_sorts_after_a_known_date(self) -> None:
        grouped = group_ties([
            _match(2, 971, 1, 2, None),
            _match(1, 971, 2, 1, datetime(2026, 5, 1))])
        self.assertEqual(
            [match.match_id for match in grouped.ties[0].matches],
            [1, 2])

    def test_series_legs_sort_before_date(self) -> None:
        grouped = group_ties([
            _match(3, 932, 20, 10, datetime(2026, 4, 20)),
            _match(1, 930, 10, 20, datetime(2026, 5, 1)),
            _match(2, 931, 10, 20, datetime(2026, 4, 18))])
        tie = grouped.ties[0]
        self.assertEqual(tie.tie_id, "cup-8-10-20")
        self.assertEqual(tie.stage_label, stage_label(8))
        self.assertEqual(
            [match.match_id for match in tie.matches],
            [1, 2, 3])
        self.assertEqual(
            [match.leg_index for match in tie.matches],
            [1, 2, 3])
        self.assertEqual(tie.source_round_numbers, (930, 931, 932))

    def test_third_place_stays_out_of_the_tree(self) -> None:
        grouped = group_ties([
            _match(1, 971, 1, 2, datetime(2026, 7, 1)),
            _match(2, 969, 4, 3, datetime(2026, 7, 18))])
        self.assertEqual(
            [tie.tie_id for tie in grouped.ties],
            ["cup-2-1-2"])
        self.assertEqual(len(grouped.third_place), 1)
        third = grouped.third_place[0]
        self.assertEqual(third.tie_id, "cup-third-3-4")
        self.assertEqual(third.family, "cup")
        self.assertIsNone(third.depth)
        self.assertEqual(third.stage_label, THIRD_PLACE_LABEL)
        self.assertEqual(third.team_ids, (3, 4))
        self.assertEqual(third.source_round_numbers, (969,))
        self.assertEqual(third.matches[0].match_id, 2)
        self.assertIsNone(third.matches[0].leg_index)

    def test_one_team_in_two_ties_stays_two_ties(self) -> None:
        grouped = group_ties([
            _match(1, 971, 1, 2),
            _match(2, 971, 3, 1)])
        self.assertEqual(
            [tie.tie_id for tie in grouped.ties],
            ["cup-2-1-2", "cup-2-1-3"])

    def test_different_depths_stay_apart(self) -> None:
        grouped = group_ties([
            _match(1, 971, 1, 2),
            _match(2, 970, 2, 1)])
        self.assertEqual(
            [tie.tie_id for tie in grouped.ties],
            ["cup-1-1-2", "cup-2-1-2"])

    def test_cup_and_relegation_do_not_merge(self) -> None:
        grouped = group_ties([
            _match(1, 970, 1, 2),
            _match(2, 1005, 2, 1)])
        self.assertEqual(
            [tie.tie_id for tie in grouped.ties],
            ["cup-1-1-2", "relegation-1-1-2"])
        cup = grouped.ties[0]
        relegation = grouped.ties[1]
        self.assertIsNone(cup.matches[0].leg_index)
        self.assertEqual(relegation.matches[0].leg_index, 1)
        self.assertEqual(relegation.family, "relegation")
        self.assertEqual(relegation.depth, 1)
        self.assertEqual(relegation.source_round_numbers, (1005,))

    def test_unknown_round_is_ignored(self) -> None:
        grouped = group_ties([
            _match(1, 100, 1, 2),
            _match(2, 8, 3, 4),
            _match(3, 444, 5, 6),
            _match(4, 555, 7, 8),
            _match(5, 970, 9, 10)])
        self.assertEqual(
            [tie.tie_id for tie in grouped.ties],
            ["cup-1-9-10"])
        self.assertEqual(grouped.third_place, [])

    def test_empty_input(self) -> None:
        self.assertEqual(group_ties([]), GroupedTies([], []))

    def _assert_unset(self, tie: BracketTie) -> None:
        self.assertIsNone(tie.pending_opponent_label)
        self.assertIsNone(tie.seed_position)
        self.assertFalse(tie.is_bye)
        self.assertIsNone(tie.score_winner_team_id)
        self.assertIsNone(tie.advanced_team_id)
        self.assertIsNone(tie.aggregate_by_team)
        self.assertIsNone(tie.series_wins_by_team)
        self.assertEqual(tie.feeder_tie_ids, ())
        self.assertFalse(tie.on_champion_path)


if __name__ == "__main__":
    unittest.main()
