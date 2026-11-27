"""Unit tests for knockout ties, football scores and series wins."""

from __future__ import annotations

import unittest
from datetime import datetime

from backend.services.knockout_stages import stage_label
from backend.services.knockout_ties import BASKETBALL_SPORT_ID
from backend.services.knockout_ties import FOOTBALL_SPORT_ID
from backend.services.knockout_ties import HOCKEY_SPORT_ID
from backend.services.knockout_ties import THIRD_PLACE_LABEL
from backend.services.knockout_ties import BracketTie
from backend.services.knockout_ties import GroupedTies
from backend.services.knockout_ties import TieMatch
from backend.services.knockout_ties import football_match_winner
from backend.services.knockout_ties import group_ties
from backend.services.knockout_ties import hockey_match_winner
from backend.services.knockout_ties import resolve_score_winner
from backend.services.knockout_ties import tie_with_score


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


def _played(
        match_id: int,
        round_number: int,
        home_team_id: int,
        away_team_id: int,
        home_goals: int | None,
        away_goals: int | None,
        result: str | None,
        game_date: datetime | None = None,
        home_extra_time_goals: int | None = None,
        away_extra_time_goals: int | None = None,
        home_penalty_goals: int | None = None,
        away_penalty_goals: int | None = None,
        ot_winner: int | None = None,
        so_winner: int | None = None) -> TieMatch:
    """Build a match whose score the winner rules can read."""
    played = (
        result not in (None, "", "0")
        and home_goals is not None
        and away_goals is not None)
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
        is_played=played,
        home_extra_time_goals=home_extra_time_goals,
        away_extra_time_goals=away_extra_time_goals,
        home_penalty_goals=home_penalty_goals,
        away_penalty_goals=away_penalty_goals,
        ot_winner=ot_winner,
        so_winner=so_winner)


def _one_tie(matches: list[TieMatch]) -> BracketTie:
    """Return the single tree tie grouped from these matches."""
    grouped = group_ties(matches)
    assert len(grouped.ties) == 1
    assert grouped.third_place == []
    return grouped.ties[0]


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


class TestFootballScore(unittest.TestCase):
    """Winner of one football match and of a two-legged tie."""

    def test_extra_time_breaks_a_scoreless_final(self) -> None:
        match = _played(
            1, 970, 10, 20, 0, 0, "X",
            datetime(2026, 7, 19),
            home_extra_time_goals=1,
            away_extra_time_goals=0)
        original = _one_tie([match])
        scored = tie_with_score(original, FOOTBALL_SPORT_ID)
        self.assertEqual(football_match_winner(match), 10)
        self.assertEqual(
            resolve_score_winner(original, FOOTBALL_SPORT_ID), 10)
        self.assertEqual(scored.score_winner_team_id, 10)
        self.assertEqual(scored.matches[0].decided_by, "extra_time")
        self.assertIsNone(scored.aggregate_by_team)
        self.assertIsNone(scored.advanced_team_id)
        self.assertIsNone(original.score_winner_team_id)
        self.assertIsNone(original.matches[0].decided_by)

    def test_penalties_break_a_draw_after_extra_time(self) -> None:
        match = _played(
            1, 970, 10, 20, 1, 1, "X",
            home_extra_time_goals=1,
            away_extra_time_goals=1,
            home_penalty_goals=4,
            away_penalty_goals=3)
        self.assertEqual(football_match_winner(match), 10)
        scored = tie_with_score(_one_tie([match]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.score_winner_team_id, 10)
        self.assertEqual(scored.matches[0].decided_by, "penalties")
        self.assertIsNone(scored.aggregate_by_team)

    def test_two_legged_sum_excludes_penalties(self) -> None:
        first = _played(
            1, 971, 10, 20, 0, 0, "X",
            datetime(2026, 5, 1))
        second = _played(
            2, 971, 20, 10, 0, 0, "X",
            datetime(2026, 5, 8),
            home_extra_time_goals=0,
            away_extra_time_goals=0,
            home_penalty_goals=4,
            away_penalty_goals=3)
        scored = tie_with_score(
            _one_tie([second, first]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.aggregate_by_team, {10: 0, 20: 0})
        self.assertEqual(scored.score_winner_team_id, 20)
        self.assertEqual(
            resolve_score_winner(scored, FOOTBALL_SPORT_ID), 20)
        self.assertEqual(
            [match.decided_by for match in scored.matches],
            [None, "penalties"])
        self.assertIsNone(scored.series_wins_by_team)

    def test_level_two_legs_advance_on_penalties(self) -> None:
        # Z perspektywy gospodarza pierwszego meczu: 1:0 i 0:1.
        first = _played(
            1, 971, 10, 20, 1, 0, "1",
            datetime(2026, 5, 1))
        second = _played(
            2, 971, 20, 10, 1, 0, "1",
            datetime(2026, 5, 8),
            home_penalty_goals=5,
            away_penalty_goals=4)
        scored = tie_with_score(
            _one_tie([first, second]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.aggregate_by_team, {10: 1, 20: 1})
        self.assertEqual(scored.score_winner_team_id, 20)
        self.assertEqual(
            [match.decided_by for match in scored.matches],
            ["regulation", "penalties"])
        self.assertNotIn(5, scored.aggregate_by_team.values())

    def test_extra_time_replaces_regulation_in_the_sum(self) -> None:
        first = _played(
            1, 971, 10, 20, 1, 0, "1",
            datetime(2026, 5, 1))
        second = _played(
            2, 971, 20, 10, 1, 0, "1",
            datetime(2026, 5, 8),
            home_extra_time_goals=1,
            away_extra_time_goals=2)
        scored = tie_with_score(
            _one_tie([first, second]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.aggregate_by_team, {10: 3, 20: 1})
        self.assertEqual(scored.score_winner_team_id, 10)
        self.assertEqual(scored.matches[1].decided_by, "extra_time")

    def test_higher_aggregate_ignores_the_shootout(self) -> None:
        first = _played(
            1, 971, 10, 20, 2, 0, "1",
            datetime(2026, 5, 1))
        second = _played(
            2, 971, 20, 10, 0, 0, "X",
            datetime(2026, 5, 8),
            home_penalty_goals=5,
            away_penalty_goals=3)
        scored = tie_with_score(
            _one_tie([first, second]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.aggregate_by_team, {10: 2, 20: 0})
        self.assertEqual(scored.score_winner_team_id, 10)

    def test_level_two_legs_without_penalties_have_no_winner(self) -> None:
        # Z perspektywy gospodarza pierwszego meczu: 1:0 i 0:1.
        first = _played(
            1, 971, 10, 20, 1, 0, "1",
            datetime(2026, 5, 1))
        second = _played(
            2, 971, 20, 10, 1, 0, "1",
            datetime(2026, 5, 8))
        scored = tie_with_score(
            _one_tie([first, second]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.aggregate_by_team, {10: 1, 20: 1})
        self.assertIsNone(scored.score_winner_team_id)
        self.assertIsNone(
            resolve_score_winner(scored, FOOTBALL_SPORT_ID))

    def test_unplayed_leg_leaves_the_pair_undecided(self) -> None:
        first = _played(
            1, 971, 10, 20, 2, 0, "1",
            datetime(2026, 5, 1))
        open_return = _played(
            2, 971, 20, 10, None, None, "0",
            datetime(2026, 5, 8))
        scored = tie_with_score(
            _one_tie([first, open_return]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.aggregate_by_team, {10: 2, 20: 0})
        self.assertIsNone(scored.score_winner_team_id)
        self.assertIsNone(
            resolve_score_winner(scored, FOOTBALL_SPORT_ID))
        # Result "0" zostaje nierozgrany także z wpisanymi bramkami.
        stray = _played(
            3, 971, 20, 10, 1, 0, "0",
            datetime(2026, 5, 8))
        with_stray = tie_with_score(
            _one_tie([first, stray]), FOOTBALL_SPORT_ID)
        self.assertEqual(with_stray.aggregate_by_team, {10: 2, 20: 0})
        self.assertIsNone(with_stray.score_winner_team_id)

    def test_unplayed_and_level_score_have_no_winner(self) -> None:
        cases = (
            _played(1, 970, 10, 20, 1, 0, "0"),
            _played(2, 970, 10, 20, 1, 0, None),
            _played(3, 970, 10, 20, 1, 0, ""),
            _played(4, 970, 10, 20, None, None, "1"),
            _played(5, 970, 10, 20, 1, 1, "X"))
        for match in cases:
            with self.subTest(match_id=match.match_id, result=match.result):
                self.assertIsNone(football_match_winner(match))
                scored = tie_with_score(
                    _one_tie([match]), FOOTBALL_SPORT_ID)
                self.assertIsNone(scored.score_winner_team_id)
                self.assertIsNone(scored.matches[0].decided_by)

    def test_regulation_goals_outrank_the_result_code(self) -> None:
        split = _played(1, 970, 10, 20, 2, 1, "2")
        self.assertEqual(football_match_winner(split), 10)
        scored = tie_with_score(_one_tie([split]), FOOTBALL_SPORT_ID)
        self.assertEqual(scored.matches[0].decided_by, "regulation")
        level = _played(2, 970, 10, 20, 0, 0, "2")
        self.assertEqual(football_match_winner(level), 20)
        level_scored = tie_with_score(
            _one_tie([level]), FOOTBALL_SPORT_ID)
        self.assertEqual(level_scored.matches[0].decided_by, "regulation")

    def test_other_sport_stays_unscored(self) -> None:
        # Sport spoza piłki, hokeja i koszykówki nie ma gałęzi wyniku.
        other_sport_id = 9
        match = _played(1, 970, 10, 20, 2, 1, "1")
        original = _one_tie([match])
        self.assertIsNone(resolve_score_winner(original, other_sport_id))
        self.assertIs(tie_with_score(original, other_sport_id), original)


class TestSeriesScore(unittest.TestCase):
    """Win counts for a hockey or basketball series."""

    def test_overtime_draw_counts_as_a_home_win(self) -> None:
        # Remis 3:3 z OTwinner 1 jest punktem gospodarza, nie remisem.
        match = _played(1, 960, 10, 20, 3, 3, "X", ot_winner=1)
        self.assertEqual(hockey_match_winner(match), 10)
        scored = tie_with_score(_one_tie([match]), HOCKEY_SPORT_ID)
        self.assertEqual(scored.series_wins_by_team, {10: 1, 20: 0})
        self.assertEqual(scored.matches[0].decided_by, "overtime")
        self.assertIsNone(scored.score_winner_team_id)
        self.assertIsNone(scored.aggregate_by_team)

    def test_hockey_series_clinches_at_four_wins(self) -> None:
        games = [
            _played(1, 960, 10, 20, 3, 3, "X", ot_winner=1),
            _played(2, 961, 10, 20, 2, 1, "1"),
            _played(3, 962, 20, 10, 4, 2, "1"),
            _played(4, 963, 10, 20, 1, 0, "1"),
            _played(5, 964, 20, 10, 3, 1, "1"),
            _played(6, 965, 10, 20, 3, 1, "1")]
        original = _one_tie(games)
        scored = tie_with_score(original, HOCKEY_SPORT_ID)
        self.assertEqual(hockey_match_winner(games[0]), 10)
        self.assertEqual(scored.series_wins_by_team, {10: 4, 20: 2})
        self.assertEqual(scored.score_winner_team_id, 10)
        self.assertEqual(
            resolve_score_winner(original, HOCKEY_SPORT_ID), 10)
        self.assertEqual(scored.matches[0].decided_by, "overtime")
        self.assertEqual(scored.matches[1].decided_by, "regulation")
        self.assertIsNone(scored.aggregate_by_team)
        self.assertIsNone(scored.advanced_team_id)
        self.assertIsNone(original.series_wins_by_team)
        self.assertIsNone(original.score_winner_team_id)
        self.assertIsNone(original.matches[0].decided_by)

    def test_series_below_four_wins_has_no_score_winner(self) -> None:
        games = [
            _played(1, 960, 10, 20, 3, 3, "X", ot_winner=1),
            _played(2, 961, 10, 20, 2, 3, "2"),
            _played(3, 962, 10, 20, 1, 0, "1"),
            _played(4, 963, 10, 20, 1, 2, "2")]
        original = _one_tie(games)
        scored = tie_with_score(original, HOCKEY_SPORT_ID)
        self.assertEqual(scored.series_wins_by_team, {10: 2, 20: 2})
        self.assertIsNone(scored.score_winner_team_id)
        self.assertIsNone(
            resolve_score_winner(original, HOCKEY_SPORT_ID))
        self.assertIsNone(scored.advanced_team_id)

    def test_shootout_names_the_winner_of_a_draw(self) -> None:
        match = _played(
            1, 960, 10, 20, 2, 2, "X",
            ot_winner=3,
            so_winner=2)
        self.assertEqual(hockey_match_winner(match), 20)
        scored = tie_with_score(_one_tie([match]), HOCKEY_SPORT_ID)
        self.assertEqual(scored.series_wins_by_team, {10: 0, 20: 1})
        self.assertEqual(scored.matches[0].decided_by, "shootout")
        self.assertIsNone(scored.score_winner_team_id)

    def test_shootout_side_outranks_overtime_side(self) -> None:
        # Przy obu kodach wygrywa karna, bo jest późniejsza.
        match = _played(
            1, 960, 10, 20, 3, 3, "X",
            ot_winner=1,
            so_winner=2)
        self.assertEqual(hockey_match_winner(match), 20)
        scored = tie_with_score(_one_tie([match]), HOCKEY_SPORT_ID)
        self.assertEqual(scored.matches[0].decided_by, "shootout")

    def test_draw_without_a_side_code_has_no_winner(self) -> None:
        match = _played(
            1, 960, 10, 20, 3, 3, "X",
            ot_winner=3,
            so_winner=0)
        self.assertIsNone(hockey_match_winner(match))
        scored = tie_with_score(_one_tie([match]), HOCKEY_SPORT_ID)
        self.assertIsNone(scored.series_wins_by_team)
        self.assertIsNone(scored.score_winner_team_id)

    def test_unplayed_hockey_game_does_not_count(self) -> None:
        match = _played(1, 960, 10, 20, 3, 2, "0")
        scored = tie_with_score(_one_tie([match]), HOCKEY_SPORT_ID)
        self.assertIsNone(hockey_match_winner(match))
        self.assertIsNone(scored.series_wins_by_team)
        self.assertIsNone(scored.score_winner_team_id)
        self.assertIsNone(scored.matches[0].decided_by)

    def test_basketball_uses_only_the_result_code(self) -> None:
        draw = _played(1, 960, 10, 20, 100, 100, "X", ot_winner=1)
        away = _played(2, 961, 10, 20, 98, 110, "2")
        self.assertEqual(hockey_match_winner(draw), 10)
        scored = tie_with_score(
            _one_tie([draw, away]), BASKETBALL_SPORT_ID)
        self.assertEqual(scored.series_wins_by_team, {10: 0, 20: 1})
        self.assertIsNone(scored.score_winner_team_id)
        self.assertEqual(
            [match.decided_by for match in scored.matches],
            [None, "regulation"])
        self.assertIsNone(scored.aggregate_by_team)

    def test_basketball_clinches_at_four_wins(self) -> None:
        games = [
            _played(index, 959 + index, 10, 20, 100, 90, "1")
            for index in range(1, 5)]
        scored = tie_with_score(_one_tie(games), BASKETBALL_SPORT_ID)
        self.assertEqual(scored.series_wins_by_team, {10: 4, 20: 0})
        self.assertEqual(scored.score_winner_team_id, 10)
        self.assertEqual(
            resolve_score_winner(scored, BASKETBALL_SPORT_ID), 10)


if __name__ == "__main__":
    unittest.main()
