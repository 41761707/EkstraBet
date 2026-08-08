"""Read-only SQL access to cached season projection runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from backend.database import get_db_connection

SUCCEEDED_STATUS = "SUCCEEDED"

_LATEST_SUCCEEDED_RUN_SQL = """
    SELECT
        r.id,
        r.league_id,
        r.season_id,
        r.mode,
        r.status,
        r.model_name,
        r.model_version,
        r.artifact_hash,
        r.n_trials,
        r.seed,
        r.fixed_matches,
        r.simulated_matches,
        r.input_fingerprint,
        r.started_at,
        r.completed_at
    FROM season_projection_runs r
    WHERE r.league_id = %s
      AND r.season_id = %s
      AND r.mode = %s
      AND r.status = %s
    ORDER BY r.completed_at DESC, r.id DESC
    LIMIT 1
"""

_TEAM_ROWS_SQL = """
    SELECT
        tr.team_id,
        t.name AS team_name,
        tr.current_position,
        tr.current_points,
        tr.expected_position,
        tr.most_likely_position,
        tr.position_min,
        tr.position_max,
        tr.expected_points,
        tr.points_variance,
        tr.points_stddev,
        tr.points_p05,
        tr.points_p50,
        tr.points_p95,
        tr.points_min,
        tr.points_max,
        tr.expected_goal_difference,
        tr.position_probabilities_json
    FROM season_projection_team_rows tr
    JOIN teams t ON t.id = tr.team_id
    WHERE tr.run_id = %s
    ORDER BY tr.expected_position ASC, tr.team_id ASC
"""


@dataclass(frozen=True)
class SeasonProjectionRunRecord:
    """One SUCCEEDED projection run row from cache."""

    id: int
    league_id: int
    season_id: int
    mode: str
    status: str
    model_name: str
    model_version: str
    artifact_hash: str
    n_trials: int
    seed: int
    fixed_matches: int
    simulated_matches: int
    input_fingerprint: str
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class SeasonProjectionTeamRowRecord:
    """One cached team projection row with display name."""

    team_id: int
    team_name: str
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


def fetch_latest_succeeded_run(
        league_id: int,
        season_id: int,
        mode: str) -> SeasonProjectionRunRecord | None:
    """Return the latest SUCCEEDED run for league/season/mode."""
    with get_db_connection() as connection:
        frame = pd.read_sql(
            _LATEST_SUCCEEDED_RUN_SQL,
            connection,
            params=(
                league_id,
                season_id,
                mode,
                SUCCEEDED_STATUS))
    if frame.empty:
        return None
    return _map_run_row(frame.iloc[0])


def fetch_team_rows_for_run(
        run_id: int) -> list[SeasonProjectionTeamRowRecord]:
    """Return team projection rows for a cached run, ordered by xPos."""
    with get_db_connection() as connection:
        frame = pd.read_sql(
            _TEAM_ROWS_SQL,
            connection,
            params=(run_id,))
    if frame.empty:
        return []
    return [_map_team_row(row) for _, row in frame.iterrows()]


def _map_run_row(row: pd.Series) -> SeasonProjectionRunRecord:
    completed_at = _require_datetime(row["completed_at"])
    return SeasonProjectionRunRecord(
        id=int(row["id"]),
        league_id=int(row["league_id"]),
        season_id=int(row["season_id"]),
        mode=str(row["mode"]),
        status=str(row["status"]),
        model_name=str(row["model_name"]),
        model_version=str(row["model_version"]),
        artifact_hash=str(row["artifact_hash"]),
        n_trials=int(row["n_trials"]),
        seed=int(row["seed"]),
        fixed_matches=int(row["fixed_matches"]),
        simulated_matches=int(row["simulated_matches"]),
        input_fingerprint=str(row["input_fingerprint"]),
        started_at=_require_datetime(row["started_at"]),
        completed_at=completed_at)


def _map_team_row(row: pd.Series) -> SeasonProjectionTeamRowRecord:
    return SeasonProjectionTeamRowRecord(
        team_id=int(row["team_id"]),
        team_name=str(row["team_name"]),
        current_position=int(row["current_position"]),
        current_points=int(row["current_points"]),
        expected_position=float(row["expected_position"]),
        most_likely_position=int(row["most_likely_position"]),
        position_min=int(row["position_min"]),
        position_max=int(row["position_max"]),
        expected_points=float(row["expected_points"]),
        points_variance=float(row["points_variance"]),
        points_stddev=float(row["points_stddev"]),
        points_p05=float(row["points_p05"]),
        points_p50=float(row["points_p50"]),
        points_p95=float(row["points_p95"]),
        points_min=float(row["points_min"]),
        points_max=float(row["points_max"]),
        expected_goal_difference=float(row["expected_goal_difference"]),
        position_probabilities=_parse_probabilities(
            row["position_probabilities_json"]))


def _parse_probabilities(raw: Any) -> list[float]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    if isinstance(raw, list):
        return [float(value) for value in raw]
    if isinstance(raw, str):
        parsed = json.loads(raw)
        return [float(value) for value in parsed]
    # mysql connector czasem zwraca juz zdekodowany typ
    if hasattr(raw, "__iter__"):
        return [float(value) for value in list(raw)]
    raise TypeError(
        f"Unsupported position_probabilities_json type: {type(raw)!r}")


def _require_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid datetime value: {value!r}")
    return parsed.to_pydatetime()
