"""Weak labels for football played-better assessment."""

from __future__ import annotations

import numpy as np
import pandas as pd

from models.pipeline.core.config import LabelerConfig
from models.pipeline.core.registry import register_labeler
from models.pipeline.features.football_match_stats import build_features

CLASS_HOME = "home_better"
CLASS_DRAW = "draw"
CLASS_AWAY = "away_better"
CLASS_LABELS = [CLASS_HOME, CLASS_DRAW, CLASS_AWAY]

ASSESSMENT_HOME = "HOME_PLAYED_BETTER"
ASSESSMENT_DRAW = "DRAW"
ASSESSMENT_AWAY = "AWAY_PLAYED_BETTER"

CLASS_TO_ASSESSMENT = {
    CLASS_HOME: ASSESSMENT_HOME,
    CLASS_DRAW: ASSESSMENT_DRAW,
    CLASS_AWAY: ASSESSMENT_AWAY
}

DEFAULT_WEIGHTS = {
    "xg_diff": 3.0,
    "shots_diff": 1.0,
    "shots_on_goal_diff": 1.2,
    "possession_diff": 0.8,
    "corners_diff": 0.6,
    "free_kicks_diff": 0.2,
    "offsides_diff": -0.1,
    "fouls_diff": -0.4,
    "yellow_cards_diff": -0.5,
    "red_cards_diff": -1.5
}

# skale wyrównują jednostki (xG vs posiadanie vs strzały)
DIFF_SCALES = {
    "xg_diff": 1.0,
    "shots_diff": 10.0,
    "shots_on_goal_diff": 5.0,
    "possession_diff": 100.0,
    "corners_diff": 5.0,
    "free_kicks_diff": 10.0,
    "offsides_diff": 5.0,
    "fouls_diff": 10.0,
    "yellow_cards_diff": 1.0,
    "red_cards_diff": 1.0
}


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def compute_dominance_score(
        features: pd.DataFrame,
        weights: dict[str, float] | None = None) -> pd.Series:
    """Compute weighted home dominance score from engineered features."""
    resolved = {**DEFAULT_WEIGHTS, **(weights or {})}
    score = pd.Series(0.0, index=features.index, dtype=float)
    for column, weight in resolved.items():
        if column not in features.columns:
            continue
        scale = DIFF_SCALES.get(column, 1.0)
        score = score + weight * (features[column].astype(float) / scale)
    return score


def soft_probabilities_from_score(
        score: pd.Series,
        temperature: float = 1.0) -> pd.DataFrame:
    """Map dominance score to home/draw/away soft probabilities."""
    temp = max(float(temperature), 1e-6)
    scaled = score.to_numpy(dtype=float) / temp
    home_raw = _sigmoid(scaled)
    away_raw = _sigmoid(-scaled)
    # remis wzmacniany blisko zera (gauss w przestrzeni score/T)
    draw_raw = np.exp(-0.5 * scaled ** 2)
    total = home_raw + away_raw + draw_raw
    total = np.where(total == 0.0, 1.0, total)
    return pd.DataFrame({
        "home_prob": home_raw / total,
        "draw_prob": draw_raw / total,
        "away_prob": away_raw / total
    }, index=score.index)


def hard_label_from_score(
        score: pd.Series,
        draw_threshold: float = 0.15) -> pd.Series:
    """Assign hard weak labels from absolute dominance threshold."""
    labels = pd.Series(CLASS_DRAW, index=score.index, dtype=object)
    labels = labels.mask(score >= draw_threshold, CLASS_HOME)
    labels = labels.mask(score <= -draw_threshold, CLASS_AWAY)
    return labels


def _is_feature_frame(frame: pd.DataFrame) -> bool:
    """True when frame already has engineered model features."""
    if "match_id" not in frame.columns:
        return False
    return (
        "possession_diff" in frame.columns
        or "shots_diff" in frame.columns
        or "xg_diff" in frame.columns)


@register_labeler("FootballPlayedBetterLabeler")
class FootballPlayedBetterLabeler:
    """Generate weak labels and soft targets for played-better training."""

    def __init__(self, config: LabelerConfig | None = None) -> None:
        self.config = config or LabelerConfig(weights=DEFAULT_WEIGHTS)
        if not self.config.weights:
            self.config.weights = dict(DEFAULT_WEIGHTS)

    def build_labels(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Build labels from raw match rows or engineered features."""
        return build_labels(frame, self.config)


def build_labels(
        frame: pd.DataFrame,
        config: LabelerConfig | None = None) -> pd.DataFrame:
    """Create weak labels and soft probabilities from match stats."""
    labeler_config = config or LabelerConfig(weights=DEFAULT_WEIGHTS)
    weights = labeler_config.weights or DEFAULT_WEIGHTS
    # NOXG nie ma xg_diff — nie wolno wtedy rebuildować rawem bez FeatureConfig
    if _is_feature_frame(frame):
        features = frame
    else:
        features = build_features(frame)
    if features.empty:
        return pd.DataFrame(columns=[
            "match_id",
            "dominance_score",
            "label",
            "home_prob",
            "draw_prob",
            "away_prob"
        ])

    score = compute_dominance_score(features, weights)
    probs = soft_probabilities_from_score(score, labeler_config.temperature)
    labels = hard_label_from_score(score, labeler_config.draw_threshold)
    result = pd.DataFrame({
        "match_id": features["match_id"].astype(int),
        "dominance_score": score.astype(float),
        "label": labels,
        "home_prob": probs["home_prob"],
        "draw_prob": probs["draw_prob"],
        "away_prob": probs["away_prob"]
    })
    return result.reset_index(drop=True)
