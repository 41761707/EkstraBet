"""Batch and single-match prediction for assessment models."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from models.pipeline.core import artifacts
from models.pipeline.core.config import ModelRunConfig, PredictionResult
from models.pipeline.core.registry import (
    get_feature_builder,
    get_labeler,
    resolve_model_id)
from models.pipeline.data.match_stats_repository import (
    fetch_match_stats,
    fetch_matches_by_ids,
    fetch_matches_by_season)
from models.pipeline.features.football_match_stats import build_feature_snapshot
from models.pipeline.labels.football_played_better import (
    ASSESSMENT_AWAY,
    ASSESSMENT_DRAW,
    ASSESSMENT_HOME,
    CLASS_AWAY,
    CLASS_DRAW,
    CLASS_HOME)

logger = logging.getLogger(__name__)

PROB_KEY_BY_CLASS = {
    CLASS_HOME: "home_played_better_probability",
    CLASS_DRAW: "draw_probability",
    CLASS_AWAY: "away_played_better_probability"
}


def _probability_map(
        classes: list[str],
        proba_row: np.ndarray) -> dict[str, float]:
    mapped = {
        PROB_KEY_BY_CLASS[CLASS_HOME]: 0.0,
        PROB_KEY_BY_CLASS[CLASS_DRAW]: 0.0,
        PROB_KEY_BY_CLASS[CLASS_AWAY]: 0.0
    }
    for index, class_name in enumerate(classes):
        key = PROB_KEY_BY_CLASS.get(str(class_name))
        if key is None:
            continue
        mapped[key] = float(proba_row[index])
    total = sum(mapped.values())
    if total > 0:
        mapped = {key: value / total for key, value in mapped.items()}
    return mapped


def _final_assessment(probabilities: dict[str, float]) -> str:
    ordered = [
        (ASSESSMENT_HOME, probabilities["home_played_better_probability"]),
        (ASSESSMENT_DRAW, probabilities["draw_probability"]),
        (ASSESSMENT_AWAY, probabilities["away_played_better_probability"])
    ]
    ordered.sort(key=lambda item: item[1], reverse=True)
    return ordered[0][0]


def _confidence(probabilities: dict[str, float]) -> float:
    values = sorted(probabilities.values(), reverse=True)
    if len(values) < 2:
        return float(values[0]) if values else 0.0
    return float(values[0] - values[1])


def _predict_frame(
        raw: pd.DataFrame,
        config: ModelRunConfig,
        model: Any,
        feature_columns: list[str],
        model_id: int) -> list[PredictionResult]:
    if raw.empty:
        return []
    feature_builder = get_feature_builder(config.feature_builder)
    features = feature_builder.build_features(raw, config.feature_config)
    if features.empty:
        logger.warning("No usable rows after feature build")
        return []

    labeler = get_labeler(config.labeler, config)
    labels = labeler.build_labels(features)
    merged = features.merge(
        labels[["match_id", "dominance_score"]],
        on="match_id",
        how="left")

    missing = [col for col in feature_columns if col not in merged.columns]
    if missing:
        raise ValueError(f"Missing feature columns for prediction: {missing}")

    x_frame = merged[feature_columns]
    proba = model.predict_proba(x_frame)
    classes = [str(item) for item in model.classes_]
    results: list[PredictionResult] = []
    for row_index, (_, row) in enumerate(merged.iterrows()):
        probabilities = _probability_map(classes, proba[row_index])
        final_key = _final_assessment(probabilities)
        snapshot = build_feature_snapshot(row)
        results.append(PredictionResult(
            match_id=int(row["match_id"]),
            model_id=model_id,
            probabilities=probabilities,
            final_event_key=final_key,
            feature_snapshot=snapshot,
            confidence=_confidence(probabilities),
            dominance_score=(
                float(row["dominance_score"])
                if pd.notna(row.get("dominance_score")) else None),
            model_version=config.model_version,
            assessment_type=config.assessment_type,
            sport_id=config.sport_id,
            artifact_path=str(config.artifact_dir)))
    return results


def predict_match(
        match_id: int,
        config: ModelRunConfig) -> PredictionResult:
    """Assess a single finished match and return probabilities."""
    # filtr xG tylko przy treningu — assess ma działać na dowolnym meczu
    raw = fetch_match_stats(match_id)
    if raw.empty:
        raise ValueError(f"Match {match_id} not found")
    if int(raw.iloc[0]["sport_id"]) != config.sport_id:
        raise ValueError(
            f"Match {match_id} sport_id does not match config sport_id")
    model_id = resolve_model_id(config.model_name)
    model = artifacts.load_model_artifact(config.artifact_dir)
    feature_columns = artifacts.load_feature_columns(config.artifact_dir)
    results = _predict_frame(raw, config, model, feature_columns, model_id)
    if not results:
        raise ValueError(
            f"Match {match_id} rejected: missing required statistics")
    return results[0]


def predict_batch(
        match_ids: list[int],
        config: ModelRunConfig,
        write: bool = False) -> list[PredictionResult]:
    """Assess multiple matches and optionally persist assessments."""
    raw = fetch_matches_by_ids(match_ids)
    if raw.empty:
        return []
    raw = raw.loc[raw["sport_id"] == config.sport_id]
    model_id = resolve_model_id(config.model_name)
    model = artifacts.load_model_artifact(config.artifact_dir)
    feature_columns = artifacts.load_feature_columns(config.artifact_dir)
    results = _predict_frame(raw, config, model, feature_columns, model_id)
    if write and results:
        from models.pipeline.persistence.match_assessment_writer import (
            write_match_assessments)
        write_match_assessments(results)
    return results


def predict_season_batch(
        season_id: int,
        config: ModelRunConfig,
        write: bool = False) -> list[PredictionResult]:
    """Assess finished matches for a season and optionally write DB rows."""
    required = (
        config.feature_config.required_columns
        or config.required_columns)
    # bez filtra xG — porównanie V1 vs NOXG na tych samych meczach
    raw = fetch_matches_by_season(
        config.sport_id,
        season_id,
        required)
    if raw.empty:
        logger.info("No matches found for season_id=%s", season_id)
        return []
    model_id = resolve_model_id(config.model_name)
    model = artifacts.load_model_artifact(config.artifact_dir)
    feature_columns = artifacts.load_feature_columns(config.artifact_dir)
    results = _predict_frame(raw, config, model, feature_columns, model_id)
    skipped = len(raw) - len(results)
    if skipped:
        logger.info(
            "Skipped %s season matches without usable features", skipped)
    if write and results:
        from models.pipeline.persistence.match_assessment_writer import (
            write_match_assessments)
        write_match_assessments(results)
    return results