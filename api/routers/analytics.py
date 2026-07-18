"""Analytics endpoints for model effectiveness statistics."""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from api.routers.utils import parse_id_list
from api.schemas.analytics import ModelAnalyticsResponse
from backend.services import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

#TODO: To najlepiej pobierać jakoś z bazy / configów, nie lubię stałych w kodzie
StatTypeFilter = Literal["ou", "btts", "result", "all"]
GroupByFilter = Literal["none", "team", "league"]
AggregationMetricFilter = Literal["accuracy", "profit"]


@router.get("/", tags=["System"])
async def analytics_info() -> dict[str, object]:
    """Zwraca metadane modułu i dostępne endpointy."""
    return {
        "module": "EkstraBet Analytics API",
        "version": "1.0.0",
        "description": (
            "Model effectiveness statistics for OU, BTTS and 1X2"),
        "endpoints": [
            "GET /analytics/models - Model prediction and bet statistics",
        ],
    }


@router.get("/models", response_model=ModelAnalyticsResponse)
async def get_model_statistics(
    stat_type: StatTypeFilter = Query(
        "all",
        description="Stat family to include"),
    model_result_ids: str | None = Query(
        None,
        description="Comma-separated REZULTAT model IDs"),
    model_ou_ids: str | None = Query(
        None,
        description="Comma-separated OU model IDs"),
    model_btts_ids: str | None = Query(
        None,
        description="Comma-separated BTTS model IDs"),
    league_ids: str | None = Query(
        None,
        description="Comma-separated league IDs"),
    season_id: int | None = Query(
        None,
        ge=1,
        description="Season ID filter"),
    date_from: date | None = Query(
        None,
        description="Inclusive start date"),
    date_to: date | None = Query(
        None,
        description="Inclusive end date"),
    round_from: int | None = Query(
        None,
        ge=1,
        description="Inclusive start round"),
    round_to: int | None = Query(
        None,
        ge=1,
        description="Inclusive end round"),
    team_id: int | None = Query(
        None,
        ge=1,
        description="Filter matches involving this team"),
    settled_only: bool = Query(
        True,
        description="Only include finished matches"),
    positive_ev_only: bool = Query(
        False,
        description="Only include bets with positive EV"),
    apply_tax: bool = Query(
        False,
        description="Apply 12% betting tax to profit calculations"),
    group_by: GroupByFilter = Query(
        "none",
        description="Optional aggregation dimension"),
    aggregation_metric: AggregationMetricFilter = Query(
        "accuracy",
        description="Metric used for league/team aggregations"),
    include_league_characteristics: bool = Query(
        False,
        description=(
            "Include actual OU/BTTS/1X2 league distribution "
            "when one league is selected"))) -> ModelAnalyticsResponse:
    """Zwraca statystyki efektywności modeli dla wykresów i tabel."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from cannot be later than date_to")

    if round_from is not None and round_to is not None and round_from > round_to:
        raise HTTPException(
            status_code=422,
            detail="round_from cannot be later than round_to")

    parsed_league_ids = parse_id_list(league_ids)
    if group_by == "team" and (
        not parsed_league_ids or len(parsed_league_ids) != 1
    ):
        raise HTTPException(
            status_code=422,
            detail="group_by=team requires exactly one league_id")

    if group_by in ("team", "league") and season_id is None:
        raise HTTPException(
            status_code=422,
            detail="group_by requires season_id")

    try:
        payload = analytics_service.get_model_statistics(
            stat_type=stat_type,
            model_result_ids=parse_id_list(model_result_ids),
            model_ou_ids=parse_id_list(model_ou_ids),
            model_btts_ids=parse_id_list(model_btts_ids),
            league_ids=parsed_league_ids,
            season_id=season_id,
            date_from=date_from,
            date_to=date_to,
            round_from=round_from,
            round_to=round_to,
            team_id=team_id,
            settled_only=settled_only,
            positive_ev_only=positive_ev_only,
            apply_tax=apply_tax,
            group_by=group_by,
            aggregation_metric=aggregation_metric,
            include_league_characteristics=include_league_characteristics)
        return ModelAnalyticsResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch model analytics: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch model analytics") from exc
