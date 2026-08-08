"""Atomic persistence for season projection runs and team rows."""

from __future__ import annotations

import hashlib
import json
import logging
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any

from backend.database import get_db_connection
from models.pipeline.core.artifacts import ARTIFACT_KERAS_MODEL_NAME
from models.pipeline.core.artifacts import ARTIFACT_MODEL_NAME
from models.pipeline.simulation.aggregation import TeamSeasonProjection
from models.pipeline.simulation.config import SimulationMode
from models.pipeline.simulation.season_simulator import SeasonSimulationResult

logger = logging.getLogger(__name__)

_INSERT_RUN_SQL = """
INSERT INTO season_projection_runs (
    league_id,
    season_id,
    mode,
    status,
    model_name,
    model_version,
    artifact_hash,
    n_trials,
    seed,
    fixed_matches,
    simulated_matches,
    input_fingerprint,
    started_at,
    completed_at,
    error_message
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

_COMPLETE_RUN_SQL = """
UPDATE season_projection_runs
SET status = %s,
    fixed_matches = %s,
    simulated_matches = %s,
    input_fingerprint = %s,
    completed_at = %s,
    error_message = NULL
WHERE id = %s
  AND status = %s
"""

_FAIL_RUN_SQL = """
UPDATE season_projection_runs
SET status = %s,
    completed_at = %s,
    error_message = %s
WHERE id = %s
  AND status = %s
"""

_INSERT_TEAM_ROW_SQL = """
INSERT INTO season_projection_team_rows (
    run_id,
    team_id,
    current_position,
    current_points,
    expected_position,
    most_likely_position,
    position_min,
    position_max,
    expected_points,
    points_variance,
    points_stddev,
    points_p05,
    points_p50,
    points_p95,
    points_min,
    points_max,
    expected_goal_difference,
    position_probabilities_json
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""


class ProjectionRunStatus(str, Enum):
    """Lifecycle status for a cached season projection run."""

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class SeasonProjectionRun:
    """Metadata for one season projection cache entry."""

    league_id: int
    season_id: int
    mode: SimulationMode
    status: ProjectionRunStatus
    model_name: str
    model_version: str
    artifact_hash: str
    n_trials: int
    seed: int
    fixed_matches: int
    simulated_matches: int
    input_fingerprint: str
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    id: int | None = None


def compute_artifact_hash(artifact_dir: Path) -> str:
    """Return SHA-256 of the primary model file in ``artifact_dir``."""
    directory = Path(artifact_dir)
    keras_path = directory / ARTIFACT_KERAS_MODEL_NAME
    joblib_path = directory / ARTIFACT_MODEL_NAME
    if keras_path.is_file():
        target = keras_path
    elif joblib_path.is_file():
        target = joblib_path
    else:
        raise FileNotFoundError(
            "No model artifact found in "
            f"{directory} ({ARTIFACT_KERAS_MODEL_NAME} or "
            f"{ARTIFACT_MODEL_NAME})")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def start_projection_run(
        run: SeasonProjectionRun,
        *,
        conn: Any | None = None) -> int:
    """Insert a RUNNING row and return its primary key."""
    if run.status is not ProjectionRunStatus.RUNNING:
        raise ValueError("start_projection_run requires status=RUNNING")
    connection_context = (
        nullcontext(conn) if conn is not None else get_db_connection())
    with connection_context as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(_INSERT_RUN_SQL, _running_params(run))
            run_id = int(cursor.lastrowid or 0)
            if run_id <= 0:
                raise RuntimeError("Failed to allocate projection run id")
            if conn is None:
                connection.commit()
        except Exception:
            if conn is None:
                connection.rollback()
            raise
        finally:
            cursor.close()
    logger.info(
        "Started projection run_id=%s league_id=%s season_id=%s mode=%s",
        run_id,
        run.league_id,
        run.season_id,
        run.mode.value)
    return run_id


def write_projection(
        result: SeasonSimulationResult,
        input_fingerprint: str,
        *,
        model_name: str,
        model_version: str,
        artifact_hash: str,
        run_id: int | None = None,
        started_at: datetime | None = None,
        conn: Any | None = None) -> int:
    """Persist a SUCCEEDED run with all team rows in one transaction.

    When ``run_id`` is set, the existing RUNNING row is completed. Otherwise
    a new SUCCEEDED run is inserted together with its team rows.
    """
    fingerprint = _require_fingerprint(result, input_fingerprint)
    completed_at = _utc_now()
    connection_context = (
        nullcontext(conn) if conn is not None else get_db_connection())
    with connection_context as connection:
        cursor = connection.cursor()
        try:
            if run_id is None:
                resolved_id = _insert_succeeded_run(
                    cursor,
                    result=result,
                    fingerprint=fingerprint,
                    model_name=model_name,
                    model_version=model_version,
                    artifact_hash=artifact_hash,
                    started_at=started_at or completed_at,
                    completed_at=completed_at)
            else:
                resolved_id = _complete_running_run(
                    cursor,
                    run_id=run_id,
                    result=result,
                    fingerprint=fingerprint,
                    completed_at=completed_at)
            _insert_team_rows(cursor, resolved_id, result.projections)
            if conn is None:
                connection.commit()
        except Exception:
            if conn is None:
                connection.rollback()
            raise
        finally:
            cursor.close()
    logger.info(
        "Wrote projection run_id=%s teams=%s mode=%s",
        resolved_id,
        len(result.projections),
        result.config.mode.value)
    return resolved_id


def fail_projection_run(
        run_id: int,
        error_message: str,
        *,
        conn: Any | None = None) -> None:
    """Mark a RUNNING projection as FAILED without writing team rows."""
    message = (error_message or "").strip() or "unknown error"
    # DB TEXT ma limity praktyczne — trzymamy czytelny skrót
    if len(message) > 4000:
        message = message[:3997] + "..."
    completed_at = _utc_now()
    connection_context = (
        nullcontext(conn) if conn is not None else get_db_connection())
    with connection_context as connection:
        cursor = connection.cursor()
        try:
            cursor.execute(
                _FAIL_RUN_SQL,
                (
                    ProjectionRunStatus.FAILED.value,
                    completed_at,
                    message,
                    run_id,
                    ProjectionRunStatus.RUNNING.value))
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Cannot fail projection run_id="
                    f"{run_id}: expected one RUNNING row")
            if conn is None:
                connection.commit()
        except Exception:
            if conn is None:
                connection.rollback()
            raise
        finally:
            cursor.close()
    logger.warning(
        "Failed projection run_id=%s error=%s",
        run_id,
        message)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _require_fingerprint(
        result: SeasonSimulationResult,
        input_fingerprint: str) -> str:
    fingerprint = str(input_fingerprint or "").strip()
    if not fingerprint:
        raise ValueError("input_fingerprint is required")
    if fingerprint != result.input_fingerprint:
        raise ValueError(
            "input_fingerprint does not match SeasonSimulationResult")
    return fingerprint


def _running_params(run: SeasonProjectionRun) -> tuple[object, ...]:
    return (
        run.league_id,
        run.season_id,
        run.mode.value,
        ProjectionRunStatus.RUNNING.value,
        run.model_name,
        run.model_version,
        run.artifact_hash,
        run.n_trials,
        run.seed,
        run.fixed_matches,
        run.simulated_matches,
        run.input_fingerprint,
        run.started_at,
        None,
        None)


def _insert_succeeded_run(
        cursor: Any,
        *,
        result: SeasonSimulationResult,
        fingerprint: str,
        model_name: str,
        model_version: str,
        artifact_hash: str,
        started_at: datetime,
        completed_at: datetime) -> int:
    cursor.execute(
        _INSERT_RUN_SQL,
        (
            result.config.league_id,
            result.config.season_id,
            result.config.mode.value,
            ProjectionRunStatus.SUCCEEDED.value,
            model_name,
            model_version,
            artifact_hash,
            result.config.n_trials,
            result.config.seed,
            result.fixed_matches,
            result.simulated_matches,
            fingerprint,
            started_at,
            completed_at,
            None))
    run_id = int(cursor.lastrowid or 0)
    if run_id <= 0:
        raise RuntimeError("Failed to allocate projection run id")
    return run_id


def _complete_running_run(
        cursor: Any,
        *,
        run_id: int,
        result: SeasonSimulationResult,
        fingerprint: str,
        completed_at: datetime) -> int:
    cursor.execute(
        _COMPLETE_RUN_SQL,
        (
            ProjectionRunStatus.SUCCEEDED.value,
            result.fixed_matches,
            result.simulated_matches,
            fingerprint,
            completed_at,
            run_id,
            ProjectionRunStatus.RUNNING.value))
    if cursor.rowcount != 1:
        raise RuntimeError(
            "Cannot complete projection run_id="
            f"{run_id}: expected one RUNNING row")
    return run_id


def _insert_team_rows(
        cursor: Any,
        run_id: int,
        projections: list[TeamSeasonProjection]) -> None:
    if not projections:
        raise ValueError("projections must not be empty")
    params = [
        _team_row_params(run_id, projection)
        for projection in projections]
    cursor.executemany(_INSERT_TEAM_ROW_SQL, params)


def _team_row_params(
        run_id: int,
        projection: TeamSeasonProjection) -> tuple[object, ...]:
    return (
        run_id,
        projection.team_id,
        projection.current_position,
        projection.current_points,
        projection.expected_position,
        projection.most_likely_position,
        projection.position_min,
        projection.position_max,
        projection.expected_points,
        projection.points_variance,
        projection.points_stddev,
        projection.points_p05,
        projection.points_p50,
        projection.points_p95,
        projection.points_min,
        projection.points_max,
        projection.expected_goal_difference,
        json.dumps(projection.position_probabilities, ensure_ascii=True))
