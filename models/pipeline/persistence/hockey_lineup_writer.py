"""Replace each club's next-game rows in ``hockey_probable_lineups``.

The table keeps one current lineup per club. A ``MODEL`` write deletes
that club's rows and inserts the new set in one transaction. The same
``match_id`` is left untouched when its source is ``EXTERNAL`` or
``CONFIRMED``. An older match is always replaced.
"""

from __future__ import annotations

import logging
import math
from contextlib import nullcontext
from typing import Any

from backend.database import get_db_connection
from models.pipeline.features.hockey.lineup_strength import ProbableLineup
from models.pipeline.features.hockey.lineup_strength import (
    ProbableLineupPlayer)


logger = logging.getLogger(__name__)

_MODEL_SOURCE = "MODEL"
_PROTECTED_SOURCES = frozenset({"EXTERNAL", "CONFIRMED"})
_SELECT_SQL = """
SELECT match_id, source
FROM hockey_probable_lineups
WHERE team_id = %s
"""
_DELETE_SQL = """
DELETE FROM hockey_probable_lineups
WHERE team_id = %s
"""
_INSERT_SQL = """
INSERT INTO hockey_probable_lineups (
    match_id,
    team_id,
    player_id,
    position,
    line,
    pp_unit,
    is_starting_goalie,
    confidence,
    source,
    start_probability
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def write_probable_lineups(
        lineups: list[ProbableLineup],
        conn: Any | None = None) -> int:
    """Replace stored ``MODEL`` lineups. Return inserted row count.

    ``conn`` is optional so tests can pass a cursor owner. A missing
    connection opens one. Nothing is committed when every club is
    skipped.
    """
    prepared = _latest_per_team(lineups)
    if not prepared:
        return 0
    context = nullcontext(conn) if conn is not None else get_db_connection()
    with context as connection:
        cursor = connection.cursor()
        try:
            written = _write_clubs(cursor, prepared)
            if written:
                connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    return written


def _write_clubs(cursor: Any, lineups: list[ProbableLineup]) -> int:
    written = 0
    for lineup in lineups:
        written += _write_club(cursor, lineup)
    return written


def _write_club(cursor: Any, lineup: ProbableLineup) -> int:
    rows = _insert_rows(lineup)
    if not rows:
        logger.warning(
            "Skipping lineup with no players for team %s match %s",
            lineup.team_id,
            lineup.match_id)
        return 0
    stored = _stored_pairs(cursor, int(lineup.team_id))
    if _same_match_is_protected(stored, int(lineup.match_id)):
        logger.info(
            "Keeping EXTERNAL or CONFIRMED lineup for team %s match %s",
            lineup.team_id,
            lineup.match_id)
        return 0
    cursor.execute(_DELETE_SQL, (int(lineup.team_id),))
    cursor.executemany(_INSERT_SQL, rows)
    return len(rows)


def _latest_per_team(
        lineups: list[ProbableLineup]) -> list[ProbableLineup]:
    chosen: dict[int, ProbableLineup] = {}
    for lineup in lineups:
        if not lineup.players:
            logger.warning(
                "Skipping empty probable lineup for team %s match %s",
                lineup.team_id,
                lineup.match_id)
            continue
        chosen[int(lineup.team_id)] = lineup
    return list(chosen.values())


def _stored_pairs(cursor: Any, team_id: int) -> list[tuple[int, str]]:
    cursor.execute(_SELECT_SQL, (team_id,))
    pairs: list[tuple[int, str]] = []
    for row in cursor.fetchall():
        pair = _stored_pair(row)
        if pair is not None:
            pairs.append(pair)
    return pairs


def _stored_pair(row: object) -> tuple[int, str] | None:
    if isinstance(row, dict):
        match_id = row.get("match_id")
        source = row.get("source")
    else:
        match_id = row[0]
        source = row[1]
    try:
        parsed_match = int(match_id)
    except (TypeError, ValueError):
        return None
    if not isinstance(source, str):
        return None
    return parsed_match, source.strip().upper()


def _same_match_is_protected(
        stored: list[tuple[int, str]],
        match_id: int) -> bool:
    for stored_match, source in stored:
        if stored_match == match_id and source in _PROTECTED_SOURCES:
            return True
    return False


def _insert_rows(
        lineup: ProbableLineup) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for player in lineup.players:
        row = _insert_row(lineup, player)
        if row is not None:
            rows.append(row)
    return rows


def _insert_row(
        lineup: ProbableLineup,
        player: ProbableLineupPlayer) -> tuple[object, ...] | None:
    position = player.position.strip().upper()
    if position == "" or len(position) > 5:
        logger.warning(
            "Skipping player %s with position %r",
            player.player_id,
            player.position)
        return None
    return (
        int(lineup.match_id),
        int(lineup.team_id),
        int(player.player_id),
        position,
        player.line,
        player.pp_unit,
        player.is_starting_goalie,
        _confidence(player.confidence),
        _MODEL_SOURCE,
        _unit_interval(player.start_probability))


def _confidence(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _unit_interval(value: float | None) -> float | None:
    """Keep a saved start probability inside 0 to 1."""
    number = _confidence(value)
    if number is None or number < 0.0 or number > 1.0:
        return None
    return number
