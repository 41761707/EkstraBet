"""Champions League Typer long-term market endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status

from api.deps import get_current_user, require_admin
from api.schemas.champions_league_typer_long_term import (
    LongTermAutoResultResponse,
    LongTermDashboardResponse,
    LongTermPickChange,
    LongTermTeamIdsRequest,
    SaveLongTermPicksResponse,
    SettleLongTermResponse)
from backend.services import (
    champions_league_typer_long_term_service as long_term_service)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/typer-lm/long-term", tags=["Typer LM"])

T = TypeVar("T")


def _invoke(operation: Callable[[], T]) -> T:
    """Run a service call and map domain errors to HTTP status codes."""
    try:
        return operation()
    except long_term_service.TyperNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)) from exc
    except long_term_service.TyperConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)) from exc
    except long_term_service.TyperValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Typer long-term request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Typer long-term request failed") from exc


def _user_id(user: dict[str, Any]) -> int:
    return int(user["id"])


@router.get("", response_model=LongTermDashboardResponse)
async def get_dashboard(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    season_id: int | None = Query(
        None,
        ge=1,
        description="Season ID; defaults to the league current season")
) -> LongTermDashboardResponse:
    """Return long-term markets with private picks and own audit."""
    payload = _invoke(
        lambda: long_term_service.get_dashboard(
            _user_id(user), season_id))
    return LongTermDashboardResponse(**payload)


@router.put(
    "/markets/{market_id}/picks",
    response_model=SaveLongTermPicksResponse)
async def save_picks(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    body: LongTermTeamIdsRequest,
    market_id: int = Path(..., ge=1, description="Long-term market ID")
) -> SaveLongTermPicksResponse:
    """Replace the current user's set before the first league-phase kick-off."""
    payload = _invoke(
        lambda: long_term_service.save_picks(
            _user_id(user), market_id, body.team_ids))
    return SaveLongTermPicksResponse(**payload)


@router.get(
    "/markets/{market_id}/history",
    response_model=list[LongTermPickChange])
async def get_own_history(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    market_id: int = Path(..., ge=1, description="Long-term market ID")
) -> list[LongTermPickChange]:
    """Return chronological audit rows for the current user's set."""
    rows = _invoke(
        lambda: long_term_service.get_own_history(
            _user_id(user), market_id))
    return [LongTermPickChange(**row) for row in rows]


@router.get(
    "/admin/markets/{market_id}/auto-result",
    response_model=LongTermAutoResultResponse)
async def get_auto_result(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    market_id: int = Path(..., ge=1, description="Long-term market ID")
) -> LongTermAutoResultResponse:
    """Return the TOP 8 proposal without writing results or points."""
    _ = user
    payload = _invoke(
        lambda: long_term_service.get_auto_result(market_id))
    return LongTermAutoResultResponse(**payload)


@router.post(
    "/admin/markets/{market_id}/settle",
    response_model=SettleLongTermResponse)
async def settle_market(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    body: LongTermTeamIdsRequest,
    market_id: int = Path(..., ge=1, description="Long-term market ID")
) -> SettleLongTermResponse:
    """Approve or correct the result after the league phase is complete."""
    payload = _invoke(
        lambda: long_term_service.settle_market(
            market_id, body.team_ids, _user_id(user)))
    return SettleLongTermResponse(**payload)


@router.get(
    "/admin/prediction-history",
    response_model=list[LongTermPickChange])
async def get_admin_history(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    user_uuid: str = Query(
        ...,
        min_length=1,
        description="Public UUID of the user whose audit is requested"),
    market_id: int | None = Query(
        None,
        ge=1,
        description="Optional long-term market ID"),
    season_id: int | None = Query(
        None,
        ge=1,
        description="Optional season ID")
) -> list[LongTermPickChange]:
    """Return another user's pick-set audit; never mutates picks."""
    _ = user
    rows = _invoke(
        lambda: long_term_service.get_admin_history(
            user_uuid, market_id, season_id))
    return [LongTermPickChange(**row) for row in rows]
