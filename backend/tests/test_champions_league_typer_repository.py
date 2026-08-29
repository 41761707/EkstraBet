"""Unit tests for Champions League Typer repository SQL contracts."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import IntegrityError

from backend.database import DatabaseConnectionError
from backend.database import get_db_connection
from backend.repositories import champions_league_typer_repository as repo

_GET_CONN = (
    "backend.repositories.champions_league_typer_repository"
    ".get_db_connection")

_GAME_DATE = datetime(2026, 9, 16, 21, 0)
_PUBLISHED_AT = datetime(2026, 9, 10, 12, 0)
_CHANGED_AT = datetime(2026, 9, 11, 18, 30)


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        fetchone_results: list[dict[str, object] | None] | None = None,
        fetchall_results: list[list[dict[str, object]]] | None = None,
        rowcount: int = 1,
        lastrowid: int = 10) -> tuple[MagicMock, MagicMock]:
    """Return mocked connection and cursor wired to get_db_connection."""
    cursor = MagicMock()
    if fetchone_results is None:
        cursor.fetchone.return_value = {"1": 1}
    else:
        cursor.fetchone.side_effect = fetchone_results
    if fetchall_results is None:
        cursor.fetchall.return_value = []
    else:
        cursor.fetchall.side_effect = fetchall_results
    cursor.rowcount = rowcount
    cursor.lastrowid = lastrowid
    conn = MagicMock()
    conn.cursor.return_value = cursor
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = conn
    mock_cm.__exit__.return_value = False
    mock_get_conn.return_value = mock_cm
    return conn, cursor


def _sql_statements(cursor: MagicMock) -> list[str]:
    statements = [
        call.args[0] for call in cursor.execute.call_args_list]
    statements.extend(
        call.args[0] for call in cursor.executemany.call_args_list)
    return statements


def _assert_no_inlined_values(
        test: unittest.TestCase,
        query: str,
        *values: object) -> None:
    for value in values:
        test.assertNotIn(str(value), query)
    test.assertIn("%s", query)


def _assert_no_odds_mutation(
        test: unittest.TestCase, statements: list[str]) -> None:
    combined = "\n".join(statements).lower()
    test.assertNotIn("insert into odds", combined)
    test.assertNotIn("update odds", combined)
    test.assertNotIn("delete from odds", combined)


def _match_row(
        match_id: int,
        round_number: int = 1,
        league: int = repo.CHAMPIONS_LEAGUE_ID,
        season: int = 13) -> dict[str, object]:
    return {
        "id": match_id,
        "league": league,
        "season": season,
        "round": round_number
    }


def _publication_row(match_id: int) -> dict[str, object]:
    return {
        "typer_match_id": match_id + 1000,
        "match_id": match_id,
        "season_id": 13,
        "round_number": 1,
        "published_by": 7,
        "published_at": _PUBLISHED_AT
    }


def _candidate_row(match_id: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "season_id": 13,
        "round_number": 1,
        "game_date": _GAME_DATE,
        "home_team_id": 1,
        "home_team_name": "Home",
        "home_team_shortcut": "HOM",
        "away_team_id": 2,
        "away_team_name": "Away",
        "away_team_shortcut": "AWY",
        "is_published": 0,
        "has_complete_superbet_odds": 0
    }


def _lock_open_row(
        *,
        prediction_id: int | None = None,
        selected_event_id: int | None = None) -> dict[str, object]:
    return {
        "typer_match_id": 50,
        "match_id": 101,
        "is_open": 1,
        "prediction_id": prediction_id,
        "selected_event_id": selected_event_id,
        "created_at": _CHANGED_AT,
        "updated_at": _CHANGED_AT
    }


def _stored_prediction_row(
        selected_event_id: int) -> dict[str, object]:
    return {
        "prediction_id": 10,
        "typer_match_id": 50,
        "user_id": 4,
        "selected_event_id": selected_event_id,
        "created_at": _CHANGED_AT,
        "updated_at": _CHANGED_AT
    }


class TestFetchAdminCandidates(unittest.TestCase):
    """Candidates expose publication state and Superbet odds completeness."""

    @patch(_GET_CONN)
    def test_query_joins_odds_without_requiring_rows(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[_candidate_row(101)]])
        rows = repo.fetch_admin_candidates(13, 1)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["is_published"])
        self.assertFalse(rows[0]["has_complete_superbet_odds"])
        query = cursor.execute.call_args_list[-1].args[0]
        self.assertIn("FROM odds o", query)
        self.assertIn("LEFT JOIN champions_league_typer_matches", query)
        self.assertIn("m.league = 42", query)
        self.assertNotIn("INSERT INTO", query)

    @patch(_GET_CONN)
    def test_params_are_season_and_round(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_admin_candidates(13, 8)
        query, params = cursor.execute.call_args_list[-1].args
        _assert_no_inlined_values(self, query, 13, 8)
        self.assertEqual(params, (13, 8))


class TestPublishMatches(unittest.TestCase):
    """Publication inserts typer rows only, under FOR UPDATE locks."""

    def _publish(
            self,
            mock_get_conn: MagicMock,
            *,
            match_ids: list[int] | None = None,
            existing: list[dict[str, object]] | None = None,
            locked: list[dict[str, object]] | None = None
            ) -> tuple[MagicMock, MagicMock, list[dict[str, object]]]:
        ids = match_ids or [101, 102]
        locked_rows = locked or [_match_row(match_id) for match_id in ids]
        published = [_publication_row(match_id) for match_id in ids]
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[
                locked_rows,
                existing or [],
                published])
        result = repo.publish_matches(13, 1, ids, admin_id=7)
        return conn, cursor, result

    @patch(_GET_CONN)
    def test_inserts_only_typer_matches_and_commits(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor, result = self._publish(mock_get_conn)
        self.assertEqual([row["match_id"] for row in result], [101, 102])
        insert_sql, insert_params = cursor.executemany.call_args.args
        self.assertIn(
            "INSERT INTO champions_league_typer_matches", insert_sql)
        self.assertEqual(
            insert_params,
            [(101, 13, 1, 7), (102, 13, 1, 7)])
        _assert_no_odds_mutation(self, _sql_statements(cursor))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        cursor.close.assert_called_once()

    @patch(_GET_CONN)
    def test_locks_matches_for_update_with_placeholders(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor, _result = self._publish(mock_get_conn)
        lock_sql, lock_params = cursor.execute.call_args_list[1].args
        self.assertIn("FOR UPDATE", lock_sql)
        self.assertIn("WHERE id IN (%s, %s)", lock_sql)
        self.assertNotIn("101", lock_sql)
        self.assertEqual(lock_params, (101, 102))

    @patch(_GET_CONN)
    def test_does_not_write_odds(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor, _result = self._publish(mock_get_conn)
        combined = "\n".join(_sql_statements(cursor)).lower()
        self.assertNotIn("odds", combined)

    @patch(_GET_CONN)
    def test_existing_publication_raises_conflict_and_rolls_back(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[
                [_match_row(101)],
                [{"match_id": 101}]])
        with self.assertRaises(repo.TyperConflictError):
            repo.publish_matches(13, 1, [101], admin_id=7)
        cursor.executemany.assert_not_called()
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_missing_match_raises_not_found(
            self, mock_get_conn: MagicMock) -> None:
        conn, _cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[_match_row(101)]])
        with self.assertRaises(repo.TyperNotFoundError):
            repo.publish_matches(13, 1, [101, 102], admin_id=7)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_integrity_error_maps_to_conflict(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[_match_row(101)], []])
        cursor.executemany.side_effect = IntegrityError(
            "Duplicate entry", 1062)
        with self.assertRaises(repo.TyperConflictError):
            repo.publish_matches(13, 1, [101], admin_id=7)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    def test_duplicate_ids_rejected_before_sql(self) -> None:
        with self.assertRaises(repo.TyperValidationError):
            repo.publish_matches(13, 1, [101, 101], admin_id=7)

    @patch(_GET_CONN)
    def test_foreign_league_raises_not_found(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[_match_row(101, league=1)]])
        with self.assertRaises(repo.TyperNotFoundError):
            repo.publish_matches(13, 1, [101], admin_id=7)
        cursor.executemany.assert_not_called()
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_other_round_raises_validation_error(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[_match_row(101, round_number=8)]])
        with self.assertRaises(repo.TyperValidationError):
            repo.publish_matches(13, 1, [101], admin_id=7)
        cursor.executemany.assert_not_called()
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_other_season_raises_not_found(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[_match_row(101, season=12)]])
        with self.assertRaises(repo.TyperNotFoundError):
            repo.publish_matches(13, 1, [101], admin_id=7)
        cursor.executemany.assert_not_called()
        conn.commit.assert_not_called()
        conn.rollback.assert_called()


class TestRemovePublication(unittest.TestCase):
    """Removal is blocked after kickoff or when picks exist."""

    @patch(_GET_CONN)
    def test_deletes_open_publication_without_picks(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[{
                "typer_match_id": 50,
                "match_id": 101,
                "is_open": 1,
                "prediction_count": 0}])
        repo.remove_publication(101)
        delete_sql, delete_params = cursor.execute.call_args_list[-1].args
        self.assertIn("DELETE FROM champions_league_typer_matches", delete_sql)
        self.assertEqual(delete_params, (50,))
        _assert_no_odds_mutation(self, _sql_statements(cursor))
        conn.commit.assert_called_once()

    @patch(_GET_CONN)
    def test_existing_picks_are_conflict(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[{
                "typer_match_id": 50,
                "match_id": 101,
                "is_open": 1,
                "prediction_count": 2}])
        with self.assertRaises(repo.TyperConflictError):
            repo.remove_publication(101)
        conn.commit.assert_not_called()
        self.assertFalse(
            any("DELETE FROM" in sql for sql in _sql_statements(cursor)))

    @patch(_GET_CONN)
    def test_kickoff_blocks_removal_even_without_picks(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[{
                "typer_match_id": 50,
                "match_id": 101,
                "is_open": 0,
                "prediction_count": 0}])
        with self.assertRaises(repo.TyperConflictError):
            repo.remove_publication(101)
        conn.commit.assert_not_called()
        self.assertFalse(
            any("DELETE FROM" in sql for sql in _sql_statements(cursor)))


class TestSavePrediction(unittest.TestCase):
    """UPSERT and audit share one transaction; no-op skips audit."""

    def _assert_audit_with_write(self, cursor: MagicMock) -> None:
        statements = _sql_statements(cursor)
        writes = [
            sql for sql in statements
            if sql.lstrip().upper().startswith(("INSERT", "UPDATE"))]
        self.assertTrue(writes)
        self.assertTrue(
            any(
                "INSERT INTO champions_league_typer_prediction_changes"
                in sql
                for sql in writes))
        last_write = writes[-1]
        self.assertIn(
            "INSERT INTO champions_league_typer_prediction_changes",
            last_write)

    @patch(_GET_CONN)
    def test_first_save_inserts_prediction_and_audit(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[
                _lock_open_row(),
                _stored_prediction_row(1)])
        result = repo.save_prediction(4, 101, 1)
        self.assertTrue(result["audit_written"])
        self.assertIsNone(result["previous_selected_event_id"])
        insert_prediction = cursor.execute.call_args_list[1].args[0]
        insert_audit, audit_params = cursor.execute.call_args_list[2].args
        self.assertIn(
            "INSERT INTO champions_league_typer_predictions",
            insert_prediction)
        self.assertIn("NOW() < m.game_date", insert_prediction)
        self.assertIn(
            "INSERT INTO champions_league_typer_prediction_changes",
            insert_audit)
        self.assertEqual(audit_params, (10, 4, None, 1))
        self._assert_audit_with_write(cursor)
        _assert_no_odds_mutation(self, _sql_statements(cursor))
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    @patch(_GET_CONN)
    def test_change_updates_pick_and_writes_audit(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[
                _lock_open_row(prediction_id=10, selected_event_id=1),
                _stored_prediction_row(2)])
        result = repo.save_prediction(4, 101, 2)
        self.assertTrue(result["audit_written"])
        self.assertEqual(result["previous_selected_event_id"], 1)
        update_sql, update_params = cursor.execute.call_args_list[1].args
        audit_sql, audit_params = cursor.execute.call_args_list[2].args
        self.assertIn("UPDATE champions_league_typer_predictions", update_sql)
        self.assertIn("NOW() < m.game_date", update_sql)
        self.assertEqual(update_params, (2, 10))
        self.assertIn(
            "INSERT INTO champions_league_typer_prediction_changes",
            audit_sql)
        self.assertEqual(audit_params, (10, 4, 1, 2))
        self._assert_audit_with_write(cursor)
        conn.commit.assert_called_once()

    @patch(_GET_CONN)
    def test_identical_pick_is_noop_without_audit(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[
                _lock_open_row(prediction_id=10, selected_event_id=1)])
        result = repo.save_prediction(4, 101, 1)
        self.assertFalse(result["audit_written"])
        combined = "\n".join(_sql_statements(cursor))
        self.assertNotIn(
            "INSERT INTO champions_league_typer_prediction_changes",
            combined)
        self.assertNotIn("UPDATE champions_league_typer_predictions", combined)
        conn.commit.assert_called_once()

    @patch(_GET_CONN)
    def test_deadline_conflict_does_not_write(
            self, mock_get_conn: MagicMock) -> None:
        locked = _lock_open_row()
        locked["is_open"] = 0
        conn, cursor = _mock_connection(
            mock_get_conn, fetchone_results=[locked])
        with self.assertRaises(repo.TyperConflictError):
            repo.save_prediction(4, 101, 1)
        combined = "\n".join(_sql_statements(cursor))
        self.assertNotIn("INSERT INTO", combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_lock_query_uses_now_and_for_update(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[
                _lock_open_row(prediction_id=10, selected_event_id=1)])
        repo.save_prediction(4, 101, 1)
        lock_sql, lock_params = cursor.execute.call_args_list[0].args
        self.assertIn("FOR UPDATE", lock_sql)
        self.assertIn("NOW() < m.game_date", lock_sql)
        self.assertEqual(lock_params, (4, 101))

    def test_rejects_event_outside_one_x_two(self) -> None:
        with self.assertRaises(repo.TyperValidationError):
            repo.save_prediction(4, 101, 5)

    @patch(_GET_CONN)
    def test_insert_rowcount_zero_is_deadline_conflict(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_lock_open_row()],
            rowcount=0)
        with self.assertRaises(repo.TyperConflictError):
            repo.save_prediction(4, 101, 1)
        combined = "\n".join(_sql_statements(cursor))
        self.assertIn(
            "INSERT INTO champions_league_typer_predictions", combined)
        self.assertNotIn(
            "INSERT INTO champions_league_typer_prediction_changes",
            combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_update_rowcount_zero_is_deadline_conflict(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[
                _lock_open_row(prediction_id=10, selected_event_id=1)],
            rowcount=0)
        with self.assertRaises(repo.TyperConflictError):
            repo.save_prediction(4, 101, 2)
        combined = "\n".join(_sql_statements(cursor))
        self.assertIn("UPDATE champions_league_typer_predictions", combined)
        self.assertNotIn(
            "INSERT INTO champions_league_typer_prediction_changes",
            combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()


class TestFetchDashboard(unittest.TestCase):
    """Dashboard reads nullable Superbet odds and private audit only."""

    @patch(_GET_CONN)
    def test_odds_are_left_joined_and_history_is_user_scoped(
            self, mock_get_conn: MagicMock) -> None:
        match_row = {
            "typer_match_id": 50,
            "match_id": 101,
            "season_id": 13,
            "round_number": 1,
            "published_at": _PUBLISHED_AT,
            "game_date": _GAME_DATE,
            "is_locked": 0,
            "result": None,
            "home_team_id": 1,
            "home_team_name": "Home",
            "home_team_shortcut": "HOM",
            "away_team_id": 2,
            "away_team_name": "Away",
            "away_team_shortcut": "AWY",
            "odds_home": None,
            "odds_draw": None,
            "odds_away": 3.4,
            "prediction_id": 10,
            "selected_event_id": 3
        }
        change_row = {
            "id": 1,
            "prediction_id": 10,
            "match_id": 101,
            "user_uuid": "u-1",
            "display_name": "Ada",
            "previous_selected_event_id": None,
            "new_selected_event_id": 3,
            "changed_at": _CHANGED_AT
        }
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[match_row], [change_row]])
        document = repo.fetch_dashboard(4, 13)
        self.assertEqual(document["season_id"], 13)
        self.assertIsNone(document["matches"][0]["odds_home"])
        self.assertEqual(document["matches"][0]["odds_away"], 3.4)
        self.assertEqual(len(document["changes"]), 1)
        match_sql, match_params = cursor.execute.call_args_list[1].args
        history_sql, history_params = cursor.execute.call_args_list[2].args
        self.assertIn("LEFT JOIN odds o_home", match_sql)
        self.assertIn("LEFT JOIN odds o_draw", match_sql)
        self.assertIn("LEFT JOIN odds o_away", match_sql)
        self.assertIn("p.user_id = %s", match_sql)
        self.assertEqual(match_params, (4, 13))
        self.assertIn("p.user_id = %s", history_sql)
        self.assertEqual(history_params, (4, 13))
        _assert_no_odds_mutation(self, _sql_statements(cursor))

    @patch(_GET_CONN)
    def test_none_season_uses_league_current_season(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[{"current_season_id": 13}],
            fetchall_results=[[], []])
        document = repo.fetch_dashboard(4, None)
        self.assertEqual(document["season_id"], 13)
        season_sql, season_params = cursor.execute.call_args_list[0].args
        self.assertIn("current_season_id", season_sql)
        self.assertIn("FROM leagues", season_sql)
        self.assertEqual(season_params, (repo.CHAMPIONS_LEAGUE_ID,))
        match_params = cursor.execute.call_args_list[1].args[1]
        history_params = cursor.execute.call_args_list[2].args[1]
        self.assertEqual(match_params, (4, 13))
        self.assertEqual(history_params, (4, 13))


class TestFetchLeaderboard(unittest.TestCase):
    """Ranking scores regulation 1X2 from odds and ignores extra time."""

    @patch(_GET_CONN)
    def test_scores_from_odds_and_sorts_by_points(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[[{
                "place": 1,
                "user_uuid": "u-1",
                "display_name": "Ada",
                "total_points": 5.5,
                "correct_predictions": 2,
                "settled_predictions": 3
            }]])
        rows = repo.fetch_leaderboard(13)
        self.assertEqual(rows[0]["total_points"], 5.5)
        query, params = cursor.execute.call_args_list[-1].args
        self.assertIn("o.odds", query)
        self.assertIn("LEFT JOIN odds o", query)
        self.assertIn("WHEN 'X' THEN 2", query)
        self.assertIn("m.result IN ('1', 'X', '2')", query)
        self.assertNotIn("NOT IN", query)
        self.assertIn("total_points DESC", query)
        self.assertIn("correct_predictions DESC", query)
        self.assertIn("display_name ASC", query)
        self.assertNotIn("football_special_round_add", query)
        self.assertEqual(params, (13,))
        _assert_no_odds_mutation(self, _sql_statements(cursor))
        _assert_no_inlined_values(self, query, 13)

    @patch(_GET_CONN)
    def test_none_season_uses_league_current_season(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[{"current_season_id": 13}],
            fetchall_results=[[]])
        rows = repo.fetch_leaderboard(None)
        self.assertEqual(rows, [])
        season_sql, season_params = cursor.execute.call_args_list[0].args
        self.assertIn("current_season_id", season_sql)
        self.assertEqual(season_params, (repo.CHAMPIONS_LEAGUE_ID,))
        _query, params = cursor.execute.call_args_list[-1].args
        self.assertEqual(params, (13,))


class TestPredictionHistory(unittest.TestCase):
    """Own history is user-scoped; admin history filters by public UUID."""

    @patch(_GET_CONN)
    def test_own_history_filters_user_and_match(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_own_prediction_history(4, 101)
        query, params = cursor.execute.call_args_list[-1].args
        self.assertIn("p.user_id = %s", query)
        self.assertIn("tm.match_id = %s", query)
        self.assertEqual(params, (4, 101))
        _assert_no_inlined_values(self, query, 4, 101)

    @patch(_GET_CONN)
    def test_admin_history_filters_uuid_match_and_season(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_admin_prediction_history(
            "u-1", match_id=101, season_id=13)
        query, params = cursor.execute.call_args_list[-1].args
        self.assertIn("u.uuid = %s", query)
        self.assertIn("tm.match_id = %s", query)
        self.assertIn("tm.season_id = %s", query)
        self.assertEqual(params, ("u-1", 101, 13))
        self.assertNotIn("UPDATE", query)
        self.assertNotIn("DELETE", query)


class TestPointsSqlSemantics(unittest.TestCase):
    """Evaluate scoring CASE in MySQL, including NULL three-valued logic."""

    def test_points_sql_uses_positive_result_membership(self) -> None:
        sql = repo._POINTS_SQL
        self.assertIn("m.result IN ('1', 'X', '2')", sql)
        self.assertNotIn("NOT IN", sql)
        self.assertIn("ELSE NULL", sql)

    def test_null_zero_miss_and_hit_without_odds(self) -> None:
        cases = [
            (None, 1, 2.5, None),
            ("0", 1, 2.5, None),
            ("1", 1, None, None),
            ("1", 2, 2.5, 0),
            ("X", 2, 3.1, 3.1),
            ("1", 1, 1.85, 1.85)]
        for result, event_id, odds, expected in cases:
            with self.subTest(
                    result=result, event_id=event_id, odds=odds):
                points = self._eval_points(result, event_id, odds)
                if expected is None:
                    self.assertIsNone(points)
                else:
                    self.assertEqual(float(points), float(expected))

    def _eval_points(
            self,
            result: str | None,
            selected_event_id: int,
            odds: float | None) -> object:
        query = f"""
            SELECT {repo._POINTS_SQL} AS points
            FROM (SELECT %s AS result) AS m
            INNER JOIN (SELECT %s AS selected_event_id) AS p
            INNER JOIN (SELECT %s AS odds) AS o
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                try:
                    cursor.execute(
                        query, (result, selected_event_id, odds))
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except DatabaseConnectionError as exc:
            self.skipTest(str(exc))
        if row is None:
            return None
        return row["points"]


if __name__ == "__main__":
    unittest.main()
