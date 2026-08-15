"""Pydantic schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials submitted to obtain an access token."""

    username: str = Field(..., min_length=1, description="Login username")
    password: str = Field(..., min_length=1, description="Plain-text password")


class UserPublic(BaseModel):
    """Public user profile exposed by the API (no internal id)."""

    uuid: str = Field(..., description="Public user UUID")
    username: str = Field(..., description="Login username")
    display_name: str | None = Field(
        None,
        description="Optional display name for the UI")
    first_login: bool = Field(
        ...,
        description="True when the user must complete first-login")


class TokenResponse(BaseModel):
    """JWT issued after a successful login."""

    access_token: str = Field(..., description="Bearer access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token lifetime in seconds")
    first_login: bool = Field(
        ...,
        description="True when the user must complete first-login")
    username: str = Field(..., description="Login username")


class CompleteFirstLoginRequest(BaseModel):
    """New credentials submitted after the first login."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Chosen login username")
    new_password: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="New plain-text password")
    new_password_confirm: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="New password confirmation")
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Chosen display name (nickname)")


class CompleteFirstLoginResponse(BaseModel):
    """Result of completing the first-login form."""

    ok: bool = Field(
        default=True,
        description="True when credentials were saved")
    user: UserPublic = Field(
        ...,
        description="Updated public user profile")


class AuthStatusResponse(BaseModel):
    """Whether authentication is currently enforced."""

    auth_enabled: bool = Field(
        ...,
        description="True when API and UI require a valid session")
