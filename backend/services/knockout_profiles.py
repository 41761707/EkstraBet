"""Seeded entry profiles for leagues that skip a knockout round."""

from __future__ import annotations

from dataclasses import dataclass


CHAMPIONS_LEAGUE_ID = 42
PENDING_OPPONENT_LABEL = "Zwycięzca barażu"
_SEEDED_PLACES = (1, 2, 3, 4, 5, 6, 7, 8)
# Ósemka tabeli wchodzi w fazę o depth 8, czyli 1/8 finału.
_CHAMPIONS_LEAGUE_ENTRY_DEPTH = 8


@dataclass(frozen=True)
class ByeProfile:
    """Table places that enter the cup at one depth.

    ``places`` are overall-table positions, starting at 1.
    ``enter_depth`` is the phase those places join.
    """

    league_id: int
    places: tuple[int, ...]
    enter_depth: int


@dataclass(frozen=True)
class SeededTeam:
    """One overall-table row that may skip a knockout round.

    ``position`` starts at 1. The service builds these rows from
    the standings only after the league phase is complete.
    """

    team_id: int
    position: int


BYE_PROFILES: dict[int, ByeProfile] = {
    CHAMPIONS_LEAGUE_ID: ByeProfile(
        league_id=CHAMPIONS_LEAGUE_ID,
        places=_SEEDED_PLACES,
        enter_depth=_CHAMPIONS_LEAGUE_ENTRY_DEPTH)}


def active_bye_profile(
        league_id: int,
        unplayed_league_matches: int) -> ByeProfile | None:
    """Return the profile when every league-phase match is played.

    A count other than zero keeps the profile off. ``apply_byes``
    still ignores the profile when the ties hold no cup match.
    This function does not read the database.
    """
    if unplayed_league_matches != 0:
        return None
    return BYE_PROFILES.get(league_id)
