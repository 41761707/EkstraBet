"""Tests for atomic season projection writer."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from models.pipeline.simulation.aggregation import TeamSeasonProjection
from models.pipeline.simulation.config import SeasonSimulationConfig
from models.pipeline.simulation.config import SimulationMode
from models.pipeline.simulation.season_simulator import SeasonSimulationResult
from models.pipeline.persistence.season_projection_writer import (
    ProjectionRunStatus,
    SeasonProjectionRun,
    compute_artifact_hash,
    fail_projection_run,
    start_projection_run,
    write_projection)


def _projection(team_id: int, mode_points: int = 0) -> TeamSeasonProjection:
    return TeamSeasonProjection(
        team_id=team_id,
        current_position=1 if team_id == 1 else 2,
        current_points=mode_points,
        expected_position=1.5,
        most_likely_position=1,
        position_min=1,
        position_max=2,
        expected_points=10.0,
        points_variance=1.0,
        points_stddev=1.0,
        points_p05=8.0,
        points_p50=10.0,
        points_p95=12.0,
        points_min=7.0,
        points_max=13.0,
        expected_goal_difference=1.0,
        position_probabilities=[0.6, 0.4])


def _result(
        mode: SimulationMode = SimulationMode.FROM_NOW,
        fingerprint: str = "fp-abc"
) -> SeasonSimulationResult:
    return SeasonSimulationResult(
        config=SeasonSimulationConfig(
            league_id=1,
            season_id=13,
            mode=mode,
            n_trials=100,
            seed=42),
        projections=[_projection(1, 3), _projection(2, 0)],
        input_fingerprint=fingerprint,
        fixed_matches=4,
        simulated_matches=8,
        processed_schedule_ids=(10, 11, 12))


def _mock_connection() -> tuple[MagicMock, MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.lastrowid = 77
    cursor.rowcount = 1
    connection = MagicMock()
    connection.cursor.return_value = cursor
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    return cursor, connection, context


def test_compute_artifact_hash_uses_keras_file(tmp_path: Path) -> None:
    model_path = tmp_path / "model.keras"
    payload = b"keras-bytes-123"
    model_path.write_bytes(payload)
    digest = compute_artifact_hash(tmp_path)
    assert digest == hashlib.sha256(payload).hexdigest()


def test_compute_artifact_hash_falls_back_to_joblib(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    payload = b"joblib-bytes"
    model_path.write_bytes(payload)
    assert compute_artifact_hash(tmp_path) == hashlib.sha256(
        payload).hexdigest()


def test_compute_artifact_hash_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compute_artifact_hash(tmp_path)


def test_start_projection_run_inserts_running() -> None:
    cursor, connection, context = _mock_connection()
    run = SeasonProjectionRun(
        league_id=1,
        season_id=13,
        mode=SimulationMode.FROM_NOW,
        status=ProjectionRunStatus.RUNNING,
        model_name="FOOTBALL_GOALS_POISSON_V1",
        model_version="1.0.0",
        artifact_hash="abc",
        n_trials=100,
        seed=42,
        fixed_matches=0,
        simulated_matches=0,
        input_fingerprint="",
        started_at=datetime(2026, 8, 6, 12, 0, 0))
    with patch(
            "models.pipeline.persistence.season_projection_writer"
            ".get_db_connection",
            return_value=context):
        run_id = start_projection_run(run)
    assert run_id == 77
    sql, params = cursor.execute.call_args.args
    assert "INSERT INTO season_projection_runs" in sql
    assert params[3] == ProjectionRunStatus.RUNNING.value
    assert params[2] == SimulationMode.FROM_NOW.value
    connection.commit.assert_called_once()


def test_write_projection_atomic_success_both_modes() -> None:
    for mode in (SimulationMode.FROM_NOW, SimulationMode.FROM_SEASON_START):
        cursor, connection, context = _mock_connection()
        result = _result(mode=mode, fingerprint=f"fp-{mode.value}")
        with patch(
                "models.pipeline.persistence.season_projection_writer"
                ".get_db_connection",
                return_value=context):
            run_id = write_projection(
                result,
                result.input_fingerprint,
                model_name="FOOTBALL_GOALS_POISSON_V1",
                model_version="1.0.0",
                artifact_hash="hash-1")
        assert run_id == 77
        insert_sql, insert_params = cursor.execute.call_args.args
        assert "INSERT INTO season_projection_runs" in insert_sql
        assert insert_params[2] == mode.value
        assert insert_params[3] == ProjectionRunStatus.SUCCEEDED.value
        assert cursor.executemany.call_count == 1
        team_sql, team_rows = cursor.executemany.call_args.args
        assert "INSERT INTO season_projection_team_rows" in team_sql
        assert len(team_rows) == 2
        connection.commit.assert_called_once()


def test_write_projection_completes_running_run() -> None:
    cursor, connection, context = _mock_connection()
    result = _result()
    with patch(
            "models.pipeline.persistence.season_projection_writer"
            ".get_db_connection",
            return_value=context):
        run_id = write_projection(
            result,
            result.input_fingerprint,
            model_name="FOOTBALL_GOALS_POISSON_V1",
            model_version="1.0.0",
            artifact_hash="hash-1",
            run_id=55)
    assert run_id == 55
    update_sql, update_params = cursor.execute.call_args.args
    assert "UPDATE season_projection_runs" in update_sql
    assert update_params[0] == ProjectionRunStatus.SUCCEEDED.value
    assert update_params[5] == 55
    assert update_params[6] == ProjectionRunStatus.RUNNING.value
    connection.commit.assert_called_once()


def test_write_projection_rejects_fingerprint_mismatch() -> None:
    result = _result(fingerprint="fp-a")
    with pytest.raises(ValueError, match="does not match"):
        write_projection(
            result,
            "fp-other",
            model_name="m",
            model_version="1",
            artifact_hash="h")


def test_write_projection_rolls_back_on_team_insert_failure() -> None:
    cursor, connection, context = _mock_connection()
    cursor.executemany.side_effect = RuntimeError("team insert failed")
    result = _result()
    with patch(
            "models.pipeline.persistence.season_projection_writer"
            ".get_db_connection",
            return_value=context):
        with pytest.raises(RuntimeError, match="team insert failed"):
            write_projection(
                result,
                result.input_fingerprint,
                model_name="m",
                model_version="1",
                artifact_hash="h")
    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()


def test_fail_projection_run_updates_status_without_team_rows() -> None:
    cursor, connection, context = _mock_connection()
    with patch(
            "models.pipeline.persistence.season_projection_writer"
            ".get_db_connection",
            return_value=context):
        fail_projection_run(55, "incomplete schedule")
    sql, params = cursor.execute.call_args.args
    assert "UPDATE season_projection_runs" in sql
    assert params[0] == ProjectionRunStatus.FAILED.value
    assert params[2] == "incomplete schedule"
    assert params[3] == 55
    cursor.executemany.assert_not_called()
    connection.commit.assert_called_once()


def test_fail_projection_run_rejects_non_running() -> None:
    cursor, connection, context = _mock_connection()
    cursor.rowcount = 0
    with patch(
            "models.pipeline.persistence.season_projection_writer"
            ".get_db_connection",
            return_value=context):
        with pytest.raises(RuntimeError, match="expected one RUNNING"):
            fail_projection_run(55, "boom")
    connection.rollback.assert_called_once()
