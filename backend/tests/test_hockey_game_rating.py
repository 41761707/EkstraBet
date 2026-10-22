"""Unit tests for hockey skater and goalie game ratings."""

from __future__ import annotations

import unittest
from decimal import Decimal

from backend.sports.hockey.game_rating import BLOCK_AVERAGE_DEFENSE
from backend.sports.hockey.game_rating import BLOCK_AVERAGE_FORWARD
from backend.sports.hockey.game_rating import RatingParts
from backend.sports.hockey.game_rating import SkaterCounts
from backend.sports.hockey.game_rating import rate_goalie
from backend.sports.hockey.game_rating import rate_skater


def _counts(
    goals: int = 0,
    assists: int = 0,
    es_points: int = 0,
    empty_net_goals: int = 0,
    shots_on_goal: int = 0,
    plus_minus: int | None = 0,
    minor_penalties: int = 0,
    major_penalties: int = 0,
    blocked: int = 0,
    block_average: float = BLOCK_AVERAGE_FORWARD,
    faceoffs_taken: int = 0,
    faceoffs_won: int = 0) -> SkaterCounts:
    """Build skater counters, with untouched stats left neutral."""
    return SkaterCounts(
        goals=goals,
        assists=assists,
        es_points=es_points,
        empty_net_goals=empty_net_goals,
        shots_on_goal=shots_on_goal,
        plus_minus=plus_minus,
        minor_penalties=minor_penalties,
        major_penalties=major_penalties,
        blocked=blocked,
        block_average=block_average,
        faceoffs_taken=faceoffs_taken,
        faceoffs_won=faceoffs_won)


class TestHockeySkaterRating(unittest.TestCase):
    """Cases that rate_skater can score from counters alone."""

    def _assert_score(
        self,
        parts: RatingParts,
        offense: str,
        defense: str,
        total: str) -> None:
        """Check the three sums and that goaltending stayed zero."""
        self.assertEqual(parts.offense, Decimal(offense))
        self.assertEqual(parts.defense, Decimal(defense))
        self.assertEqual(parts.total, Decimal(total))
        self.assertEqual(parts.offense + parts.defense, parts.total)
        self.assertEqual(parts.goaltending, Decimal("0.0"))

    def test_even_strength_three_points_and_plus_three_score_3_2(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            assists=2,
            es_points=3,
            shots_on_goal=4,
            plus_minus=3))
        self._assert_score(parts, "3.2", "0.0", "3.2")
        self.assertEqual(parts.production, Decimal("3.0"))
        self.assertEqual(parts.shots, Decimal("0.2"))
        self.assertEqual(format(parts.empty_net, "f"), "0.0")
        self.assertEqual(format(parts.penalties, "f"), "0.0")
        self.assertEqual(format(parts.goals_against, "f"), "0.0")
        self.assertEqual(format(parts.blocks, "f"), "0.0")

    def test_even_strength_three_points_and_minus_one_score_1_8(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            assists=2,
            es_points=3,
            shots_on_goal=4,
            plus_minus=-1))
        self._assert_score(parts, "3.2", "-1.4", "1.8")
        self.assertEqual(parts.production, Decimal("3.0"))
        self.assertEqual(parts.shots, Decimal("0.2"))
        self.assertEqual(parts.goals_against, Decimal("-1.4"))

    def test_quiet_defender_scores_shots_teammates_and_blocks(self) -> None:
        parts = rate_skater(_counts(
            shots_on_goal=1,
            plus_minus=2,
            blocked=4,
            block_average=BLOCK_AVERAGE_DEFENSE))
        self._assert_score(parts, "0.5", "0.1", "0.6")
        self.assertEqual(parts.shots, Decimal("0.1"))
        self.assertEqual(parts.teammate_goals, Decimal("0.4"))
        self.assertEqual(parts.blocks, Decimal("0.1"))

    def test_two_minors_and_minus_three_score_minus_1_4(self) -> None:
        parts = rate_skater(_counts(
            plus_minus=-3,
            minor_penalties=2))
        self._assert_score(parts, "0.0", "-1.4", "-1.4")
        self.assertEqual(parts.goals_against, Decimal("-1.1"))
        self.assertEqual(parts.penalties, Decimal("-0.3"))

    def test_one_minor_rounds_half_up(self) -> None:
        parts = rate_skater(_counts(minor_penalties=1))
        self.assertEqual(parts.penalties, Decimal("-0.2"))
        self._assert_score(parts, "0.0", "-0.2", "-0.2")

    def test_minor_plus_major_round_as_one_leaf(self) -> None:
        parts = rate_skater(_counts(
            minor_penalties=1,
            major_penalties=1))
        self.assertEqual(parts.penalties, Decimal("-0.5"))
        self._assert_score(parts, "0.0", "-0.5", "-0.5")

    def test_faceoffs_ten_of_fourteen_round_to_one_tenth(self) -> None:
        parts = rate_skater(_counts(
            faceoffs_taken=14,
            faceoffs_won=10))
        self.assertEqual(parts.faceoffs, Decimal("0.1"))
        self._assert_score(parts, "0.1", "0.0", "0.1")

    def test_missing_plus_minus_keeps_ice_at_zero(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            es_points=1,
            plus_minus=None))
        self._assert_score(parts, "1.0", "0.0", "1.0")
        self.assertEqual(parts.production, Decimal("1.0"))
        self.assertEqual(parts.teammate_goals, Decimal("0.0"))
        self.assertEqual(parts.goals_against, Decimal("0.0"))

    def test_power_play_goal_does_not_count_as_a_goal_against(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            es_points=0,
            shots_on_goal=3,
            plus_minus=0))
        self._assert_score(parts, "1.1", "0.0", "1.1")
        self.assertEqual(parts.production, Decimal("1.0"))
        self.assertEqual(parts.shots, Decimal("0.1"))
        self.assertEqual(parts.goals_against, Decimal("0.0"))

    def test_empty_net_goal_trims_the_goal(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            es_points=1,
            empty_net_goals=1,
            shots_on_goal=1,
            plus_minus=1))
        self._assert_score(parts, "0.7", "0.0", "0.7")
        self.assertEqual(parts.production, Decimal("1.0"))
        self.assertEqual(parts.empty_net, Decimal("-0.3"))

    def test_power_play_assist_stays_out_of_even_strength_ice(self) -> None:
        parts = rate_skater(_counts(
            goals=1,
            assists=1,
            es_points=1,
            shots_on_goal=1,
            plus_minus=1))
        self._assert_score(parts, "2.0", "0.0", "2.0")
        self.assertEqual(parts.production, Decimal("2.0"))
        self.assertEqual(parts.shots, Decimal("0.0"))
        self.assertEqual(parts.goals_against, Decimal("0.0"))

    def test_zero_blocks_follow_the_position_average(self) -> None:
        forward = rate_skater(_counts(
            blocked=0,
            block_average=BLOCK_AVERAGE_FORWARD))
        defense = rate_skater(_counts(
            blocked=0,
            block_average=BLOCK_AVERAGE_DEFENSE))
        self.assertEqual(forward.blocks, Decimal("0.0"))
        self.assertEqual(defense.blocks, Decimal("-0.1"))


class TestHockeyGoalieRating(unittest.TestCase):
    """rate_goalie scores saves above a season rate and nothing else."""

    def test_shutout_on_thirty_shots_scores_2_8(self) -> None:
        self.assertEqual(rate_goalie(30, 30, 0.907), 2.8)

    def test_twenty_three_saves_on_twenty_eight_shots_score_minus_2_4(
        self) -> None:
        self.assertEqual(rate_goalie(28, 23, 0.907), -2.4)

    def test_missing_shots_against_score_zero(self) -> None:
        self.assertEqual(rate_goalie(None, 30, 0.907), 0.0)

    def test_zero_shots_against_score_zero(self) -> None:
        self.assertEqual(rate_goalie(0, 0, 0.907), 0.0)

    def test_missing_saves_use_the_rounded_negative_expectation(self) -> None:
        # -0.907 * 10 = -9.07, czyli -9.1 po tym samym zaokrągleniu.
        self.assertEqual(rate_goalie(10, None, 0.907), -9.1)


if __name__ == "__main__":
    unittest.main()
