"""SQL queries for bet recommendations and market opportunities."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

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

# sortowanie EV po przeliczonym (p.value/100)*odds, nie po historycznym b.EV
_SORT_COLUMNS = {
    "ev": "(p.value / 100.0) * b.odds - 1",
    "probability": "p.value",
    "game_date": "m.game_date",
}

_EV_EXPR = "(p.value / 100.0) * b.odds - 1"
_EV_AFTER_TAX_EXPR = "(p.value / 100.0) * b.odds * (1 - %s) - 1"
_PRED_EV_EXPR = "(p.value / 100.0) * bo.odds - 1"
_PRED_EV_AFTER_TAX_EXPR = (
    "(p.value / 100.0) * bo.odds * (1 - %s) - 1")


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
    match_id: int | None,
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

    if match_id is not None:
        conditions.append("b.match_id = %s")
        params.append(match_id)

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
            conditions.append(f"{_EV_AFTER_TAX_EXPR} > 0")
            params.append(tax_rate)
        else:
            conditions.append(f"{_EV_EXPR} > 0")

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
    match_id: int | None = None,
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
        match_id=match_id,
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
        ORDER BY {sort_column} {order}, b.id ASC
        LIMIT %s OFFSET %s
    """
    query_params = params + [page_size, offset]

    with get_db_connection() as conn:
        count_frame = pd.read_sql(count_query, conn, params=tuple(params))
        frame = pd.read_sql(query, conn, params=tuple(query_params))

    total = int(count_frame.iloc[0]["total"])
    return frame, total


def _opportunity_date_bounds(
    match_date: date | None,
    date_from: date | None,
    date_to: date | None) -> tuple[datetime | None, datetime | None]:
    """Build inclusive [start, end) datetime bounds for indexable filters."""
    if match_date is not None:
        start = datetime.combine(match_date, time.min)
        return start, start + timedelta(days=1)
    start = (
        datetime.combine(date_from, time.min) if date_from is not None
        else None)
    end = (
        datetime.combine(date_to + timedelta(days=1), time.min)
        if date_to is not None else None)
    return start, end


def _filtered_matches_cte_sql(
    date_start: datetime | None,
    date_end: datetime | None,
    from_now: bool) -> tuple[str, list[object]]:
    """Return CTE SQL and params for sport/date-scoped matches."""
    conditions = ["m.sport_id = %s"]
    params: list[object] = []
    if date_start is not None:
        conditions.append("m.game_date >= %s")
        params.append(date_start)
    if date_end is not None:
        conditions.append("m.game_date < %s")
        params.append(date_end)
    if from_now:
        conditions.append("m.game_date >= CURRENT_TIMESTAMP")
    where_sql = " AND ".join(conditions)
    cte = f"""
        filtered_matches AS (
            SELECT
                m.id,
                m.game_date,
                m.league AS league_id,
                m.sport_id,
                m.home_team AS home_team_id,
                m.away_team AS away_team_id
            FROM matches m
            WHERE {where_sql}
        )
    """
    return cte, params


def _exclusion_keys_sql(
    keys: list[tuple[int, int, int]]) -> tuple[str, list[object]]:
    """Build NOT IN exclusion for (match_id, event_id, model_id) triples."""
    if not keys:
        return "", []
    placeholders = ", ".join(["(%s, %s, %s)"] * len(keys))
    params: list[object] = []
    for match_id, event_id, model_id in keys:
        params.extend([match_id, event_id, model_id])
    clause = (
        f"AND (p.match_id, p.event_id, p.model_id) NOT IN ({placeholders})")
    return clause, params


def _bet_match_rank_sql(apply_tax: bool) -> str:
    """Return optional ROW_NUMBER window for bet-tier one-per-match."""
    if apply_tax:
        return f""",
            ROW_NUMBER() OVER (
                PARTITION BY b.match_id
                ORDER BY {_EV_AFTER_TAX_EXPR} DESC, b.id ASC
            ) AS match_rank
        """
    return f""",
        ROW_NUMBER() OVER (
            PARTITION BY b.match_id
            ORDER BY {_EV_EXPR} DESC, b.id ASC
        ) AS match_rank
    """


def _build_bet_opportunities_sql(
    cte: str,
    apply_tax: bool,
    one_per_match: bool,
    positive_ev_only: bool) -> tuple[str, str]:
    """Return bet-tier SQL and ranking_basis bind value."""
    ranking_basis = "ev_after_tax" if apply_tax else "ev"
    order_metric = "ranked.ev_after_tax" if apply_tax else "ranked.ev"
    ev_after_tax_select = (
        f"{_EV_AFTER_TAX_EXPR} AS ev_after_tax"
        if apply_tax else "NULL AS ev_after_tax")
    match_rank_sql = _bet_match_rank_sql(apply_tax) if one_per_match else ""
    outer_where = "WHERE ranked.match_rank = 1" if one_per_match else ""
    if positive_ev_only:
        where_extra = (
            f"WHERE {_EV_AFTER_TAX_EXPR} > 0"
            if apply_tax else f"WHERE {_EV_EXPR} > 0")
    else:
        where_extra = ""
    query = f"""
        WITH {cte}
        SELECT * FROM (
            SELECT
                b.match_id,
                fm.sport_id,
                fm.league_id,
                l.name AS league_name,
                fm.game_date,
                t1.name AS home_team,
                t2.name AS away_team,
                b.event_id,
                e.name AS event_name,
                b.model_id,
                ml.name AS model_name,
                (p.value / 100.0) AS probability,
                p.value AS probability_pct,
                b.odds,
                b.bookmaker AS bookmaker_id,
                bk.name AS bookmaker_name,
                {_EV_EXPR} AS ev,
                {ev_after_tax_select},
                'bet' AS source,
                %s AS ranking_basis
                {match_rank_sql}
            FROM bets b
            JOIN filtered_matches fm ON b.match_id = fm.id
            JOIN predictions p ON (
                b.match_id = p.match_id
                AND b.event_id = p.event_id
                AND b.model_id = p.model_id)
            JOIN final_predictions fp ON p.id = fp.predictions_id
            JOIN models ml ON p.model_id = ml.id
            JOIN events e ON b.event_id = e.id
            JOIN leagues l ON fm.league_id = l.id
            JOIN teams t1 ON fm.home_team_id = t1.id
            JOIN teams t2 ON fm.away_team_id = t2.id
            LEFT JOIN bookmakers bk ON b.bookmaker = bk.id
            {where_extra}
        ) ranked
        {outer_where}
        ORDER BY {order_metric} DESC, ranked.match_id ASC, ranked.event_id ASC
        LIMIT %s
    """
    return query, ranking_basis


def _execute_bet_opportunities_query(
    conn: object,
    sport_id: int,
    date_start: datetime | None,
    date_end: datetime | None,
    from_now: bool,
    apply_tax: bool,
    tax_rate: float,
    positive_ev_only: bool,
    one_per_match: bool,
    limit: int) -> pd.DataFrame:
    """Execute the bet-tier opportunities SQL with correct bind order."""
    cte, date_params = _filtered_matches_cte_sql(
        date_start, date_end, from_now)
    query, ranking_basis = _build_bet_opportunities_sql(
        cte=cte,
        apply_tax=apply_tax,
        one_per_match=one_per_match,
        positive_ev_only=positive_ev_only)

    # kolejność %s: CTE -> SELECT tax -> ranking_basis -> window -> filter
    params: list[object] = [sport_id, *date_params]
    if apply_tax:
        params.append(tax_rate)
    params.append(ranking_basis)
    if one_per_match and apply_tax:
        params.append(tax_rate)
    if positive_ev_only and apply_tax:
        params.append(tax_rate)
    params.append(limit)
    return pd.read_sql(query, conn, params=tuple(params))


def _prediction_rank_window_sql(apply_tax: bool) -> str:
    """Return ROW_NUMBER window for prediction-tier one-per-match ranking."""
    if apply_tax:
        return f""",
            ROW_NUMBER() OVER (
                PARTITION BY p.match_id
                ORDER BY
                    CASE WHEN bo.odds IS NOT NULL THEN 0 ELSE 1 END,
                    CASE WHEN bo.odds IS NOT NULL
                        THEN {_PRED_EV_AFTER_TAX_EXPR}
                        ELSE p.value / 100.0 END DESC,
                    p.id ASC
            ) AS match_rank
        """
    return f""",
        ROW_NUMBER() OVER (
            PARTITION BY p.match_id
            ORDER BY
                CASE WHEN bo.odds IS NOT NULL THEN 0 ELSE 1 END,
                CASE WHEN bo.odds IS NOT NULL
                    THEN {_PRED_EV_EXPR}
                    ELSE p.value / 100.0 END DESC,
                p.id ASC
        ) AS match_rank
    """


def _prediction_ev_select_sql(apply_tax: bool) -> tuple[str, str, str, str]:
    """Return EV select fragments and positive-EV filter for predictions."""
    ev_select = (
        f"CASE WHEN bo.odds IS NOT NULL THEN {_PRED_EV_EXPR} "
        "ELSE NULL END AS ev")
    if apply_tax:
        ev_after_tax_select = (
            f"CASE WHEN bo.odds IS NOT NULL "
            f"THEN {_PRED_EV_AFTER_TAX_EXPR} "
            "ELSE NULL END AS ev_after_tax")
        positive_filter = (
            "AND (bo.odds IS NULL OR "
            f"{_PRED_EV_AFTER_TAX_EXPR} > 0)")
    else:
        ev_after_tax_select = "NULL AS ev_after_tax"
        positive_filter = (
            f"AND (bo.odds IS NULL OR {_PRED_EV_EXPR} > 0)")
    ranking_basis_sql = (
        "CASE WHEN bo.odds IS NULL THEN 'probability' "
        f"WHEN {'TRUE' if apply_tax else 'FALSE'} THEN 'ev_after_tax' "
        "ELSE 'ev' END")
    return ev_select, ev_after_tax_select, positive_filter, ranking_basis_sql


def _build_prediction_opportunities_sql(
    cte: str,
    apply_tax: bool,
    one_per_match: bool,
    positive_ev_only: bool,
    exclude_sql: str,
    match_exclude_sql: str) -> str:
    """Assemble prediction-tier opportunities SQL."""
    (
        ev_select,
        ev_after_tax_select,
        positive_filter,
        ranking_basis_sql
    ) = _prediction_ev_select_sql(apply_tax)
    if not positive_ev_only:
        positive_filter = ""
    match_rank_sql = (
        _prediction_rank_window_sql(apply_tax) if one_per_match else "")
    outer_where = "WHERE ranked.match_rank = 1" if one_per_match else ""
    return f"""
        WITH {cte},
        best_odds AS (
            SELECT
                o.match_id,
                o.event AS event_id,
                o.odds,
                o.bookmaker AS bookmaker_id,
                bk.name AS bookmaker_name,
                ROW_NUMBER() OVER (
                    PARTITION BY o.match_id, o.event
                    ORDER BY o.odds DESC, o.id ASC
                ) AS rn
            FROM odds o
            JOIN filtered_matches fm ON o.match_id = fm.id
            LEFT JOIN bookmakers bk ON o.bookmaker = bk.id
        )
        SELECT * FROM (
            SELECT
                p.match_id,
                fm.sport_id,
                fm.league_id,
                l.name AS league_name,
                fm.game_date,
                t1.name AS home_team,
                t2.name AS away_team,
                p.event_id,
                e.name AS event_name,
                p.model_id,
                ml.name AS model_name,
                (p.value / 100.0) AS probability,
                p.value AS probability_pct,
                bo.odds,
                bo.bookmaker_id,
                bo.bookmaker_name,
                {ev_select},
                {ev_after_tax_select},
                'prediction' AS source,
                {ranking_basis_sql} AS ranking_basis
                {match_rank_sql}
            FROM final_predictions fp
            JOIN predictions p ON p.id = fp.predictions_id
            JOIN filtered_matches fm ON p.match_id = fm.id
            JOIN models ml ON p.model_id = ml.id
            JOIN events e ON p.event_id = e.id
            JOIN leagues l ON fm.league_id = l.id
            JOIN teams t1 ON fm.home_team_id = t1.id
            JOIN teams t2 ON fm.away_team_id = t2.id
            LEFT JOIN best_odds bo ON (
                bo.match_id = p.match_id
                AND bo.event_id = p.event_id
                AND bo.rn = 1)
            WHERE 1 = 1
              {exclude_sql}
              {match_exclude_sql}
              {positive_filter}
        ) ranked
        {outer_where}
        ORDER BY
            CASE WHEN ranked.odds IS NOT NULL THEN 0 ELSE 1 END,
            CASE
                WHEN ranked.odds IS NOT NULL
                    AND ranked.ev_after_tax IS NOT NULL
                    THEN ranked.ev_after_tax
                WHEN ranked.odds IS NOT NULL THEN ranked.ev
                ELSE ranked.probability
            END DESC,
            ranked.match_id ASC,
            ranked.event_id ASC
        LIMIT %s
    """


def _execute_prediction_opportunities_query(
    conn: object,
    sport_id: int,
    date_start: datetime | None,
    date_end: datetime | None,
    from_now: bool,
    apply_tax: bool,
    tax_rate: float,
    positive_ev_only: bool,
    one_per_match: bool,
    exclude_keys: list[tuple[int, int, int]],
    exclude_match_ids: list[int],
    limit: int) -> pd.DataFrame:
    """Fetch prediction-tier opportunities with optional best odds."""
    cte, date_params = _filtered_matches_cte_sql(
        date_start, date_end, from_now)
    exclude_sql, exclude_params = _exclusion_keys_sql(exclude_keys)

    match_exclude_sql = ""
    match_exclude_params: list[object] = []
    if one_per_match and exclude_match_ids:
        placeholders = ", ".join(["%s"] * len(exclude_match_ids))
        match_exclude_sql = f"AND p.match_id NOT IN ({placeholders})"
        match_exclude_params = list(exclude_match_ids)

    query = _build_prediction_opportunities_sql(
        cte=cte,
        apply_tax=apply_tax,
        one_per_match=one_per_match,
        positive_ev_only=positive_ev_only,
        exclude_sql=exclude_sql,
        match_exclude_sql=match_exclude_sql)

    # kolejność %s: CTE -> SELECT tax -> window tax -> exclude -> filter tax
    params: list[object] = [sport_id, *date_params]
    if apply_tax:
        params.append(tax_rate)
    if one_per_match and apply_tax:
        params.append(tax_rate)
    params.extend(exclude_params)
    params.extend(match_exclude_params)
    if positive_ev_only and apply_tax:
        params.append(tax_rate)
    params.append(limit)
    return pd.read_sql(query, conn, params=tuple(params))


def _collect_bet_exclusion_keys(
    bet_frame: pd.DataFrame,
    one_per_match: bool) -> tuple[list[tuple[int, int, int]], list[int]]:
    """Collect dedupe keys and match IDs already covered by bet tier."""
    exclude_keys: list[tuple[int, int, int]] = []
    exclude_match_ids: list[int] = []
    if bet_frame.empty:
        return exclude_keys, exclude_match_ids
    for _, row in bet_frame.iterrows():
        exclude_keys.append((
            int(row["match_id"]),
            int(row["event_id"]),
            int(row["model_id"])))
        if one_per_match:
            exclude_match_ids.append(int(row["match_id"]))
    return exclude_keys, list(dict.fromkeys(exclude_match_ids))


def search_market_opportunities(
    sport_id: int,
    match_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    from_now: bool = True,
    apply_tax: bool = True,
    tax_rate: float = 0.12,
    positive_ev_only: bool = True,
    include_prediction_fallback: bool = True,
    one_per_match: bool = True,
    limit: int = 10) -> tuple[pd.DataFrame, int, dict[str, int]]:
    """Return global market opportunities across all leagues of a sport.

    Tier 1: ready ``bets`` ranked by recalculated EV.
    Tier 2: ``final_predictions`` (+ best odds when present) filling gaps.
    """
    date_start, date_end = _opportunity_date_bounds(
        match_date, date_from, date_to)
    source_counts = {"bet": 0, "prediction": 0}

    with get_db_connection() as conn:
        bet_frame = _execute_bet_opportunities_query(
            conn=conn,
            sport_id=sport_id,
            date_start=date_start,
            date_end=date_end,
            from_now=from_now,
            apply_tax=apply_tax,
            tax_rate=tax_rate,
            positive_ev_only=positive_ev_only,
            one_per_match=one_per_match,
            limit=limit)
        source_counts["bet"] = len(bet_frame)

        frames = [bet_frame] if not bet_frame.empty else []
        remaining = limit - len(bet_frame)

        if include_prediction_fallback and remaining > 0:
            exclude_keys, exclude_match_ids = _collect_bet_exclusion_keys(
                bet_frame, one_per_match)
            pred_frame = _execute_prediction_opportunities_query(
                conn=conn,
                sport_id=sport_id,
                date_start=date_start,
                date_end=date_end,
                from_now=from_now,
                apply_tax=apply_tax,
                tax_rate=tax_rate,
                positive_ev_only=positive_ev_only,
                one_per_match=one_per_match,
                exclude_keys=exclude_keys,
                exclude_match_ids=exclude_match_ids,
                limit=remaining)
            source_counts["prediction"] = len(pred_frame)
            if not pred_frame.empty:
                frames.append(pred_frame)

    if not frames:
        empty = pd.DataFrame()
        return empty, 0, source_counts

    combined = pd.concat(frames, ignore_index=True)
    return combined, len(combined), source_counts
