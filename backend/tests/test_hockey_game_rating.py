"""Unit tests for hockey skater and goalie game ratings."""

from __future__ import annotations

import unittest
from decimal import Decimal

import pandas as pd

from backend.sports.hockey.game_rating import BLOCK_AVERAGE_DEFENSE
from backend.sports.hockey.game_rating import BLOCK_AVERAGE_FORWARD
from backend.sports.hockey.game_rating import GOAL_EVENT_ID
from backend.sports.hockey.game_rating import MAJOR_PENALTY_EVENT_ID
from backend.sports.hockey.game_rating import MINOR_PENALTY_EVENT_ID
from backend.sports.hockey.game_rating import RatingParts
from backend.sports.hockey.game_rating import SkaterCounts
from backend.sports.hockey.game_rating import attribute_events
from backend.sports.hockey.game_rating import normalize
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


HOME_TEAM_ID = 10
AWAY_TEAM_ID = 20


def _player(
    player_id: int,
    player_name: str,
    team_id: int = HOME_TEAM_ID,
    goals: int = 0,
    assists: int = 0) -> dict[str, object]:
    """Build one player row. The name column is the common name."""
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "goals": goals,
        "assists": assists
    }


def _event(
    player_id: int,
    event_id: int,
    team_id: int = HOME_TEAM_ID,
    description: str | None = None,
    pp_flag: int = 0,
    en_flag: int = 0) -> dict[str, object]:
    """Build one play-by-play row."""
    return {
        "event_id": event_id,
        "player_id": player_id,
        "team_id": team_id,
        "pp_flag": pp_flag,
        "en_flag": en_flag,
        "description": description
    }


class TestHockeyEventCredits(unittest.TestCase):
    """attribute_events reads goals, assists and penalties."""

    def test_event_ids_are_goal_minor_and_major(self) -> None:
        self.assertEqual(GOAL_EVENT_ID, 181)
        self.assertEqual(MINOR_PENALTY_EVENT_ID, 183)
        self.assertEqual(MAJOR_PENALTY_EVENT_ID, 185)

    def test_normalize_matches_a_name_without_diacritics(self) -> None:
        self.assertEqual(normalize("Stützle T."), normalize("Stutzle T."))

    def test_assist_matches_stutzle_without_diacritics(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Stützle T.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Stutzle T.")
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[2].es_points, 1)
        self.assertEqual(credits[1].es_points, 1)
        self.assertEqual(credits[1].empty_net_goals, 0)

    def test_power_play_goal_adds_no_even_strength_points(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Sanderson J."),
            _player(3, "Halliday S.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Sanderson J. + Halliday S., W przewadze",
                pp_flag=1,
                en_flag=0)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[1].empty_net_goals, 0)
        self.assertEqual(credits[2].es_points, 0)
        self.assertEqual(credits[3].es_points, 0)

    def test_empty_net_goal_credits_scorer_and_assists(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Armia J."),
            _player(3, "Haula E.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Armia J. + Haula E., Do pustej bramki",
                pp_flag=0,
                en_flag=1)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].empty_net_goals, 1)
        self.assertEqual(credits[1].es_points, 1)
        self.assertEqual(credits[2].es_points, 1)
        self.assertEqual(credits[2].empty_net_goals, 0)
        self.assertEqual(credits[3].es_points, 1)
        self.assertEqual(credits[3].empty_net_goals, 0)

    def test_empty_net_still_counts_on_a_power_play_goal(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Assist A.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Assist A.",
                pp_flag=1,
                en_flag=1)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].empty_net_goals, 1)
        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[2].es_points, 0)

    def test_unmatched_and_ambiguous_assists_are_skipped(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Twin T."),
            _player(3, "Twin T."),
            _player(4, "Away A.", team_id=AWAY_TEAM_ID),
            _player(5, "Real R.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Nobody N. + Twin T. + Away A. + Real R.")
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].es_points, 1)
        self.assertEqual(credits[2].es_points, 0)
        self.assertEqual(credits[3].es_points, 0)
        self.assertEqual(credits[4].es_points, 0)
        self.assertEqual(credits[5].es_points, 1)

    def test_same_player_is_credited_once_per_goal(self) -> None:
        players = pd.DataFrame([
            _player(1, "Scorer S."),
            _player(2, "Haula E.")
        ])
        events = pd.DataFrame([
            _event(
                player_id=1,
                event_id=181,
                description="Haula E. + Haula E.")
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[2].es_points, 1)

    def test_missing_goal_events_use_box_score_points(self) -> None:
        players = pd.DataFrame([
            _player(1, "Assist A.", assists=2),
            _player(2, "Quiet Q.", goals=1, assists=1)
        ])

        credits = attribute_events(players, pd.DataFrame())

        self.assertEqual(credits[1].es_points, 2)
        self.assertEqual(credits[1].empty_net_goals, 0)
        self.assertEqual(credits[1].minor_penalties, 0)
        self.assertEqual(credits[2].es_points, 2)
        self.assertEqual(credits[2].empty_net_goals, 0)

    def test_one_goal_event_disables_box_score_fallback(self) -> None:
        players = pd.DataFrame([
            _player(1, "Assist A.", assists=2),
            _player(2, "Scorer S.", goals=1)
        ])
        events = pd.DataFrame([
            _event(player_id=2, event_id=181, description=None),
            _event(player_id=1, event_id=183)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[1].minor_penalties, 1)
        self.assertEqual(credits[2].es_points, 1)
        self.assertEqual(credits[2].empty_net_goals, 0)

    def test_penalties_are_counted_from_events_not_minutes(self) -> None:
        players = pd.DataFrame([_player(1, "Penal P.")])
        events = pd.DataFrame([
            _event(player_id=1, event_id=183),
            _event(player_id=1, event_id=183),
            _event(player_id=1, event_id=185),
            _event(player_id=1, event_id=184),
            _event(player_id=1, event_id=186),
            _event(player_id=1, event_id=187),
            _event(player_id=1, event_id=188),
            _event(player_id=1, event_id=189)
        ])

        credits = attribute_events(players, events)

        self.assertEqual(credits[1].minor_penalties, 2)
        self.assertEqual(credits[1].major_penalties, 1)
        self.assertEqual(credits[1].es_points, 0)
        self.assertEqual(credits[1].empty_net_goals, 0)


if __name__ == "__main__":
    unittest.main()
