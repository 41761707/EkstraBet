"""Tests for rating-progress PNG renderer and CLI wrapper."""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt

from backend.services import rating_progress_renderer as renderer
from backend.services.rating_progress_renderer import (
    render_rating_progress_png)
from backend.services.rating_progress_service import select_teams
from backend.sports.football.rating_progress import RatingPoint
from backend.sports.football.rating_progress import RatingProgressResult
from backend.sports.football.rating_progress import TeamRatingProgress


def _point(
        match_id: int,
        rating: float,
        *,
        day: int = 1,
        round_number: int = 1) -> RatingPoint:
    return RatingPoint(
        match_id=match_id,
        round_number=round_number,
        played_at=datetime(2025, 8, day),
        rating=rating)


def _team(
        team_id: int,
        *,
        name: str | None = None,
        shortcut: str | None = None,
        start: float = 1500.0,
        ratings: list[float] | None = None,
        rank: int = 1) -> TeamRatingProgress:
    values = ratings or [start + 10.0, start + 20.0]
    points = [
        _point(team_id * 10 + index, value, day=index + 1, round_number=index + 1)
        for index, value in enumerate(values)]
    current = points[-1].rating
    return TeamRatingProgress(
        team_id=team_id,
        team_name=name or f"Team {team_id}",
        team_shortcut=shortcut or f"T{team_id}",
        start_rating=start,
        current_rating=current,
        change=current - start,
        current_rank=rank,
        points=points)


def _result(teams: list[TeamRatingProgress]) -> RatingProgressResult:
    rise = max(teams, key=lambda team: team.change) if teams else None
    fall = min(teams, key=lambda team: team.change) if teams else None
    return RatingProgressResult(
        league_id=10,
        league_name="Ekstraklasa",
        season_id=100,
        season_years="2025/2026",
        metric="elo",
        last_played_match_id=99,
        last_played_at=datetime(2025, 8, 20),
        teams=teams,
        biggest_rise=rise,
        biggest_fall=fall)


class TestRenderRatingProgressPng(unittest.TestCase):
    """PNG bytes contract and figure lifecycle."""

    def setUp(self) -> None:
        plt.close("all")

    def tearDown(self) -> None:
        plt.close("all")

    def test_returns_non_empty_png_signature(self) -> None:
        payload = render_rating_progress_png(_result([
            _team(1, rank=1, ratings=[1510.0, 1525.0]),
            _team(2, rank=2, ratings=[1490.0, 1480.0])]))
        self.assertTrue(payload.startswith(renderer.PNG_SIGNATURE))
        self.assertGreater(len(payload), 1000)

    def test_closes_figure_after_success(self) -> None:
        render_rating_progress_png(_result([_team(1)]))
        self.assertEqual(plt.get_fignums(), [])

    def test_closes_figure_when_savefig_fails(self) -> None:
        with patch.object(
                renderer.Figure,
                "savefig",
                side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                render_rating_progress_png(_result([_team(1)]))
        self.assertEqual(plt.get_fignums(), [])

    def test_renders_top_filter_subset(self) -> None:
        full = _result([
            _team(1, rank=1, ratings=[1600.0, 1610.0]),
            _team(2, rank=2, ratings=[1550.0, 1560.0]),
            _team(3, rank=3, ratings=[1400.0, 1390.0])])
        filtered = select_teams(full, top=2)
        payload = render_rating_progress_png(filtered)
        self.assertTrue(payload.startswith(renderer.PNG_SIGNATURE))
        self.assertEqual(len(filtered.teams), 2)

    def test_renders_team_ids_filter_subset(self) -> None:
        full = _result([
            _team(1, rank=1),
            _team(2, rank=2),
            _team(3, rank=3)])
        filtered = select_teams(full, team_ids=[3, 1])
        payload = render_rating_progress_png(filtered)
        self.assertTrue(payload.startswith(renderer.PNG_SIGNATURE))
        self.assertEqual(
            [team.team_id for team in filtered.teams],
            [1, 3])

    def test_empty_teams_still_produce_png(self) -> None:
        payload = render_rating_progress_png(_result([]))
        self.assertTrue(payload.startswith(renderer.PNG_SIGNATURE))
        self.assertEqual(plt.get_fignums(), [])

    def test_color_for_team_is_stable(self) -> None:
        first = renderer.color_for_team(42)
        second = renderer.color_for_team(42)
        other = renderer.color_for_team(43)
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_label_collision_spreads_close_ratings(self) -> None:
        spread = renderer._resolve_label_y_positions(
            [1500.0, 1499.0, 1498.0],
            min_gap=5.0)
        self.assertEqual(spread[0], 1500.0)
        self.assertLessEqual(spread[1], 1500.0 - 5.0)
        self.assertLessEqual(spread[2], spread[1] - 5.0)

    def test_series_starts_from_start_rating_baseline(self) -> None:
        team = _team(
            1,
            start=1500.0,
            ratings=[1510.0, 1520.0],
            rank=1)
        baseline = datetime(2025, 8, 1)
        dates, ratings = renderer._series_plot_points(team, baseline)
        self.assertEqual(dates[0], baseline)
        self.assertEqual(ratings[0], 1500.0)
        self.assertEqual(ratings[1:], [1510.0, 1520.0])
        self.assertEqual(len(dates), 3)

    def test_single_round_series_has_progress_segment(self) -> None:
        team = _team(7, start=1480.0, ratings=[1495.0], rank=1)
        result = _result([team])
        baseline = renderer._season_baseline_date(result)
        dates, ratings = renderer._series_plot_points(team, baseline)
        self.assertEqual(len(dates), 2)
        self.assertEqual(ratings, [1480.0, 1495.0])
        self.assertEqual(dates[0], team.points[0].played_at)
        payload = render_rating_progress_png(result)
        self.assertTrue(payload.startswith(renderer.PNG_SIGNATURE))

    def test_shared_baseline_uses_earliest_first_match(self) -> None:
        early = _team(1, ratings=[1510.0], rank=1)
        late = TeamRatingProgress(
            team_id=2,
            team_name="Late",
            team_shortcut="LAT",
            start_rating=1500.0,
            current_rating=1490.0,
            change=-10.0,
            current_rank=2,
            points=[_point(20, 1490.0, day=10, round_number=2)])
        result = _result([early, late])
        baseline = renderer._season_baseline_date(result)
        self.assertEqual(baseline, early.points[0].played_at)
        late_dates, late_ratings = renderer._series_plot_points(
            late,
            baseline)
        self.assertEqual(late_dates[0], baseline)
        self.assertEqual(late_ratings[0], 1500.0)

    def test_series_x_follows_match_dates_not_rounds(self) -> None:
        # Chronologia dat, nawet gdy numery kolejek są w innej kolejności.
        team = TeamRatingProgress(
            team_id=5,
            team_name="Postponed",
            team_shortcut="POS",
            start_rating=1500.0,
            current_rating=1510.0,
            change=10.0,
            current_rank=1,
            points=[
                _point(1, 1505.0, day=1, round_number=3),
                _point(2, 1510.0, day=8, round_number=2)])
        dates, _ = renderer._series_plot_points(
            team,
            datetime(2025, 8, 1))
        self.assertEqual(
            dates[1:],
            [datetime(2025, 8, 1), datetime(2025, 8, 8)])
        self.assertLess(dates[1], dates[2])

    def test_figure_height_grows_with_team_count(self) -> None:
        short = renderer.figure_height_for(6, rating_span=200.0)
        tall = renderer.figure_height_for(24, rating_span=200.0)
        self.assertGreaterEqual(short, renderer.FIGURE_HEIGHT_MIN)
        self.assertGreater(tall, short)
        self.assertLessEqual(tall, renderer.FIGURE_HEIGHT_MAX)

    def test_figure_height_grows_when_ratings_are_dense(self) -> None:
        wide = renderer.figure_height_for(18, rating_span=400.0)
        dense = renderer.figure_height_for(18, rating_span=80.0)
        self.assertGreater(dense, wide)

    def test_label_min_gap_stays_near_data_span(self) -> None:
        # Duży absolutny gap nie może wypchnąć etykiet daleko od kul.
        gap = renderer._label_min_gap(
            y_span=200.0,
            team_count=24,
            fig_height=16.0)
        self.assertLess(gap * 23, 200.0 * 0.5)

    def test_label_min_gap_smaller_on_taller_figure(self) -> None:
        short = renderer._label_min_gap(
            y_span=250.0,
            team_count=20,
            fig_height=8.0)
        tall = renderer._label_min_gap(
            y_span=250.0,
            team_count=20,
            fig_height=18.0)
        self.assertLessEqual(tall, short)


class TestRatingProgressCli(unittest.TestCase):
    """Smoke tests for the rewritten graphics_code CLI."""

    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        graphics_path = str(repo_root / "graphics_code")
        if graphics_path not in sys.path:
            sys.path.insert(0, graphics_path)
        # Odśwież moduł CLI po zmianach w tej sesji testowej.
        if "rating_progress" in sys.modules:
            cls.cli = importlib.reload(sys.modules["rating_progress"])
        else:
            cls.cli = importlib.import_module("rating_progress")

    def test_parse_team_ids(self) -> None:
        self.assertEqual(self.cli.parse_team_ids("3, 1,2"), [3, 1, 2])
        self.assertIsNone(self.cli.parse_team_ids(None))
        with self.assertRaises(ValueError):
            self.cli.parse_team_ids("")
        with self.assertRaises(ValueError):
            self.cli.parse_team_ids("1,x")

    def test_cli_writes_output_with_mocked_service(self) -> None:
        sample = _result([
            _team(1, rank=1),
            _team(2, rank=2)])
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "out" / "chart.png"
            with patch.object(
                    self.cli,
                    "get_rating_progress",
                    return_value=sample) as mock_get:
                with patch.object(
                        self.cli,
                        "select_teams",
                        side_effect=select_teams) as mock_select:
                    exit_code = self.cli.main([
                        "--league",
                        "10",
                        "--season",
                        "100",
                        "--top",
                        "1",
                        "--output",
                        str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.is_file())
            payload = output.read_bytes()
            self.assertTrue(payload.startswith(renderer.PNG_SIGNATURE))
            mock_get.assert_called_once_with(10, 100, metric="elo")
            mock_select.assert_called_once()
            self.assertEqual(mock_select.call_args.kwargs["top"], 1)

    def test_cli_country_uses_country_service(self) -> None:
        sample = _result([_team(1, rank=1)])
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "country.png"
            with patch.object(
                    self.cli,
                    "get_country_rating_progress",
                    return_value=sample) as mock_get:
                exit_code = self.cli.main([
                    "--country",
                    "1",
                    "--season",
                    "100",
                    "--top",
                    "1",
                    "--output",
                    str(output)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.is_file())
            mock_get.assert_called_once_with(1, 100, metric="elo")

    def test_cli_returns_error_when_progress_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "missing.png"
            with patch.object(
                    self.cli,
                    "get_rating_progress",
                    return_value=None):
                exit_code = self.cli.main([
                    "--league",
                    "10",
                    "--season",
                    "100",
                    "--output",
                    str(output)])
            self.assertEqual(exit_code, 1)
            self.assertFalse(output.exists())

    def test_cli_source_has_no_csv_or_show(self) -> None:
        source_path = Path(self.cli.__file__)
        source = source_path.read_text(encoding="utf-8").lower()
        self.assertNotIn("ratings_elo_", source)
        self.assertNotIn("plt.show", source)
        self.assertNotIn("glob.glob", source)
        self.assertNotIn("read_csv", source)


if __name__ == "__main__":
    unittest.main()
