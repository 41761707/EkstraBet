"""Write match assessment results to MySQL."""

from __future__ import annotations

import json
import logging

from backend.database import get_db_connection
from models.pipeline.core.config import PredictionResult

logger = logging.getLogger(__name__)

_UPSERT_SQL = """
INSERT INTO match_model_assessments (
    match_id,
    model_id,
    model_version,
    sport_id,
    assessment_type,
    home_played_better_probability,
    draw_probability,
    away_played_better_probability,
    final_assessment,
    confidence,
    dominance_score,
    feature_snapshot,
    artifact_path
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    home_played_better_probability = VALUES(home_played_better_probability),
    draw_probability = VALUES(draw_probability),
    away_played_better_probability = VALUES(away_played_better_probability),
    final_assessment = VALUES(final_assessment),
    confidence = VALUES(confidence),
    dominance_score = VALUES(dominance_score),
    feature_snapshot = VALUES(feature_snapshot),
    artifact_path = VALUES(artifact_path),
    updated_at = CURRENT_TIMESTAMP
"""


class MatchAssessmentWriter:
    """Persist played-better assessments with upsert semantics."""

    def write_match_assessment(self, result: PredictionResult) -> None:
        """Upsert one assessment row keyed by match/model/version/type."""
        write_match_assessment(result)

    def write_many(self, results: list[PredictionResult]) -> None:
        """Upsert multiple assessment rows in one connection."""
        write_match_assessments(results)


def choose_final_assessment(probabilities: dict[str, float]) -> str:
    """Pick final assessment label from three probability outputs."""
    ordered = sorted(
        [
            ("HOME_PLAYED_BETTER", probabilities["home_played_better_probability"]),
            ("DRAW", probabilities["draw_probability"]),
            ("AWAY_PLAYED_BETTER", probabilities["away_played_better_probability"])
        ],
        key=lambda item: item[1],
        reverse=True)
    return ordered[0][0]


def _ensure_active_model(model_id: int) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM models WHERE id = %s AND active = 1 LIMIT 1",
                (model_id,))
            row = cursor.fetchone()
        finally:
            cursor.close()
    if row is None:
        raise ValueError(
            f"Cannot write assessment: model_id={model_id} missing/inactive")


def _assessment_params(result: PredictionResult) -> tuple[object, ...]:
    probs = result.probabilities
    return (
        result.match_id,
        result.model_id,
        result.model_version,
        result.sport_id,
        result.assessment_type,
        float(probs["home_played_better_probability"]),
        float(probs["draw_probability"]),
        float(probs["away_played_better_probability"]),
        result.final_event_key,
        result.confidence,
        result.dominance_score,
        json.dumps(result.feature_snapshot, ensure_ascii=True),
        result.artifact_path)


def write_match_assessment(result: PredictionResult) -> None:
    """Upsert a single match assessment after validating model metadata."""
    _ensure_active_model(result.model_id)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(_UPSERT_SQL, _assessment_params(result))
            conn.commit()
        finally:
            cursor.close()
    logger.info(
        "Wrote assessment match_id=%s model_id=%s final=%s",
        result.match_id,
        result.model_id,
        result.final_event_key)


def write_match_assessments(results: list[PredictionResult]) -> None:
    """Upsert many assessments using one DB session."""
    if not results:
        return
    for result in results:
        _ensure_active_model(result.model_id)
    params = [_assessment_params(result) for result in results]
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(_UPSERT_SQL, params)
            conn.commit()
        finally:
            cursor.close()
    logger.info("Wrote %s match assessments", len(results))
