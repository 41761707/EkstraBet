"""SQL repository for football match statistics used by ML models."""

from __future__ import annotations

import logging

import pandas as pd

from backend.database import get_db_connection
from models.pipeline.core.config import ModelRunConfig

logger = logging.getLogger(__name__)

_MATCH_STAT_COLUMNS = [
    "id",
    "league",
    "season",
    "home_team",
    "away_team",
    "game_date",
    "round",
    "sport_id",
    "home_team_goals",
    "away_team_goals",
    "result",
    "home_team_xg",
    "away_team_xg",
    "home_team_bp",
    "away_team_bp",
    "home_team_sc",
    "away_team_sc",
    "home_team_sog",
    "away_team_sog",
    "home_team_fk",
    "away_team_fk",
    "home_team_ck",
    "away_team_ck",
    "home_team_off",
    "away_team_off",
    "home_team_fouls",
    "away_team_fouls",
    "home_team_yc",
    "away_team_yc",
    "home_team_rc",
    "away_team_rc"
]

_MINIMAL_REQUIRED = [
    "home_team_sc",
    "away_team_sc",
    "home_team_sog",
    "away_team_sog",
    "home_team_bp",
    "away_team_bp",
    "home_team_ck",
    "away_team_ck"
]

_XG_COLUMNS = ("home_team_xg", "away_team_xg")


def _select_clause() -> str:
    return ",\n        ".join(f"m.{column}" for column in _MATCH_STAT_COLUMNS)


def _finished_match_filter() -> str:
    return "m.result <> '0'"


def _required_stats_filter(required_columns: list[str]) -> str:
    columns = required_columns or _MINIMAL_REQUIRED
    return " AND ".join(f"m.{column} IS NOT NULL" for column in columns)


def _xg_positive_sql() -> str:
    # xG=0 bywa znacznikiem braku danych z ligi, nie zerowej jakości szans
    return "m.home_team_xg > 0 AND m.away_team_xg > 0"


def _xg_filter(
        require_positive_xg: bool = False,
        exclude_positive_xg: bool = False) -> str | None:
    """Return optional SQL predicate for the xG availability."""
    if require_positive_xg and exclude_positive_xg:
        raise ValueError(
            "require_positive_xg and exclude_positive_xg are mutually exclusive")
    if require_positive_xg:
        return _xg_positive_sql()
    if exclude_positive_xg:
        return f"NOT ({_xg_positive_sql()})"
    return None


def _append_xg_filter(
        clauses: list[str],
        require_positive_xg: bool = False,
        exclude_positive_xg: bool = False) -> None:
    xg_filter = _xg_filter(require_positive_xg, exclude_positive_xg)
    if xg_filter:
        clauses.append(xg_filter)


def _normalize_zero_xg_as_missing(frame: pd.DataFrame) -> pd.DataFrame:
    """Treat non-positive xG as missing so required-column checks stay consistent."""
    if frame.empty:
        return frame
    working = frame.copy()
    for column in _XG_COLUMNS:
        if column not in working.columns:
            continue
        numeric = pd.to_numeric(working[column], errors="coerce")
        working[column] = numeric.mask(numeric <= 0)
    return working


def _resolve_required_columns(config: ModelRunConfig) -> list[str]:
    return (
        config.feature_config.required_columns
        or config.required_columns
        or _MINIMAL_REQUIRED)


def _resolve_xg_flags(
        config: ModelRunConfig | None = None,
        require_positive_xg: bool | None = None,
        exclude_positive_xg: bool | None = None
) -> tuple[bool, bool]:
    if require_positive_xg is None:
        require_positive_xg = (
            config.feature_config.require_positive_xg if config else False)
    if exclude_positive_xg is None:
        exclude_positive_xg = (
            config.feature_config.exclude_positive_xg if config else False)
    return bool(require_positive_xg), bool(exclude_positive_xg)


def fetch_training_matches(config: ModelRunConfig) -> pd.DataFrame:
    """Fetch finished football matches with required match statistics."""
    required = _resolve_required_columns(config)
    require_xg, exclude_xg = _resolve_xg_flags(config)
    where_parts = [
        "m.sport_id = %s",
        _finished_match_filter(),
        _required_stats_filter(required)
    ]
    _append_xg_filter(where_parts, require_xg, exclude_xg)
    query = f"""
        SELECT
            {_select_clause()}
        FROM matches m
        WHERE {" AND ".join(where_parts)}
        ORDER BY m.game_date, m.id
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(config.sport_id,))
    frame = _normalize_zero_xg_as_missing(frame)
    logger.info("Fetched %s training matches for %s", len(frame), config.model_name)
    return frame


def fetch_match_stats(
        match_id: int,
        require_positive_xg: bool = False,
        exclude_positive_xg: bool = False) -> pd.DataFrame:
    """Fetch a single match row for assessment."""
    where_parts = ["m.id = %s"]
    _append_xg_filter(where_parts, require_positive_xg, exclude_positive_xg)
    query = f"""
        SELECT
            {_select_clause()}
        FROM matches m
        WHERE {" AND ".join(where_parts)}
        LIMIT 1
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(match_id,))
    return _normalize_zero_xg_as_missing(frame)


def fetch_matches_by_ids(
        match_ids: list[int],
        require_positive_xg: bool = False,
        exclude_positive_xg: bool = False) -> pd.DataFrame:
    """Fetch multiple match rows by primary key."""
    if not match_ids:
        return pd.DataFrame(columns=_MATCH_STAT_COLUMNS)
    placeholders = ", ".join(["%s"] * len(match_ids))
    where_parts = [f"m.id IN ({placeholders})"]
    _append_xg_filter(where_parts, require_positive_xg, exclude_positive_xg)
    query = f"""
        SELECT
            {_select_clause()}
        FROM matches m
        WHERE {" AND ".join(where_parts)}
        ORDER BY m.game_date, m.id
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(match_ids))
    return _normalize_zero_xg_as_missing(frame)


def fetch_matches_by_season(
        sport_id: int,
        season_id: int,
        required_columns: list[str] | None = None,
        require_positive_xg: bool = False,
        exclude_positive_xg: bool = False) -> pd.DataFrame:
    """Fetch finished matches for a season primary key."""
    required = required_columns or _MINIMAL_REQUIRED
    where_parts = [
        "m.sport_id = %s",
        "m.season = %s",
        _finished_match_filter(),
        _required_stats_filter(required)
    ]
    _append_xg_filter(where_parts, require_positive_xg, exclude_positive_xg)
    query = f"""
        SELECT
            {_select_clause()}
        FROM matches m
        WHERE {" AND ".join(where_parts)}
        ORDER BY m.game_date, m.id
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=(sport_id, season_id))
    return _normalize_zero_xg_as_missing(frame)
