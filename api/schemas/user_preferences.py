"""Pydantic schemas for the current user's private preferences."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FavoriteLeagueIdsResponse(BaseModel):
    """Favorite league IDs of the authenticated user."""

    league_ids: list[int] = Field(
        ...,
        description=(
            "Favorite league IDs without duplicates, sorted ascending"))


class FavoriteLeagueMutationResponse(BaseModel):
    """Result of adding or removing a favorite league."""

    league_id: int = Field(..., description="Affected league ID")
    is_favorite: bool = Field(
        ...,
        description="True when the league is in the user's favorites")
