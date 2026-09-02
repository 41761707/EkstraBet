"""Administrative user and league endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.deps import require_admin
from api.schemas.admin import AdminCountry
from api.schemas.admin import AdminLeague
from api.schemas.admin import AdminSeason
from api.schemas.admin import AdminSport
from api.schemas.admin import AdminUser
from api.schemas.admin import CreateLeagueRequest
from api.schemas.admin import CreateUserRequest
from api.schemas.admin import LeagueActiveUpdate
from api.schemas.admin import UserActiveUpdate
from api.schemas.admin import UserAdminUpdate
from backend.services import admin_league_service
from backend.services import admin_user_service
from backend.services.admin_errors import AdminConflictError
from backend.services.admin_errors import AdminForbiddenError
from backend.services.admin_errors import AdminNotFoundError
from backend.services.admin_errors import AdminValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

T = TypeVar("T")


def _invoke(operation: Callable[[], T]) -> T:
    """Run a service call and map domain errors to HTTP status codes."""
    try:
        return operation()
    except AdminNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)) from exc
    except AdminConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)) from exc
    except AdminValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)) from exc
    except AdminForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Admin request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin request failed") from exc


@router.get("/users", response_model=list[AdminUser])
async def list_users(
    user: Annotated[dict[str, Any], Depends(require_admin)]
) -> list[AdminUser]:
    """Return all user accounts without password hashes."""
    _ = user
    rows = _invoke(admin_user_service.list_users)
    return [AdminUser(**row) for row in rows]


@router.post(
    "/users",
    response_model=AdminUser,
    status_code=status.HTTP_201_CREATED)
async def create_user(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    body: CreateUserRequest
) -> AdminUser:
    """Create an active first-login account with an admin-supplied password."""
    _ = user
    # hasło tymczasowe zostaje w body — DTO i logi go nie powielają
    payload = _invoke(
        lambda: admin_user_service.create_user(
            body.username,
            body.temporary_password,
            body.display_name,
            body.is_admin))
    return AdminUser(**payload)


@router.put("/users/{uuid}/active", response_model=AdminUser)
async def set_user_active(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    body: UserActiveUpdate,
    uuid: str = Path(..., min_length=1, description="Public user UUID")
) -> AdminUser:
    """Activate or suspend a user; self-deactivation is rejected."""
    payload = _invoke(
        lambda: admin_user_service.set_user_active(
            user, uuid, body.is_active))
    return AdminUser(**payload)


@router.put("/users/{uuid}/admin", response_model=AdminUser)
async def set_user_admin(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    body: UserAdminUpdate,
    uuid: str = Path(..., min_length=1, description="Public user UUID")
) -> AdminUser:
    """Grant or revoke the admin role; self-revocation is rejected."""
    payload = _invoke(
        lambda: admin_user_service.set_user_admin(
            user, uuid, body.is_admin))
    return AdminUser(**payload)


@router.get("/leagues", response_model=list[AdminLeague])
async def list_leagues(
    user: Annotated[dict[str, Any], Depends(require_admin)]
) -> list[AdminLeague]:
    """Return all leagues, including inactive ones."""
    _ = user
    rows = _invoke(admin_league_service.list_leagues)
    return [AdminLeague(**row) for row in rows]


@router.post(
    "/leagues",
    response_model=AdminLeague,
    status_code=status.HTTP_201_CREATED)
async def create_league(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    body: CreateLeagueRequest
) -> AdminLeague:
    """Create a league after validating country, sport and season FKs."""
    _ = user
    payload = _invoke(
        lambda: admin_league_service.create_league(
            body.name,
            body.country_id,
            body.sport_id,
            body.current_season_id,
            body.tier,
            body.has_player_stats))
    return AdminLeague(**payload)


@router.put("/leagues/{league_id}/active", response_model=AdminLeague)
async def set_league_active(
    user: Annotated[dict[str, Any], Depends(require_admin)],
    body: LeagueActiveUpdate,
    league_id: int = Path(..., ge=1, description="League ID")
) -> AdminLeague:
    """Activate or deactivate a league."""
    _ = user
    payload = _invoke(
        lambda: admin_league_service.set_league_active(
            league_id, body.active))
    return AdminLeague(**payload)


@router.get("/countries", response_model=list[AdminCountry])
async def list_countries(
    user: Annotated[dict[str, Any], Depends(require_admin)]
) -> list[AdminCountry]:
    """Return country dropdown rows for the league form."""
    _ = user
    rows = _invoke(admin_league_service.list_countries)
    return [AdminCountry(**row) for row in rows]


@router.get("/sports", response_model=list[AdminSport])
async def list_sports(
    user: Annotated[dict[str, Any], Depends(require_admin)]
) -> list[AdminSport]:
    """Return sport dropdown rows for the league form."""
    _ = user
    rows = _invoke(admin_league_service.list_sports)
    return [AdminSport(**row) for row in rows]


@router.get("/seasons", response_model=list[AdminSeason])
async def list_seasons(
    user: Annotated[dict[str, Any], Depends(require_admin)]
) -> list[AdminSeason]:
    """Return season dropdown rows for the league form."""
    _ = user
    rows = _invoke(admin_league_service.list_seasons)
    return [AdminSeason(**row) for row in rows]
