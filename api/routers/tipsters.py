"""HTTP endpoints for tipster bankroll, coupons and ranking."""

from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, Any, Callable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.deps import get_current_user, require_admin, require_auth
from api.routers.utils import parse_id_list
from api.schemas.tipster import BankrollConfigureRequest
from api.schemas.tipster import BankrollSettings
from api.schemas.tipster import CatalogMatchesResponse
from api.schemas.tipster import CouponCreateRequest
from api.schemas.tipster import CouponPage
from api.schemas.tipster import CouponSummary
from api.schemas.tipster import LeaderboardResponse
from api.schemas.tipster import LeaderboardSortBy
from api.schemas.tipster import LeaderboardSortOrder
from api.schemas.tipster import PerformanceBreakdown
from api.schemas.tipster import SettlementResult
from api.schemas.tipster import SuggestedCatalogOdds
from api.schemas.tipster import TipsterProfileResponse
from api.schemas.tipster import TopUpRequest
from backend.config import get_settings
from backend.services import tipster_service
from backend.services import tipster_settlement_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tipsters", tags=["Tipsters"])

T = TypeVar("T")

_DEFAULT_PAGE = 1


def _invoke(operation: Callable[[], T]) -> T:
    """Run a service call and map domain errors to HTTP status codes."""
    try:
        return operation()
    except tipster_service.TipsterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)) from exc
    except tipster_service.TipsterForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc)) from exc
    except tipster_service.TipsterConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)) from exc
    except tipster_service.TipsterValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)) from exc
    except tipster_service.TipsterUnprocessableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Tipster request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tipster request failed") from exc


def _resolved_page_size(page_size: int) -> int:
    settings = get_settings()
    if page_size > settings.max_page_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"page_size cannot exceed {settings.max_page_size}")
    return page_size


def _assert_date_range(
        date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from cannot be later than date_to")


def _parse_event_family(raw_value: str | None) -> str | int | None:
    if raw_value is None:
        return None
    token = raw_value.strip()
    if not token:
        return None
    if token.upper() == "OTHER":
        return "OTHER"
    try:
        return int(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="event_family must be OTHER, 0 or an event family id") from exc


@router.get("/me/bankroll", response_model=BankrollSettings)
async def get_my_bankroll(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    apply_tax: bool = Query(
        False,
        description="Recompute settled profit with the 12% betting tax")
) -> BankrollSettings:
    """Return the caller's bankroll, or 404 when onboarding is missing."""
    payload = _invoke(
        lambda: tipster_service.get_my_bankroll(
            user, apply_tax=apply_tax))
    return BankrollSettings.model_validate(payload)


@router.put("/me/bankroll", response_model=BankrollSettings)
async def put_my_bankroll(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    body: BankrollConfigureRequest
) -> BankrollSettings:
    """Create bankroll settings, or update unit and currency after onboarding."""
    payload = _invoke(
        lambda: tipster_service.configure_bankroll(
            user,
            body.currency,
            body.initial_capital,
            body.unit_size))
    return BankrollSettings.model_validate(payload)


@router.post("/me/top-up", response_model=BankrollSettings)
async def post_my_top_up(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    body: TopUpRequest
) -> BankrollSettings:
    """Increase initial_capital; system accounts cannot use /me."""
    payload = _invoke(lambda: tipster_service.top_up(user, body.amount))
    return BankrollSettings.model_validate(payload)


@router.get("/me/coupons", response_model=CouponPage)
async def get_my_coupons(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    settled: int | None = Query(
        None,
        ge=0,
        le=1,
        description="Filter by settled flag (0/1)"),
    page: int = Query(
        _DEFAULT_PAGE, ge=1, description="Page number"),
    page_size: int = Query(
        tipster_service.DEFAULT_COUPON_PAGE_SIZE,
        ge=1,
        description="Page size"),
    apply_tax: bool = Query(
        False,
        description="Recompute settled profit with the 12% betting tax")
) -> CouponPage:
    """Return a coupon page for the authenticated owner."""
    size = _resolved_page_size(page_size)
    payload = _invoke(
        lambda: tipster_service.get_my_coupons(
            user, settled, page, size, apply_tax=apply_tax))
    return CouponPage.model_validate(payload)


@router.post(
    "/me/coupons",
    response_model=CouponSummary,
    status_code=status.HTTP_201_CREATED)
async def post_my_coupon(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    body: CouponCreateRequest
) -> CouponSummary:
    """Place a coupon for the interactive caller; 403 for system accounts."""
    payload = _invoke(
        lambda: tipster_service.create_coupon(user, body.model_dump()))
    return CouponSummary.model_validate(payload)


@router.get("/me/performance", response_model=PerformanceBreakdown)
async def get_my_performance(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    apply_tax: bool = Query(
        False,
        description="Recompute settled profit with the 12% betting tax")
) -> PerformanceBreakdown:
    """Return settled-coupon breakdowns for the authenticated owner."""
    payload = _invoke(
        lambda: tipster_service.get_my_performance(
            user, apply_tax=apply_tax))
    return PerformanceBreakdown.model_validate(payload)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    is_system: int | None = Query(
        None,
        ge=0,
        le=1,
        description="Optional filter: 0 human, 1 system agent"),
    league_ids: str | None = Query(
        None,
        description="Comma-separated league IDs"),
    tier: int | None = Query(None, description="League tier filter"),
    event_family: str | None = Query(
        None,
        description="Event family id, 0, or OTHER"),
    event_ids: str | None = Query(
        None,
        description="Comma-separated event IDs"),
    date_from: date | None = Query(
        None,
        description="Inclusive coupon created_at start"),
    date_to: date | None = Query(
        None,
        description="Inclusive coupon created_at end"),
    sort_by: LeaderboardSortBy = Query(
        "profit_total",
        description="Sort field"),
    sort_order: LeaderboardSortOrder = Query(
        "desc",
        description="Sort direction"),
    page: int = Query(
        _DEFAULT_PAGE, ge=1, description="Page number"),
    page_size: int = Query(
        tipster_service.DEFAULT_COUPON_PAGE_SIZE,
        ge=1,
        description="Page size"),
    apply_tax: bool = Query(
        False,
        description="Recompute settled profit with the 12% betting tax")
) -> LeaderboardResponse:
    """Return a ranking page of users who have a bankroll row."""
    _assert_date_range(date_from, date_to)
    filters = {"is_system": is_system,
        "league_ids": parse_id_list(league_ids),
        "tier": tier,
        "event_family": _parse_event_family(event_family),
        "event_ids": parse_id_list(event_ids),
        "date_from": date_from,
        "date_to": date_to,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "page": page,
        "page_size": _resolved_page_size(page_size),
        "apply_tax": apply_tax}
    payload = _invoke(lambda: tipster_service.get_leaderboard(filters))
    return LeaderboardResponse.model_validate(payload)


@router.get(
    "/profile/{username}",
    response_model=TipsterProfileResponse)
async def get_tipster_profile(
    username: str,
    viewer: Annotated[
        dict[str, Any] | None, Depends(require_auth)],
    page: int = Query(
        _DEFAULT_PAGE, ge=1, description="Coupon page number"),
    page_size: int = Query(
        tipster_service.DEFAULT_COUPON_PAGE_SIZE,
        ge=1,
        description="Coupon page size"),
    apply_tax: bool = Query(
        False,
        description="Recompute settled profit with the 12% betting tax")
) -> TipsterProfileResponse:
    """Return public identity; coupons only for owner or system target."""
    size = _resolved_page_size(page_size)
    payload = _invoke(
        lambda: tipster_service.get_public_profile(
            username, viewer, page, size, apply_tax=apply_tax))
    return TipsterProfileResponse.model_validate(payload)


@router.get("/catalog/matches", response_model=CatalogMatchesResponse)
async def get_catalog_matches(
    date_from: date | None = Query(
        None,
        description="Inclusive kick-off date start"),
    date_to: date | None = Query(
        None,
        description="Inclusive kick-off date end"),
    league_ids: str | None = Query(
        None,
        description="Comma-separated league IDs")
) -> CatalogMatchesResponse:
    """Return upcoming unfinished matches and settleable catalog events."""
    _assert_date_range(date_from, date_to)
    payload = _invoke(
        lambda: tipster_service.get_catalog_matches(
            date_from, date_to, parse_id_list(league_ids)))
    return CatalogMatchesResponse.model_validate(payload)


@router.get(
    "/catalog/suggested-odds",
    response_model=SuggestedCatalogOdds)
async def get_suggested_catalog_odds(
    match_id: int = Query(..., ge=1, description="Match ID"),
    event_id: int = Query(..., ge=1, description="Catalog event ID")
) -> SuggestedCatalogOdds:
    """Suggest stored odds for one predicted event; the value stays editable."""
    payload = _invoke(
        lambda: tipster_service.get_suggested_catalog_odds(
            match_id, event_id))
    return SuggestedCatalogOdds.model_validate(payload)


@router.post(
    "/parlays/settle",
    response_model=SettlementResult)
async def settle_open_parlays(
    user: Annotated[dict[str, Any], Depends(require_admin)]
) -> SettlementResult:
    """Settle open tipster coupons; administrator role required."""
    _ = user
    payload = _invoke(tipster_settlement_service.settle_open_coupons)
    return SettlementResult.model_validate(payload)
