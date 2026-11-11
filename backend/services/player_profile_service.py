"""Player profile lookup, filter validation and domain errors."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.repositories import player_profile_repository as repo
from backend.sports.player_profile import (
    PLAYER_SEARCH_LIMIT,
    PLAYER_SEARCH_MIN_LENGTH,
    PROFILE_SOURCES,
    SLICE_MATCH_LIMIT)


class PlayerProfileNotFoundError(Exception):
    """Raised when no player exists for the given id."""


class PlayerProfileUnavailableError(Exception):
    """Raised when the sport has no profile source."""


class PlayerProfileValidationError(Exception):
    """Raised when a profile filter is rejected."""

    def __init__(self, message: str) -> None:
        """Store the English message returned to the client."""
        self.message = message
        super().__init__(message)


def search_players(sport_id: int, term: str | None) -> dict[str, Any]:
    """Return players of a registered sport whose name matches the term."""
    if sport_id not in PROFILE_SOURCES:
        raise PlayerProfileUnavailableError()
    cleaned = "" if term is None else term.strip()
    if len(cleaned) < PLAYER_SEARCH_MIN_LENGTH:
        raise PlayerProfileValidationError(
            "Search must contain at least 2 characters")
    players = repo.fetch_player_search(
        sport_id,
        cleaned,
        PLAYER_SEARCH_LIMIT)
    return {
        "players": players,
        "total_count": len(players)}


def get_player_profile(
        player_id: int,
        season_id: int | None,
        opponent_team_id: int | None,
        own_team_id: int | None,
        teammate_id: int | None) -> dict[str, Any]:
    """Return the profile envelope for one player slice."""
    player = repo.fetch_player(player_id)
    if player is None:
        raise PlayerProfileNotFoundError()
    sport_id = player["sport_id"]
    if sport_id not in PROFILE_SOURCES:
        raise PlayerProfileUnavailableError()
    _validate_filters(
        player_id,
        int(sport_id),
        season_id,
        opponent_team_id,
        own_team_id,
        teammate_id)
    source = PROFILE_SOURCES[sport_id]
    frame = source.fetch_slice(
        player_id,
        season_id,
        opponent_team_id,
        own_team_id,
        teammate_id,
        SLICE_MATCH_LIMIT)
    truncated = len(frame.index) == SLICE_MATCH_LIMIT
    event_frame = source.fetch_event_facts(
        player_id,
        _match_ids(frame))
    return {
        "player_id": int(player["player_id"]),
        "player_name": str(player["player_name"]),
        "sport_id": int(sport_id),
        "filters": {
            "player_id": player_id,
            "season_id": season_id,
            "opponent_team_id": opponent_team_id,
            "own_team_id": own_team_id,
            "teammate_id": teammate_id},
        "match_count": len(frame.index),
        "truncated": truncated,
        "body": source.build_body(
            player,
            frame,
            event_frame,
            truncated)}


def _validate_filters(
        player_id: int,
        sport_id: int,
        season_id: int | None,
        opponent_team_id: int | None,
        own_team_id: int | None,
        teammate_id: int | None) -> None:
    """Reject a slice that cannot be read for this sport.

    The first failing check wins. Later filters are not queried.
    """
    if teammate_id is not None and teammate_id == player_id:
        raise PlayerProfileValidationError(
            "teammate_id must differ from player_id")
    if (
            opponent_team_id is not None
            and own_team_id is not None
            and opponent_team_id == own_team_id):
        raise PlayerProfileValidationError(
            "opponent_team_id must differ from own_team_id")
    if season_id is not None and not repo.season_exists(
            season_id,
            sport_id):
        raise PlayerProfileValidationError("Unknown season")
    _require_team(opponent_team_id, sport_id)
    _require_team(own_team_id, sport_id)
    _require_teammate(teammate_id, sport_id)


def _require_team(team_id: int | None, sport_id: int) -> None:
    """Reject a team that is not in the player's sport."""
    if team_id is None:
        return
    if not repo.team_exists(team_id, sport_id):
        raise PlayerProfileValidationError("Unknown team")


def _require_teammate(teammate_id: int | None, sport_id: int) -> None:
    """Reject a teammate who is missing or plays another sport."""
    if teammate_id is None:
        return
    teammate = repo.fetch_player(teammate_id)
    if teammate is None or teammate.get("sport_id") != sport_id:
        raise PlayerProfileValidationError("Unknown teammate")


def _match_ids(frame: pd.DataFrame) -> list[int]:
    """Return match ids in slice order. An empty frame has none."""
    if frame.empty or "match_id" not in frame.columns:
        return []
    return [int(match_id) for match_id in frame["match_id"].tolist()]
