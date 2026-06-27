"""SQL queries for bet recommendations."""

from __future__ import annotations

from datetime import date

import pandas as pd

from backend.database import get_db_connection

_EVENT_FAMILY_JOIN = """
    LEFT JOIN (
        SELECT
            efm.event_id,
            MIN(efm.event_family_id) AS event_family_id
        FROM event_family_mappings efm
        GROUP BY efm.event_id
    ) efm_one ON e.id = efm_one.event_id
    LEFT JOIN event_families ef ON efm_one.event_family_id = ef.id
"""

_BASE_FROM = f"""
    FROM bets b
    JOIN predictions p ON (
        b.match_id = p.match_id
        AND b.event_id = p.event_id
        AND b.model_id = p.model_id)
    JOIN final_predictions fp ON p.id = fp.predictions_id
    JOIN models ml ON p.model_id = ml.id
    JOIN matches m ON b.match_id = m.id
    JOIN teams t1 ON m.home_team = t1.id
    JOIN teams t2 ON m.away_team = t2.id
    JOIN events e ON b.event_id = e.id
    JOIN leagues l ON m.league = l.id
    LEFT JOIN bookmakers bk ON b.bookmaker = bk.id
    {_EVENT_FAMILY_JOIN}
"""

_SELECT_COLUMNS = """
    SELECT
        b.id AS bet_id,
        b.match_id,
        b.event_id,
        b.odds,
        b.EV AS ev,
        b.outcome AS bet_outcome,
        b.custom_bet,
        b.bookmaker AS bookmaker_id,
        bk.name AS bookmaker_name,
        p.id AS prediction_id,
        p.value AS probability,
        p.model_id,
        ml.name AS model_name,
        m.game_date,
        m.league AS league_id,
        l.name AS league_name,
        m.season AS season_id,
        m.home_team AS home_team_id,
        t1.name AS home_team_name,
        t1.shortcut AS home_team_shortcut,
        m.away_team AS away_team_id,
        t2.name AS away_team_name,
        t2.shortcut AS away_team_shortcut,
        e.name AS event_name,
        ef.id AS event_family_id,
        ef.name AS event_family_name
"""

_SORT_COLUMNS = {
    "ev": "b.EV",
    "probability": "p.value",
    "game_date": "m.game_date",
}


def _append_in_filter(
    column: str,
    values: list[int] | None,
    conditions: list[str],
    params: list[object]) -> None:
    """Append an IN (...) filter when values are provided."""
    if not values:
        return
    placeholders = ",".join(["%s"] * len(values))
    conditions.append(f"{column} IN ({placeholders})")
    params.extend(values)


def _build_filters(
    league_ids: list[int] | None,
    season_id: int | None,
    event_ids: list[int] | None,
    model_ids: list[int] | None,
    bookmaker_ids: list[int] | None,
    match_date: date | None,
    date_from: date | None,
    date_to: date | None,
    from_now: bool,
    min_odds: float | None,
    positive_ev_only: bool,
    apply_tax: bool,
    tax_rate: float,
    settlement_status: str | None) -> tuple[list[str], list[object]]:
    """Build WHERE conditions and query parameters."""
    conditions: list[str] = []
    params: list[object] = []

    _append_in_filter("m.league", league_ids, conditions, params)
    _append_in_filter("b.event_id", event_ids, conditions, params)
    _append_in_filter("p.model_id", model_ids, conditions, params)
    _append_in_filter("b.bookmaker", bookmaker_ids, conditions, params)

    if season_id is not None:
        conditions.append("m.season = %s")
        params.append(season_id)

    if from_now:
        conditions.append("m.game_date >= CURRENT_TIMESTAMP")
    elif match_date is not None:
        conditions.append("CAST(m.game_date AS DATE) = %s")
        params.append(match_date)
    else:
        if date_from is not None:
            conditions.append("CAST(m.game_date AS DATE) >= %s")
            params.append(date_from)
        if date_to is not None:
            conditions.append("CAST(m.game_date AS DATE) <= %s")
            params.append(date_to)

    if min_odds is not None:
        conditions.append("b.odds >= %s")
        params.append(min_odds)

    if positive_ev_only:
        if apply_tax:
            conditions.append(
                "(p.value * b.odds * (1 - %s) - 1) > 0")
            params.append(tax_rate)
        else:
            conditions.append("b.EV > 0")

    if settlement_status == "pending":
        conditions.append("b.outcome IS NULL")
    elif settlement_status == "settled":
        conditions.append("b.outcome IS NOT NULL")
    elif settlement_status == "won":
        conditions.append("b.outcome = 1")
    elif settlement_status == "lost":
        conditions.append("b.outcome = 0")

    return conditions, params


def search_bet_recommendations(
    league_ids: list[int] | None = None,
    season_id: int | None = None,
    event_ids: list[int] | None = None,
    model_ids: list[int] | None = None,
    bookmaker_ids: list[int] | None = None,
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
    """Return paginated bet recommendations and total count."""
    conditions, params = _build_filters(
        league_ids=league_ids,
        season_id=season_id,
        event_ids=event_ids,
        model_ids=model_ids,
        bookmaker_ids=bookmaker_ids,
        match_date=match_date,
        date_from=date_from,
        date_to=date_to,
        from_now=from_now,
        min_odds=min_odds,
        positive_ev_only=positive_ev_only,
        apply_tax=apply_tax,
        tax_rate=tax_rate,
        settlement_status=settlement_status)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sort_column = _SORT_COLUMNS.get(sort_by, "b.EV")
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
        ORDER BY {sort_column} {order}, b.id ASC
        LIMIT %s OFFSET %s
    """
    query_params = params + [page_size, offset]

    with get_db_connection() as conn:
        count_frame = pd.read_sql(count_query, conn, params=tuple(params))
        frame = pd.read_sql(query, conn, params=tuple(query_params))

    total = int(count_frame.iloc[0]["total"])
    return frame, total
