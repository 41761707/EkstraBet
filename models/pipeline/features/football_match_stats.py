"""Football match statistics feature extraction."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from models.pipeline.core.config import FeatureConfig
from models.pipeline.core.registry import register_feature_builder

logger = logging.getLogger(__name__)

RESULT_COLUMNS = ["home_team_goals", "away_team_goals", "result"]

BASE_FEATURE_COLUMNS = [
    "possession_diff",
    "shots_diff",
    "shots_on_goal_diff",
    "corners_diff",
    "free_kicks_diff",
    "offsides_diff",
    "fouls_diff",
    "yellow_cards_diff",
    "red_cards_diff",
    "total_shots",
    "total_shots_on_goal",
    "total_corners",
    "total_cards",
    "home_shots_share",
    "home_sog_share",
    "home_corners_share",
    "home_possession_share",
    "home_sog_per_shot",
    "away_sog_per_shot"
]

FEATURE_COLUMNS = [
    "xg_diff",
    "possession_diff",
    "shots_diff",
    "shots_on_goal_diff",
    "corners_diff",
    "free_kicks_diff",
    "offsides_diff",
    "fouls_diff",
    "yellow_cards_diff",
    "red_cards_diff",
    "total_xg",
    "total_shots",
    "total_shots_on_goal",
    "total_corners",
    "total_cards",
    "home_xg_share",
    "home_shots_share",
    "home_sog_share",
    "home_corners_share",
    "home_possession_share",
    "home_sog_per_shot",
    "away_sog_per_shot",
    "xg_per_shot_home",
    "xg_per_shot_away"
]

DEFAULT_REQUIRED_COLUMNS = [
    "home_team_xg",
    "away_team_xg",
    "home_team_sc",
    "away_team_sc",
    "home_team_sog",
    "away_team_sog",
    "home_team_bp",
    "away_team_bp",
    "home_team_ck",
    "away_team_ck"
]

DEFAULT_IMPUTABLE_COLUMNS = [
    "home_team_fk",
    "away_team_fk",
    "home_team_off",
    "away_team_off",
    "home_team_fouls",
    "away_team_fouls",
    "home_team_yc",
    "away_team_yc",
    "home_team_rc",
    "away_team_rc"
]


def _safe_share(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = denominator.replace(0, np.nan)
    share = numerator / denom
    return share.fillna(0.5)


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = denominator.replace(0, np.nan)
    ratio = numerator / denom
    return ratio.fillna(0.0)


def _normalize_zero_xg_as_missing(frame: pd.DataFrame) -> pd.DataFrame:
    """Map non-positive xG to NaN before required-column filtering."""
    working = frame.copy()
    for column in ("home_team_xg", "away_team_xg"):
        if column not in working.columns:
            continue
        numeric = pd.to_numeric(working[column], errors="coerce")
        working[column] = numeric.mask(numeric <= 0)
    return working


def _config_requests_xg(config: FeatureConfig) -> bool:
    """True when model config opts into xG-derived features."""
    if config.exclude_positive_xg:
        return False
    if config.require_positive_xg:
        return True
    required = config.required_columns or DEFAULT_REQUIRED_COLUMNS
    if "home_team_xg" in required or "away_team_xg" in required:
        return True
    if config.source_columns and (
            "home_team_xg" in config.source_columns
            or "away_team_xg" in config.source_columns):
        return True
    return False


def _filter_usable_rows(
        frame: pd.DataFrame,
        config: FeatureConfig) -> tuple[pd.DataFrame, int]:
    """Drop rows missing required stats; optionally impute softer columns."""
    working = _normalize_zero_xg_as_missing(frame)
    required = config.required_columns or DEFAULT_REQUIRED_COLUMNS
    before = len(working)
    if config.sport_id is not None and "sport_id" in working.columns:
        working = working.loc[working["sport_id"] == config.sport_id]
    for column in required:
        if column not in working.columns:
            raise KeyError(f"Missing required source column: {column}")
        working = working.loc[working[column].notna()]
    imputable = config.imputable_columns or DEFAULT_IMPUTABLE_COLUMNS
    for column in imputable:
        if column in working.columns:
            working[column] = working[column].fillna(0)
    skipped = before - len(working)
    if skipped:
        logger.info("Skipped %s matches without required stats", skipped)
    return working, skipped


@register_feature_builder("FootballMatchStatsFeatureBuilder")
class FootballMatchStatsFeatureBuilder:
    """Build symmetric home-vs-away features from matches stats."""

    def build_features(
            self,
            frame: pd.DataFrame,
            config: FeatureConfig) -> pd.DataFrame:
        """Return numeric model features aligned with input rows."""
        return build_features(frame, config)


def resolve_feature_columns(
        available_columns: pd.Index | list[str],
        include_goals: bool = False) -> list[str]:
    """Return ordered model feature columns present in the frame."""
    columns = list(FEATURE_COLUMNS)
    if include_goals:
        columns.append("goals_diff")
    available = set(available_columns)
    return [column for column in columns if column in available]


def build_features(
        frame: pd.DataFrame,
        config: FeatureConfig | None = None) -> pd.DataFrame:
    """Create numeric football match features from raw match rows."""
    feature_config = config or FeatureConfig(
        required_columns=DEFAULT_REQUIRED_COLUMNS,
        imputable_columns=DEFAULT_IMPUTABLE_COLUMNS)
    usable, _skipped = _filter_usable_rows(frame, feature_config)
    # xG tylko gdy config tego chce — nie gdy w batchu „gdzieś” jest non-null
    include_xg = _config_requests_xg(feature_config)
    output_columns = ["match_id", *BASE_FEATURE_COLUMNS]
    if include_xg:
        # zachowujemy kolejność FEATURE_COLUMNS dla kompatybilności artefaktów
        output_columns = ["match_id", *FEATURE_COLUMNS]
    if feature_config.include_goals_as_features:
        output_columns.append("goals_diff")
    if usable.empty:
        return pd.DataFrame(columns=output_columns)

    home_bp = usable["home_team_bp"].astype(float)
    away_bp = usable["away_team_bp"].astype(float)
    home_sc = usable["home_team_sc"].astype(float)
    away_sc = usable["away_team_sc"].astype(float)
    home_sog = usable["home_team_sog"].astype(float)
    away_sog = usable["away_team_sog"].astype(float)
    home_ck = usable["home_team_ck"].astype(float)
    away_ck = usable["away_team_ck"].astype(float)
    home_fk = usable.get("home_team_fk", 0)
    away_fk = usable.get("away_team_fk", 0)
    home_off = usable.get("home_team_off", 0)
    away_off = usable.get("away_team_off", 0)
    home_fouls = usable.get("home_team_fouls", 0)
    away_fouls = usable.get("away_team_fouls", 0)
    home_yc = usable.get("home_team_yc", 0)
    away_yc = usable.get("away_team_yc", 0)
    home_rc = usable.get("home_team_rc", 0)
    away_rc = usable.get("away_team_rc", 0)

    features = pd.DataFrame(index=usable.index)
    features["match_id"] = usable["id"].astype(int)
    if include_xg:
        home_xg = usable["home_team_xg"].astype(float)
        away_xg = usable["away_team_xg"].astype(float)
        features["xg_diff"] = home_xg - away_xg
        features["total_xg"] = home_xg + away_xg
        features["home_xg_share"] = _safe_share(home_xg, home_xg + away_xg)
        features["xg_per_shot_home"] = _safe_ratio(home_xg, home_sc)
        features["xg_per_shot_away"] = _safe_ratio(away_xg, away_sc)
    features["possession_diff"] = home_bp - away_bp
    features["shots_diff"] = home_sc - away_sc
    features["shots_on_goal_diff"] = home_sog - away_sog
    features["corners_diff"] = home_ck - away_ck
    features["free_kicks_diff"] = (
        pd.Series(home_fk, index=usable.index).astype(float)
        - pd.Series(away_fk, index=usable.index).astype(float))
    features["offsides_diff"] = (
        pd.Series(home_off, index=usable.index).astype(float)
        - pd.Series(away_off, index=usable.index).astype(float))
    features["fouls_diff"] = (
        pd.Series(home_fouls, index=usable.index).astype(float)
        - pd.Series(away_fouls, index=usable.index).astype(float))
    features["yellow_cards_diff"] = (
        pd.Series(home_yc, index=usable.index).astype(float)
        - pd.Series(away_yc, index=usable.index).astype(float))
    features["red_cards_diff"] = (
        pd.Series(home_rc, index=usable.index).astype(float)
        - pd.Series(away_rc, index=usable.index).astype(float))
    features["total_shots"] = home_sc + away_sc
    features["total_shots_on_goal"] = home_sog + away_sog
    features["total_corners"] = home_ck + away_ck
    features["total_cards"] = (
        pd.Series(home_yc, index=usable.index).astype(float)
        + pd.Series(away_yc, index=usable.index).astype(float)
        + pd.Series(home_rc, index=usable.index).astype(float)
        + pd.Series(away_rc, index=usable.index).astype(float))
    features["home_shots_share"] = _safe_share(home_sc, home_sc + away_sc)
    features["home_sog_share"] = _safe_share(home_sog, home_sog + away_sog)
    features["home_corners_share"] = _safe_share(home_ck, home_ck + away_ck)
    features["home_possession_share"] = _safe_share(home_bp, home_bp + away_bp)
    features["home_sog_per_shot"] = _safe_ratio(home_sog, home_sc)
    features["away_sog_per_shot"] = _safe_ratio(away_sog, away_sc)

    if feature_config.include_goals_as_features:
        features["goals_diff"] = (
            usable["home_team_goals"].astype(float)
            - usable["away_team_goals"].astype(float))

    return features.reset_index(drop=True)


def build_feature_snapshot(
        feature_row: pd.Series,
        exclude_result: bool = True) -> dict[str, float]:
    """Serialize a feature row for DB audit without result columns."""
    snapshot: dict[str, float] = {}
    for key, value in feature_row.items():
        if key == "match_id":
            continue
        if exclude_result and key in RESULT_COLUMNS:
            continue
        if pd.isna(value):
            continue
        snapshot[str(key)] = float(value)
    return snapshot
