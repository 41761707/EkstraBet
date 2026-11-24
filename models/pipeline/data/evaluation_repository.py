"""Read-only lookups used by model comparison reports."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from backend.database import get_db_connection


_SEASON_YEARS_QUERY = """
    SELECT id, years AS label
    FROM seasons
    WHERE id IN ({placeholders})
"""

_LEAGUE_NAMES_QUERY = """
    SELECT id, name AS label
    FROM leagues
    WHERE id IN ({placeholders})
"""

# Paczka 500 id mieści się w limicie placeholderów zapytania.
_ODDS_ID_BATCH = 500
_ODDS_COLUMNS = ("match_id", "bookmaker_id", "event_id", "odds")
_ODDS_QUERY = """
    SELECT
        match_id,
        bookmaker AS bookmaker_id,
        event AS event_id,
        odds
    FROM odds
    WHERE match_id IN ({match_placeholders})
        AND event IN ({event_placeholders})
        AND odds > 1
"""


def fetch_season_years(season_ids: Sequence[int]) -> dict[int, str]:
    """Return ``seasons.years`` keyed by season id.

    A null label is omitted. The segment helper then marks that
    season as unknown.
    """
    return _labels_by_id(season_ids, _SEASON_YEARS_QUERY)


def fetch_league_names(league_ids: Sequence[int]) -> dict[int, str]:
    """Return ``leagues.name`` keyed by league id.

    A null name is omitted.
    """
    return _labels_by_id(league_ids, _LEAGUE_NAMES_QUERY)


def fetch_match_odds(
        match_ids: Sequence[int],
        event_ids: Sequence[int]) -> pd.DataFrame:
    """Return prices above 1 for the given matches and events.

    Match ids are queried in batches of 500. ``bookmaker`` and
    ``event`` come back as ``bookmaker_id`` and ``event_id``.
    An empty id list does not open a connection.
    """
    matches = _unique_ids(match_ids)
    events = _unique_ids(event_ids)
    if not matches or not events:
        return _empty_odds()
    frames: list[pd.DataFrame] = []
    with get_db_connection() as connection:
        for offset in range(0, len(matches), _ODDS_ID_BATCH):
            batch = matches[offset:offset + _ODDS_ID_BATCH]
            frames.append(_read_odds(connection, batch, events))
    return _stack_odds(frames)


def _read_odds(
        connection: object,
        match_ids: list[int],
        event_ids: list[int]) -> pd.DataFrame:
    """Read one batch of prices for the given matches."""
    query = _ODDS_QUERY.format(
        match_placeholders=", ".join(["%s"] * len(match_ids)),
        event_placeholders=", ".join(["%s"] * len(event_ids)))
    params = tuple(match_ids) + tuple(event_ids)
    return pd.read_sql(query, connection, params=params)


def _stack_odds(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate batch frames into the public column order."""
    usable = [frame for frame in frames if not frame.empty]
    if not usable:
        return _empty_odds()
    stacked = pd.concat(usable, ignore_index=True)
    return stacked.loc[:, list(_ODDS_COLUMNS)]


def _empty_odds() -> pd.DataFrame:
    """Return an empty odds frame with the public columns."""
    return pd.DataFrame(columns=list(_ODDS_COLUMNS))


def _labels_by_id(
        raw_ids: Sequence[int],
        query_template: str) -> dict[int, str]:
    ids = _unique_ids(raw_ids)
    if not ids:
        return {}
    query = query_template.format(
        placeholders=", ".join(["%s"] * len(ids)))
    with get_db_connection() as connection:
        frame = pd.read_sql(query, connection, params=tuple(ids))
    return _label_map(frame)


def _label_map(frame: pd.DataFrame) -> dict[int, str]:
    labels: dict[int, str] = {}
    if frame.empty:
        return labels
    for _, row in frame.iterrows():
        if pd.isna(row["id"]) or pd.isna(row["label"]):
            continue
        labels[int(row["id"])] = str(row["label"])
    return labels


def _unique_ids(values: Sequence[int] | np.ndarray) -> list[int]:
    seen: set[int] = set()
    unique: list[int] = []
    for value in _id_values(values):
        number = _plain_int(value)
        if number in seen:
            continue
        seen.add(number)
        unique.append(number)
    return unique


def _id_values(values: Sequence[int] | np.ndarray) -> list[object]:
    # Payload batcha trzyma id sezonu i ligi w tablicy, nie na liście.
    if isinstance(values, np.ndarray):
        if values.ndim != 1:
            raise ValueError("ids must be a sequence of integers")
        return values.tolist()
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError("ids must be a sequence of integers")
    return list(values)


def _plain_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError("ids must be integers")
    return int(value)
