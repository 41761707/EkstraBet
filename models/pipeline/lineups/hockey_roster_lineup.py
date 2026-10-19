"""Read the next-game NHL lineup from ``hockey_rosters``.

The feed keeps that table current. A goalie on line 1 starts.
A goalie on line 2 is the backup and stays on the sheet.
Line 0 and injured players are left out. An empty seat stays empty.
"""

from __future__ import annotations

import pandas as pd

from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)


FORWARD_POSITIONS = frozenset({"LW", "C", "RW"})
DEFENSE_POSITION = "D"
GOALIE_POSITION = "G"
STARTER_GOALIE_LINE = 1
BACKUP_GOALIE_LINE = 2
FORWARD_LINES = frozenset({1, 2, 3, 4})
DEFENSE_LINES = frozenset({1, 2, 3})
_ROSTER_SOURCE = "ROSTER"


def load_roster_lineup(
        roster_rows: pd.DataFrame,
        team_id: int,
        match_id: int) -> ProbableLineup | None:
    """Return the dressed sheet for one club, or None when it is empty.

    ``match_id`` is the game being scored. The roster itself is not
    stored per match.
    """
    players = _dressed_players(roster_rows, int(team_id))
    if not players:
        return None
    return ProbableLineup(
        match_id=int(match_id),
        team_id=int(team_id),
        players=players)


def _dressed_players(
        roster_rows: pd.DataFrame,
        team_id: int) -> list[ProbableLineupPlayer]:
    if roster_rows is None or roster_rows.empty:
        return []
    if "team_id" not in roster_rows.columns:
        return []
    team = roster_rows.loc[roster_rows["team_id"] == team_id]
    players: list[ProbableLineupPlayer] = []
    for row in team.itertuples(index=False):
        player = _roster_player(row)
        if player is not None:
            players.append(player)
    return players


def _roster_player(row: object) -> ProbableLineupPlayer | None:
    if _is_injured(row):
        return None
    position = _position(getattr(row, "position", None))
    line = _line(getattr(row, "line", None))
    if position is None or line is None:
        return None
    starter = _goalie_role(position, line)
    if starter is None and not _is_dressed_skater(position, line):
        return None
    return ProbableLineupPlayer(
        player_id=int(getattr(row, "player_id")),
        position=position,
        line=line,
        pp_unit=_line(getattr(row, "pp", None)),
        is_starting_goalie=0 if starter is None else starter,
        confidence=1.0,
        source=_ROSTER_SOURCE,
        start_probability=None)


def _goalie_role(position: str, line: int) -> int | None:
    """Return 1 for the starter, 0 for the backup, or None for others."""
    if position != GOALIE_POSITION:
        return None
    if line == STARTER_GOALIE_LINE:
        return 1
    if line == BACKUP_GOALIE_LINE:
        return 0
    return None


def _is_dressed_skater(position: str, line: int) -> bool:
    if position in FORWARD_POSITIONS and line in FORWARD_LINES:
        return True
    return position == DEFENSE_POSITION and line in DEFENSE_LINES


def _is_injured(row: object) -> bool:
    value = getattr(row, "is_injured", None)
    if value is None or pd.isna(value):
        return False
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        return False


def _position(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text == "":
        return None
    return text


def _line(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
