"""Unit tests for rating-progress service orchestration."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from backend.repositories.rating_progress_repository import (
    RatingProgressContext)
from backend.services import rating_progress_service as service
from backend.sports.football.rating_progress import RatingPoint
from backend.sports.football.rating_progress import RatingProgressResult
from backend.sports.football.rating_progress import TeamRatingProgress


def _point(
        match_id: int,
        rating: float,
        *,
        round_number: int = 1) -> RatingPoint:
    return RatingPoint(
        match_id=match_id,
        round_number=round_number,
        played_at=datetime(2025, 8, match_id),
        rating=rating)


def _team(
        team_id: int,
        *,
        name: str | None = None,
        start: float = 1500.0,
        current: float = 1500.0,
        rank: int = 1) -> TeamRatingProgress:
    change = current - start
    return TeamRatingProgress(
        team_id=team_id,
        team_name=name or f"Team {team_id}",
        team_shortcut=f"T{team_id}",
        start_rating=start,
        current_rating=current,
        change=change,
        current_rank=rank,
        points=[_point(team_id, current)])


def _result(
        teams: list[TeamRatingProgress],
        *,
        metric: str = "elo") -> RatingProgressResult:
    rise, fall = service._pick_leaders(teams)
    return RatingProgressResult(
        league_id=10,
        league_name="Test League",
        season_id=100,
        season_years="2025/2026",
        metric=metric,  # type: ignore[arg-type]
        last_played_match_id=99,
        last_played_at=datetime(2025, 8, 20),
        teams=teams,
        biggest_rise=rise,
        biggest_fall=fall)


def _context(
        *,
        sport_id: int = 1,
        last_played_match_id: int | None = 50,
        last_played_at: datetime | None = None,
        matches: pd.DataFrame | None = None,
        participants: pd.DataFrame | None = None
) -> RatingProgressContext:
    if last_played_at is None and last_played_match_id is not None:
        last_played_at = datetime(2025, 8, 10)
    return RatingProgressContext(
        league_id=10,
        league_name="Test League",
        country_id=1,
        country_name="Poland",
        sport_id=sport_id,
        tier=1,
        season_id=100,
        season_years="2025/2026",
        participants=(
            participants
            if participants is not None
            else pd.DataFrame([
                {
                    "team_id": 1,
                    "team_name": "Alpha",
                    "team_shortcut": "ALP"
                },
                {
                    "team_id": 2,
                    "team_name": "Beta",
                    "team_shortcut": "BET"
                }
            ])),
        matches=matches if matches is not None else pd.DataFrame(),
        last_played_match_id=last_played_match_id,
        last_played_at=last_played_at)


class TestGetRatingProgress(unittest.TestCase):
    """Tests for context validation and result assembly."""

    @patch(
        "backend.services.rating_progress_service"
        ".fetch_rating_progress_context",
        return_value=None)
    def test_returns_none_when_league_or_season_missing(
            self,
            _mock_fetch: unittest.mock.MagicMock) -> None:
        self.assertIsNone(service.get_rating_progress(999, 1))

    @patch(
        "backend.services.rating_progress_service"
        ".fetch_rating_progress_context")
    def test_returns_none_when_season_has_no_finished_matches(
            self,
            mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = _context(
            last_played_match_id=None,
            last_played_at=None)
        self.assertIsNone(service.get_rating_progress(10, 100))

    @patch(
        "backend.services.rating_progress_service"
        ".fetch_rating_progress_context")
    def test_raises_for_non_football_league(
            self,
            mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = _context(sport_id=2)
        with self.assertRaises(service.NonFootballLeagueError):
            service.get_rating_progress(10, 100)

    def test_unsupported_metric_raises(self) -> None:
        with self.assertRaises(ValueError):
            service.get_rating_progress(10, 100, metric="gap")

    @patch(
        "backend.services.rating_progress_service"
        ".compute_team_rating_progress")
    @patch(
        "backend.services.rating_progress_service"
        ".fetch_rating_progress_context")
    def test_maps_names_ranks_and_leaders(
            self,
            mock_fetch: unittest.mock.MagicMock,
            mock_compute: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = _context()
        # compute zwraca już posortowane po rankingu.
        mock_compute.return_value = [
            _team(1, name="Alpha", start=1500, current=1550, rank=1),
            _team(2, name="Beta", start=1500, current=1480, rank=2)]

        result = service.get_rating_progress(10, 100, metric="elo")

        assert result is not None
        self.assertEqual(result.league_id, 10)
        self.assertEqual(result.league_name, "Test League")
        self.assertEqual(result.season_years, "2025/2026")
        self.assertEqual(result.metric, "elo")
        self.assertEqual(result.last_played_match_id, 50)
        self.assertEqual([team.team_name for team in result.teams], [
            "Alpha",
            "Beta"])
        assert result.biggest_rise is not None
        assert result.biggest_fall is not None
        self.assertEqual(result.biggest_rise.team_id, 1)
        self.assertEqual(result.biggest_rise.change, 50.0)
        self.assertEqual(result.biggest_fall.team_id, 2)
        self.assertEqual(result.biggest_fall.change, -20.0)
        mock_compute.assert_called_once()
        self.assertEqual(
            mock_compute.call_args.kwargs["metric"],
            "elo")

    @patch(
        "backend.services.rating_progress_service"
        ".compute_team_rating_progress")
    @patch(
        "backend.services.rating_progress_service"
        ".fetch_rating_progress_context")
    def test_tie_rank_order_uses_lower_team_id(
            self,
            mock_fetch: unittest.mock.MagicMock,
            mock_compute: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = _context()
        # Remis ratingu: ekstraktor już ustawił rank po team_id.
        mock_compute.return_value = [
            _team(3, start=1500, current=1600, rank=1),
            _team(7, start=1500, current=1600, rank=2)]

        result = service.get_rating_progress(10, 100)

        assert result is not None
        self.assertEqual(result.teams[0].team_id, 3)
        self.assertEqual(result.teams[0].current_rank, 1)
        self.assertEqual(result.teams[1].team_id, 7)
        self.assertEqual(result.teams[1].current_rank, 2)
        # Remis zmiany: niższe team_id jako lider wzrostu i spadku.
        assert result.biggest_rise is not None
        assert result.biggest_fall is not None
        self.assertEqual(result.biggest_rise.team_id, 3)
        self.assertEqual(result.biggest_fall.team_id, 3)


class TestGetCountryRatingProgress(unittest.TestCase):
    """Country-wide progress across all football leagues."""

    @patch(
        "backend.services.rating_progress_service"
        ".fetch_country_rating_progress_context",
        return_value=None)
    def test_returns_none_when_country_or_season_missing(
            self,
            _mock_fetch: unittest.mock.MagicMock) -> None:
        self.assertIsNone(service.get_country_rating_progress(999, 1))

    @patch(
        "backend.services.rating_progress_service"
        ".compute_team_rating_progress")
    @patch(
        "backend.services.rating_progress_service"
        ".fetch_country_rating_progress_context")
    def test_extracts_with_league_id_none(
            self,
            mock_fetch: unittest.mock.MagicMock,
            mock_compute: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = RatingProgressContext(
            league_id=1,
            league_name="Polska — wszystkie ligi",
            country_id=1,
            country_name="Polska",
            sport_id=1,
            tier=None,
            season_id=100,
            season_years="2025/2026",
            participants=pd.DataFrame([
                {
                    "team_id": 1,
                    "team_name": "Alpha",
                    "team_shortcut": "ALP"
                }
            ]),
            matches=pd.DataFrame(),
            last_played_match_id=50,
            last_played_at=datetime(2025, 8, 10))
        mock_compute.return_value = [
            _team(1, name="Alpha", start=1500, current=1550, rank=1)]

        result = service.get_country_rating_progress(1, 100)

        assert result is not None
        self.assertEqual(result.league_name, "Polska — wszystkie ligi")
        mock_compute.assert_called_once()
        self.assertIsNone(
            mock_compute.call_args.kwargs["target_league_id"])


class TestSelectTeams(unittest.TestCase):
    """Tests for shared team_ids / top filtering."""

    def setUp(self) -> None:
        self.teams = [
            _team(1, name="Alpha", start=1500, current=1600, rank=1),
            _team(2, name="Beta", start=1500, current=1550, rank=2),
            _team(3, name="Gamma", start=1500, current=1400, rank=3),
            _team(4, name="Delta", start=1520, current=1510, rank=4)]
        self.full = _result(self.teams)

    def test_no_filter_returns_same_result(self) -> None:
        filtered = service.select_teams(self.full)
        self.assertIs(filtered, self.full)

    def test_rejects_unfiltered_over_max_teams(self) -> None:
        many = [
            _team(index, rank=index)
            for index in range(1, service.MAX_SELECTED_TEAMS + 2)]
        with self.assertRaises(service.RatingProgressFilterError):
            service.select_teams(_result(many))

    def test_top_keeps_current_rank_order(self) -> None:
        filtered = service.select_teams(self.full, top=2)
        self.assertEqual(
            [team.team_id for team in filtered.teams],
            [1, 2])
        self.assertEqual(filtered.teams[0].current_rank, 1)
        self.assertEqual(filtered.teams[1].current_rank, 2)
        assert filtered.biggest_rise is not None
        assert filtered.biggest_fall is not None
        self.assertEqual(filtered.biggest_rise.team_id, 1)
        self.assertEqual(filtered.biggest_fall.team_id, 2)

    def test_team_ids_preserves_rank_order_and_dedupes(self) -> None:
        filtered = service.select_teams(
            self.full,
            team_ids=[3, 1, 3, 4])
        self.assertEqual(
            [team.team_id for team in filtered.teams],
            [1, 3, 4])
        assert filtered.biggest_rise is not None
        assert filtered.biggest_fall is not None
        self.assertEqual(filtered.biggest_rise.team_id, 1)
        self.assertEqual(filtered.biggest_fall.team_id, 3)

    def test_rejects_mutual_top_and_team_ids(self) -> None:
        with self.assertRaises(service.RatingProgressFilterError):
            service.select_teams(self.full, team_ids=[1], top=2)

    def test_rejects_empty_team_ids(self) -> None:
        with self.assertRaises(service.RatingProgressFilterError):
            service.select_teams(self.full, team_ids=[])

    def test_rejects_unknown_team_ids(self) -> None:
        with self.assertRaises(service.RatingProgressFilterError) as ctx:
            service.select_teams(self.full, team_ids=[1, 99])
        self.assertIn("99", str(ctx.exception))

    def test_rejects_top_out_of_range(self) -> None:
        with self.assertRaises(service.RatingProgressFilterError):
            service.select_teams(self.full, top=0)
        with self.assertRaises(service.RatingProgressFilterError):
            service.select_teams(
                self.full,
                top=service.MAX_SELECTED_TEAMS + 1)

    def test_rejects_too_many_team_ids(self) -> None:
        too_many = list(range(1, service.MAX_SELECTED_TEAMS + 2))
        with self.assertRaises(service.RatingProgressFilterError):
            service.select_teams(self.full, team_ids=too_many)

    def test_module_does_not_import_fastapi_or_matplotlib(self) -> None:
        source_path = service.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as handle:
            source = handle.read()
        import_lines = [
            line.strip().lower()
            for line in source.splitlines()
            if line.lstrip().startswith(("import ", "from "))]
        for line in import_lines:
            self.assertNotIn("fastapi", line)
            self.assertNotIn("matplotlib", line)
            self.assertNotIn("pyplot", line)


if __name__ == "__main__":
    unittest.main()
