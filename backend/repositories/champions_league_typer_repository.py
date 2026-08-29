"""SQL access for Champions League Typer publications, picks and audit."""

from __future__ import annotations

from typing import Any

from mysql.connector.errors import IntegrityError

from backend.database import get_db_connection


CHAMPIONS_LEAGUE_ID = 42
SUPERBET_BOOKMAKER_ID = 1
HOME_EVENT_ID = 1
DRAW_EVENT_ID = 2
AWAY_EVENT_ID = 3
ONE_X_TWO_EVENT_IDS = (HOME_EVENT_ID, DRAW_EVENT_ID, AWAY_EVENT_ID)


class TyperRepositoryError(Exception):
    """Base error for Champions League Typer persistence failures."""


class TyperNotFoundError(TyperRepositoryError):
    """Match, publication, season or user row was not found."""


class TyperConflictError(TyperRepositoryError):
    """Publication or pick cannot change in the current stored state."""


class TyperValidationError(TyperRepositoryError):
    """Stored match rows are inconsistent with the requested set."""


_RESULT_EVENT_SQL = """
    CASE m.result
        WHEN '1' THEN 1
        WHEN 'X' THEN 2
        WHEN '2' THEN 3
        ELSE NULL
    END
"""

# kanoniczna punktacja Typera (tożsama z score_prediction w serwisie):
# pudło przy result 1/X/2 -> 0 nawet bez kursu; trafienie bez kursu Superbet
# -> NULL; wyłącznie matches.result, bez dogrywki i karnych.
_POINTS_SQL = f"""
    CASE
        WHEN m.result IN ('1', 'X', '2') THEN
            CASE
                WHEN p.selected_event_id <> {_RESULT_EVENT_SQL} THEN 0
                WHEN o.odds IS NULL THEN NULL
                ELSE o.odds
            END
        ELSE NULL
    END
"""

_CANDIDATE_SQL = f"""
    SELECT
        m.id AS match_id,
        m.season AS season_id,
        m.round AS round_number,
        m.game_date,
        m.home_team AS home_team_id,
        home.name AS home_team_name,
        home.shortcut AS home_team_shortcut,
        m.away_team AS away_team_id,
        away.name AS away_team_name,
        away.shortcut AS away_team_shortcut,
        (tm.id IS NOT NULL) AS is_published,
        (
            SELECT COUNT(DISTINCT o.event) = 3
            FROM odds o
            WHERE o.match_id = m.id
              AND o.bookmaker = {SUPERBET_BOOKMAKER_ID}
              AND o.event IN (
                {HOME_EVENT_ID}, {DRAW_EVENT_ID}, {AWAY_EVENT_ID})
        ) AS has_complete_superbet_odds
    FROM matches m
    JOIN teams home ON home.id = m.home_team
    JOIN teams away ON away.id = m.away_team
    LEFT JOIN champions_league_typer_matches tm ON tm.match_id = m.id
    WHERE m.league = {CHAMPIONS_LEAGUE_ID}
      AND m.season = %s
      AND m.round = %s
    ORDER BY m.game_date ASC, m.id ASC
"""

_LOCK_ROUND_MATCHES_SQL = f"""
    SELECT id, league, season, round
    FROM matches
    WHERE league = {CHAMPIONS_LEAGUE_ID}
      AND season = %s
      AND round = %s
    ORDER BY id
    FOR UPDATE
"""

_LOCK_MATCHES_SQL = """
    SELECT id, league, season, round
    FROM matches
    WHERE id IN ({placeholders})
    ORDER BY id
    FOR UPDATE
"""

_LOCK_ROUND_PUBLICATIONS_SQL = """
    SELECT match_id
    FROM champions_league_typer_matches
    WHERE season_id = %s
      AND round_number = %s
    ORDER BY match_id
    FOR UPDATE
"""

_INSERT_PUBLICATION_SQL = """
    INSERT INTO champions_league_typer_matches (
        match_id, season_id, round_number, published_by)
    VALUES (%s, %s, %s, %s)
"""

_FETCH_PUBLICATIONS_SQL = """
    SELECT
        tm.id AS typer_match_id,
        tm.match_id,
        tm.season_id,
        tm.round_number,
        tm.published_by,
        tm.published_at
    FROM champions_league_typer_matches tm
    WHERE tm.match_id IN ({placeholders})
    ORDER BY tm.match_id
"""

_LOCK_PREDICTION_SQL = f"""
    SELECT
        tm.id AS typer_match_id,
        tm.match_id,
        (NOW() < m.game_date) AS is_open,
        p.id AS prediction_id,
        p.selected_event_id,
        p.created_at,
        p.updated_at
    FROM champions_league_typer_matches tm
    JOIN matches m ON m.id = tm.match_id
    LEFT JOIN champions_league_typer_predictions p
        ON p.typer_match_id = tm.id
       AND p.user_id = %s
    WHERE tm.match_id = %s
      AND m.league = {CHAMPIONS_LEAGUE_ID}
    FOR UPDATE
"""

_INSERT_PREDICTION_SQL = """
    INSERT INTO champions_league_typer_predictions (
        typer_match_id, user_id, selected_event_id)
    SELECT %s, %s, %s
    FROM champions_league_typer_matches tm
    JOIN matches m ON m.id = tm.match_id
    WHERE tm.id = %s
      AND NOW() < m.game_date
"""

_UPDATE_PREDICTION_SQL = """
    UPDATE champions_league_typer_predictions p
    JOIN champions_league_typer_matches tm ON tm.id = p.typer_match_id
    JOIN matches m ON m.id = tm.match_id
    SET p.selected_event_id = %s
    WHERE p.id = %s
      AND NOW() < m.game_date
"""

_INSERT_AUDIT_SQL = """
    INSERT INTO champions_league_typer_prediction_changes (
        prediction_id,
        changed_by,
        previous_selected_event_id,
        new_selected_event_id)
    VALUES (%s, %s, %s, %s)
"""

_FETCH_PREDICTION_SQL = """
    SELECT
        id AS prediction_id,
        typer_match_id,
        user_id,
        selected_event_id,
        created_at,
        updated_at
    FROM champions_league_typer_predictions
    WHERE id = %s
"""

_LOCK_PUBLICATION_FOR_DELETE_SQL = f"""
    SELECT
        tm.id AS typer_match_id,
        tm.match_id,
        (NOW() < m.game_date) AS is_open,
        (
            SELECT COUNT(*)
            FROM champions_league_typer_predictions p
            WHERE p.typer_match_id = tm.id
        ) AS prediction_count
    FROM champions_league_typer_matches tm
    JOIN matches m ON m.id = tm.match_id
    WHERE tm.match_id = %s
      AND m.league = {CHAMPIONS_LEAGUE_ID}
    FOR UPDATE
"""

_DELETE_PUBLICATION_SQL = """
    DELETE FROM champions_league_typer_matches
    WHERE id = %s
"""

_DASHBOARD_MATCHES_SQL = f"""
    SELECT
        tm.id AS typer_match_id,
        tm.match_id,
        tm.season_id,
        tm.round_number,
        tm.published_at,
        m.game_date,
        (NOW() >= m.game_date) AS is_locked,
        m.result,
        m.home_team AS home_team_id,
        home.name AS home_team_name,
        home.shortcut AS home_team_shortcut,
        m.away_team AS away_team_id,
        away.name AS away_team_name,
        away.shortcut AS away_team_shortcut,
        o_home.odds AS odds_home,
        o_draw.odds AS odds_draw,
        o_away.odds AS odds_away,
        p.id AS prediction_id,
        p.selected_event_id
    FROM champions_league_typer_matches tm
    JOIN matches m ON m.id = tm.match_id
    JOIN teams home ON home.id = m.home_team
    JOIN teams away ON away.id = m.away_team
    LEFT JOIN odds o_home
        ON o_home.match_id = m.id
       AND o_home.bookmaker = {SUPERBET_BOOKMAKER_ID}
       AND o_home.event = {HOME_EVENT_ID}
    LEFT JOIN odds o_draw
        ON o_draw.match_id = m.id
       AND o_draw.bookmaker = {SUPERBET_BOOKMAKER_ID}
       AND o_draw.event = {DRAW_EVENT_ID}
    LEFT JOIN odds o_away
        ON o_away.match_id = m.id
       AND o_away.bookmaker = {SUPERBET_BOOKMAKER_ID}
       AND o_away.event = {AWAY_EVENT_ID}
    LEFT JOIN champions_league_typer_predictions p
        ON p.typer_match_id = tm.id
       AND p.user_id = %s
    WHERE tm.season_id = %s
    ORDER BY tm.round_number ASC, m.game_date ASC, tm.match_id ASC
"""

_CHANGES_SELECT_SQL = """
    SELECT
        c.id,
        c.prediction_id,
        tm.match_id,
        u.uuid AS user_uuid,
        u.display_name,
        c.previous_selected_event_id,
        c.new_selected_event_id,
        c.changed_at
    FROM champions_league_typer_prediction_changes c
    JOIN champions_league_typer_predictions p ON p.id = c.prediction_id
    JOIN champions_league_typer_matches tm ON tm.id = p.typer_match_id
    JOIN users u ON u.id = p.user_id
"""

_OWN_HISTORY_SQL = _CHANGES_SELECT_SQL + """
    WHERE p.user_id = %s
      AND tm.match_id = %s
    ORDER BY c.changed_at ASC, c.id ASC
"""

_DASHBOARD_HISTORY_SQL = _CHANGES_SELECT_SQL + """
    WHERE p.user_id = %s
      AND tm.season_id = %s
    ORDER BY tm.match_id ASC, c.changed_at ASC, c.id ASC
"""

_LEADERBOARD_SQL = f"""
    SELECT
        ROW_NUMBER() OVER (
            ORDER BY ranked.total_points DESC,
                     ranked.correct_predictions DESC,
                     ranked.display_name ASC
        ) AS place,
        ranked.user_uuid,
        ranked.display_name,
        ranked.total_points,
        ranked.correct_predictions,
        ranked.settled_predictions
    FROM (
        SELECT
            scored.user_uuid,
            scored.display_name,
            COALESCE(SUM(COALESCE(scored.points, 0)), 0) AS total_points,
            COALESCE(SUM(
                CASE
                    WHEN scored.points IS NOT NULL
                     AND scored.points > 0 THEN 1
                    ELSE 0
                END
            ), 0) AS correct_predictions,
            COALESCE(SUM(
                CASE
                    WHEN scored.points IS NOT NULL THEN 1
                    ELSE 0
                END
            ), 0) AS settled_predictions
        FROM (
            SELECT
                u.id AS user_id,
                u.uuid AS user_uuid,
                u.display_name,
                {_POINTS_SQL} AS points
            FROM champions_league_typer_predictions p
            JOIN champions_league_typer_matches tm
                ON tm.id = p.typer_match_id
            JOIN matches m ON m.id = tm.match_id
            JOIN users u ON u.id = p.user_id
            LEFT JOIN odds o
                ON o.match_id = m.id
               AND o.bookmaker = {SUPERBET_BOOKMAKER_ID}
               AND o.event = p.selected_event_id
            WHERE tm.season_id = %s
        ) scored
        GROUP BY scored.user_id, scored.user_uuid, scored.display_name
    ) ranked
    ORDER BY ranked.total_points DESC,
             ranked.correct_predictions DESC,
             ranked.display_name ASC
"""


def fetch_admin_candidates(
        season_id: int,
        round_number: int) -> list[dict[str, Any]]:
    """Return CL matches for a round with publication and odds flags."""
    _require_positive_ids(season_id=season_id, round_number=round_number)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            _require_season(cursor, season_id)
            cursor.execute(_CANDIDATE_SQL, (season_id, round_number))
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [_map_candidate_row(row) for row in rows]


def publish_matches(
        season_id: int,
        round_number: int,
        match_ids: list[int],
        admin_id: int,
        *,
        group_match_count: int | None = None) -> list[dict[str, Any]]:
    """Insert a round's publications in one locked transaction.

    Does not read, insert or update ``odds``. Odds completeness is not
    required. All Champions League ``matches`` of the round are locked
    first so parallel publishes cannot exceed the group-stage limit or
    skip knockout completeness.
    """
    _require_positive_ids(
        season_id=season_id, round_number=round_number, admin_id=admin_id)
    _require_group_match_count(group_match_count)
    unique_ids = _unique_match_ids(match_ids)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            _require_season(cursor, season_id)
            round_rows = _lock_round_matches(
                cursor, season_id, round_number)
            _lock_matches_for_publish(
                cursor, unique_ids, season_id, round_number)
            published_ids = _lock_round_publications(
                cursor, season_id, round_number)
            _assert_phase_publication_rules(
                unique_ids,
                round_rows,
                published_ids,
                group_match_count)
            _insert_publications(
                cursor, unique_ids, season_id, round_number, admin_id)
            rows = _fetch_publications_by_match_ids(cursor, unique_ids)
            # mysql-connector bez autocommit — close bez commit cofa INSERT
            conn.commit()
        except IntegrityError as exc:
            conn.rollback()
            raise TyperConflictError(
                "One or more matches are already published") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return [_map_publication_row(row) for row in rows]


def remove_publication(match_id: int) -> None:
    """Delete a publication only before kickoff and when no picks exist."""
    _require_positive_ids(match_id=match_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(_LOCK_PUBLICATION_FOR_DELETE_SQL, (match_id,))
            row = cursor.fetchone()
            if row is None:
                raise TyperNotFoundError("Published match not found")
            if not _as_bool(row["is_open"]):
                raise TyperConflictError(
                    "Publication cannot be removed after kickoff")
            if int(row["prediction_count"] or 0) > 0:
                raise TyperConflictError(
                    "Publication cannot be removed while picks exist")
            cursor.execute(
                _DELETE_PUBLICATION_SQL, (int(row["typer_match_id"]),))
            # mysql-connector bez autocommit — close bez commit cofa DELETE
            conn.commit()
        except TyperRepositoryError:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def save_prediction(
        user_id: int,
        match_id: int,
        selected_event_id: int) -> dict[str, Any]:
    """Upsert the current pick and append audit in the same transaction.

    Deadline is enforced in SQL via ``NOW() < matches.game_date``. An
    identical pick is a no-op and does not insert an audit row.
    """
    _require_positive_ids(user_id=user_id, match_id=match_id)
    _require_one_x_two_event(selected_event_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            context = _lock_prediction_context(cursor, user_id, match_id)
            result = _upsert_prediction_with_audit(
                cursor, context, user_id, match_id, selected_event_id)
            # mysql-connector bez autocommit — close bez commit cofa UPSERT/audyt
            conn.commit()
        except TyperRepositoryError:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return result


def fetch_dashboard(
        user_id: int,
        season_id: int | None) -> dict[str, Any]:
    """Return published matches, Superbet 1X2 odds and the user's audit."""
    _require_positive_ids(user_id=user_id)
    if season_id is not None:
        _require_positive_ids(season_id=season_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            resolved_season_id = _resolve_season_id(cursor, season_id)
            cursor.execute(
                _DASHBOARD_MATCHES_SQL, (user_id, resolved_season_id))
            match_rows = cursor.fetchall()
            cursor.execute(
                _DASHBOARD_HISTORY_SQL, (user_id, resolved_season_id))
            change_rows = cursor.fetchall()
        finally:
            cursor.close()
    return {
        "season_id": resolved_season_id,
        "matches": [_map_dashboard_match_row(row) for row in match_rows],
        "changes": [_map_change_row(row) for row in change_rows]
    }


def fetch_leaderboard(season_id: int | None) -> list[dict[str, Any]]:
    """Return ranking scored from ``matches.result`` and ``odds.odds``."""
    if season_id is not None:
        _require_positive_ids(season_id=season_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            resolved_season_id = _resolve_season_id(cursor, season_id)
            cursor.execute(_LEADERBOARD_SQL, (resolved_season_id,))
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [_map_leaderboard_row(row) for row in rows]


def fetch_own_prediction_history(
        user_id: int,
        match_id: int) -> list[dict[str, Any]]:
    """Return chronological audit rows for the caller's pick on a match."""
    _require_positive_ids(user_id=user_id, match_id=match_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            _require_published_match(cursor, match_id)
            cursor.execute(_OWN_HISTORY_SQL, (user_id, match_id))
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [_map_change_row(row) for row in rows]


def fetch_admin_prediction_history(
        user_uuid: str,
        match_id: int | None = None,
        season_id: int | None = None) -> list[dict[str, Any]]:
    """Return audit rows for a user identified by public UUID."""
    if not user_uuid or not user_uuid.strip():
        raise TyperValidationError("user_uuid is required")
    if match_id is not None:
        _require_positive_ids(match_id=match_id)
    if season_id is not None:
        _require_positive_ids(season_id=season_id)
    query, params = _admin_history_query(user_uuid.strip(), match_id, season_id)
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            _require_user_uuid(cursor, user_uuid.strip())
            if season_id is not None:
                _require_season(cursor, season_id)
            cursor.execute(query, params)
            rows = cursor.fetchall()
        finally:
            cursor.close()
    return [_map_change_row(row) for row in rows]


def _admin_history_query(
        user_uuid: str,
        match_id: int | None,
        season_id: int | None) -> tuple[str, tuple[object, ...]]:
    conditions = ["u.uuid = %s"]
    params: list[object] = [user_uuid]
    if match_id is not None:
        conditions.append("tm.match_id = %s")
        params.append(match_id)
    if season_id is not None:
        conditions.append("tm.season_id = %s")
        params.append(season_id)
    where_sql = " AND ".join(conditions)
    query = (
        _CHANGES_SELECT_SQL
        + f" WHERE {where_sql}"
        + " ORDER BY c.changed_at ASC, c.id ASC")
    return query, tuple(params)


def _unique_match_ids(match_ids: list[int]) -> list[int]:
    if not match_ids:
        raise TyperValidationError("At least one match id is required")
    unique_ids: list[int] = []
    seen: set[int] = set()
    for match_id in match_ids:
        if not isinstance(match_id, int) or match_id <= 0:
            raise TyperValidationError("Match ids must be positive integers")
        if match_id in seen:
            raise TyperValidationError(
                "Duplicate match ids in publication set")
        seen.add(match_id)
        unique_ids.append(match_id)
    return unique_ids


def _in_placeholders(count: int) -> str:
    return ", ".join(["%s"] * count)


def _require_group_match_count(group_match_count: int | None) -> None:
    if group_match_count is None:
        return
    if not isinstance(group_match_count, int) or group_match_count <= 0:
        raise TyperValidationError(
            "group_match_count must be a positive integer")


def _lock_round_matches(
        cursor: Any,
        season_id: int,
        round_number: int) -> list[dict[str, Any]]:
    # blokada całej rundy LM serializuje równoległe publikacje zestawów
    cursor.execute(_LOCK_ROUND_MATCHES_SQL, (season_id, round_number))
    return list(cursor.fetchall())


def _lock_round_publications(
        cursor: Any, season_id: int, round_number: int) -> set[int]:
    cursor.execute(
        _LOCK_ROUND_PUBLICATIONS_SQL, (season_id, round_number))
    return {int(row["match_id"]) for row in cursor.fetchall()}


def _assert_phase_publication_rules(
        match_ids: list[int],
        round_rows: list[dict[str, Any]],
        published_ids: set[int],
        group_match_count: int | None) -> None:
    round_ids = {int(row["id"]) for row in round_rows}
    unpublished_ids = round_ids - published_ids
    requested_ids = set(match_ids)
    if requested_ids & published_ids:
        raise TyperConflictError(
            "One or more matches are already published")
    if group_match_count is not None:
        _assert_group_stage_under_lock(
            match_ids,
            unpublished_ids,
            published_ids,
            group_match_count)
        return
    if not round_ids:
        raise TyperNotFoundError(
            "No Champions League matches for this round")
    if requested_ids != unpublished_ids:
        raise TyperValidationError(
            "Knockout publication must include every unpublished "
            "imported match of the round")


def _assert_group_stage_under_lock(
        match_ids: list[int],
        unpublished_ids: set[int],
        published_ids: set[int],
        group_match_count: int) -> None:
    if not set(match_ids).issubset(unpublished_ids):
        raise TyperValidationError(
            "Group-stage match ids must be unpublished matches "
            "of the requested round")
    if len(published_ids) + len(match_ids) != group_match_count:
        raise TyperValidationError(
            f"Group-stage round must have exactly {group_match_count} "
            "published matches")


def _lock_matches_for_publish(
        cursor: Any,
        match_ids: list[int],
        season_id: int,
        round_number: int) -> None:
    query = _LOCK_MATCHES_SQL.format(
        placeholders=_in_placeholders(len(match_ids)))
    # ORDER BY id + FOR UPDATE: ta sama kolejność blokad przy równoległym publish
    cursor.execute(query, tuple(match_ids))
    rows = cursor.fetchall()
    found_ids = {int(row["id"]) for row in rows}
    missing = [match_id for match_id in match_ids if match_id not in found_ids]
    if missing:
        raise TyperNotFoundError("Match not found")
    for row in rows:
        if int(row["league"]) != CHAMPIONS_LEAGUE_ID:
            raise TyperNotFoundError(
                "Match does not belong to Champions League")
        if int(row["season"]) != season_id:
            raise TyperNotFoundError(
                "Match does not belong to the requested season")
        if int(row["round"]) != round_number:
            raise TyperValidationError(
                "Match round does not match the requested round")


def _insert_publications(
        cursor: Any,
        match_ids: list[int],
        season_id: int,
        round_number: int,
        admin_id: int) -> None:
    params = [
        (match_id, season_id, round_number, admin_id)
        for match_id in match_ids]
    cursor.executemany(_INSERT_PUBLICATION_SQL, params)


def _fetch_publications_by_match_ids(
        cursor: Any, match_ids: list[int]) -> list[dict[str, Any]]:
    query = _FETCH_PUBLICATIONS_SQL.format(
        placeholders=_in_placeholders(len(match_ids)))
    cursor.execute(query, tuple(match_ids))
    return list(cursor.fetchall())


def _lock_prediction_context(
        cursor: Any, user_id: int, match_id: int) -> dict[str, Any]:
    cursor.execute(_LOCK_PREDICTION_SQL, (user_id, match_id))
    row = cursor.fetchone()
    if row is None:
        raise TyperNotFoundError("Published match not found")
    if not _as_bool(row["is_open"]):
        raise TyperConflictError(
            "Prediction cannot be saved after kickoff")
    return row


def _upsert_prediction_with_audit(
        cursor: Any,
        context: dict[str, Any],
        user_id: int,
        match_id: int,
        selected_event_id: int) -> dict[str, Any]:
    prediction_id = context["prediction_id"]
    previous_event_id = _as_optional_int(context["selected_event_id"])
    if prediction_id is not None and previous_event_id == selected_event_id:
        return _prediction_result(
            context, user_id, match_id, selected_event_id, False)
    if prediction_id is None:
        prediction_id = _insert_prediction(
            cursor,
            int(context["typer_match_id"]),
            user_id,
            selected_event_id)
        previous_event_id = None
    else:
        _update_prediction(cursor, int(prediction_id), selected_event_id)
        prediction_id = int(prediction_id)
    _insert_audit_row(
        cursor, prediction_id, user_id, previous_event_id, selected_event_id)
    stored = _fetch_prediction_row(cursor, prediction_id)
    return {
        "prediction_id": int(stored["prediction_id"]),
        "typer_match_id": int(stored["typer_match_id"]),
        "match_id": match_id,
        "user_id": int(stored["user_id"]),
        "selected_event_id": int(stored["selected_event_id"]),
        "previous_selected_event_id": previous_event_id,
        "audit_written": True,
        "created_at": stored["created_at"],
        "updated_at": stored["updated_at"]
    }


def _insert_prediction(
        cursor: Any,
        typer_match_id: int,
        user_id: int,
        selected_event_id: int) -> int:
    cursor.execute(
        _INSERT_PREDICTION_SQL,
        (typer_match_id, user_id, selected_event_id, typer_match_id))
    if cursor.rowcount == 0:
        raise TyperConflictError(
            "Prediction cannot be saved after kickoff")
    return int(cursor.lastrowid)


def _update_prediction(
        cursor: Any, prediction_id: int, selected_event_id: int) -> None:
    cursor.execute(
        _UPDATE_PREDICTION_SQL, (selected_event_id, prediction_id))
    if cursor.rowcount == 0:
        raise TyperConflictError(
            "Prediction cannot be saved after kickoff")


def _insert_audit_row(
        cursor: Any,
        prediction_id: int,
        user_id: int,
        previous_event_id: int | None,
        selected_event_id: int) -> None:
    cursor.execute(
        _INSERT_AUDIT_SQL,
        (prediction_id, user_id, previous_event_id, selected_event_id))


def _fetch_prediction_row(cursor: Any, prediction_id: int) -> dict[str, Any]:
    cursor.execute(_FETCH_PREDICTION_SQL, (prediction_id,))
    row = cursor.fetchone()
    if row is None:
        raise TyperNotFoundError("Prediction not found after save")
    return row


def _prediction_result(
        context: dict[str, Any],
        user_id: int,
        match_id: int,
        selected_event_id: int,
        audit_written: bool) -> dict[str, Any]:
    return {
        "prediction_id": int(context["prediction_id"]),
        "typer_match_id": int(context["typer_match_id"]),
        "match_id": match_id,
        "user_id": user_id,
        "selected_event_id": selected_event_id,
        "previous_selected_event_id": _as_optional_int(
            context["selected_event_id"]),
        "audit_written": audit_written,
        "created_at": context["created_at"],
        "updated_at": context["updated_at"]
    }


def _require_published_match(cursor: Any, match_id: int) -> None:
    cursor.execute(
        """
        SELECT 1
        FROM champions_league_typer_matches tm
        JOIN matches m ON m.id = tm.match_id
        WHERE tm.match_id = %s
          AND m.league = %s
        LIMIT 1
        """,
        (match_id, CHAMPIONS_LEAGUE_ID))
    if cursor.fetchone() is None:
        raise TyperNotFoundError("Published match not found")


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


def _require_one_x_two_event(selected_event_id: int) -> None:
    if selected_event_id not in ONE_X_TWO_EVENT_IDS:
        raise TyperValidationError(
            "selected_event_id must be 1, 2 or 3")


def _require_positive_ids(**ids: int) -> None:
    for name, value in ids.items():
        if not isinstance(value, int) or value <= 0:
            raise TyperValidationError(f"{name} must be a positive integer")


def _as_bool(value: object) -> bool:
    return bool(value)


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _as_optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _map_candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": int(row["match_id"]),
        "season_id": int(row["season_id"]),
        "round_number": int(row["round_number"]),
        "game_date": row["game_date"],
        "home_team_id": int(row["home_team_id"]),
        "home_team_name": str(row["home_team_name"]),
        "home_team_shortcut": str(row["home_team_shortcut"]),
        "away_team_id": int(row["away_team_id"]),
        "away_team_name": str(row["away_team_name"]),
        "away_team_shortcut": str(row["away_team_shortcut"]),
        "is_published": _as_bool(row["is_published"]),
        "has_complete_superbet_odds": _as_bool(
            row["has_complete_superbet_odds"])
    }


def _map_publication_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "typer_match_id": int(row["typer_match_id"]),
        "match_id": int(row["match_id"]),
        "season_id": int(row["season_id"]),
        "round_number": int(row["round_number"]),
        "published_by": int(row["published_by"]),
        "published_at": row["published_at"]
    }


def _map_dashboard_match_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "typer_match_id": int(row["typer_match_id"]),
        "match_id": int(row["match_id"]),
        "season_id": int(row["season_id"]),
        "round_number": int(row["round_number"]),
        "published_at": row["published_at"],
        "game_date": row["game_date"],
        "is_locked": _as_bool(row["is_locked"]),
        "result": None if row["result"] is None else str(row["result"]),
        "home_team_id": int(row["home_team_id"]),
        "home_team_name": str(row["home_team_name"]),
        "home_team_shortcut": str(row["home_team_shortcut"]),
        "away_team_id": int(row["away_team_id"]),
        "away_team_name": str(row["away_team_name"]),
        "away_team_shortcut": str(row["away_team_shortcut"]),
        "odds_home": _as_optional_float(row["odds_home"]),
        "odds_draw": _as_optional_float(row["odds_draw"]),
        "odds_away": _as_optional_float(row["odds_away"]),
        "prediction_id": _as_optional_int(row["prediction_id"]),
        "selected_event_id": _as_optional_int(row["selected_event_id"])
    }


def _map_change_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "prediction_id": int(row["prediction_id"]),
        "match_id": int(row["match_id"]),
        "user_uuid": str(row["user_uuid"]),
        "display_name": str(row["display_name"]),
        "previous_selected_event_id": _as_optional_int(
            row["previous_selected_event_id"]),
        "new_selected_event_id": int(row["new_selected_event_id"]),
        "changed_at": row["changed_at"]
    }


def _map_leaderboard_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "place": int(row["place"]),
        "user_uuid": str(row["user_uuid"]),
        "display_name": str(row["display_name"]),
        "total_points": float(row["total_points"]),
        "correct_predictions": int(row["correct_predictions"]),
        "settled_predictions": int(row["settled_predictions"])
    }
