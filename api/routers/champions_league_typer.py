"""Champions League Typer contest endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import Response, status

from api.deps import get_current_user, require_admin
from api.schemas.champions_league_typer import (
    PublishMatchesRequest,
    PublishMatchesResponse,
    SavePredictionRequest,
    SavePredictionResponse,
    TyperAdminCandidate,
    TyperAdminCandidatesResponse,
    TyperDashboardResponse,
    TyperLeaderboardRow,
    TyperPredictionChange,
    TyperPublication,
    TyperRevealedPredictionsResponse)
from backend.config import get_settings
from backend.services import champions_league_typer_service as typer_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/typer-lm", tags=["Typer LM"])

T = TypeVar("T")


def _invoke(operation: Callable[[], T]) -> T:
    """Run a service call and map domain errors to HTTP status codes."""
    try:
        return operation()
    except typer_service.TyperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)) from exc
    except typer_service.TyperConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)) from exc
    except typer_service.TyperValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Champions League Typer request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Champions League Typer request failed") from exc


def _user_id(user: dict[str, Any]) -> int:
    return int(user["id"])


@router.get("/dashboard", response_model=TyperDashboardResponse)
async def get_dashboard(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    season_id: int | None = Query(
        None,
        ge=1,
        description="Season ID; defaults to the league current season")
) -> TyperDashboardResponse:
    """Return published rounds, private picks, odds and own audit."""
    payload = _invoke(
        lambda: typer_service.get_dashboard(_user_id(user), season_id))
    return TyperDashboardResponse(**payload)


@router.get(
    "/revealed-predictions",
    response_model=TyperRevealedPredictionsResponse)
async def get_revealed_predictions(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    season_id: int | None = Query(
        None,
        ge=1,
        description="Season ID; defaults to the league current season"),
    round_number: int = Query(..., ge=1, description="Round number")
) -> TyperRevealedPredictionsResponse:
    """Return revealed 1X2 picks for started published matches."""
    _ = user
    payload = _invoke(
        lambda: typer_service.get_revealed_predictions(
            season_id, round_number))
    return TyperRevealedPredictionsResponse(**payload)


@router.put(
    "/predictions/{match_id}",
    response_model=SavePredictionResponse)
async def save_prediction(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    body: SavePredictionRequest,
    match_id: int = Path(..., ge=1, description="Published match ID")
) -> SavePredictionResponse:
    """Create or update the current user's 1X2 pick before kick-off."""
    payload = _invoke(
        lambda: typer_service.save_prediction(
            _user_id(user), match_id, body.outcome))
    return SavePredictionResponse(**payload)


@router.get(
    "/predictions/{match_id}/history",
    response_model=list[TyperPredictionChange])
async def get_own_prediction_history(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    match_id: int = Path(..., ge=1, description="Published match ID")
) -> list[TyperPredictionChange]:
    """Return chronological audit rows for the current user's pick."""
    rows = _invoke(
        lambda: typer_service.get_own_prediction_history(
            _user_id(user), match_id))
    return [TyperPredictionChange(**row) for row in rows]


@router.get(
    "/leaderboard",
    response_model=list[TyperLeaderboardRow])
async def get_leaderboard(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    season_id: int | None = Query(
        None,
        ge=1,
        description="Season ID; defaults to the league current season")
) -> list[TyperLeaderboardRow]:
    """Return ranking aggregates without exposing other users' picks."""
    _ = user
    rows = _invoke(lambda: typer_service.get_leaderboard(season_id))
    return [TyperLeaderboardRow(**row) for row in rows]


@router.get(
    "/admin/candidates",
    response_model=TyperAdminCandidatesResponse)
async def get_admin_candidates(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    season_id: int = Query(..., ge=1, description="Season ID"),
    round_number: int = Query(..., ge=1, description="Round number")
) -> TyperAdminCandidatesResponse:
    """Return CL matches for a round with publication and odds flags."""
    _ = user
    rows = _invoke(
        lambda: typer_service.get_admin_candidates(season_id, round_number))
    mapped = [TyperAdminCandidate(**row) for row in rows]
    return TyperAdminCandidatesResponse(
        season_id=season_id,
        round_number=round_number,
        candidates=mapped,
        total_count=len(mapped),
        group_match_count=get_settings().typer_lm_group_match_count)


@router.post(
    "/admin/publications",
    response_model=PublishMatchesResponse,
    status_code=status.HTTP_201_CREATED)
async def publish_matches(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    body: PublishMatchesRequest
) -> PublishMatchesResponse:
    """Publish a group-stage set or a complete knockout round atomically."""
    rows = _invoke(
        lambda: typer_service.publish_matches(
            body.season_id,
            body.round_number,
            body.match_ids,
            _user_id(user)))
    mapped = [TyperPublication(**row) for row in rows]
    return PublishMatchesResponse(
        publications=mapped,
        total_count=len(mapped))


@router.delete(
    "/admin/publications/{match_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None)
async def delete_publication(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    match_id: int = Path(..., ge=1, description="Published match ID")
) -> None:
    """Remove a publication before kick-off when no picks exist."""
    _invoke(
        lambda: typer_service.remove_publication(match_id, _user_id(user)))


@router.get(
    "/admin/prediction-history",
    response_model=list[TyperPredictionChange])
async def get_admin_prediction_history(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    user_uuid: str = Query(
        ...,
        min_length=1,
        description="Public UUID of the user whose audit is requested"),
    match_id: int | None = Query(
        None,
        ge=1,
        description="Optional published match ID"),
    season_id: int | None = Query(
        None,
        ge=1,
        description="Optional season ID")
) -> list[TyperPredictionChange]:
    """Return another user's pick audit; never mutates picks."""
    _ = user
    rows = _invoke(
        lambda: typer_service.get_admin_prediction_history(
            user_uuid, match_id, season_id))
    return [TyperPredictionChange(**row) for row in rows]
