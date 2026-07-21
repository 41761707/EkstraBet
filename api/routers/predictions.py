"""Prediction read endpoints for the EkstraBet API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Path, Query

from api.schemas.prediction import (
    MatchPredictionListResponse,
    PredictionPreviewRequest,
    PredictionPreviewResponse,
    PredictionSearchResponse,
    TeamPredictionListResponse)
from api.routers.utils import parse_id_list
from backend.config import get_settings
from backend.services import prediction_service
from backend.services import prediction_preview_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/", tags=["System"])
async def predictions_info() -> dict[str, object]:
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Predictions API",
        "version": "1.0.0",
        "description": "Read-only endpoints for model predictions",
        "endpoints": [
            "GET /predictions/search - Search predictions with filters",
            "GET /predictions/team/{team_id}/{season_id} - Team predictions",
            "GET /predictions/match/{match_id} - Final match predictions",
            "POST /predictions/preview - Preview future-event predictions",
        ],
    }


@router.post(
    "/preview",
    response_model=PredictionPreviewResponse,
    summary="Preview a future football match",
    description=(
        "Runs synchronous local ML inference for a home and away team. "
        "Requires EKSTRABET_ML_PREVIEW=1"),
    responses={
        409: {"description": "Insufficient team match history"},
        503: {"description": "ML preview is disabled"}
    })
async def preview_prediction(
    request: PredictionPreviewRequest
) -> PredictionPreviewResponse:
    """Return future-event probabilities for an arbitrary team pair."""
    if not get_settings().ekstrabet_ml_preview:
        raise HTTPException(
            status_code=503,
            detail=(
                "ML prediction preview is disabled. "
                "Set EKSTRABET_ML_PREVIEW=1 to enable local inference"))

    try:
        payload = prediction_preview_service.preview_prediction(
            home_team_id=request.home_team_id,
            away_team_id=request.away_team_id,
            league_id=request.league_id,
            as_of_date=request.as_of_date)
        return PredictionPreviewResponse(**payload)
    except prediction_preview_service.PredictionPreviewHistoryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to generate prediction preview")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate prediction preview") from exc


@router.get("/search", response_model=PredictionSearchResponse)
async def search_predictions(
    match_id: int | None = Query(
        None,
        ge=1,
        description="Optional match ID filter"),
    event_id: int | None = Query(
        None,
        ge=1,
        description="Optional event ID filter"),
    model_ids: str | None = Query(
        None,
        description="Comma-separated model IDs, e.g. '1,2,3'"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int | None = Query(
        None,
        ge=1,
        description="Page size")) -> PredictionSearchResponse:
    """Search raw predictions with optional filters and pagination."""
    settings = get_settings()
    resolved_page_size = page_size or settings.default_page_size
    if resolved_page_size > settings.max_page_size:
        raise HTTPException(
            status_code=422,
            detail=f"page_size cannot exceed {settings.max_page_size}")

    parsed_model_ids = parse_id_list(model_ids)

    try:
        payload = prediction_service.search_predictions(
            match_id=match_id,
            event_id=event_id,
            model_ids=parsed_model_ids,
            page=page,
            page_size=resolved_page_size)
        return PredictionSearchResponse(**payload)
    except Exception as exc:
        logger.error("Failed to search predictions: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to search predictions") from exc


@router.get(
    "/team/{team_id}/{season_id}",
    response_model=TeamPredictionListResponse)
async def get_team_predictions(
    team_id: int = Path(..., ge=1, description="Team ID"),
    season_id: int = Path(..., ge=1, description="Season ID")
) -> TeamPredictionListResponse:
    """Return evaluated final predictions for a team in a season."""
    try:
        payload = prediction_service.get_team_predictions(
            team_id,
            season_id)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"Team {team_id} or season {season_id} not found")
        return TeamPredictionListResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch team predictions for %s/%s: %s",
            team_id,
            season_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch team predictions") from exc


@router.get(
    "/match/{match_id}",
    response_model=MatchPredictionListResponse)
async def get_match_predictions(
    match_id: int = Path(..., ge=1, description="Match ID"),
    model_ids: str | None = Query(
        None,
        description="Comma-separated model IDs, e.g. '1,2,3'")
) -> MatchPredictionListResponse:
    """Return final predictions for a match with event family metadata."""
    parsed_model_ids = parse_id_list(model_ids)

    try:
        payload = prediction_service.get_match_predictions(
            match_id,
            model_ids=parsed_model_ids)
        if payload is None:
            raise HTTPException(
                status_code=404,
                detail=f"Match {match_id} not found")
        return MatchPredictionListResponse(**payload)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch match predictions for %s: %s",
            match_id,
            exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch match predictions") from exc
