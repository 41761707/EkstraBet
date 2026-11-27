"""Unit tests for knockout linking and bracket visibility."""

from __future__ import annotations

import unittest
from datetime import datetime

from backend.services.knockout_stages import stage_label
from backend.services.knockout_ties import FOOTBALL_SPORT_ID
from backend.services.knockout_ties import BracketTie
from backend.services.knockout_ties import TieMatch
from backend.services.knockout_ties import group_ties
from backend.services.knockout_ties import tie_with_score
from backend.services.knockout_tree import KnockoutBracket
from backend.services.knockout_tree import link_feeders
from backend.services.knockout_tree import visible_brackets


def _played(
        match_id: int,
        round_number: int,
        home_team_id: int,
        away_team_id: int,
        home_goals: int | None,
        away_goals: int | None,
        result: str,
        game_date: datetime | None = None) -> TieMatch:
    """Build one football match the score rules can read."""
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
        home_goals=home_goals,
        away_goals=away_goals,
        result=result,
        is_played=result not in ("", "0"))


def _linked(matches: list[TieMatch]) -> list[BracketTie]:
    """Score the tree ties and link them. Third place is separate."""
    grouped = group_ties(matches)
    scored = [
        tie_with_score(tie, FOOTBALL_SPORT_ID)
        for tie in grouped.ties]
    return link_feeders(scored)


def _bracket(
        ties: list[BracketTie],
        third_place: BracketTie | None = None,
        bracket_id: str = "cup") -> KnockoutBracket:
    """A bracket whose title and rounds are still empty."""
    return KnockoutBracket(
        bracket_id=bracket_id,
        title="",
        ties=ties,
        third_place=third_place)


def _bye(team_id: int, depth: int) -> BracketTie:
    """A bye card with no match, at the given depth."""
    return BracketTie(
        tie_id=f"bye-cup-{depth}-{team_id}",
        family="cup",
        depth=depth,
        stage_label=stage_label(depth),
        matches=[],
        team_ids=(team_id,),
        is_bye=True)


class TestLinkFeeders(unittest.TestCase):
    """Advancement follows the next phase inside one family."""

    def test_four_team_cup_feeds_the_final(self) -> None:
        grouped = group_ties([
            _played(1, 971, 1, 2, 2, 0, "1", datetime(2026, 7, 1)),
            _played(2, 971, 3, 4, 1, 0, "1", datetime(2026, 7, 2)),
            _played(3, 970, 1, 3, 1, 0, "1", datetime(2026, 7, 10)),
            _played(4, 969, 2, 4, 2, 1, "1", datetime(2026, 7, 18))])
        scored = [
            tie_with_score(tie, FOOTBALL_SPORT_ID)
            for tie in grouped.ties]
        third = tie_with_score(
            grouped.third_place[0], FOOTBALL_SPORT_ID)
        linked = link_feeders(scored + [third])
        tree = [tie for tie in linked if tie.depth is not None]
        linked_third = next(tie for tie in linked if tie.depth is None)
        by_id = {tie.tie_id: tie for tie in tree}
        final = by_id["cup-1-1-3"]
        self.assertEqual(
            final.feeder_tie_ids,
            ("cup-2-1-2", "cup-2-3-4"))
        self.assertEqual(by_id["cup-2-1-2"].advanced_team_id, 1)
        self.assertEqual(by_id["cup-2-3-4"].advanced_team_id, 3)
        self.assertEqual(final.advanced_team_id, 1)
        self.assertEqual(linked_third.tie_id, "cup-third-2-4")
        self.assertEqual(linked_third.score_winner_team_id, 2)
        self.assertIsNone(linked_third.advanced_team_id)
        self.assertEqual(linked_third.feeder_tie_ids, ())
        self.assertIs(linked_third, third)
        for tie in tree:
            self.assertNotIn(linked_third.tie_id, tie.feeder_tie_ids)
        self.assertIsNone(scored[0].advanced_team_id)
        self.assertEqual(scored[0].feeder_tie_ids, ())
        shown = visible_brackets([
            _bracket(tree, third_place=linked_third)])
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0].title, "Drabinka")
        self.assertEqual(
            shown[0].consumed_round_numbers,
            (969, 970, 971))
        self.assertIs(shown[0].third_place, linked_third)

    def test_next_match_overrides_the_goal_sum(self) -> None:
        # Suma półfinału wskazuje 10, a w finale gra 20. Awans idzie
        # za składem finału, jak w Championship.
        linked = _linked([
            _played(1, 971, 10, 20, 3, 0, "1", datetime(2026, 5, 1)),
            _played(2, 971, 20, 10, 0, 0, "X", datetime(2026, 5, 8)),
            _played(3, 970, 20, 30, 1, 0, "1", datetime(2026, 5, 20))])
        by_id = {tie.tie_id: tie for tie in linked}
        semi = by_id["cup-2-10-20"]
        final = by_id["cup-1-20-30"]
        self.assertEqual(semi.aggregate_by_team, {10: 3, 20: 0})
        self.assertEqual(semi.score_winner_team_id, 10)
        self.assertEqual(semi.advanced_team_id, 20)
        self.assertEqual(final.feeder_tie_ids, (semi.tie_id,))
        self.assertEqual(final.advanced_team_id, 20)

    def test_team_links_to_the_nearest_later_phase(self) -> None:
        linked = _linked([
            _played(1, 974, 1, 2, 2, 0, "1"),
            _played(2, 973, 7, 8, 1, 0, "1"),
            _played(3, 972, 1, 5, 1, 0, "1")])
        by_id = {tie.tie_id: tie for tie in linked}
        opening = by_id["cup-16-1-2"]
        skipped = by_id["cup-8-7-8"]
        quarter = by_id["cup-4-1-5"]
        self.assertEqual(opening.advanced_team_id, 1)
        self.assertEqual(quarter.feeder_tie_ids, (opening.tie_id,))
        self.assertEqual(skipped.feeder_tie_ids, ())
        self.assertIsNone(skipped.advanced_team_id)
        self.assertEqual(skipped.score_winner_team_id, 7)
        self.assertEqual(quarter.advanced_team_id, 1)

    def test_two_later_ties_draw_no_line(self) -> None:
        linked = _linked([
            _played(1, 972, 1, 2, 3, 0, "1"),
            _played(2, 971, 1, 3, 1, 0, "1"),
            _played(3, 971, 1, 4, 1, 0, "1")])
        by_id = {tie.tie_id: tie for tie in linked}
        quarter = by_id["cup-4-1-2"]
        self.assertEqual(quarter.score_winner_team_id, 1)
        self.assertIsNone(quarter.advanced_team_id)
        for tie in linked:
            self.assertNotIn(quarter.tie_id, tie.feeder_tie_ids)

    def test_unplayed_final_names_nobody(self) -> None:
        linked = _linked([
            _played(1, 970, 1, 2, None, None, "0")])
        self.assertIsNone(linked[0].score_winner_team_id)
        self.assertIsNone(linked[0].advanced_team_id)
        self.assertEqual(linked[0].feeder_tie_ids, ())

    def test_empty_input(self) -> None:
        self.assertEqual(link_feeders([]), [])


class TestVisibleBrackets(unittest.TestCase):
    """One phase without a bye stays a round button."""

    def test_relegation_stays_apart_from_the_cup_final(self) -> None:
        linked = _linked([
            _played(1, 970, 1, 2, 1, 0, "1", datetime(2026, 5, 20)),
            _played(2, 1003, 1, 3, 2, 0, "1", datetime(2026, 5, 1)),
            _played(3, 1004, 3, 1, 0, 1, "2", datetime(2026, 5, 8)),
            _played(4, 1005, 1, 4, 1, 0, "1", datetime(2026, 5, 15)),
            _played(5, 1006, 4, 1, 0, 2, "2", datetime(2026, 5, 22))])
        cup = [tie for tie in linked if tie.family == "cup"]
        relegation = [
            tie for tie in linked if tie.family == "relegation"]
        by_id = {tie.tie_id: tie for tie in linked}
        cup_final = by_id["cup-1-1-2"]
        semi = by_id["relegation-2-1-3"]
        rel_final = by_id["relegation-1-1-4"]
        self.assertEqual(cup_final.feeder_tie_ids, ())
        self.assertEqual(rel_final.feeder_tie_ids, (semi.tie_id,))
        self.assertEqual(semi.advanced_team_id, 1)
        self.assertNotIn(cup_final.tie_id, rel_final.feeder_tie_ids)
        shown = visible_brackets([
            _bracket(cup, bracket_id="cup"),
            _bracket(relegation, bracket_id="relegation")])
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0].bracket_id, "relegation")
        self.assertEqual(shown[0].title, "Baraż o utrzymanie")
        self.assertEqual(
            shown[0].consumed_round_numbers,
            (1003, 1004, 1005, 1006))
        self.assertNotIn(970, shown[0].consumed_round_numbers)

    def test_relegation_final_alone_is_hidden(self) -> None:
        ties = _linked([
            _played(1, 1005, 1, 2, 1, 0, "1", datetime(2026, 5, 1)),
            _played(2, 1006, 2, 1, 0, 1, "2", datetime(2026, 5, 8))])
        self.assertEqual(len(ties), 1)
        self.assertEqual(ties[0].depth, 1)
        self.assertEqual(
            visible_brackets([
                _bracket(ties, bracket_id="relegation")]),
            [])

    def test_one_phase_with_a_bye_stays_visible(self) -> None:
        final = _linked([_played(1, 970, 1, 2, 1, 0, "1")])
        shown = visible_brackets([_bracket(final + [_bye(3, 1)])])
        self.assertEqual(len(shown), 1)
        self.assertEqual(shown[0].title, "Drabinka")
        self.assertEqual(shown[0].consumed_round_numbers, (970,))

    def test_open_card_without_a_match_stays_hidden(self) -> None:
        placeholder = BracketTie(
            tie_id="cup-8-1-pending",
            family="cup",
            depth=8,
            stage_label=stage_label(8),
            matches=[],
            team_ids=(1,),
            pending_opponent_label="Zwycięzca barażu",
            seed_position=1)
        self.assertEqual(
            visible_brackets([_bracket([placeholder])]),
            [])

    def test_empty_input(self) -> None:
        self.assertEqual(visible_brackets([]), [])


if __name__ == "__main__":
    unittest.main()
