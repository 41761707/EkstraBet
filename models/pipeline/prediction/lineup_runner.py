"""Predict a champion and challenger lineup and route the rows."""

from __future__ import annotations

from typing import Any

from models.pipeline.core.config import MatchupInput
from models.pipeline.core.model_lineup import LineupEntry
from models.pipeline.core.model_lineup import ModelLineup
from models.pipeline.core.model_roles import ModelRoles
from models.pipeline.core.model_roles import fetch_event_family_ids
from models.pipeline.core.registry import resolve_event_map
from models.pipeline.data.shared_history_context import SharedHistoryContext
from models.pipeline.persistence.prediction_writer import (
    map_predictions_to_rows)
from models.pipeline.persistence.prediction_writer import persist_routed_rows
from models.pipeline.persistence.prediction_writer import route_prediction_rows
from models.pipeline.prediction.future_events_predictor import FeatureCache
from models.pipeline.prediction.future_events_predictor import (
    FutureEventsPredictor)


_TASK_SLOTS = {
    "result": "result_config",
    "btts": "btts_config",
    "goals_poisson": "goals_config"}


def build_lineup_predictors(
        lineup: ModelLineup
        ) -> list[tuple[LineupEntry, FutureEventsPredictor]]:
    """Build one predictor per entry, slotted by ``task_type``."""
    return [
        (entry, _predictor_for(entry))
        for entry in lineup.entries]


def lineup_rating_params(lineup: ModelLineup) -> list[dict[str, Any]]:
    """Return rating parameters of every lineup config."""
    return [entry.config.ratings for entry in lineup.entries]


def lineup_event_families(
        predictors: list[tuple[LineupEntry, FutureEventsPredictor]]
        ) -> dict[int, int]:
    """Resolve every configured event id to a family, once per batch."""
    event_ids: list[int] = []
    for entry, _predictor in predictors:
        mapped = resolve_event_map(entry.config.events)
        event_ids.extend(mapped.values())
    return fetch_event_family_ids(event_ids)


def predict_lineup_pair(
        matchup: MatchupInput,
        predictors: list[tuple[LineupEntry, FutureEventsPredictor]],
        *,
        context: SharedHistoryContext | None,
        feature_cache: FeatureCache) -> dict[str, dict[str, object]]:
    """Predict every lineup model with one shared feature cache."""
    predictions: dict[str, dict[str, object]] = {}
    for entry, predictor in predictors:
        predictions[entry.model_name] = predictor.predict_pair(
            matchup,
            context=context,
            feature_cache=feature_cache)
    return predictions


def persist_lineup_prediction(
        matchup: MatchupInput,
        predictors: list[tuple[LineupEntry, FutureEventsPredictor]],
        predictions: dict[str, dict[str, object]],
        roles: ModelRoles,
        select_finals: bool,
        *,
        event_families: dict[int, int] | None = None) -> dict[str, int]:
    """Map, route and persist one matchup for the whole lineup.

    Pass ``event_families`` loaded once for the batch. When it is
    omitted, families are resolved here.
    """
    if matchup.match_id is None:
        raise ValueError("--write-db requires match_id for every pair")
    families = event_families
    if families is None:
        families = lineup_event_families(predictors)
    published = 0
    shadow = 0
    for entry, _predictor in predictors:
        rows = map_predictions_to_rows(
            matchup.match_id,
            predictions[entry.model_name],
            _model_ids(entry),
            resolve_event_map(entry.config.events),
            select_finals)
        # Zerujemy finał pretendenta zanim zapis otworzy transakcję.
        routed = route_prediction_rows(rows, roles, families)
        added_published, added_shadow = persist_routed_rows(
            [*routed.published, *routed.shadow],
            roles,
            families)
        published += added_published
        shadow += added_shadow
    return {"published": published, "shadow": shadow}


def _predictor_for(entry: LineupEntry) -> FutureEventsPredictor:
    slot = _TASK_SLOTS.get(entry.config.task_type)
    if slot is None:
        raise ValueError(
            f"Unsupported task_type {entry.config.task_type!r} "
            f"for {entry.model_name}")
    return FutureEventsPredictor(**{slot: entry.config})


def _model_ids(entry: LineupEntry) -> dict[str, int]:
    """Point every family of this predictor at the same model id."""
    return {entry.config.task_type: entry.model_id}
