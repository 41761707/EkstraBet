"""Aggregate Monte Carlo trial tables into season projections."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BaselineStanding:
    """Day-0 or post-fixed-match standing for one team."""

    team_id: int
    points: int
    position: int
    goal_difference: int = 0


@dataclass(frozen=True)
class TeamSeasonProjection:
    """Projected end-of-season stats for one team across trials."""

    team_id: int
    current_position: int
    current_points: int
    expected_position: float
    most_likely_position: int
    position_min: int
    position_max: int
    expected_points: float
    points_variance: float
    points_stddev: float
    points_p05: float
    points_p50: float
    points_p95: float
    points_min: float
    points_max: float
    expected_goal_difference: float
    position_probabilities: list[float]


def rank_teams(
        team_ids: tuple[int, ...] | list[int],
        points: np.ndarray,
        goal_difference: np.ndarray) -> np.ndarray:
    """Return 1-based positions sorted by points, GD, then team id.

    Ties break toward the lower stable ``team_id`` (better position).
    """
    ids = np.asarray(team_ids, dtype=int)
    pts = np.asarray(points, dtype=float)
    gd = np.asarray(goal_difference, dtype=float)
    if ids.shape != pts.shape or ids.shape != gd.shape:
        raise ValueError("team_ids, points, and goal_difference must match")
    # punkty i GD malejąco, team_id rosnąco — deterministyczny tie-break
    order = np.lexsort((ids, -gd, -pts))
    positions = np.empty(len(ids), dtype=int)
    positions[order] = np.arange(1, len(ids) + 1)
    return positions


def aggregate_projection(
        final_points: np.ndarray,
        final_goal_difference: np.ndarray,
        team_ids: tuple[int, ...] | list[int],
        baseline: list[BaselineStanding]) -> list[TeamSeasonProjection]:
    """Build per-team projections from trial end tables.

    Args:
        final_points: Shape ``(n_trials, n_teams)`` end-of-season points.
        final_goal_difference: Same shape, final goal difference.
        team_ids: Stable column order matching the arrays.
        baseline: Current points/position before remaining fixtures
            (zeros in ``from_season_start``; after fixed commits in
            ``from_now``).
    """
    points = np.asarray(final_points, dtype=float)
    gd = np.asarray(final_goal_difference, dtype=float)
    ids = tuple(int(team_id) for team_id in team_ids)
    if points.ndim != 2 or gd.ndim != 2:
        raise ValueError("final tables must be 2-D (trials x teams)")
    if points.shape != gd.shape:
        raise ValueError("points and goal_difference shapes must match")
    if points.shape[1] != len(ids):
        raise ValueError("team_ids length must match table columns")
    if points.shape[0] == 0:
        raise ValueError("at least one trial is required")
    baseline_by_id = {row.team_id: row for row in baseline}
    missing = [team_id for team_id in ids if team_id not in baseline_by_id]
    if missing:
        raise ValueError(f"baseline missing teams: {missing}")

    n_trials, n_teams = points.shape
    positions = np.empty((n_trials, n_teams), dtype=int)
    for trial_index in range(n_trials):
        positions[trial_index] = rank_teams(
            ids, points[trial_index], gd[trial_index])

    projections: list[TeamSeasonProjection] = []
    for column, team_id in enumerate(ids):
        team_points = points[:, column]
        team_positions = positions[:, column]
        team_gd = gd[:, column]
        position_probabilities = _position_probabilities(
            team_positions, n_teams)
        variance = float(np.var(team_points, ddof=0))
        projections.append(TeamSeasonProjection(
            team_id=team_id,
            current_position=baseline_by_id[team_id].position,
            current_points=baseline_by_id[team_id].points,
            expected_position=float(np.mean(team_positions)),
            most_likely_position=int(np.argmax(position_probabilities) + 1),
            position_min=int(np.min(team_positions)),
            position_max=int(np.max(team_positions)),
            expected_points=float(np.mean(team_points)),
            points_variance=variance,
            points_stddev=float(np.sqrt(variance)),
            points_p05=float(np.percentile(team_points, 5)),
            points_p50=float(np.percentile(team_points, 50)),
            points_p95=float(np.percentile(team_points, 95)),
            points_min=float(np.min(team_points)),
            points_max=float(np.max(team_points)),
            expected_goal_difference=float(np.mean(team_gd)),
            position_probabilities=position_probabilities))
    return projections


def baseline_from_standings(
        team_ids: tuple[int, ...] | list[int],
        points: np.ndarray,
        goal_difference: np.ndarray) -> list[BaselineStanding]:
    """Build baseline rows from a single standings vector."""
    ids = tuple(int(team_id) for team_id in team_ids)
    pts = np.asarray(points, dtype=int).reshape(-1)
    gd = np.asarray(goal_difference, dtype=int).reshape(-1)
    positions = rank_teams(ids, pts, gd)
    return [
        BaselineStanding(
            team_id=team_id,
            points=int(pts[index]),
            position=int(positions[index]),
            goal_difference=int(gd[index]))
        for index, team_id in enumerate(ids)]


def _position_probabilities(
        positions: np.ndarray,
        n_teams: int) -> list[float]:
    counts = np.bincount(positions, minlength=n_teams + 1)
    # indeks 0 nieużywany — pozycje są 1..N
    probs = counts[1:n_teams + 1].astype(float)
    total = float(probs.sum())
    if total <= 0.0:
        raise ValueError("position counts must be positive")
    return (probs / total).tolist()
