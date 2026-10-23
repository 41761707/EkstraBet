"""Fill hockey_player_game_ratings from the live rating functions."""

from __future__ import annotations

import pandas as pd

from backend.repositories.hockey_game_rating_repository import (
    fetch_hockey_rating_match)
from backend.repositories.hockey_game_rating_repository import (
    fetch_played_hockey_match_ids)
from backend.repositories.hockey_game_rating_repository import (
    replace_match_ratings)
from backend.repositories.match_repository import (
    fetch_hockey_game_rating_players)
from backend.repositories.match_repository import (
    fetch_hockey_match_events)
from backend.repositories.match_repository import (
    fetch_hockey_season_save_rate)
from backend.repositories.sport_league_repository import HOCKEY_SPORT_ID
from backend.sports.hockey.game_rating import build_match_rating
from backend.sports.hockey.game_rating_rows import rows_from_rating


def resolve_fill_target(
        match_id: int | None,
        season_id: int | None) -> tuple[str, int]:
    """Require exactly one of a match id or a season id."""
    if match_id is not None and season_id is None:
        return ("match", match_id)
    if season_id is not None and match_id is None:
        return ("season", season_id)
    raise ValueError(
        "Pass exactly one of --match-id or --season-id")


def _result_blocks_fill(result: object) -> bool:
    """Return True when the match has no recorded score."""
    if result is None:
        return True
    text = str(result)
    return text == "" or text == "0"


def _write_match(
        match_id: int,
        sides: dict,
        players: pd.DataFrame,
        events: pd.DataFrame,
        save_rate: float) -> int:
    """Store a rating built from data the caller already loaded."""
    payload = build_match_rating(
        players,
        events,
        save_rate,
        int(sides["home_team"]),
        int(sides["away_team"]),
        str(sides["home_team_name"]),
        str(sides["away_team_name"]))
    rows = rows_from_rating(payload)
    return replace_match_ratings(match_id, rows)


def fill_match(match_id: int) -> int:
    """Replace stored ratings for one played hockey match.

    A missing match, another sport, an unplayed result or an empty
    player frame raises ValueError and leaves stored rows in place.
    """
    sides = fetch_hockey_rating_match(match_id)
    if sides is None:
        raise ValueError(f"Hockey match {match_id} was not found")
    if int(sides["sport_id"]) != HOCKEY_SPORT_ID:
        raise ValueError(f"Match {match_id} is not a hockey match")
    if _result_blocks_fill(sides["result"]):
        raise ValueError(f"Match {match_id} is not played")
    players = fetch_hockey_game_rating_players(match_id)
    if players.empty:
        raise ValueError(
            f"Match {match_id} has no hockey player stats")
    events = fetch_hockey_match_events(match_id)
    save_rate = fetch_hockey_season_save_rate(match_id)
    return _write_match(
        match_id, sides, players, events, save_rate)


def fill_season(season_id: int) -> dict[str, int]:
    """Rate played hockey matches in one season, one commit each.

    An empty player frame is skipped and its stored rows stay.
    A later match failure does not roll back matches already stored.
    """
    # Commit siedzi w replace_match_ratings, więc wyjątek nie cofa
    # meczów zapisanych wcześniej. fill_match tu nie wchodzi: pusta
    # ramka ma być pominięciem, a nie ValueError.
    matches = 0
    written_rows = 0
    skipped = 0
    for match_id in fetch_played_hockey_match_ids(season_id):
        players = fetch_hockey_game_rating_players(match_id)
        if players.empty:
            skipped += 1
            continue
        sides = fetch_hockey_rating_match(match_id)
        if sides is None:
            raise ValueError(f"Hockey match {match_id} was not found")
        events = fetch_hockey_match_events(match_id)
        save_rate = fetch_hockey_season_save_rate(match_id)
        written_rows += _write_match(
            match_id, sides, players, events, save_rate)
        matches += 1
    return {
        "matches": matches,
        "rows": written_rows,
        "skipped": skipped
    }
