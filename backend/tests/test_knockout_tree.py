"""Unit tests for knockout linking, byes and bracket visibility."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime

from backend.services.knockout_profiles import CHAMPIONS_LEAGUE_ID
from backend.services.knockout_profiles import SeededTeam
from backend.services.knockout_profiles import active_bye_profile
from backend.services.knockout_stages import stage_label
from backend.services.knockout_ties import FOOTBALL_SPORT_ID
from backend.services.knockout_ties import BracketTie
from backend.services.knockout_ties import TieMatch
from backend.services.knockout_ties import group_ties
from backend.services.knockout_ties import tie_with_score
from backend.services.knockout_tree import KnockoutBracket
from backend.services.knockout_tree import apply_byes
from backend.services.knockout_tree import champion_path
from backend.services.knockout_tree import link_feeders
from backend.services.knockout_tree import order_ties
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


class TestApplyByes(unittest.TestCase):
    """Byes from a missing earlier round, then the league profile."""

    def test_four_teams_entering_later_get_a_bye(self) -> None:
        linked = _linked([
            _played(1, 974, 1, 2, 2, 0, "1"),
            _played(2, 974, 3, 4, 2, 0, "1"),
            _played(3, 974, 5, 6, 2, 0, "1"),
            _played(4, 974, 7, 8, 2, 0, "1"),
            _played(5, 973, 1, 9, 1, 0, "1"),
            _played(6, 973, 3, 10, 1, 0, "1"),
            _played(7, 973, 5, 11, 1, 0, "1"),
            _played(8, 973, 7, 12, 1, 0, "1")])
        before = {tie.tie_id: tie.feeder_tie_ids for tie in linked}
        result = apply_byes(linked, [], None)
        byes = [tie for tie in result if tie.is_bye]
        self.assertEqual(
            [bye.tie_id for bye in byes],
            [
                "bye-cup-16-9",
                "bye-cup-16-10",
                "bye-cup-16-11",
                "bye-cup-16-12"])
        self.assertEqual(
            [bye.team_ids for bye in byes],
            [(9,), (10,), (11,), (12,)])
        for bye in byes:
            self.assertEqual(bye.depth, 16)
            self.assertEqual(bye.family, "cup")
            self.assertEqual(bye.matches, [])
            self.assertEqual(bye.feeder_tie_ids, ())
        by_id = {tie.tie_id: tie for tie in result}
        expected = {
            "cup-8-1-9": ("cup-16-1-2", "bye-cup-16-9"),
            "cup-8-3-10": ("cup-16-3-4", "bye-cup-16-10"),
            "cup-8-5-11": ("cup-16-5-6", "bye-cup-16-11"),
            "cup-8-7-12": ("cup-16-7-8", "bye-cup-16-12")}
        for tie_id, feeders in expected.items():
            self.assertEqual(by_id[tie_id].feeder_tie_ids, feeders)
        self.assertEqual(
            {tie.tie_id: tie.feeder_tie_ids for tie in linked},
            before)

    def test_bye_stops_at_the_previous_phase(self) -> None:
        result = apply_byes(_linked([
            _played(1, 974, 1, 2, 1, 0, "1"),
            _played(2, 973, 1, 2, 1, 0, "1"),
            _played(3, 972, 9, 1, 1, 0, "1")]), [], None)
        byes = [tie for tie in result if tie.is_bye]
        self.assertEqual([bye.tie_id for bye in byes], ["bye-cup-8-9"])
        by_id = {tie.tie_id: tie for tie in result}
        self.assertEqual(
            by_id["cup-4-1-9"].feeder_tie_ids,
            ("cup-8-1-2", "bye-cup-8-9"))
        self.assertNotIn("bye-cup-8-9", by_id["cup-8-1-2"].feeder_tie_ids)
        self.assertNotIn("bye-cup-16-9", by_id)

    def test_relegation_bye_stays_in_that_family(self) -> None:
        result = apply_byes(_linked([
            _played(1, 1003, 1, 2, 1, 0, "1"),
            _played(2, 1005, 1, 4, 1, 0, "1")]), [], None)
        byes = [tie for tie in result if tie.is_bye]
        self.assertEqual(
            [bye.tie_id for bye in byes],
            ["bye-relegation-2-4"])
        final = next(tie for tie in result if tie.depth == 1)
        self.assertEqual(
            final.feeder_tie_ids,
            ("relegation-2-1-2", "bye-relegation-2-4"))

    def test_unplayed_league_phase_adds_no_seed_cards(self) -> None:
        self.assertIsNone(active_bye_profile(CHAMPIONS_LEAGUE_ID, 3))
        self.assertIsNone(active_bye_profile(1, 0))
        linked = _linked([
            _played(1, 974, 20, 21, 1, 0, "1")])
        seeds = _seeds()
        result = apply_byes(linked, seeds, None)
        self.assertEqual(
            [tie.tie_id for tie in result],
            [tie.tie_id for tie in linked])
        self.assertFalse(any(tie.is_bye for tie in result))
        self.assertFalse(any(
            tie.pending_opponent_label is not None for tie in result))

    def test_complete_table_adds_placeholders_without_lines(self) -> None:
        profile = active_bye_profile(CHAMPIONS_LEAGUE_ID, 0)
        self.assertIsNotNone(profile)
        linked = _linked([
            _played(1, 974, 20, 21, 1, 0, "1"),
            _played(2, 974, 22, 23, 2, 0, "1")])
        before = {tie.tie_id: tie.feeder_tie_ids for tie in linked}
        result = apply_byes(linked, _seeds(), profile)
        placeholders = [
            tie for tie in result
            if tie.pending_opponent_label is not None]
        self.assertEqual(
            [tie.seed_position for tie in placeholders],
            [1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(
            [tie.team_ids for tie in placeholders],
            [(309,), (308,), (307,), (306,), (305,), (304,), (303,), (302,)])
        for tie in placeholders:
            self.assertEqual(tie.depth, 8)
            self.assertEqual(tie.family, "cup")
            self.assertEqual(
                tie.pending_opponent_label,
                "Zwycięzca barażu")
            self.assertEqual(tie.feeder_tie_ids, ())
            self.assertFalse(tie.is_bye)
            self.assertEqual(tie.matches, [])
            self.assertEqual(
                tie.tie_id,
                f"cup-8-{tie.team_ids[0]}-pending")
        kept = [tie for tie in result if tie.tie_id in before]
        self.assertEqual(
            {tie.tie_id: tie.feeder_tie_ids for tie in kept},
            before)
        placeholder_ids = {tie.tie_id for tie in placeholders}
        for tie in kept:
            self.assertTrue(placeholder_ids.isdisjoint(tie.feeder_tie_ids))

    def test_drawn_seed_gets_a_bye_on_the_ladder_step(self) -> None:
        profile = active_bye_profile(CHAMPIONS_LEAGUE_ID, 0)
        seeds = [
            SeededTeam(team_id=2, position=2),
            SeededTeam(team_id=1, position=1)]
        result = apply_byes(_linked([
            _played(1, 973, 1, 50, 1, 0, "1")]), seeds, profile)
        byes = [tie for tie in result if tie.is_bye]
        self.assertEqual([bye.tie_id for bye in byes], ["bye-cup-16-1"])
        self.assertEqual(byes[0].depth, 16)
        self.assertEqual(byes[0].matches, [])
        self.assertFalse(any(
            tie.pending_opponent_label is not None for tie in result))
        destination = next(tie for tie in result if tie.depth == 8)
        self.assertEqual(destination.feeder_tie_ids, ("bye-cup-16-1",))

    def test_real_feeder_blocks_the_seed_bye(self) -> None:
        profile = active_bye_profile(CHAMPIONS_LEAGUE_ID, 0)
        result = apply_byes(_linked([
            _played(1, 974, 1, 60, 2, 0, "1"),
            _played(2, 974, 50, 51, 1, 0, "1"),
            _played(3, 973, 1, 50, 1, 0, "1")]), [
                SeededTeam(team_id=1, position=1)], profile)
        self.assertFalse(any(tie.is_bye for tie in result))
        self.assertFalse(any(
            tie.pending_opponent_label is not None for tie in result))
        destination = next(tie for tie in result if tie.depth == 8)
        self.assertEqual(
            destination.feeder_tie_ids,
            ("cup-16-1-60", "cup-16-50-51"))

    def test_profile_does_not_duplicate_a_structural_bye(self) -> None:
        profile = active_bye_profile(CHAMPIONS_LEAGUE_ID, 0)
        seeds = [
            SeededTeam(team_id=1, position=1),
            SeededTeam(team_id=2, position=2)]
        result = apply_byes(_linked([
            _played(1, 974, 20, 21, 1, 0, "1"),
            _played(2, 973, 1, 50, 1, 0, "1")]), seeds, profile)
        bye_ids = [tie.tie_id for tie in result if tie.is_bye]
        self.assertEqual(bye_ids, ["bye-cup-16-1", "bye-cup-16-50"])
        self.assertEqual(bye_ids.count("bye-cup-16-1"), 1)
        self.assertFalse(any(
            tie.pending_opponent_label is not None for tie in result))

    def test_profile_without_a_cup_match_adds_nothing(self) -> None:
        profile = active_bye_profile(CHAMPIONS_LEAGUE_ID, 0)
        seeds = _seeds()
        self.assertEqual(apply_byes([], seeds, profile), [])
        linked = _linked([
            _played(1, 1005, 1, 2, 1, 0, "1")])
        result = apply_byes(linked, seeds, profile)
        self.assertEqual(
            [tie.tie_id for tie in result],
            [tie.tie_id for tie in linked])

    def test_empty_input(self) -> None:
        self.assertEqual(apply_byes([], [], None), [])


class TestChampionPath(unittest.TestCase):
    """The accent follows the club that won the closest tie."""

    def test_four_team_cup_marks_only_the_winners_road(self) -> None:
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
        linked = link_feeders(scored)
        placeholder = _placeholder(1)
        source = _with_feeder(
            linked,
            "cup-1-1-3",
            placeholder.tie_id) + [third, placeholder]
        marked = champion_path(source)
        by_id = {tie.tie_id: tie for tie in marked}
        self.assertEqual(
            [tie.tie_id for tie in marked],
            [tie.tie_id for tie in source])
        self.assertTrue(by_id["cup-1-1-3"].on_champion_path)
        self.assertTrue(by_id["cup-2-1-2"].on_champion_path)
        self.assertFalse(by_id["cup-2-3-4"].on_champion_path)
        self.assertFalse(by_id[third.tie_id].on_champion_path)
        self.assertFalse(by_id[placeholder.tie_id].on_champion_path)
        self.assertTrue(all(
            not tie.on_champion_path for tie in source))

    def test_unplayed_final_leaves_the_path_dark(self) -> None:
        marked = champion_path(_linked([
            _played(1, 971, 1, 2, 2, 0, "1", datetime(2026, 7, 1)),
            _played(2, 971, 3, 4, 1, 0, "1", datetime(2026, 7, 2)),
            _played(3, 970, 1, 3, None, None, "0", datetime(2026, 7, 10))]))
        final = next(tie for tie in marked if tie.depth == 1)
        semis = [tie for tie in marked if tie.depth == 2]
        self.assertIsNone(final.advanced_team_id)
        self.assertTrue(all(
            tie.advanced_team_id is not None for tie in semis))
        self.assertTrue(all(not tie.on_champion_path for tie in marked))

    def test_winner_road_crosses_three_rounds(self) -> None:
        marked = champion_path(_linked([
            _played(1, 972, 1, 8, 1, 0, "1", datetime(2026, 6, 1)),
            _played(2, 972, 3, 4, 1, 0, "1", datetime(2026, 6, 2)),
            _played(3, 971, 1, 5, 1, 0, "1", datetime(2026, 7, 1)),
            _played(4, 971, 3, 6, 1, 0, "1", datetime(2026, 7, 2)),
            _played(5, 970, 1, 3, 2, 0, "1", datetime(2026, 7, 10))]))
        by_id = {tie.tie_id: tie for tie in marked}
        on_path = {
            tie.tie_id for tie in marked if tie.on_champion_path}
        self.assertEqual(
            on_path,
            {"cup-4-1-8", "cup-2-1-5", "cup-1-1-3"})
        self.assertFalse(by_id["cup-4-3-4"].on_champion_path)
        self.assertFalse(by_id["cup-2-3-6"].on_champion_path)

    def test_each_family_keeps_its_own_winner(self) -> None:
        marked = champion_path(_linked([
            _played(1, 970, 1, 2, 1, 0, "1", datetime(2026, 5, 20)),
            _played(2, 1003, 10, 11, 2, 0, "1", datetime(2026, 5, 1)),
            _played(3, 1005, 10, 12, 1, 0, "1", datetime(2026, 5, 15))]))
        on_path = {
            tie.tie_id for tie in marked if tie.on_champion_path}
        self.assertEqual(
            on_path,
            {
                "cup-1-1-2",
                "relegation-2-10-11",
                "relegation-1-10-12"})

    def test_empty_input(self) -> None:
        self.assertEqual(champion_path([]), [])


class TestOrderTies(unittest.TestCase):
    """Upper and lower follow the date, not the input order."""

    def test_earlier_semi_stays_above_on_every_call(self) -> None:
        linked = _linked([
            _played(2, 971, 1, 2, 2, 0, "1", datetime(2026, 7, 2)),
            _played(1, 971, 3, 4, 1, 0, "1", datetime(2026, 7, 1)),
            _played(3, 970, 1, 3, 1, 0, "1", datetime(2026, 7, 10))])
        expected = ["cup-2-3-4", "cup-2-1-2", "cup-1-1-3"]
        first = [tie.tie_id for tie in order_ties(linked)]
        second = [tie.tie_id for tie in order_ties(linked)]
        shuffled = [
            tie.tie_id
            for tie in order_ties(list(reversed(linked)))]
        self.assertEqual(first, expected)
        self.assertEqual(second, first)
        self.assertEqual(shuffled, first)

    def test_same_date_uses_the_smaller_match_id(self) -> None:
        linked = _linked([
            _played(20, 971, 3, 4, 1, 0, "1", datetime(2026, 7, 1)),
            _played(5, 971, 1, 2, 2, 0, "1", datetime(2026, 7, 1)),
            _played(30, 970, 1, 3, 1, 0, "1", datetime(2026, 7, 10))])
        self.assertEqual(
            [tie.tie_id for tie in order_ties(linked)],
            ["cup-2-1-2", "cup-2-3-4", "cup-1-1-3"])

    def test_byes_without_a_date_use_the_smaller_team_id(self) -> None:
        upper = _bye(3, 2)
        lower = _bye(8, 2)
        final = BracketTie(
            tie_id="cup-1-3-8",
            family="cup",
            depth=1,
            stage_label=stage_label(1),
            matches=[_played(
                1, 970, 3, 8, 1, 0, "1", datetime(2026, 7, 10))],
            team_ids=(3, 8),
            advanced_team_id=3,
            feeder_tie_ids=(lower.tie_id, upper.tie_id))
        ordered = [
            tie.tie_id
            for tie in order_ties([final, lower, upper])]
        self.assertEqual(
            ordered,
            [upper.tie_id, lower.tie_id, final.tie_id])
        self.assertEqual(
            final.feeder_tie_ids,
            (lower.tie_id, upper.tie_id))

    def test_unlinked_tie_sits_under_the_column(self) -> None:
        linked = _linked([
            _played(1, 972, 1, 10, 1, 0, "1", datetime(2026, 6, 20)),
            _played(2, 972, 50, 51, 1, 0, "1", datetime(2026, 6, 1)),
            _played(3, 971, 1, 2, 2, 0, "1", datetime(2026, 7, 1)),
            _played(4, 971, 3, 4, 1, 0, "1", datetime(2026, 7, 2)),
            _played(5, 970, 1, 3, 1, 0, "1", datetime(2026, 7, 10))])
        self.assertEqual(
            [tie.tie_id for tie in order_ties(linked)],
            [
                "cup-4-1-10",
                "cup-4-50-51",
                "cup-2-1-2",
                "cup-2-3-4",
                "cup-1-1-3"])

    def test_without_a_final_columns_follow_the_date(self) -> None:
        linked = _linked([
            _played(1, 971, 1, 2, 1, 0, "1", datetime(2026, 7, 2)),
            _played(9, 971, 3, 4, 1, 0, "1", datetime(2026, 7, 1))])
        self.assertEqual(
            [tie.tie_id for tie in order_ties(linked)],
            ["cup-2-3-4", "cup-2-1-2"])

    def test_empty_input(self) -> None:
        self.assertEqual(order_ties([]), [])


def _placeholder(team_id: int, depth: int = 8) -> BracketTie:
    """A seeded card whose opponent has not been drawn."""
    return BracketTie(
        tie_id=f"cup-{depth}-{team_id}-pending",
        family="cup",
        depth=depth,
        stage_label=stage_label(depth),
        matches=[],
        team_ids=(team_id,),
        pending_opponent_label="Zwycięzca barażu",
        seed_position=1)


def _with_feeder(
        ties: list[BracketTie],
        tie_id: str,
        feeder_id: str) -> list[BracketTie]:
    """Point one tie at an extra feeder without editing the original."""
    planted: list[BracketTie] = []
    for tie in ties:
        if tie.tie_id != tie_id:
            planted.append(tie)
            continue
        planted.append(replace(
            tie,
            feeder_tie_ids=tie.feeder_tie_ids + (feeder_id,)))
    return planted


def _seeds() -> list[SeededTeam]:
    """Places 1–8 in shuffled order, plus a row the profile ignores.

    Team ids run backwards from the place, so a sort by team id is
    not a sort by the table.
    """
    places = (4, 1, 8, 2, 7, 3, 6, 5, 9)
    return [
        SeededTeam(team_id=310 - place, position=place)
        for place in places]


if __name__ == "__main__":
    unittest.main()
