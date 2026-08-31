"""SQL access for Typer long-term markets, picks and CSV audit."""

from __future__ import annotations

from typing import Any

from mysql.connector.errors import IntegrityError

from backend.database import get_db_connection
from backend.repositories.champions_league_typer_repository import (
    TyperConflictError,
    TyperNotFoundError,
    TyperRepositoryError,
    TyperValidationError)


CHAMPIONS_LEAGUE_ID = 42
LEAGUE_PHASE_MIN_ROUND = 1
LEAGUE_PHASE_MAX_ROUND = 8
LEAGUE_PHASE_TEAM_COUNT = 36
LEAGUE_PHASE_MATCHES_PER_TEAM = 8
LEAGUE_PHASE_SETTLED_MATCH_COUNT = 144

# deadline fazy ligowej: MIN(game_date) dla ligi i sezonu rynku, rund 1-8
_DEADLINE_SQL = f"""
    SELECT MIN(mt.game_date)
    FROM matches mt
    WHERE mt.league = m.league_id
      AND mt.season = m.season_id
      AND mt.round BETWEEN {LEAGUE_PHASE_MIN_ROUND}
          AND {LEAGUE_PHASE_MAX_ROUND}
"""

# odczyt rynku bez locka (auto-wynik); FOR UPDATE tylko przy zapisie
_SELECT_MARKET_SQL = f"""
    SELECT
        m.id AS market_id,
        m.league_id,
        m.season_id,
        m.market_key,
        m.title,
        m.description,
        m.selection_size,
        m.points_per_correct,
        m.settled_at,
        m.settled_by,
        ({_DEADLINE_SQL}) AS deadline_at,
        (NOW() < ({_DEADLINE_SQL})) AS is_open
    FROM typer_long_term_markets m
    WHERE m.id = %s
      AND m.league_id = %s
"""

# FOR UPDATE tylko na rynku: konto API nie ma UPDATE na matches
_LOCK_MARKET_SQL = _SELECT_MARKET_SQL + "    FOR UPDATE"

_CANDIDATE_TEAMS_SQL = f"""
    SELECT
        t.id AS team_id,
        t.name AS team_name,
        t.shortcut AS team_shortcut
    FROM teams t
    WHERE t.id IN (
        SELECT m.home_team
        FROM matches m
        WHERE m.league = %s
          AND m.season = %s
          AND m.round BETWEEN {LEAGUE_PHASE_MIN_ROUND}
              AND {LEAGUE_PHASE_MAX_ROUND}
        UNION
        SELECT m.away_team
        FROM matches m
        WHERE m.league = %s
          AND m.season = %s
          AND m.round BETWEEN {LEAGUE_PHASE_MIN_ROUND}
              AND {LEAGUE_PHASE_MAX_ROUND}
    )
    ORDER BY t.name ASC, t.id ASC
"""

_CURRENT_PICKS_SQL = """
    SELECT team_id
    FROM typer_long_term_picks
    WHERE market_id = %s
      AND user_id = %s
    ORDER BY team_id ASC
"""

_DELETE_PICKS_SQL = """
    DELETE FROM typer_long_term_picks
    WHERE market_id = %s
      AND user_id = %s
"""

_INSERT_PICKS_SQL = f"""
    INSERT INTO typer_long_term_picks (
        market_id, user_id, team_id)
    SELECT %s, %s, t.team_id
    FROM typer_long_term_markets m
    JOIN ({{union_sql}}) t
    WHERE m.id = %s
      AND NOW() < ({_DEADLINE_SQL})
"""

_INSERT_AUDIT_SQL = """
    INSERT INTO typer_long_term_pick_changes (
        market_id,
        user_id,
        changed_by,
        previous_team_ids,
        new_team_ids)
    VALUES (%s, %s, %s, %s, %s)
"""

# sezon bywa współdzielony między ligami — ten moduł pokazuje tylko LM (42)
_DASHBOARD_MARKETS_SQL = f"""
    SELECT
        m.id AS market_id,
        m.league_id,
        m.season_id,
        m.market_key,
        m.title,
        m.description,
        m.selection_size,
        m.points_per_correct,
        m.settled_at,
        m.settled_by,
        ({_DEADLINE_SQL}) AS deadline_at,
        (NOW() < ({_DEADLINE_SQL})) AS is_open
    FROM typer_long_term_markets m
    WHERE m.season_id = %s
      AND m.league_id = %s
    ORDER BY m.id ASC
"""

_DASHBOARD_PICKS_SQL = """
    SELECT market_id, team_id
    FROM typer_long_term_picks
    WHERE user_id = %s
      AND market_id IN ({placeholders})
    ORDER BY market_id ASC, team_id ASC
"""

_DASHBOARD_RESULTS_SQL = """
    SELECT market_id, team_id
    FROM typer_long_term_results
    WHERE market_id IN ({placeholders})
    ORDER BY market_id ASC, team_id ASC
"""

_CHANGES_SELECT_SQL = """
    SELECT
        c.id,
        c.market_id,
        u.uuid AS user_uuid,
        u.display_name,
        c.previous_team_ids,
        c.new_team_ids,
        c.changed_at
    FROM typer_long_term_pick_changes c
    JOIN users u ON u.id = c.user_id
"""

_OWN_HISTORY_SQL = _CHANGES_SELECT_SQL + """
    WHERE c.user_id = %s
      AND c.market_id = %s
    ORDER BY c.changed_at ASC, c.id ASC
"""

_DASHBOARD_HISTORY_SQL = _CHANGES_SELECT_SQL + """
    WHERE c.user_id = %s
      AND c.market_id IN ({placeholders})
    ORDER BY c.market_id ASC, c.changed_at ASC, c.id ASC
"""

# tabela fazy ligowej: punkty, różnica bramek, gole; dalsze kryteria UEFA
# nie są tutaj — wynik zostaje propozycją do zatwierdzenia przez admina
_LEAGUE_PHASE_STANDINGS_SQL = f"""
    WITH phase_matches AS (
        SELECT
            m.home_team,
            m.away_team,
            m.home_team_goals,
            m.away_team_goals,
            m.result
        FROM matches m
        WHERE m.league = %s
          AND m.season = %s
          AND m.round BETWEEN {LEAGUE_PHASE_MIN_ROUND}
              AND {LEAGUE_PHASE_MAX_ROUND}
    ),
    participants AS (
        SELECT home_team AS team_id
        FROM phase_matches
        UNION
        SELECT away_team
        FROM phase_matches
    ),
    team_stats AS (
        SELECT
            team_id,
            COUNT(*) AS played,
            SUM(match_points) AS points,
            SUM(goals_for) - SUM(goals_against) AS goal_difference,
            SUM(goals_for) AS goals_for
        FROM (
            SELECT
                home_team AS team_id,
                CASE result
                    WHEN '1' THEN 3
                    WHEN 'X' THEN 1
                    ELSE 0
                END AS match_points,
                COALESCE(home_team_goals, 0) AS goals_for,
                COALESCE(away_team_goals, 0) AS goals_against
            FROM phase_matches
            WHERE result IN ('1', 'X', '2')
            UNION ALL
            SELECT
                away_team AS team_id,
                CASE result
                    WHEN '2' THEN 3
                    WHEN 'X' THEN 1
                    ELSE 0
                END AS match_points,
                COALESCE(away_team_goals, 0) AS goals_for,
                COALESCE(home_team_goals, 0) AS goals_against
            FROM phase_matches
            WHERE result IN ('1', 'X', '2')
        ) appearances
        GROUP BY team_id
    )
    SELECT
        t.id AS team_id,
        t.name AS team_name,
        t.shortcut AS team_shortcut,
        COALESCE(s.played, 0) AS played,
        COALESCE(s.points, 0) AS points,
        COALESCE(s.goal_difference, 0) AS goal_difference,
        COALESCE(s.goals_for, 0) AS goals_for
    FROM participants p
    JOIN teams t ON t.id = p.team_id
    LEFT JOIN team_stats s ON s.team_id = t.id
    ORDER BY
        COALESCE(s.points, 0) DESC,
        COALESCE(s.goal_difference, 0) DESC,
        COALESCE(s.goals_for, 0) DESC,
        t.id ASC
"""

_DELETE_RESULTS_SQL = """
    DELETE FROM typer_long_term_results
    WHERE market_id = %s
"""

_INSERT_RESULTS_SQL = """
    INSERT INTO typer_long_term_results (
        market_id, team_id)
    SELECT %s, t.team_id
    FROM ({union_sql}) t
"""

_UPDATE_MARKET_SETTLED_SQL = """
    UPDATE typer_long_term_markets
    SET settled_at = NOW(),
        settled_by = %s
    WHERE id = %s
      AND league_id = %s
"""


def fetch_long_term_dashboard(
        user_id: int,
        season_id: int | None) -> dict[str, Any]:
    """Return markets, candidates and the caller's private picks."""
    _require_positive_ids(user_id=user_id)
    if season_id is not None:
        _require_positive_ids(season_id=season_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            resolved_season_id = _resolve_season_id(cursor, season_id)
            cursor.execute(
                _DASHBOARD_MARKETS_SQL,
                (resolved_season_id, CHAMPIONS_LEAGUE_ID))
            market_rows = list(cursor.fetchall())
            document = _build_dashboard_document(
                cursor, user_id, resolved_season_id, market_rows)
        finally:
            cursor.close()
    return document


def save_long_term_picks(
        user_id: int,
        market_id: int,
        team_ids: list[int]) -> dict[str, Any]:
    """Replace the user's set and append CSV audit in one transaction.

    Deadline is enforced in SQL via ``NOW() < MIN(matches.game_date)``.
    An identical set (order ignored) is a no-op without an audit row.
    """
    _require_positive_ids(user_id=user_id, market_id=market_id)
    unique_ids = _unique_team_ids(team_ids)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            market = _lock_market(cursor, market_id)
            result = _replace_picks_with_audit(
                cursor, market, user_id, unique_ids)
            # mysql-connector bez autocommit — close bez commit cofa zapis
            conn.commit()
        except TyperRepositoryError:
            conn.rollback()
            raise
        except IntegrityError as exc:
            conn.rollback()
            raise TyperConflictError(
                "Long-term picks could not be saved") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return result


def fetch_own_long_term_history(
        user_id: int,
        market_id: int) -> list[dict[str, Any]]:
    """Return chronological audit rows for the caller's market set."""
    _require_positive_ids(user_id=user_id, market_id=market_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            _require_market(cursor, market_id)
            cursor.execute(_OWN_HISTORY_SQL, (user_id, market_id))
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [_map_change_row(row) for row in rows]


def fetch_admin_long_term_history(
        user_uuid: str,
        market_id: int | None = None,
        season_id: int | None = None) -> list[dict[str, Any]]:
    """Return audit rows for a user identified by public UUID."""
    if not user_uuid or not user_uuid.strip():
        raise TyperValidationError("user_uuid is required")
    if market_id is not None:
        _require_positive_ids(market_id=market_id)
    if season_id is not None:
        _require_positive_ids(season_id=season_id)
    query, params = _admin_history_query(
        user_uuid.strip(), market_id, season_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            _require_user_uuid(cursor, user_uuid.strip())
            if season_id is not None:
                _require_season(cursor, season_id)
            if market_id is not None:
                _require_market(cursor, market_id)
            cursor.execute(query, params)
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [_map_change_row(row) for row in rows]


def fetch_auto_result(market_id: int) -> dict[str, Any]:
    """Return league-phase standings and completeness counts.

    Does not write results or award points. The ranking is a proposal
    because UEFA tie-breakers beyond points, GD and goals are omitted.
    """
    _require_positive_ids(market_id=market_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            market = _fetch_market(cursor, market_id)
            standings = _fetch_league_phase_standings(
                cursor,
                int(market["league_id"]),
                int(market["season_id"]))
        finally:
            cursor.close()
    return _auto_result_document(market, standings)


def settle_market(
        market_id: int,
        team_ids: list[int],
        admin_id: int) -> dict[str, Any]:
    """Replace the approved result set and stamp the market as settled.

    Does not modify stored picks. Rankings are recalculated on read.
    Deadline is not required: settlement happens after kickoff.
    """
    _require_positive_ids(market_id=market_id, admin_id=admin_id)
    unique_ids = _unique_team_ids(team_ids)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            market = _fetch_locked_market(cursor, market_id)
            result = _replace_results(
                cursor, market, unique_ids, admin_id)
            # mysql-connector bez autocommit — close bez commit cofa zapis
            conn.commit()
        except TyperRepositoryError:
            conn.rollback()
            raise
        except IntegrityError as exc:
            conn.rollback()
            raise TyperConflictError(
                "Long-term result could not be saved") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return result


def _build_dashboard_document(
        cursor: Any,
        user_id: int,
        season_id: int,
        market_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not market_rows:
        return {"season_id": season_id, "markets": [], "changes": []}
    market_ids = [int(row["market_id"]) for row in market_rows]
    candidates_by_key = _fetch_candidates_for_markets(cursor, market_rows)
    picks_by_market = _fetch_grouped_team_ids(
        cursor, _DASHBOARD_PICKS_SQL, market_ids, (user_id,))
    results_by_market = _fetch_grouped_team_ids(
        cursor, _DASHBOARD_RESULTS_SQL, market_ids)
    change_rows = _fetch_dashboard_changes(cursor, user_id, market_ids)
    markets = [
        _map_dashboard_market_row(
            row,
            candidates_by_key[
                (int(row["league_id"]), int(row["season_id"]))],
            picks_by_market.get(int(row["market_id"]), []),
            results_by_market.get(int(row["market_id"]), []))
        for row in market_rows]
    return {
        "season_id": season_id,
        "markets": markets,
        "changes": [_map_change_row(row) for row in change_rows]
    }


def _fetch_candidates_for_markets(
        cursor: Any,
        market_rows: list[dict[str, Any]]
        ) -> dict[tuple[int, int], list[dict[str, Any]]]:
    cache: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in market_rows:
        key = (int(row["league_id"]), int(row["season_id"]))
        if key not in cache:
            cache[key] = _fetch_candidate_teams(cursor, key[0], key[1])
    return cache


def _fetch_candidate_teams(
        cursor: Any,
        league_id: int,
        season_id: int) -> list[dict[str, Any]]:
    cursor.execute(
        _CANDIDATE_TEAMS_SQL,
        (league_id, season_id, league_id, season_id))
    return [_map_candidate_row(row) for row in cursor.fetchall()]


def _fetch_grouped_team_ids(
        cursor: Any,
        query_template: str,
        market_ids: list[int],
        extra_params: tuple[object, ...] = ()
        ) -> dict[int, list[int]]:
    query = query_template.format(
        placeholders=_in_placeholders(len(market_ids)))
    cursor.execute(query, extra_params + tuple(market_ids))
    grouped: dict[int, list[int]] = {}
    for row in cursor.fetchall():
        market_id = int(row["market_id"])
        grouped.setdefault(market_id, []).append(int(row["team_id"]))
    return grouped


def _fetch_dashboard_changes(
        cursor: Any,
        user_id: int,
        market_ids: list[int]) -> list[dict[str, Any]]:
    query = _DASHBOARD_HISTORY_SQL.format(
        placeholders=_in_placeholders(len(market_ids)))
    cursor.execute(query, (user_id, *market_ids))
    return list(cursor.fetchall())


def _lock_market(cursor: Any, market_id: int) -> dict[str, Any]:
    row = _fetch_locked_market(cursor, market_id)
    if not _as_bool(row["is_open"]):
        raise TyperConflictError(
            "Picks cannot be saved after kickoff")
    return row


def _fetch_locked_market(cursor: Any, market_id: int) -> dict[str, Any]:
    return _fetch_market(cursor, market_id, for_update=True)


def _fetch_market(
        cursor: Any,
        market_id: int,
        *,
        for_update: bool = False) -> dict[str, Any]:
    query = _LOCK_MARKET_SQL if for_update else _SELECT_MARKET_SQL
    cursor.execute(query, (market_id, CHAMPIONS_LEAGUE_ID))
    row = cursor.fetchone()
    if row is None:
        raise TyperNotFoundError("Long-term market not found")
    return row


def _fetch_league_phase_standings(
        cursor: Any,
        league_id: int,
        season_id: int) -> list[dict[str, Any]]:
    cursor.execute(
        _LEAGUE_PHASE_STANDINGS_SQL, (league_id, season_id))
    return [_map_standing_row(row) for row in cursor.fetchall()]


def _auto_result_document(
        market: dict[str, Any],
        standings: list[dict[str, Any]]) -> dict[str, Any]:
    played = [int(row["played"]) for row in standings]
    return {
        "market_id": int(market["market_id"]),
        "league_id": int(market["league_id"]),
        "season_id": int(market["season_id"]),
        "market_key": str(market["market_key"]),
        "selection_size": int(market["selection_size"]),
        "points_per_correct": float(market["points_per_correct"]),
        "settled_at": market["settled_at"],
        "settled_by": _as_optional_int(market["settled_by"]),
        "participant_count": len(standings),
        "settled_match_count": sum(played) // 2,
        "min_matches_per_team": min(played) if played else 0,
        "max_matches_per_team": max(played) if played else 0,
        "standings": standings
    }


def _replace_results(
        cursor: Any,
        market: dict[str, Any],
        team_ids: list[int],
        admin_id: int) -> dict[str, Any]:
    market_id = int(market["market_id"])
    _assert_selection_size(market, team_ids)
    _assert_candidate_membership(cursor, market, team_ids)
    cursor.execute(_DELETE_RESULTS_SQL, (market_id,))
    _insert_results(cursor, market_id, team_ids)
    cursor.execute(
        _UPDATE_MARKET_SETTLED_SQL,
        (admin_id, market_id, CHAMPIONS_LEAGUE_ID))
    updated = _fetch_market(cursor, market_id)
    return {
        "market_id": market_id,
        "team_ids": sorted(team_ids),
        "settled_by": admin_id,
        "settled_at": updated["settled_at"],
        "result_team_ids": sorted(team_ids)
    }


def _insert_results(
        cursor: Any,
        market_id: int,
        team_ids: list[int]) -> None:
    union_sql = " UNION ALL ".join(
        ["SELECT %s AS team_id"] * len(team_ids))
    query = _INSERT_RESULTS_SQL.format(union_sql=union_sql)
    cursor.execute(query, (market_id, *sorted(team_ids)))
    if cursor.rowcount != len(team_ids):
        raise TyperConflictError(
            "Long-term result could not be saved")


def _replace_picks_with_audit(
        cursor: Any,
        market: dict[str, Any],
        user_id: int,
        team_ids: list[int]) -> dict[str, Any]:
    market_id = int(market["market_id"])
    _assert_selection_size(market, team_ids)
    _assert_candidate_membership(cursor, market, team_ids)
    previous_ids = _fetch_current_pick_ids(cursor, market_id, user_id)
    previous_csv = _team_ids_csv(previous_ids) if previous_ids else None
    new_csv = _team_ids_csv(team_ids)
    if previous_csv == new_csv:
        return _picks_result(
            market_id, user_id, team_ids, previous_ids, False)
    _delete_current_picks(cursor, market_id, user_id)
    _insert_picks_with_deadline(cursor, market_id, user_id, team_ids)
    _insert_pick_audit(
        cursor, market_id, user_id, user_id, previous_csv, new_csv)
    return _picks_result(
        market_id, user_id, team_ids, previous_ids, True)


def _assert_selection_size(
        market: dict[str, Any], team_ids: list[int]) -> None:
    selection_size = int(market["selection_size"])
    if len(team_ids) != selection_size:
        raise TyperValidationError(
            f"Long-term pick set must contain exactly {selection_size} "
            "teams")


def _assert_candidate_membership(
        cursor: Any,
        market: dict[str, Any],
        team_ids: list[int]) -> None:
    candidates = _fetch_candidate_teams(
        cursor, int(market["league_id"]), int(market["season_id"]))
    candidate_ids = {int(row["team_id"]) for row in candidates}
    for team_id in team_ids:
        if team_id not in candidate_ids:
            raise TyperValidationError(
                "Team is not a league-phase participant")


def _fetch_current_pick_ids(
        cursor: Any, market_id: int, user_id: int) -> list[int]:
    cursor.execute(_CURRENT_PICKS_SQL, (market_id, user_id))
    return [int(row["team_id"]) for row in cursor.fetchall()]


def _delete_current_picks(
        cursor: Any, market_id: int, user_id: int) -> None:
    cursor.execute(_DELETE_PICKS_SQL, (market_id, user_id))


def _insert_picks_with_deadline(
        cursor: Any,
        market_id: int,
        user_id: int,
        team_ids: list[int]) -> None:
    union_sql = " UNION ALL ".join(
        ["SELECT %s AS team_id"] * len(team_ids))
    query = _INSERT_PICKS_SQL.format(union_sql=union_sql)
    cursor.execute(
        query, (market_id, user_id, *sorted(team_ids), market_id))
    if cursor.rowcount != len(team_ids):
        raise TyperConflictError(
            "Picks cannot be saved after kickoff")


def _insert_pick_audit(
        cursor: Any,
        market_id: int,
        user_id: int,
        changed_by: int,
        previous_csv: str | None,
        new_csv: str) -> None:
    cursor.execute(
        _INSERT_AUDIT_SQL,
        (market_id, user_id, changed_by, previous_csv, new_csv))


def _picks_result(
        market_id: int,
        user_id: int,
        team_ids: list[int],
        previous_ids: list[int],
        audit_written: bool) -> dict[str, Any]:
    sorted_ids = sorted(team_ids)
    previous = sorted(previous_ids) if previous_ids else None
    return {
        "market_id": market_id,
        "user_id": user_id,
        "team_ids": sorted_ids,
        "previous_team_ids": previous,
        "audit_written": audit_written
    }


def _unique_team_ids(team_ids: list[int]) -> list[int]:
    if not team_ids:
        raise TyperValidationError("At least one team id is required")
    unique_ids: list[int] = []
    seen: set[int] = set()
    for team_id in team_ids:
        if not isinstance(team_id, int) or team_id <= 0:
            raise TyperValidationError(
                "Team ids must be positive integers")
        if team_id in seen:
            raise TyperValidationError(
                "Duplicate team ids in long-term pick set")
        seen.add(team_id)
        unique_ids.append(team_id)
    return unique_ids


def _team_ids_csv(team_ids: list[int]) -> str:
    return ",".join(str(team_id) for team_id in sorted(team_ids))


def _parse_team_ids_csv(value: object) -> list[int] | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return []
    return [int(part) for part in text.split(",")]


def _admin_history_query(
        user_uuid: str,
        market_id: int | None,
        season_id: int | None) -> tuple[str, tuple[object, ...]]:
    # ten moduł jest sąsiadem typera LM: audyt tylko ligi 42
    conditions = ["u.uuid = %s", "m.league_id = %s"]
    params: list[object] = [user_uuid, CHAMPIONS_LEAGUE_ID]
    if market_id is not None:
        conditions.append("c.market_id = %s")
        params.append(market_id)
    if season_id is not None:
        conditions.append("m.season_id = %s")
        params.append(season_id)
    where_sql = " AND ".join(conditions)
    query = (
        _CHANGES_SELECT_SQL
        + " JOIN typer_long_term_markets m ON m.id = c.market_id"
        + f" WHERE {where_sql}"
        + " ORDER BY c.changed_at ASC, c.id ASC")
    return query, tuple(params)


def _require_market(cursor: Any, market_id: int) -> None:
    cursor.execute(
        """
        SELECT 1
        FROM typer_long_term_markets
        WHERE id = %s
          AND league_id = %s
        LIMIT 1
        """,
        (market_id, CHAMPIONS_LEAGUE_ID))
    if cursor.fetchone() is None:
        raise TyperNotFoundError("Long-term market not found")


def _require_season(cursor: Any, season_id: int) -> None:
    cursor.execute(
        "SELECT 1 FROM seasons WHERE id = %s LIMIT 1", (season_id,))
    if cursor.fetchone() is None:
        raise TyperNotFoundError("Season not found")


def _require_user_uuid(cursor: Any, user_uuid: str) -> None:
    cursor.execute(
        "SELECT 1 FROM users WHERE uuid = %s LIMIT 1", (user_uuid,))
    if cursor.fetchone() is None:
        raise TyperNotFoundError("User not found")


def _resolve_season_id(cursor: Any, season_id: int | None) -> int:
    if season_id is not None:
        _require_season(cursor, season_id)
        return season_id
    cursor.execute(
        "SELECT current_season_id FROM leagues WHERE id = %s",
        (CHAMPIONS_LEAGUE_ID,))
    row = cursor.fetchone()
    if row is None or row["current_season_id"] is None:
        raise TyperNotFoundError(
            "Champions League current season is not set")
    return int(row["current_season_id"])


def _require_positive_ids(**ids: int) -> None:
    for name, value in ids.items():
        if not isinstance(value, int) or value <= 0:
            raise TyperValidationError(f"{name} must be a positive integer")


def _in_placeholders(count: int) -> str:
    return ", ".join(["%s"] * count)


def _as_bool(value: object) -> bool:
    return bool(value)


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _map_candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": int(row["team_id"]),
        "team_name": str(row["team_name"]),
        "team_shortcut": str(row["team_shortcut"])
    }


def _map_standing_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": int(row["team_id"]),
        "team_name": str(row["team_name"]),
        "team_shortcut": str(row["team_shortcut"]),
        "played": int(row["played"]),
        "points": int(row["points"]),
        "goal_difference": int(row["goal_difference"]),
        "goals_for": int(row["goals_for"])
    }


def _map_dashboard_market_row(
        row: dict[str, Any],
        candidates: list[dict[str, Any]],
        picked_team_ids: list[int],
        result_team_ids: list[int]) -> dict[str, Any]:
    return {
        "market_id": int(row["market_id"]),
        "league_id": int(row["league_id"]),
        "season_id": int(row["season_id"]),
        "market_key": str(row["market_key"]),
        "title": str(row["title"]),
        "description": (
            None if row["description"] is None
            else str(row["description"])),
        "selection_size": int(row["selection_size"]),
        "points_per_correct": float(row["points_per_correct"]),
        "settled_at": row["settled_at"],
        "settled_by": _as_optional_int(row["settled_by"]),
        "deadline_at": row["deadline_at"],
        "is_locked": not _as_bool(row["is_open"]),
        "candidates": candidates,
        "picked_team_ids": list(picked_team_ids),
        "result_team_ids": list(result_team_ids)
    }


def _map_change_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "market_id": int(row["market_id"]),
        "user_uuid": str(row["user_uuid"]),
        "display_name": str(row["display_name"]),
        "previous_team_ids": _parse_team_ids_csv(
            row["previous_team_ids"]),
        "new_team_ids": _parse_team_ids_csv(row["new_team_ids"]) or [],
        "changed_at": row["changed_at"]
    }
