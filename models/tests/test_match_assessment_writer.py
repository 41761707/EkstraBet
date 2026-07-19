"""Tests for match assessment writer helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from models.pipeline.core.config import PredictionResult
from models.pipeline.persistence.match_assessment_writer import (
    choose_final_assessment,
    write_match_assessment)


def _sample_result() -> PredictionResult:
    return PredictionResult(
        match_id=101,
        model_id=6,
        probabilities={
            "home_played_better_probability": 0.55,
            "draw_probability": 0.25,
            "away_played_better_probability": 0.20
        },
        final_event_key="HOME_PLAYED_BETTER",
        feature_snapshot={"xg_diff": 1.2},
        confidence=0.30,
        dominance_score=0.8,
        model_version="1.0.0",
        assessment_type="PLAYED_BETTER",
        sport_id=1,
        artifact_path="models/artifacts/dev/football_played_better_v1")


def test_choose_final_assessment_picks_highest_probability() -> None:
    assert choose_final_assessment({
        "home_played_better_probability": 0.2,
        "draw_probability": 0.5,
        "away_played_better_probability": 0.3
    }) == "DRAW"
    assert choose_final_assessment({
        "home_played_better_probability": 0.1,
        "draw_probability": 0.2,
        "away_played_better_probability": 0.7
    }) == "AWAY_PLAYED_BETTER"


def test_write_match_assessment_upserts_single_row() -> None:
    result = _sample_result()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (6,)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = False

    with patch(
            "models.pipeline.persistence.match_assessment_writer.get_db_connection",
            return_value=mock_cm):
        write_match_assessment(result)

    assert mock_cursor.execute.call_count == 2
    upsert_sql = mock_cursor.execute.call_args_list[1].args[0]
    upsert_params = mock_cursor.execute.call_args_list[1].args[1]
    assert "ON DUPLICATE KEY UPDATE" in upsert_sql
    assert upsert_params[0] == 101
    assert upsert_params[1] == 6
    assert upsert_params[5] == 0.55
    assert upsert_params[8] == "HOME_PLAYED_BETTER"
    mock_conn.commit.assert_called_once()


def test_write_match_assessment_rejects_missing_model() -> None:
    result = _sample_result()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_conn
    mock_cm.__exit__.return_value = False

    with patch(
            "models.pipeline.persistence.match_assessment_writer.get_db_connection",
            return_value=mock_cm):
        try:
            write_match_assessment(result)
            raised = False
        except ValueError as exc:
            raised = True
            assert "missing/inactive" in str(exc)
    assert raised
