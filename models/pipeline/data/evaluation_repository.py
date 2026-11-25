"""Read-only lookups used by model comparison reports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

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
_VALUE_COLUMNS = ("match_id", "event_id", "value")
_FINISHED_COLUMNS = (
    "id",
    "league",
    "season",
    "game_date",
    "home_team_goals",
    "away_team_goals",
    "result")
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

# date_to jest wyłączne, tak jak historia meczów (game_date < date_to).
_FINISHED_RESULTS_QUERY = """
    SELECT
        id,
        league,
        season,
        game_date,
        home_team_goals,
        away_team_goals,
        result
    FROM matches
    WHERE sport_id = %s
        AND game_date >= %s
        AND game_date < %s
        AND result IN ('1', 'X', '2')
        AND home_team_goals IS NOT NULL
        AND away_team_goals IS NOT NULL
    ORDER BY game_date, id
"""

_PUBLISHED_VALUES_QUERY = """
    SELECT match_id, event_id, value
    FROM predictions
    WHERE model_id = %s
        AND match_id IN ({match_placeholders})
        AND event_id IN ({event_placeholders})
"""

_SHADOW_VALUES_QUERY = """
    SELECT match_id, event_id, value
    FROM model_shadow_predictions
    WHERE model_id = %s
        AND match_id IN ({match_placeholders})
        AND event_id IN ({event_placeholders})
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


def fetch_finished_results(
        date_from: date,
        date_to: date,
        sport_id: int) -> pd.DataFrame:
    """Return finished matches in ``[date_from, date_to)``.

    A played match has result ``1``, ``X`` or ``2`` and both goal
    columns filled. ``date_to`` is exclusive, matching finished-match
    history. Rows are ordered by kickoff, then id.
    """
    start = _require_date(date_from, "date_from")
    end = _require_date(date_to, "date_to")
    if start >= end:
        raise ValueError("date_from must be before date_to")
    sport = _plain_int(sport_id)
    with get_db_connection() as connection:
        frame = pd.read_sql(
            _FINISHED_RESULTS_QUERY,
            connection,
            params=(sport, start, end))
    return frame.loc[:, list(_FINISHED_COLUMNS)]


def fetch_published_values(
        model_id: int,
        event_ids: Sequence[int],
        match_ids: Sequence[int]) -> pd.DataFrame:
    """Return champion percentages from ``predictions``.

    Columns are ``match_id``, ``event_id`` and ``value``. Values stay
    on the stored 0–100 scale. An empty id list does not open a
    connection. Match ids are queried in batches of 500.
    """
    return _fetch_values(
        model_id, event_ids, match_ids, _PUBLISHED_VALUES_QUERY)


def fetch_shadow_values(
        model_id: int,
        event_ids: Sequence[int],
        match_ids: Sequence[int]) -> pd.DataFrame:
    """Return challenger percentages from ``model_shadow_predictions``.

    The columns and the batching match ``fetch_published_values``.
    """
    return _fetch_values(
        model_id, event_ids, match_ids, _SHADOW_VALUES_QUERY)


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


def _require_date(value: object, name: str) -> date:
    if type(value) is not date:
        raise ValueError(f"{name} must be a date")
    return value


def _fetch_values(
        model_id: int,
        event_ids: Sequence[int],
        match_ids: Sequence[int],
        query_template: str) -> pd.DataFrame:
    model = _plain_int(model_id)
    events = _unique_ids(event_ids)
    matches = _unique_ids(match_ids)
    if not events or not matches:
        return _empty_values()
    frames: list[pd.DataFrame] = []
    with get_db_connection() as connection:
        for offset in range(0, len(matches), _ODDS_ID_BATCH):
            batch = matches[offset:offset + _ODDS_ID_BATCH]
            frames.append(
                _read_values(
                    connection, model, batch, events, query_template))
    return _stack_values(frames)


def _read_values(
        connection: object,
        model_id: int,
        match_ids: list[int],
        event_ids: list[int],
        query_template: str) -> pd.DataFrame:
    query = query_template.format(
        match_placeholders=", ".join(["%s"] * len(match_ids)),
        event_placeholders=", ".join(["%s"] * len(event_ids)))
    params = (model_id, *match_ids, *event_ids)
    return pd.read_sql(query, connection, params=params)


def _stack_values(frames: list[pd.DataFrame]) -> pd.DataFrame:
    usable = [frame for frame in frames if not frame.empty]
    if not usable:
        return _empty_values()
    stacked = pd.concat(usable, ignore_index=True)
    return stacked.loc[:, list(_VALUE_COLUMNS)]


def _empty_values() -> pd.DataFrame:
    return pd.DataFrame(columns=list(_VALUE_COLUMNS))
