"""Pydantic schemas for administrative user and league endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from backend.services.admin_league_service import MAX_LEAGUE_NAME_LENGTH
from backend.services.auth_service import MAX_DISPLAY_NAME_LENGTH
from backend.services.auth_service import MAX_PASSWORD_LENGTH
from backend.services.auth_service import MAX_USERNAME_LENGTH
from backend.services.auth_service import MIN_PASSWORD_LENGTH
from backend.services.auth_service import MIN_USERNAME_LENGTH


class AdminUser(BaseModel):
    """Public admin view of a user account without secrets."""

    uuid: str = Field(..., description="Public user UUID")
    username: str = Field(..., description="Login username")
    display_name: str | None = Field(
        None,
        description="Optional display name")
    is_active: bool = Field(..., description="Whether the account is active")
    is_admin: bool = Field(
        ...,
        description="Whether the user has the administrator role")
    first_login: bool = Field(
        ...,
        description="True when first-login is still required")
    created_at: datetime | None = Field(
        None,
        description="Account creation timestamp")
    updated_at: datetime | None = Field(
        None,
        description="Last account update timestamp")


class CreateUserRequest(BaseModel):
    """Payload for creating a first-login account."""

    username: str = Field(
        ...,
        min_length=MIN_USERNAME_LENGTH,
        max_length=MAX_USERNAME_LENGTH,
        description="Login username")
    temporary_password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        description="Temporary password supplied by the administrator")
    display_name: str | None = Field(
        None,
        max_length=MAX_DISPLAY_NAME_LENGTH,
        description="Optional display name")
    is_admin: bool = Field(
        False,
        description="Whether the new account should have the admin role")


class UserActiveUpdate(BaseModel):
    """Payload for toggling a user account's active flag."""

    is_active: bool = Field(
        ...,
        description="True to activate the account, false to suspend it")


class UserAdminUpdate(BaseModel):
    """Payload for toggling a user account's administrator role."""

    is_admin: bool = Field(
        ...,
        description="True to grant the admin role, false to revoke it")


class AdminLeague(BaseModel):
    """Admin view of a league, including inactive rows."""

    id: int = Field(..., description="League ID")
    name: str | None = Field(
        None,
        description="League name; null only for existing incomplete rows")
    country_id: int | None = Field(None, description="Country ID")
    country_name: str | None = Field(None, description="Country name")
    country_emoji: str | None = Field(None, description="Country flag emoji")
    sport_id: int | None = Field(None, description="Sport ID")
    sport_name: str | None = Field(None, description="Sport name")
    active: bool = Field(..., description="Whether the league is active")
    last_update: date | None = Field(
        None,
        description="Last data update date")
    current_season_id: int | None = Field(
        None,
        description="Current season ID configured for the league")
    tier: int | None = Field(None, description="League tier level")
    has_player_stats: bool = Field(
        ...,
        description="Whether player stats are available")


class CreateLeagueRequest(BaseModel):
    """Payload for creating a league after dictionary FK checks."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=MAX_LEAGUE_NAME_LENGTH,
        description="League name")
    country_id: int = Field(..., ge=1, description="Country ID")
    sport_id: int = Field(..., ge=1, description="Sport ID")
    current_season_id: int | None = Field(
        None,
        ge=1,
        description="Optional current season ID")
    tier: int | None = Field(None, description="Optional league tier")
    has_player_stats: bool = Field(
        False,
        description="Whether player stats are available")


class LeagueActiveUpdate(BaseModel):
    """Payload for toggling a league's active flag."""

    active: bool = Field(
        ...,
        description="True to activate the league, false to deactivate it")


class AdminCountry(BaseModel):
    """Country dropdown row for the league form."""

    id: int = Field(..., description="Country ID")
    name: str = Field(..., description="Country name")
    short_name: str | None = Field(None, description="Country short name")
    emoji: str | None = Field(None, description="Country flag emoji")


class AdminSport(BaseModel):
    """Sport dropdown row for the league form."""

    id: int = Field(..., description="Sport ID")
    name: str = Field(..., description="Sport name")


class AdminSeason(BaseModel):
    """Season dropdown row for the league form."""

    id: int = Field(..., description="Season ID")
    years: str = Field(..., description="Season years label")
