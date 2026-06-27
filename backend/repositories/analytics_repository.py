"""SQL queries for model analytics and statistics."""

from __future__ import annotations
from datetime import date
import pandas as pd
from backend.database import get_db_connection

RESULT_EVENT_IDS = (1, 2, 3)
OU_EVENT_IDS = (8, 12)
BTTS_EVENT_IDS = (6, 172)

_STAT_EVENT_IDS = {
    "ou": OU_EVENT_IDS,
    "btts": BTTS_EVENT_IDS,
    "result": RESULT_EVENT_IDS,
}

_PREDICTION_BET_SELECT = """
    SELECT
        m.id AS match_id,
        m.league AS league_id,
        m.season AS season_id,
        m.home_team AS home_team_id,
        m.away_team AS away_team_id,
        m.result,
        m.home_team_goals,
        m.away_team_goals,
        p.event_id,
        fp.outcome AS pred_outcome,
        b.event_id AS bet_event_id,
        b.odds,
        b.EV AS ev,
        b.outcome AS bet_outcome
    FROM matches m
    JOIN predictions p ON p.match_id = m.id
    JOIN final_predictions fp ON fp.predictions_id = p.id
    JOIN bets b ON (
        b.match_id = m.id
        AND b.event_id = p.event_id
        AND b.model_id = p.model_id)
    WHERE p.model_id IN ({model_placeholders})
"""


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


def _build_match_filters(
    league_ids: list[int] | None,
    season_id: int | None,
    date_from: date | None,
    date_to: date | None,
    round_from: int | None,
    round_to: int | None,
    team_id: int | None,
    settled_only: bool,
    positive_ev_only: bool,
    apply_tax: bool,
    tax_rate: float) -> tuple[list[str], list[object]]:
    """Build shared match and bet filter conditions."""
    conditions: list[str] = []
    params: list[object] = []

    _append_in_filter("m.league", league_ids, conditions, params)

    if season_id is not None:
        conditions.append("m.season = %s")
        params.append(season_id)

    if date_from is not None:
        conditions.append("CAST(m.game_date AS DATE) >= %s")
        params.append(date_from)

    if date_to is not None:
        conditions.append("CAST(m.game_date AS DATE) <= %s")
        params.append(date_to)

    if round_from is not None:
        conditions.append("m.round >= %s")
        params.append(round_from)

    if round_to is not None:
        conditions.append("m.round <= %s")
        params.append(round_to)

    if team_id is not None:
        conditions.append("(m.home_team = %s OR m.away_team = %s)")
        params.extend([team_id, team_id])

    if settled_only:
        conditions.append("m.result != '0'")

    if positive_ev_only:
        if apply_tax:
            conditions.append("(p.value * b.odds * (1 - %s) - 1) > 0")
            params.append(tax_rate)
        else:
            conditions.append("b.EV > 0")

    return conditions, params


def fetch_prediction_bet_rows(
    stat_type: str,
    model_ids: list[int],
    league_ids: list[int] | None = None,
    season_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    round_from: int | None = None,
    round_to: int | None = None,
    team_id: int | None = None,
    settled_only: bool = True,
    positive_ev_only: bool = False,
    apply_tax: bool = False,
    tax_rate: float = 0.12) -> pd.DataFrame:
    """Return joined prediction and bet rows for one stat family."""
    if not model_ids:
        return pd.DataFrame()

    event_ids = _STAT_EVENT_IDS[stat_type]
    event_placeholders = ",".join(["%s"] * len(event_ids))
    model_placeholders = ",".join(["%s"] * len(model_ids))

    conditions, params = _build_match_filters(
        league_ids=league_ids,
        season_id=season_id,
        date_from=date_from,
        date_to=date_to,
        round_from=round_from,
        round_to=round_to,
        team_id=team_id,
        settled_only=settled_only,
        positive_ev_only=positive_ev_only,
        apply_tax=apply_tax,
        tax_rate=tax_rate)

    conditions.append(f"p.event_id IN ({event_placeholders})")
    params.extend(event_ids)

    where_clause = " AND ".join(conditions)
    query = _PREDICTION_BET_SELECT.format(
        model_placeholders=model_placeholders)
    query = f"{query} AND {where_clause}"
    query_params = tuple(model_ids) + tuple(params)

    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=query_params)


def _event_id_placeholders(stat_type: str) -> str:
    """Return SQL placeholders for a stat family's event IDs."""
    event_ids = _STAT_EVENT_IDS[stat_type]
    return ",".join(["%s"] * len(event_ids))


def fetch_league_prediction_aggregation(
    season_id: int,
    stat_type: str) -> pd.DataFrame:
    """Return per-league prediction accuracy for active leagues."""
    event_placeholders = _event_id_placeholders(stat_type)
    query = f"""
        SELECT
            l.id AS entity_id,
            l.name AS entity_name,
            COUNT(CASE WHEN p.event_id IN ({event_placeholders}) THEN 1 END)
                AS total_predictions,
            COUNT(
                CASE
                    WHEN p.event_id IN ({event_placeholders})
                        AND fp.outcome = 1 THEN 1
                END) AS correct_predictions
        FROM predictions p
        JOIN final_predictions fp ON fp.predictions_id = p.id
        JOIN matches m ON p.match_id = m.id
        JOIN leagues l ON m.league = l.id
        WHERE m.season = %s
            AND m.result != '0'
            AND l.active = 1
            AND p.event_id IN ({event_placeholders})
        GROUP BY l.id, l.name
        HAVING total_predictions > 0
        ORDER BY l.name
    """
    event_ids = _STAT_EVENT_IDS[stat_type]
    params = (season_id, *event_ids, *event_ids, *event_ids)

    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_team_prediction_aggregation(
    season_id: int,
    league_id: int,
    stat_type: str) -> pd.DataFrame:
    """Return per-team prediction accuracy for one league and season."""
    event_placeholders = _event_id_placeholders(stat_type)
    query = f"""
        SELECT
            t.id AS entity_id,
            t.name AS entity_name,
            COUNT(CASE WHEN p.event_id IN ({event_placeholders}) THEN 1 END)
                AS total_predictions,
            COUNT(
                CASE
                    WHEN p.event_id IN ({event_placeholders})
                        AND fp.outcome = 1 THEN 1
                END) AS correct_predictions
        FROM predictions p
        JOIN final_predictions fp ON fp.predictions_id = p.id
        JOIN matches m ON p.match_id = m.id
        JOIN teams t ON (m.home_team = t.id OR m.away_team = t.id)
        WHERE m.season = %s
            AND m.league = %s
            AND m.result != '0'
            AND p.event_id IN ({event_placeholders})
        GROUP BY t.id, t.name
        HAVING total_predictions > 0
        ORDER BY t.name
    """
    event_ids = _STAT_EVENT_IDS[stat_type]
    params = (season_id, league_id, *event_ids, *event_ids, *event_ids)

    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_league_average_prediction_stats(
    season_id: int,
    stat_type: str,
    league_id: int | None = None) -> tuple[int, int]:
    """Return league-wide or global prediction totals for one stat family."""
    event_placeholders = _event_id_placeholders(stat_type)
    conditions = [
        "m.season = %s",
        "m.result != '0'",
        f"p.event_id IN ({event_placeholders})",
    ]
    params: list[object] = [season_id, *_STAT_EVENT_IDS[stat_type]]

    if league_id is not None:
        conditions.append("m.league = %s")
        params.append(league_id)

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT
            COUNT(CASE WHEN p.event_id IN ({event_placeholders}) THEN 1 END)
                AS total_predictions,
            COUNT(
                CASE
                    WHEN p.event_id IN ({event_placeholders})
                        AND fp.outcome = 1 THEN 1
                END) AS correct_predictions
        FROM predictions p
        JOIN final_predictions fp ON fp.predictions_id = p.id
        JOIN matches m ON p.match_id = m.id
        WHERE {where_clause}
    """
    params.extend(_STAT_EVENT_IDS[stat_type])
    params.extend(_STAT_EVENT_IDS[stat_type])

    with get_db_connection() as conn:
        frame = pd.read_sql(query, conn, params=tuple(params))

    if frame.empty:
        return 0, 0
    row = frame.iloc[0]
    return int(row["total_predictions"]), int(row["correct_predictions"])


def fetch_league_bet_profit_aggregation(
    season_id: int,
    apply_tax: bool,
    tax_rate: float) -> pd.DataFrame:
    """Return per-league bet profit broken down by stat family."""
    if apply_tax:
        profit_expr = """
            SUM(CASE
                WHEN b.event_id IN (1, 2, 3) AND b.outcome = 1
                    THEN (b.odds * (1 - %s)) - 1
                WHEN b.event_id IN (1, 2, 3) AND b.outcome = 0 THEN -1
                ELSE 0 END) AS result_profit,
            SUM(CASE
                WHEN b.event_id IN (8, 12) AND b.outcome = 1
                    THEN (b.odds * (1 - %s)) - 1
                WHEN b.event_id IN (8, 12) AND b.outcome = 0 THEN -1
                ELSE 0 END) AS ou_profit,
            SUM(CASE
                WHEN b.event_id IN (6, 172) AND b.outcome = 1
                    THEN (b.odds * (1 - %s)) - 1
                WHEN b.event_id IN (6, 172) AND b.outcome = 0 THEN -1
                ELSE 0 END) AS btts_profit
        """
        profit_params = (tax_rate, tax_rate, tax_rate)
    else:
        profit_expr = """
            SUM(CASE
                WHEN b.event_id IN (1, 2, 3) AND b.outcome = 1 THEN b.odds - 1
                WHEN b.event_id IN (1, 2, 3) AND b.outcome = 0 THEN -1
                ELSE 0 END) AS result_profit,
            SUM(CASE
                WHEN b.event_id IN (8, 12) AND b.outcome = 1 THEN b.odds - 1
                WHEN b.event_id IN (8, 12) AND b.outcome = 0 THEN -1
                ELSE 0 END) AS ou_profit,
            SUM(CASE
                WHEN b.event_id IN (6, 172) AND b.outcome = 1 THEN b.odds - 1
                WHEN b.event_id IN (6, 172) AND b.outcome = 0 THEN -1
                ELSE 0 END) AS btts_profit
        """
        profit_params = ()

    query = f"""
        SELECT
            l.id AS entity_id,
            l.name AS entity_name,
            {profit_expr}
        FROM bets b
        JOIN matches m ON b.match_id = m.id
        JOIN leagues l ON m.league = l.id
        WHERE m.season = %s
            AND m.result != '0'
            AND l.active = 1
        GROUP BY l.id, l.name
        HAVING (
            COUNT(CASE WHEN b.event_id IN (1, 2, 3) THEN 1 END) > 0
        )
        ORDER BY l.name
    """
    params = profit_params + (season_id,)

    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def fetch_league_characteristics(
    league_id: int,
    season_id: int) -> dict[str, object] | None:
    """Return OU, BTTS and 1X2 distribution for a league season."""
    query = """
        SELECT
            COUNT(*) AS played_matches,
            SUM(CASE WHEN home_team_goals + away_team_goals > 2.5 THEN 1 ELSE 0 END)
                AS over_count,
            SUM(CASE WHEN home_team_goals + away_team_goals < 2.5 THEN 1 ELSE 0 END)
                AS under_count,
            AVG(home_team_goals + away_team_goals) AS avg_goals,
            SUM(CASE WHEN home_team_goals > 0 AND away_team_goals > 0 THEN 1 ELSE 0 END)
                AS btts_yes_count,
            SUM(CASE WHEN home_team_goals = 0 OR away_team_goals = 0 THEN 1 ELSE 0 END)
                AS btts_no_count,
            SUM(CASE WHEN result = '1' THEN 1 ELSE 0 END) AS home_win_count,
            SUM(CASE WHEN result = 'X' THEN 1 ELSE 0 END) AS draw_count,
            SUM(CASE WHEN result = '2' THEN 1 ELSE 0 END) AS away_win_count
        FROM matches
        WHERE league = %s
            AND season = %s
            AND result != '0'
    """
    with get_db_connection() as conn:
        frame = pd.read_sql(
            query,
            conn,
            params=(league_id, season_id))

    if frame.empty:
        return None

    row = frame.iloc[0]
    played = int(row["played_matches"])
    if played == 0:
        return None

    def _pct(count: float) -> float:
        return round(float(count) * 100 / played, 2)

    return {
        "played_matches": played,
        "avg_goals_per_match": round(float(row["avg_goals"]), 2),
        "ou": {
            "under_2_5": {
                "count": int(row["under_count"]),
                "percentage": _pct(row["under_count"]),
            },
            "over_2_5": {
                "count": int(row["over_count"]),
                "percentage": _pct(row["over_count"]),
            },
        },
        "btts": {
            "no": {
                "count": int(row["btts_no_count"]),
                "percentage": _pct(row["btts_no_count"]),
            },
            "yes": {
                "count": int(row["btts_yes_count"]),
                "percentage": _pct(row["btts_yes_count"]),
            },
        },
        "result": {
            "home": {
                "count": int(row["home_win_count"]),
                "percentage": _pct(row["home_win_count"]),
            },
            "draw": {
                "count": int(row["draw_count"]),
                "percentage": _pct(row["draw_count"]),
            },
            "away": {
                "count": int(row["away_win_count"]),
                "percentage": _pct(row["away_win_count"]),
            },
        },
    }
