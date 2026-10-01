"""Read the probable lineup stored for one NHL club and stage.

``initial`` prefers ``CONFIRMED``, then ``EXTERNAL``, then ``MODEL``.
``final`` keeps only ``CONFIRMED``. No row means the caller should
use typical lineup strength and the team-average save rate.
"""

from __future__ import annotations

import logging

import pandas as pd

from backend.database import get_db_connection
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)


logger = logging.getLogger(__name__)

_INITIAL_STAGE = "initial"
_FINAL_STAGE = "final"
_SOURCE_RANK = {"CONFIRMED": 0, "EXTERNAL": 1, "MODEL": 2}
_LINEUP_QUERY = """
    SELECT
        player_id,
        position,
        line,
        pp_unit,
        is_starting_goalie,
        confidence,
        source
    FROM hockey_probable_lineups
    WHERE match_id = %s
      AND team_id = %s
"""


def resolve_lineup_for_stage(
        match_id: int,
        team_id: int,
        stage: str) -> ProbableLineup | None:
    """Return the stored lineup for this stage, or None."""
    frame = _fetch_rows(int(match_id), int(team_id))
    return lineup_for_stage(int(match_id), int(team_id), stage, frame)


def lineup_for_stage(
        match_id: int,
        team_id: int,
        stage: str,
        frame: pd.DataFrame) -> ProbableLineup | None:
    """Pick one source from rows already loaded for a club."""
    chosen = _rows_for_stage(frame, stage)
    if chosen.empty:
        return None
    players = [
        player
        for player in (
            _player_from_row(row) for row in chosen.itertuples(index=False))
        if player is not None]
    if not players:
        return None
    return ProbableLineup(
        match_id=match_id,
        team_id=team_id,
        players=players)


def _fetch_rows(match_id: int, team_id: int) -> pd.DataFrame:
    with get_db_connection() as connection:
        frame = pd.read_sql(
            _LINEUP_QUERY, connection, params=(match_id, team_id))
    logger.info(
        "Fetched %s probable lineup rows for match %s team %s",
        len(frame),
        match_id,
        team_id)
    return frame


def _rows_for_stage(frame: pd.DataFrame, stage: str) -> pd.DataFrame:
    if frame.empty or "source" not in frame.columns:
        return frame.iloc[0:0]
    sources = frame["source"].astype(str)
    if stage == _FINAL_STAGE:
        return frame.loc[sources == "CONFIRMED"]
    if stage != _INITIAL_STAGE:
        return frame.iloc[0:0]
    ranked = sources.map(lambda source: _SOURCE_RANK.get(source, 99))
    best = int(ranked.min())
    if best > max(_SOURCE_RANK.values()):
        return frame.iloc[0:0]
    return frame.loc[ranked == best]


def _player_from_row(row: object) -> ProbableLineupPlayer | None:
    player_id = _whole(getattr(row, "player_id", None))
    position = getattr(row, "position", None)
    if player_id is None or not isinstance(position, str) or position == "":
        return None
    source = getattr(row, "source", None)
    if not isinstance(source, str) or source not in _SOURCE_RANK:
        return None
    return ProbableLineupPlayer(
        player_id=player_id,
        position=position,
        line=_whole(getattr(row, "line", None)),
        pp_unit=_whole(getattr(row, "pp_unit", None)),
        is_starting_goalie=_whole(getattr(row, "is_starting_goalie", None)),
        confidence=_finite(getattr(row, "confidence", None)),
        source=source,
        start_probability=None)


def _whole(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not number.is_integer():
        return None
    return int(number)


def _finite(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number
