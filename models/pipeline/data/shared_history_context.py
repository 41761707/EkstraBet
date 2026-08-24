"""Shared in-memory history for one future-events predict batch."""

from __future__ import annotations

import json
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from typing import Any

import pandas as pd

from models.pipeline.core.config import FutureEventsRunConfig
from models.pipeline.data.match_history_repository import (
    fetch_finished_matches)
from models.pipeline.data.match_history_repository import (
    fetch_league_context)
from models.pipeline.features.ratings import compute_ratings_timeline


@dataclass(frozen=True)
class FeatureSignature:
    """Identity of the feature tensor layout for one model family."""

    feature_builder: str
    window_size: int
    ratings_key: str
    sequence_feature_columns: tuple[str, ...]
    static_feature_columns: tuple[str, ...]


@dataclass
class SharedHistoryContext:
    """In-memory history and ratings for one predict batch."""

    sport_id: int
    finished_matches: pd.DataFrame
    ratings_timeline: pd.DataFrame
    league_tiers: dict[int, int | None]
    max_as_of_date: date
    ratings_by_key: dict[str, pd.DataFrame] | None = None


def _ratings_key(params: Mapping[str, Any] | None) -> str:
    """Return a canonical JSON dump of rating parameters."""
    return json.dumps(params or {}, sort_keys=True, default=str)


def _as_date(value: date | datetime) -> date:
    """Normalize a datetime cutoff to a calendar date."""
    if isinstance(value, datetime):
        return value.date()
    return value


def _unique_rating_params(
        rating_param_sets: Sequence[Mapping[str, Any] | None]
        ) -> dict[str, Mapping[str, Any]]:
    unique: dict[str, Mapping[str, Any]] = {}
    for params in rating_param_sets:
        key = _ratings_key(params)
        if key not in unique:
            unique[key] = params or {}
    return unique


def _league_tiers(sport_id: int) -> dict[int, int | None]:
    context = fetch_league_context(sport_id)
    tiers: dict[int, int | None] = {}
    for _, row in context.iterrows():
        league_id = int(row["league_id"])
        tier_value = row["tier"]
        if pd.notna(tier_value):
            tiers[league_id] = int(tier_value)
        else:
            tiers[league_id] = None
    return tiers


def feature_signature(config: FutureEventsRunConfig) -> FeatureSignature:
    """Build the identity of one model's feature tensor layout."""
    return FeatureSignature(
        feature_builder=config.feature_builder,
        window_size=config.window_size,
        ratings_key=_ratings_key(config.ratings),
        sequence_feature_columns=tuple(config.sequence_feature_columns),
        static_feature_columns=tuple(config.static_feature_columns))


def build_shared_history_context(
        sport_id: int,
        max_as_of: date | datetime,
        rating_param_sets: Sequence[Mapping[str, Any] | None]
        ) -> SharedHistoryContext:
    """Fetch finished matches once and compute unique rating timelines."""
    max_as_of_date = _as_date(max_as_of)
    finished_matches = fetch_finished_matches(sport_id, max_as_of)
    unique_params = _unique_rating_params(rating_param_sets)
    ratings_by_key: dict[str, pd.DataFrame] = {}
    for key, params in unique_params.items():
        ratings_by_key[key] = compute_ratings_timeline(
            finished_matches, params=params)
    # ratings_timeline zostaje w kontrakcie dataclass; źródłem prawdy jest mapa
    if ratings_by_key:
        ratings_timeline = next(iter(ratings_by_key.values()))
    else:
        ratings_timeline = pd.DataFrame()
    return SharedHistoryContext(
        sport_id=sport_id,
        finished_matches=finished_matches,
        ratings_timeline=ratings_timeline,
        league_tiers=_league_tiers(sport_id),
        max_as_of_date=max_as_of_date,
        ratings_by_key=ratings_by_key)
