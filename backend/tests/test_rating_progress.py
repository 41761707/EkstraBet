"""Integration tests for football rating-progress extraction."""

from __future__ import annotations

import unittest
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch

import pandas as pd

from backend.sports.football import rating_progress as progress
from models.pipeline.features.ratings import compute_ratings_timeline


def _match(
        *,
        match_id: int,
        league: int,
        season: int,
        home_team: int,
        away_team: int,
        game_date: datetime,
        home_goals: int,
        away_goals: int,
        round_number: int = 1,
        result: str | None = None,
        tier: int = 1) -> dict[str, object]:
    if result is None:
        if home_goals > away_goals:
            result = "1"
        elif home_goals < away_goals:
            result = "2"
        else:
            result = "X"
    return {
        "id": match_id,
        "league": league,
        "season": season,
        "round": round_number,
        "game_date": game_date,
        "home_team": home_team,
        "away_team": away_team,
        "home_team_goals": home_goals,
        "away_team_goals": away_goals,
        "result": result,
        "sport_id": 1,
        "tier": tier
    }


def _participants(*teams: tuple[int, str, str | None]) -> pd.DataFrame:
    rows = [{
        "team_id": team_id,
        "team_name": name,
        "team_shortcut": shortcut
    } for team_id, name, shortcut in teams]
    return pd.DataFrame(rows)


class TestExtractTeamProgress(unittest.TestCase):
    """Verify extraction against real compute_ratings_timeline values."""

    def test_start_is_first_pre_points_are_post_and_match_timeline(
            self) -> None:
        day = datetime(2025, 8, 1)
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=day,
                home_goals=2,
                away_goals=0,
                round_number=1),
            _match(
                match_id=2,
                league=10,
                season=100,
                home_team=2,
                away_team=1,
                game_date=day + timedelta(days=7),
                home_goals=1,
                away_goals=1,
                round_number=2)
        ])
        timeline = compute_ratings_timeline(matches)
        participants = _participants(
            (1, "Alpha", "ALP"),
            (2, "Beta", "BET"))

        teams = progress.extract_team_progress(
            timeline, 10, 100, participants, metric="elo")

        self.assertEqual(len(teams), 2)
        by_id = {team.team_id: team for team in teams}
        alpha = by_id[1]
        self.assertEqual(alpha.start_rating, timeline.loc[0, "home_elo"])
        self.assertEqual(
            [point.rating for point in alpha.points],
            [
                float(timeline.loc[0, "home_elo_post"]),
                float(timeline.loc[1, "away_elo_post"])
            ])
        self.assertEqual(alpha.current_rating, alpha.points[-1].rating)
        self.assertEqual(
            alpha.change,
            alpha.current_rating - alpha.start_rating)
        self.assertEqual(alpha.points[0].match_id, 1)
        self.assertEqual(alpha.points[0].round_number, 1)
        self.assertEqual(alpha.points[1].match_id, 2)
        self.assertEqual(alpha.points[1].round_number, 2)

    def test_same_date_batching_uses_shared_pre_match_state(self) -> None:
        day = datetime(2025, 8, 10)
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=day,
                home_goals=3,
                away_goals=0),
            _match(
                match_id=2,
                league=10,
                season=100,
                home_team=3,
                away_team=4,
                game_date=day,
                home_goals=1,
                away_goals=0)
        ])
        timeline = compute_ratings_timeline(matches)
        # Oba mecze tego samego dnia startują od bazowego ELO.
        self.assertEqual(timeline.loc[0, "home_elo"], 1500.0)
        self.assertEqual(timeline.loc[1, "home_elo"], 1500.0)
        participants = _participants(
            (1, "A", "A"),
            (2, "B", "B"),
            (3, "C", "C"),
            (4, "D", "D"))

        teams = progress.extract_team_progress(
            timeline, 10, 100, participants)

        starts = {team.team_id: team.start_rating for team in teams}
        self.assertEqual(starts[1], 1500.0)
        self.assertEqual(starts[3], 1500.0)
        self.assertGreater(starts[1], 0)
        # Post po wygranej 3:0 różni się od post po 1:0.
        by_id = {team.team_id: team for team in teams}
        self.assertNotEqual(
            by_id[1].points[0].rating,
            by_id[3].points[0].rating)

    def test_warmup_from_other_season_affects_start_only(self) -> None:
        day = datetime(2024, 5, 1)
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=99,
                home_team=1,
                away_team=2,
                game_date=day,
                home_goals=2,
                away_goals=0,
                round_number=30),
            _match(
                match_id=2,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=day + timedelta(days=100),
                home_goals=1,
                away_goals=0,
                round_number=1)
        ])
        timeline = compute_ratings_timeline(matches)
        participants = _participants(
            (1, "Alpha", "ALP"),
            (2, "Beta", "BET"))

        teams = progress.extract_team_progress(
            timeline, 10, 100, participants)

        by_id = {team.team_id: team for team in teams}
        target_row = timeline.loc[timeline["id"] == 2].iloc[0]
        self.assertEqual(by_id[1].start_rating, float(target_row["home_elo"]))
        self.assertGreater(by_id[1].start_rating, 1500.0)
        self.assertEqual(len(by_id[1].points), 1)
        self.assertEqual(by_id[1].points[0].match_id, 2)
        # Mecze rozgrzewki nie trafiają do punktów sezonu docelowego.
        all_match_ids = {
            point.match_id
            for team in teams
            for point in team.points
        }
        self.assertEqual(all_match_ids, {2})

    def test_promotion_keeps_rating_from_lower_league(self) -> None:
        day = datetime(2024, 6, 1)
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=20,
                season=50,
                home_team=5,
                away_team=6,
                game_date=day,
                home_goals=4,
                away_goals=0,
                tier=2),
            _match(
                match_id=2,
                league=10,
                season=100,
                home_team=5,
                away_team=7,
                game_date=day + timedelta(days=90),
                home_goals=0,
                away_goals=0,
                tier=1)
        ])
        timeline = compute_ratings_timeline(matches)
        participants = _participants(
            (5, "Promoted", "PRO"),
            (7, "TopSide", "TOP"))

        teams = progress.extract_team_progress(
            timeline, 10, 100, participants)

        by_id = {team.team_id: team for team in teams}
        target_row = timeline.loc[timeline["id"] == 2].iloc[0]
        self.assertEqual(
            by_id[5].start_rating,
            float(target_row["home_elo"]))
        self.assertGreater(by_id[5].start_rating, 1500.0)
        self.assertEqual(by_id[7].start_rating, 1500.0)

    def test_filters_out_other_league_and_season_matches(self) -> None:
        day = datetime(2025, 8, 1)
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=day,
                home_goals=1,
                away_goals=0),
            _match(
                match_id=2,
                league=11,
                season=100,
                home_team=1,
                away_team=3,
                game_date=day + timedelta(days=1),
                home_goals=2,
                away_goals=0),
            _match(
                match_id=3,
                league=10,
                season=101,
                home_team=1,
                away_team=2,
                game_date=day + timedelta(days=2),
                home_goals=3,
                away_goals=0)
        ])
        timeline = compute_ratings_timeline(matches)
        participants = _participants(
            (1, "Alpha", "ALP"),
            (2, "Beta", "BET"))

        teams = progress.extract_team_progress(
            timeline, 10, 100, participants)

        by_id = {team.team_id: team for team in teams}
        self.assertEqual(
            [point.match_id for point in by_id[1].points],
            [1])

    def test_ranks_by_current_rating_descending(self) -> None:
        day = datetime(2025, 8, 1)
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=day,
                home_goals=5,
                away_goals=0)
        ])
        participants = _participants(
            (1, "Winner", "WIN"),
            (2, "Loser", "LOS"))

        teams = progress.compute_team_rating_progress(
            matches, 10, 100, participants)

        self.assertEqual(teams[0].team_id, 1)
        self.assertEqual(teams[0].current_rank, 1)
        self.assertEqual(teams[1].team_id, 2)
        self.assertEqual(teams[1].current_rank, 2)
        self.assertGreater(
            teams[0].current_rating,
            teams[1].current_rating)

    def test_skips_participants_without_season_matches(self) -> None:
        day = datetime(2025, 8, 1)
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=day,
                home_goals=1,
                away_goals=0)
        ])
        participants = _participants(
            (1, "Alpha", "ALP"),
            (2, "Beta", "BET"),
            (99, "Idle", "IDL"))

        teams = progress.compute_team_rating_progress(
            matches, 10, 100, participants)

        self.assertEqual({team.team_id for team in teams}, {1, 2})

    def test_empty_timeline_or_participants_returns_empty(self) -> None:
        participants = _participants((1, "Alpha", "ALP"))
        self.assertEqual(
            progress.extract_team_progress(
                pd.DataFrame(), 10, 100, participants),
            [])
        timeline = compute_ratings_timeline(pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=datetime(2025, 8, 1),
                home_goals=1,
                away_goals=0)
        ]))
        self.assertEqual(
            progress.extract_team_progress(
                timeline, 10, 100, pd.DataFrame()),
            [])

    def test_unsupported_metric_raises(self) -> None:
        timeline = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=datetime(2025, 8, 1),
                home_goals=1,
                away_goals=0)
        ])
        participants = _participants((1, "Alpha", "ALP"))
        with self.assertRaises(ValueError):
            progress.extract_team_progress(
                timeline,
                10,
                100,
                participants,
                metric="gap")  # type: ignore[arg-type]

    def test_build_ratings_timeline_delegates_to_canonical_function(
            self) -> None:
        matches = pd.DataFrame([
            _match(
                match_id=1,
                league=10,
                season=100,
                home_team=1,
                away_team=2,
                game_date=datetime(2025, 8, 1),
                home_goals=1,
                away_goals=0)
        ])
        with patch(
                "backend.sports.football.rating_progress"
                ".compute_ratings_timeline") as mock_timeline:
            mock_timeline.return_value = pd.DataFrame({"ok": [1]})
            result = progress.build_ratings_timeline(matches)
        mock_timeline.assert_called_once()
        self.assertEqual(list(result.columns), ["ok"])

    def test_module_does_not_import_elo_update_formula(self) -> None:
        source_path = progress.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("update_elo", source)
        self.assertNotIn("expected_home_score", source)
        self.assertNotIn("k_factor", source)


if __name__ == "__main__":
    unittest.main()
