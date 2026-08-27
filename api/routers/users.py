"""Private endpoints for the authenticated user's resources."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.deps import get_current_user
from api.schemas.user_preferences import (
    FavoriteLeagueIdsResponse,
    FavoriteLeagueMutationResponse,
    UserPreferencesResponse,
    UserPreferencesUpdate)
from backend.services import favorite_league_service
from backend.services import user_preferences_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me/favorite-leagues",
    response_model=FavoriteLeagueIdsResponse)
async def get_favorite_leagues(
    user: Annotated[dict[str, Any], Depends(get_current_user)]
) -> FavoriteLeagueIdsResponse:
    """Return favorite league IDs for the current user."""
    league_ids = favorite_league_service.get_favorite_league_ids(user)
    return FavoriteLeagueIdsResponse(league_ids=league_ids)


@router.put(
    "/me/favorite-leagues/{league_id}",
    response_model=FavoriteLeagueMutationResponse)
async def add_favorite_league(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    league_id: int = Path(..., ge=1, description="League ID")
) -> FavoriteLeagueMutationResponse:
    """Add a league to favorites; repeating the call is a no-op."""
    try:
        favorite_league_service.add_favorite_league(user, league_id)
    except favorite_league_service.LeagueNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)) from exc
    return FavoriteLeagueMutationResponse(
        league_id=league_id,
        is_favorite=True)


@router.delete(
    "/me/favorite-leagues/{league_id}",
    response_model=FavoriteLeagueMutationResponse)
async def remove_favorite_league(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    league_id: int = Path(..., ge=1, description="League ID")
) -> FavoriteLeagueMutationResponse:
    """Remove a favorite league; a missing relation still succeeds."""
    favorite_league_service.remove_favorite_league(user, league_id)
    return FavoriteLeagueMutationResponse(
        league_id=league_id,
        is_favorite=False)


@router.get(
    "/me/preferences",
    response_model=UserPreferencesResponse)
async def get_preferences(
    user: Annotated[dict[str, Any], Depends(get_current_user)]
) -> UserPreferencesResponse:
    """Return stored scalar preferences, or 404 when the account has no row."""
    row = user_preferences_service.get_preferences(user)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not found")
    return UserPreferencesResponse.model_validate(row)


@router.put(
    "/me/preferences",
    response_model=UserPreferencesResponse)
async def put_preferences(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
    payload: UserPreferencesUpdate
) -> UserPreferencesResponse:
    """Merge provided fields only; omitted columns stay unchanged."""
    try:
        row = user_preferences_service.update_preferences(
            user,
            theme=payload.theme,
            team_name_display=payload.team_name_display)
    except (
            user_preferences_service.InvalidThemeError,
            user_preferences_service.InvalidTeamNameDisplayError,
            user_preferences_service.EmptyPreferencesPatchError
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)) from exc
    return UserPreferencesResponse.model_validate(row)
