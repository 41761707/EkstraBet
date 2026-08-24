"""Pydantic schemas for the current user's private preferences."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ThemePreference = Literal["system", "dark", "light"]


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


class UserPreferencesResponse(BaseModel):
    """Full document of known scalar UI preferences (v1: theme only)."""

    theme: ThemePreference = Field(
        ...,
        description="Account color-scheme preference")


class UserPreferencesUpdate(BaseModel):
    """Partial update; only provided fields are written (v1: theme)."""

    theme: ThemePreference = Field(
        ...,
        description="Account color-scheme preference")
