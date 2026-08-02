"""API tests for league rating-progress JSON endpoint."""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DB_PASSWORD", "test-db-password")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("AUTH_ENABLED", "false")

from api.main import create_app
from backend.services.rating_progress_service import NonFootballLeagueError
from backend.sports.football.rating_progress import RatingPoint
from backend.sports.football.rating_progress import RatingProgressResult
from backend.sports.football.rating_progress import TeamRatingProgress


def _point(
        match_id: int,
        rating: float,
        *,
        day: int = 1) -> RatingPoint:
    return RatingPoint(
        match_id=match_id,
        round_number=1,
        played_at=datetime(2025, 8, day),
        rating=rating)


def _team(
        team_id: int,
        *,
        name: str | None = None,
        start: float = 1500.0,
        current: float = 1510.0,
        rank: int = 1) -> TeamRatingProgress:
    return TeamRatingProgress(
        team_id=team_id,
        team_name=name or f"Team {team_id}",
        team_shortcut=f"T{team_id}",
        start_rating=start,
        current_rating=current,
        change=current - start,
        current_rank=rank,
        points=[_point(team_id * 10, current)])


def _result(
        teams: list[TeamRatingProgress] | None = None
) -> RatingProgressResult:
    resolved = teams if teams is not None else [
        _team(1, name="Alpha", start=1500, current=1550, rank=1),
        _team(2, name="Beta", start=1500, current=1480, rank=2)]
    rise = max(resolved, key=lambda team: team.change)
    fall = min(resolved, key=lambda team: team.change)
    return RatingProgressResult(
        league_id=1,
        league_name="Ekstraklasa",
        season_id=12,
        season_years="2025/2026",
        metric="elo",
        last_played_match_id=99,
        last_played_at=datetime(2025, 8, 20),
        teams=resolved,
        biggest_rise=rise,
        biggest_fall=fall)


class TestRatingProgressRouter(unittest.TestCase):
    """HTTP contract tests for the rating-progress JSON endpoint."""

    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_json_requires_season_id(self) -> None:
        response = self.client.get("/leagues/1/rating-progress")
        self.assertEqual(response.status_code, 422)

    @patch("api.routers.leagues.get_rating_progress", return_value=_result())
    def test_json_returns_full_payload(
            self,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/leagues/1/rating-progress?season_id=12&metric=elo")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["league_id"], 1)
        self.assertEqual(payload["league_name"], "Ekstraklasa")
        self.assertEqual(payload["season_id"], 12)
        self.assertEqual(payload["season_years"], "2025/2026")
        self.assertEqual(payload["metric"], "elo")
        self.assertEqual(payload["last_played_match_id"], 99)
        self.assertEqual(len(payload["teams"]), 2)
        self.assertEqual(payload["teams"][0]["team_name"], "Alpha")
        self.assertEqual(payload["teams"][0]["change"], 50.0)
        self.assertEqual(payload["biggest_rise"]["team_id"], 1)
        self.assertEqual(payload["biggest_fall"]["team_id"], 2)
        self.assertEqual(len(payload["teams"][0]["points"]), 1)
        mock_get.assert_called_once_with(1, 12, metric="elo")

    @patch(
        "api.routers.leagues.classify_missing_progress",
        return_value="not_found")
    @patch("api.routers.leagues.get_rating_progress", return_value=None)
    def test_json_404_when_league_or_season_missing(
            self,
            mock_get: MagicMock,
            mock_classify: MagicMock) -> None:
        response = self.client.get(
            "/leagues/999/rating-progress?season_id=1")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"])
        mock_get.assert_called_once()
        mock_classify.assert_called_once_with(999, 1)

    @patch(
        "api.routers.leagues.classify_missing_progress",
        return_value="empty_season")
    @patch("api.routers.leagues.get_rating_progress", return_value=None)
    def test_json_404_when_season_has_no_matches(
            self,
            _mock_get: MagicMock,
            mock_classify: MagicMock) -> None:
        response = self.client.get(
            "/leagues/1/rating-progress?season_id=12")
        self.assertEqual(response.status_code, 404)
        self.assertIn("No played matches", response.json()["detail"])
        mock_classify.assert_called_once_with(1, 12)

    @patch(
        "api.routers.leagues.get_rating_progress",
        side_effect=NonFootballLeagueError(
            "League 5 is not a football league"))
    def test_json_400_for_non_football_league(
            self,
            mock_get: MagicMock) -> None:
        response = self.client.get(
            "/leagues/5/rating-progress?season_id=12")
        self.assertEqual(response.status_code, 400)
        self.assertIn("not a football league", response.json()["detail"])
        mock_get.assert_called_once()

    def test_json_rejects_unsupported_metric_before_service(self) -> None:
        with patch("api.routers.leagues.get_rating_progress") as mock_get:
            response = self.client.get(
                "/leagues/1/rating-progress?season_id=12&metric=gap")
        self.assertEqual(response.status_code, 422)
        mock_get.assert_not_called()

    def test_png_endpoint_is_not_registered(self) -> None:
        response = self.client.get(
            "/leagues/1/rating-progress.png?season_id=12")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
