"""Pydantic schemas for the current user's private preferences."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ThemePreference = Literal["system", "dark", "light"]
TeamNameDisplayPreference = Literal["full", "shortcut"]


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
    """Full document of known scalar UI preferences."""

    theme: ThemePreference = Field(
        ...,
        description="Account color-scheme preference")
    team_name_display: TeamNameDisplayPreference = Field(
        ...,
        description="Preferred team label in abbreviation-capable UI")


class UserPreferencesUpdate(BaseModel):
    """Partial update; only provided fields are written."""

    theme: ThemePreference | None = Field(
        None,
        description="Account color-scheme preference")
    team_name_display: TeamNameDisplayPreference | None = Field(
        None,
        description="Preferred team label in abbreviation-capable UI")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UserPreferencesUpdate:
        """Reject an empty patch so omitted fields stay distinguishable."""
        if self.theme is None and self.team_name_display is None:
            raise ValueError("At least one preference field is required")
        return self
