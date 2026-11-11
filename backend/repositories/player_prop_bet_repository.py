"""Read hockey player-prop lines, predictions and recent stats."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from backend.database import get_db_connection
from backend.sports.hockey.player_prop_history import (
    LINE_MATCH_EPSILON,
    OVER_PROP_EVENT_IDS,
    settlement_case_sql)


_EV_EXPR = "(pp.probability / 100.0) * ppl.odds - 1"
_EV_AFTER_TAX_EXPR = (
    "(pp.probability / 100.0) * ppl.odds * (1 - %s) - 1")
_LINE_MATCH_SQL = f"ABS(pp.line - ppl.line) < {LINE_MATCH_EPSILON}"
_CATALOG_EVENT_IDS = ", ".join(
    str(event_id) for event_id in OVER_PROP_EVENT_IDS)
_SETTLEMENT_SQL = settlement_case_sql("hs", "ppl")
_EXACT_SETTLEMENT = frozenset({"pending", "won", "lost"})
_SORT_COLUMNS = {
    "ev": _EV_EXPR,
    "probability": "pp.probability",
    "game_date": "m.game_date"}
# Identyfikator kolumny nie może być parametrem SQL.
_ALLOWED_STAT_COLUMNS = frozenset({"sog", "points", "assists", "goals"})

_SELECT_COLUMNS = f"""
    SELECT
        ppl.id AS line_id,
        ppl.player_id AS player_id,
        pl.common_name AS player_name,
        ppl.line AS line,
        ppl.match_id AS match_id,
        m.league AS league_id,
        l.name AS league_name,
        m.season AS season_id,
        m.game_date AS game_date,
        m.home_team AS home_team_id,
        t1.name AS home_team_name,
        t1.shortcut AS home_team_shortcut,
        m.away_team AS away_team_id,
        t2.name AS away_team_name,
        t2.shortcut AS away_team_shortcut,
        ppl.event_id AS event_id,
        e.name AS event_name,
        ppl.odds AS odds,
        pp.probability AS probability,
        ppl.bookmaker_id AS bookmaker_id,
        bk.name AS bookmaker_name,
        pp.model_id AS model_id,
        ml.name AS model_name,
        {_SETTLEMENT_SQL} AS settlement_status
"""

_BASE_FROM = f"""
    FROM player_props_lines ppl
    JOIN player_predictions pp ON (
        pp.player_id = ppl.player_id
        AND pp.match_id = ppl.match_id
        AND pp.event_id = ppl.event_id
        AND {_LINE_MATCH_SQL})
    JOIN models ml ON pp.model_id = ml.id
    JOIN matches m ON ppl.match_id = m.id
    JOIN leagues l ON m.league = l.id
    JOIN events e ON ppl.event_id = e.id
    JOIN players pl ON ppl.player_id = pl.id
    JOIN teams t1 ON m.home_team = t1.id
    JOIN teams t2 ON m.away_team = t2.id
    LEFT JOIN bookmakers bk ON ppl.bookmaker_id = bk.id
    LEFT JOIN hockey_match_player_stats hs ON (
        hs.player_id = ppl.player_id
        AND hs.match_id = ppl.match_id)
"""


def _catalog_conditions() -> list[str]:
    """Return predicates that do not depend on the request."""
    return [
        f"ppl.event_id IN ({_CATALOG_EVENT_IDS})",
        "ppl.odds >= 1",
        "ppl.line > 0",
        _LINE_MATCH_SQL]


def _append_in_filter(
        column: str,
        values: list[int] | None,
        conditions: list[str],
        params: list[object]) -> None:
    """Append an IN (...) filter when values are provided."""
    if not values:
        return
    placeholders = ", ".join(["%s"] * len(values))
    conditions.append(f"{column} IN ({placeholders})")
    params.extend(values)


def _append_date_filter(
        match_date: date | None,
        date_from: date | None,
        date_to: date | None,
        from_now: bool,
        conditions: list[str],
        params: list[object]) -> None:
    """Apply the same date rule as team bet recommendations."""
    if from_now:
        conditions.append("m.game_date >= CURRENT_TIMESTAMP")
        return
    if match_date is not None:
        conditions.append("CAST(m.game_date AS DATE) = %s")
        params.append(match_date)
        return
    if date_from is not None:
        conditions.append("CAST(m.game_date AS DATE) >= %s")
        params.append(date_from)
    if date_to is not None:
        conditions.append("CAST(m.game_date AS DATE) <= %s")
        params.append(date_to)


def _append_positive_ev(
        positive_ev_only: bool,
        apply_tax: bool,
        tax_rate: float,
        conditions: list[str],
        params: list[object]) -> None:
    """Keep rows with positive EV, after tax when requested."""
    if not positive_ev_only:
        return
    if apply_tax:
        conditions.append(f"{_EV_AFTER_TAX_EXPR} > 0")
        params.append(tax_rate)
        return
    conditions.append(f"{_EV_EXPR} > 0")


def _append_settlement(
        settlement_status: str | None,
        conditions: list[str],
        params: list[object]) -> None:
    """Filter by the settlement CASE. The status is a bound value."""
    if settlement_status == "settled":
        conditions.append(f"{_SETTLEMENT_SQL} <> 'pending'")
        return
    if settlement_status in _EXACT_SETTLEMENT:
        conditions.append(f"{_SETTLEMENT_SQL} = %s")
        params.append(settlement_status)


def _narrow_event_ids(event_ids: list[int] | None) -> list[int] | None:
    """Keep only catalog events from the request.

    ``None`` means the caller did not narrow events. An empty list
    means nothing in the request is in the catalog.
    """
    if not event_ids:
        return None
    allowed = set(OVER_PROP_EVENT_IDS)
    return [
        event_id for event_id in event_ids
        if event_id in allowed]


def _build_filters(
        league_ids: list[int] | None,
        event_ids: list[int] | None,
        model_ids: list[int] | None,
        match_date: date | None,
        date_from: date | None,
        date_to: date | None,
        from_now: bool,
        min_odds: float | None,
        positive_ev_only: bool,
        apply_tax: bool,
        tax_rate: float,
        settlement_status: str | None) -> tuple[list[str], list[object]]:
    """Build WHERE conditions and bound parameters."""
    conditions = _catalog_conditions()
    params: list[object] = []
    _append_in_filter("m.league", league_ids, conditions, params)
    _append_in_filter("ppl.event_id", event_ids, conditions, params)
    _append_in_filter("pp.model_id", model_ids, conditions, params)
    _append_date_filter(
        match_date, date_from, date_to, from_now, conditions, params)
    if min_odds is not None:
        conditions.append("ppl.odds >= %s")
        params.append(min_odds)
    _append_positive_ev(
        positive_ev_only, apply_tax, tax_rate, conditions, params)
    _append_settlement(settlement_status, conditions, params)
    return conditions, params


def search_player_prop_recommendations(
        league_ids: list[int] | None = None,
        event_ids: list[int] | None = None,
        model_ids: list[int] | None = None,
        match_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        from_now: bool = False,
        min_odds: float | None = None,
        positive_ev_only: bool = False,
        apply_tax: bool = False,
        tax_rate: float = 0.12,
        settlement_status: str | None = None,
        sort_by: str = "ev",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 50) -> tuple[pd.DataFrame, int]:
    """Return one page of prop lines paired with predictions.

    The settlement CASE is both a column and, when requested, a
    WHERE predicate, so LIMIT does not run before that filter.
    """
    narrowed_event_ids = _narrow_event_ids(event_ids)
    # IN () jest niepoprawne, a same identyfikatory spoza katalogu
    # nie mogą zastąpić czwórki. Taka prośba ma pustą stronę.
    if narrowed_event_ids is not None and not narrowed_event_ids:
        return pd.DataFrame(), 0

    conditions, params = _build_filters(
        league_ids=league_ids,
        event_ids=narrowed_event_ids,
        model_ids=model_ids,
        match_date=match_date,
        date_from=date_from,
        date_to=date_to,
        from_now=from_now,
        min_odds=min_odds,
        positive_ev_only=positive_ev_only,
        apply_tax=apply_tax,
        tax_rate=tax_rate,
        settlement_status=settlement_status)
    where_clause = "WHERE " + " AND ".join(conditions)
    sort_column = _SORT_COLUMNS.get(sort_by, _SORT_COLUMNS["ev"])
    order = "ASC" if sort_order == "asc" else "DESC"
    offset = (page - 1) * page_size
    count_query = f"""
        SELECT COUNT(*) AS total
        {_BASE_FROM}
        {where_clause}
    """
    query = f"""
        {_SELECT_COLUMNS}
        {_BASE_FROM}
        {where_clause}
        ORDER BY {sort_column} {order}, ppl.id ASC, pp.model_id ASC
        LIMIT %s OFFSET %s
    """
    with get_db_connection() as conn:
        count_frame = pd.read_sql(
            count_query, conn, params=tuple(params))
        frame = pd.read_sql(
            query, conn, params=tuple(params + [page_size, offset]))
    total = int(count_frame.iloc[0]["total"])
    return frame, total


def fetch_recent_player_stats(
        anchors: list[tuple[int, int, datetime, str]],
        window: int) -> pd.DataFrame:
    """Return at most ``window`` earlier values for each anchor.

    An anchor is ``(player_id, match_id, game_date, column)``.
    Rows are newest first inside one anchor. Anchors that share a
    column share one query. An empty list does not open a connection.

    The same player, match and column is queried once, so two models
    do not repeat the series. ``stat_column`` separates shots from
    goals of that match. Model identity stays on the recommendation.
    """
    if not anchors:
        return pd.DataFrame()
    grouped = _group_anchors_by_column(_unique_anchors(anchors))
    frames: list[pd.DataFrame] = []
    with get_db_connection() as conn:
        for column, group in grouped:
            frames.append(
                _read_recent_column(conn, column, group, window))
    if len(frames) == 1:
        return frames[0]
    return pd.concat(frames, ignore_index=True)


def fetch_match_player_stats(
        pairs: list[tuple[int, int]]) -> pd.DataFrame:
    """Return one stats row for each player and match.

    Columns are sog, points, assists and goals, plus the pair key.
    A repeated pair is read once. An empty list does not open a
    connection. A pair with no stats row is absent.
    """
    if not pairs:
        return pd.DataFrame()
    unique_pairs = _unique_pairs(pairs)
    params: list[object] = []
    for player_id, match_id in unique_pairs:
        params.extend((player_id, match_id))
    query = _match_stats_query(len(unique_pairs))
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=tuple(params))


def _assert_stat_column(column: str) -> None:
    """Reject a column that is not one of the four prop stats."""
    if column in _ALLOWED_STAT_COLUMNS:
        return
    raise ValueError(f"Unknown player prop stat column: {column}")


def _unique_anchors(
        anchors: list[tuple[int, int, datetime, str]]
        ) -> list[tuple[int, int, datetime, str]]:
    """Keep the first anchor for each player, match and column."""
    # Historia należy do zawodnika i meczu, nie do modelu.
    # Druga kopia kotwicy powtórzyłaby te same mecze bez modelu.
    seen: set[tuple[int, int, str]] = set()
    unique: list[tuple[int, int, datetime, str]] = []
    for player_id, match_id, game_date, column in anchors:
        _assert_stat_column(column)
        key = (player_id, match_id, column)
        if key in seen:
            continue
        seen.add(key)
        unique.append((player_id, match_id, game_date, column))
    return unique


def _unique_pairs(
        pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Keep the first pair for each player and match."""
    # Kilka zdarzeń i kilka modeli wskazują ten sam mecz.
    seen: set[tuple[int, int]] = set()
    unique: list[tuple[int, int]] = []
    for pair in pairs:
        if pair in seen:
            continue
        seen.add(pair)
        unique.append(pair)
    return unique


def _group_anchors_by_column(
        anchors: list[tuple[int, int, datetime, str]]
        ) -> list[tuple[str, list[tuple[int, int, datetime]]]]:
    """Group anchors by column, in the order columns first appear."""
    grouped: dict[str, list[tuple[int, int, datetime]]] = {}
    for player_id, match_id, game_date, column in anchors:
        _assert_stat_column(column)
        grouped.setdefault(column, []).append(
            (player_id, match_id, game_date))
    return list(grouped.items())


def _read_recent_column(
        conn: object,
        column: str,
        group: list[tuple[int, int, datetime]],
        window: int) -> pd.DataFrame:
    """Run one lateral query for every anchor of a single column."""
    params: list[object] = []
    for player_id, match_id, game_date in group:
        params.extend((player_id, match_id, game_date))
    params.append(window)
    query = _history_query(column, len(group))
    frame = pd.read_sql(query, conn, params=tuple(params))
    # Ta sama para zawodnik-mecz ma osobną serię na każdą kolumnę.
    frame["stat_column"] = column
    return frame


def _history_query(column: str, anchor_count: int) -> str:
    """Build the lateral history query for one whitelisted column."""
    _assert_stat_column(column)
    union_sql = _anchor_union(anchor_count)
    return f"""
        SELECT
            anchor.player_id,
            anchor.match_id AS anchor_match_id,
            hist.match_id,
            hist.game_date,
            hist.stat_value
        FROM (
            {union_sql}
        ) anchor
        JOIN LATERAL (
            SELECT
                s.match_id,
                m.game_date,
                s.{column} AS stat_value
            FROM hockey_match_player_stats s
            JOIN matches m ON m.id = s.match_id
            WHERE s.player_id = anchor.player_id
                AND m.game_date < anchor.before_ts
                AND s.match_id <> anchor.match_id
                AND s.{column} IS NOT NULL
            ORDER BY m.game_date DESC, s.match_id DESC
            LIMIT %s
        ) hist ON TRUE
    """


def _anchor_union(anchor_count: int) -> str:
    """Build the anchor derived table. The first row names columns."""
    first = (
        "SELECT %s AS player_id, %s AS match_id, "
        "%s AS before_ts")
    if anchor_count == 1:
        return first
    rest = "\n            UNION ALL\n            SELECT %s, %s, %s"
    return first + rest * (anchor_count - 1)


def _match_stats_query(pair_count: int) -> str:
    """Build the stats lookup for pairs from the recommendation page."""
    union_sql = _pair_union(pair_count)
    return f"""
        SELECT
            s.player_id,
            s.match_id,
            s.sog,
            s.points,
            s.assists,
            s.goals
        FROM (
            {union_sql}
        ) wanted
        JOIN hockey_match_player_stats s ON (
            s.player_id = wanted.player_id
            AND s.match_id = wanted.match_id)
    """


def _pair_union(pair_count: int) -> str:
    """Build the pair derived table. The first row names columns."""
    first = "SELECT %s AS player_id, %s AS match_id"
    if pair_count == 1:
        return first
    rest = "\n            UNION ALL\n            SELECT %s, %s"
    return first + rest * (pair_count - 1)
