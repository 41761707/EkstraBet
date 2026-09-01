"""Unit tests for Typer long-term picks repository SQL contracts."""

from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

from mysql.connector.errors import IntegrityError

from backend.repositories import (
    champions_league_typer_long_term_repository as repo)

_GET_CONN = (
    "backend.repositories.champions_league_typer_long_term_repository"
    ".get_db_connection")

_DEADLINE = datetime(2026, 9, 16, 21, 0)
_CHANGED_AT = datetime(2026, 8, 20, 12, 0)
_USER_ID = 4
_MARKET_ID = 20
_SEASON_ID = 13
_TEAM_IDS = [12, 45, 101, 200, 201, 202, 203, 204]
_TEAM_CSV = "12,45,101,200,201,202,203,204"


def _mock_connection(
        mock_get_conn: MagicMock,
        *,
        fetchone_results: list[dict[str, object] | None] | None = None,
        fetchall_results: list[list[dict[str, object]]] | None = None,
        rowcount: int = 8,
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


def _combined_sql(cursor: MagicMock) -> str:
    return "\n".join(_sql_statements(cursor))


def _assert_no_inlined_values(
        test: unittest.TestCase,
        query: str,
        *values: object) -> None:
    for value in values:
        test.assertNotIn(str(value), query)
    test.assertIn("%s", query)


def _assert_long_term_table_names(
        test: unittest.TestCase, sql: str) -> None:
    test.assertNotIn("champions_league_typer_long_term", sql)
    test.assertIn("typer_long_term_", sql)


def _assert_audit_append_only(
        test: unittest.TestCase, cursor: MagicMock) -> None:
    combined = _combined_sql(cursor).lower()
    test.assertNotIn(
        "update typer_long_term_pick_changes", combined)
    test.assertNotIn(
        "delete from typer_long_term_pick_changes", combined)


def _market_lock_row(
        *,
        is_open: int = 1,
        selection_size: int = 8) -> dict[str, object]:
    return {
        "market_id": _MARKET_ID,
        "league_id": repo.CHAMPIONS_LEAGUE_ID,
        "season_id": _SEASON_ID,
        "market_key": "top8_direct_r16",
        "title": "TOP 8",
        "description": "Pick 8 teams",
        "selection_size": selection_size,
        "points_per_correct": Decimal("2.00"),
        "settled_at": None,
        "settled_by": None,
        "deadline_at": _DEADLINE,
        "is_open": is_open
    }


def _candidate_row(
        team_id: int,
        name: str | None = None) -> dict[str, object]:
    label = name or f"Team {team_id}"
    return {
        "team_id": team_id,
        "team_name": label,
        "team_shortcut": label[:3].upper()
    }


def _candidate_rows(extra: list[int] | None = None) -> list[dict[str, object]]:
    ids = list(_TEAM_IDS)
    if extra:
        ids.extend(extra)
    return [_candidate_row(team_id) for team_id in ids]


def _pick_rows(team_ids: list[int]) -> list[dict[str, object]]:
    return [{"team_id": team_id} for team_id in team_ids]


def _dashboard_market_row() -> dict[str, object]:
    row = _market_lock_row()
    return row


def _change_row() -> dict[str, object]:
    return {
        "id": 9,
        "market_id": _MARKET_ID,
        "user_uuid": "u-1",
        "display_name": "Ada",
        "previous_team_ids": None,
        "new_team_ids": _TEAM_CSV,
        "changed_at": _CHANGED_AT
    }


class TestSaveLongTermPicks(unittest.TestCase):
    """Atomic replace of eight teams plus CSV audit; identical set is no-op."""

    def _save(
            self,
            mock_get_conn: MagicMock,
            *,
            team_ids: list[int] | None = None,
            current_ids: list[int] | None = None,
            candidates: list[dict[str, object]] | None = None,
            is_open: int = 1,
            rowcount: int = 8
            ) -> tuple[MagicMock, MagicMock, dict[str, object]]:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row(is_open=is_open)],
            fetchall_results=[
                candidates if candidates is not None else _candidate_rows(),
                _pick_rows(current_ids or [])],
            rowcount=rowcount)
        result = repo.save_long_term_picks(
            _USER_ID, _MARKET_ID, team_ids or list(_TEAM_IDS))
        return conn, cursor, result

    @patch(_GET_CONN)
    def test_first_save_replaces_picks_and_writes_audit(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor, result = self._save(mock_get_conn, current_ids=[])
        self.assertTrue(result["audit_written"])
        self.assertIsNone(result["previous_team_ids"])
        self.assertEqual(result["team_ids"], list(_TEAM_IDS))
        statements = _sql_statements(cursor)
        self.assertTrue(
            any("FOR UPDATE" in sql for sql in statements))
        self.assertTrue(
            any("NOW() <" in sql and "MIN(" in sql for sql in statements))
        delete_sql = next(
            sql for sql in statements
            if "DELETE FROM typer_long_term_picks" in sql)
        insert_sql, insert_params = next(
            (call.args[0], call.args[1])
            for call in cursor.execute.call_args_list
            if "INSERT INTO typer_long_term_picks" in call.args[0])
        audit_sql, audit_params = next(
            (call.args[0], call.args[1])
            for call in cursor.execute.call_args_list
            if "INSERT INTO typer_long_term_pick_changes" in call.args[0])
        self.assertIn("DELETE FROM typer_long_term_picks", delete_sql)
        self.assertIn("NOW() <", insert_sql)
        self.assertEqual(
            insert_params,
            (_MARKET_ID, _USER_ID, *_TEAM_IDS, _MARKET_ID))
        self.assertEqual(
            audit_params,
            (_MARKET_ID, _USER_ID, _USER_ID, None, _TEAM_CSV))
        self.assertNotIn(" ", audit_params[-1])
        _assert_long_term_table_names(self, insert_sql)
        _assert_long_term_table_names(self, audit_sql)
        _assert_audit_append_only(self, cursor)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    @patch(_GET_CONN)
    def test_change_rewrites_set_and_audits_previous_csv(
            self, mock_get_conn: MagicMock) -> None:
        new_ids = [12, 45, 101, 200, 201, 202, 203, 205]
        new_csv = "12,45,101,200,201,202,203,205"
        conn, cursor, result = self._save(
            mock_get_conn,
            team_ids=new_ids,
            current_ids=list(_TEAM_IDS),
            candidates=_candidate_rows([205]))
        self.assertTrue(result["audit_written"])
        self.assertEqual(result["previous_team_ids"], list(_TEAM_IDS))
        audit_params = next(
            call.args[1]
            for call in cursor.execute.call_args_list
            if "INSERT INTO typer_long_term_pick_changes" in call.args[0])
        self.assertEqual(
            audit_params,
            (_MARKET_ID, _USER_ID, _USER_ID, _TEAM_CSV, new_csv))
        conn.commit.assert_called_once()

    @patch(_GET_CONN)
    def test_identical_set_is_noop_without_audit(
            self, mock_get_conn: MagicMock) -> None:
        reversed_ids = list(reversed(_TEAM_IDS))
        conn, cursor, result = self._save(
            mock_get_conn,
            team_ids=reversed_ids,
            current_ids=list(_TEAM_IDS))
        self.assertFalse(result["audit_written"])
        self.assertEqual(result["team_ids"], list(_TEAM_IDS))
        combined = _combined_sql(cursor)
        self.assertNotIn(
            "INSERT INTO typer_long_term_pick_changes", combined)
        self.assertNotIn("DELETE FROM typer_long_term_picks", combined)
        self.assertNotIn("INSERT INTO typer_long_term_picks", combined)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    @patch(_GET_CONN)
    def test_seven_teams_are_rejected(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row()])
        with self.assertRaises(repo.TyperValidationError):
            repo.save_long_term_picks(
                _USER_ID, _MARKET_ID, _TEAM_IDS[:7])
        combined = _combined_sql(cursor)
        self.assertNotIn("INSERT INTO typer_long_term_picks", combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_nine_teams_are_rejected(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row()])
        with self.assertRaises(repo.TyperValidationError):
            repo.save_long_term_picks(
                _USER_ID, _MARKET_ID, _TEAM_IDS + [205])
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    def test_duplicate_team_ids_rejected_before_sql(self) -> None:
        with self.assertRaises(repo.TyperValidationError):
            repo.save_long_term_picks(
                _USER_ID, _MARKET_ID, _TEAM_IDS[:7] + [_TEAM_IDS[0]])

    def test_empty_set_rejected_before_sql(self) -> None:
        with self.assertRaises(repo.TyperValidationError):
            repo.save_long_term_picks(_USER_ID, _MARKET_ID, [])

    @patch(_GET_CONN)
    def test_team_outside_league_phase_is_rejected(
            self, mock_get_conn: MagicMock) -> None:
        outsider = [12, 45, 101, 200, 201, 202, 203, 999]
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row()],
            fetchall_results=[_candidate_rows()])
        with self.assertRaises(repo.TyperValidationError):
            repo.save_long_term_picks(
                _USER_ID, _MARKET_ID, outsider)
        combined = _combined_sql(cursor)
        self.assertIn("home_team", combined)
        self.assertIn("away_team", combined)
        self.assertIn("BETWEEN 1", combined)
        self.assertNotIn("INSERT INTO typer_long_term_picks", combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_deadline_conflict_does_not_write(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row(is_open=0)])
        with self.assertRaises(repo.TyperConflictError):
            repo.save_long_term_picks(
                _USER_ID, _MARKET_ID, list(_TEAM_IDS))
        combined = _combined_sql(cursor)
        self.assertNotIn("INSERT INTO", combined)
        self.assertNotIn("DELETE FROM", combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_insert_rowcount_zero_is_deadline_conflict(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row()],
            fetchall_results=[_candidate_rows(), []],
            rowcount=0)
        with self.assertRaises(repo.TyperConflictError):
            repo.save_long_term_picks(
                _USER_ID, _MARKET_ID, list(_TEAM_IDS))
        combined = _combined_sql(cursor)
        self.assertIn("INSERT INTO typer_long_term_picks", combined)
        self.assertNotIn(
            "INSERT INTO typer_long_term_pick_changes", combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_integrity_error_rolls_back_without_commit(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row()],
            fetchall_results=[_candidate_rows(), []])
        cursor.execute.side_effect = [
            None,
            None,
            None,
            None,
            IntegrityError("Duplicate entry", 1062)]
        with self.assertRaises(repo.TyperConflictError):
            repo.save_long_term_picks(
                _USER_ID, _MARKET_ID, list(_TEAM_IDS))
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_lock_query_uses_now_min_and_for_update(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor, _result = self._save(
            mock_get_conn, current_ids=list(_TEAM_IDS))
        lock_sql, lock_params = cursor.execute.call_args_list[0].args
        self.assertIn("FROM typer_long_term_markets m", lock_sql)
        self.assertIn("FOR UPDATE", lock_sql)
        self.assertNotIn("JOIN matches", lock_sql)
        self.assertIn("NOW() <", lock_sql)
        self.assertIn("MIN(mt.game_date)", lock_sql)
        self.assertEqual(
            lock_params, (_MARKET_ID, repo.CHAMPIONS_LEAGUE_ID))
        self.assertIn("m.league_id = %s", lock_sql)
        _assert_no_inlined_values(
            self, lock_sql, _MARKET_ID, _USER_ID, repo.CHAMPIONS_LEAGUE_ID)
        _assert_long_term_table_names(self, lock_sql)

    @patch(_GET_CONN)
    def test_candidate_query_uses_market_league_not_hardcoded_cl(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor, _result = self._save(mock_get_conn)
        candidate_sql, candidate_params = cursor.execute.call_args_list[1].args
        self.assertIn("m.home_team", candidate_sql)
        self.assertIn("m.away_team", candidate_sql)
        self.assertIn("m.league = %s", candidate_sql)
        self.assertNotIn("m.league = 42", candidate_sql)
        self.assertEqual(
            candidate_params,
            (
                repo.CHAMPIONS_LEAGUE_ID,
                _SEASON_ID,
                repo.CHAMPIONS_LEAGUE_ID,
                _SEASON_ID))
        _assert_no_inlined_values(
            self, candidate_sql, _MARKET_ID, _USER_ID, _SEASON_ID)


class TestFetchLongTermDashboard(unittest.TestCase):
    """Dashboard lists candidates and only the caller's picks."""

    @patch(_GET_CONN)
    def test_picks_are_user_scoped_and_results_are_readable(
            self, mock_get_conn: MagicMock) -> None:
        pick_row = {"market_id": _MARKET_ID, "team_id": 12}
        result_row = {"market_id": _MARKET_ID, "team_id": 45}
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchall_results=[
                [_dashboard_market_row()],
                _candidate_rows(),
                [pick_row],
                [result_row],
                [_change_row()]])
        document = repo.fetch_long_term_dashboard(_USER_ID, _SEASON_ID)
        self.assertEqual(document["season_id"], _SEASON_ID)
        market = document["markets"][0]
        self.assertEqual(market["picked_team_ids"], [12])
        self.assertEqual(market["result_team_ids"], [45])
        self.assertEqual(len(market["candidates"]), 8)
        self.assertFalse(market["is_locked"])
        self.assertEqual(market["points_per_correct"], 2.0)
        self.assertEqual(len(document["changes"]), 1)
        self.assertIsNone(document["changes"][0]["previous_team_ids"])
        self.assertEqual(document["changes"][0]["new_team_ids"], _TEAM_IDS)
        picks_sql, picks_params = cursor.execute.call_args_list[3].args
        history_sql, history_params = cursor.execute.call_args_list[5].args
        self.assertIn("FROM typer_long_term_picks", picks_sql)
        self.assertIn("user_id = %s", picks_sql)
        self.assertEqual(picks_params[0], _USER_ID)
        self.assertIn("c.user_id = %s", history_sql)
        self.assertEqual(history_params[0], _USER_ID)
        _assert_long_term_table_names(self, picks_sql)
        _assert_no_inlined_values(self, picks_sql, _USER_ID, _MARKET_ID)

    @patch(_GET_CONN)
    def test_markets_are_scoped_to_champions_league(
            self, mock_get_conn: MagicMock) -> None:
        foreign_league_id = 7
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_long_term_dashboard(_USER_ID, _SEASON_ID)
        markets_sql, markets_params = cursor.execute.call_args_list[1].args
        self.assertIn("m.league_id = %s", markets_sql)
        self.assertIn("m.season_id = %s", markets_sql)
        self.assertNotIn(f"m.league_id = {foreign_league_id}", markets_sql)
        self.assertEqual(
            markets_params, (_SEASON_ID, repo.CHAMPIONS_LEAGUE_ID))
        self.assertNotIn(foreign_league_id, markets_params)
        _assert_no_inlined_values(
            self, markets_sql, _SEASON_ID, repo.CHAMPIONS_LEAGUE_ID)

    @patch(_GET_CONN)
    def test_none_season_uses_league_current_season(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[{"current_season_id": _SEASON_ID}],
            fetchall_results=[[]])
        document = repo.fetch_long_term_dashboard(_USER_ID, None)
        self.assertEqual(document["season_id"], _SEASON_ID)
        self.assertEqual(document["markets"], [])
        self.assertEqual(document["changes"], [])
        season_sql, season_params = cursor.execute.call_args_list[0].args
        self.assertIn("current_season_id", season_sql)
        self.assertIn("FROM leagues", season_sql)
        self.assertEqual(season_params, (repo.CHAMPIONS_LEAGUE_ID,))
        markets_params = cursor.execute.call_args_list[1].args[1]
        self.assertEqual(
            markets_params, (_SEASON_ID, repo.CHAMPIONS_LEAGUE_ID))

    @patch(_GET_CONN)
    def test_empty_markets_skip_in_queries(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        document = repo.fetch_long_term_dashboard(_USER_ID, _SEASON_ID)
        self.assertEqual(document["markets"], [])
        combined = _combined_sql(cursor)
        self.assertNotIn("IN ()", combined)
        self.assertNotIn("FROM typer_long_term_picks", combined)


class TestLongTermHistory(unittest.TestCase):
    """Own history is user-scoped; admin history filters by public UUID."""

    @patch(_GET_CONN)
    def test_own_history_filters_user_and_market(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_own_long_term_history(_USER_ID, _MARKET_ID)
        require_sql, require_params = cursor.execute.call_args_list[0].args
        self.assertIn("league_id = %s", require_sql)
        self.assertEqual(
            require_params, (_MARKET_ID, repo.CHAMPIONS_LEAGUE_ID))
        query, params = cursor.execute.call_args_list[-1].args
        self.assertIn("c.user_id = %s", query)
        self.assertIn("c.market_id = %s", query)
        self.assertIn("typer_long_term_pick_changes", query)
        self.assertEqual(params, (_USER_ID, _MARKET_ID))
        _assert_no_inlined_values(self, query, _USER_ID, _MARKET_ID)
        _assert_long_term_table_names(self, query)
        _assert_audit_append_only(self, cursor)

    @patch(_GET_CONN)
    def test_own_history_missing_market_is_not_found(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, fetchone_results=[None])
        with self.assertRaises(repo.TyperNotFoundError):
            repo.fetch_own_long_term_history(_USER_ID, _MARKET_ID)
        combined = _combined_sql(cursor)
        self.assertNotIn("typer_long_term_pick_changes", combined)

    @patch(_GET_CONN)
    def test_admin_history_filters_uuid_market_and_season(
            self, mock_get_conn: MagicMock) -> None:
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_admin_long_term_history(
            "u-1", market_id=_MARKET_ID, season_id=_SEASON_ID)
        query, params = cursor.execute.call_args_list[-1].args
        self.assertIn("u.uuid = %s", query)
        self.assertIn("c.market_id = %s", query)
        self.assertIn("m.season_id = %s", query)
        self.assertIn("m.league_id = %s", query)
        self.assertEqual(
            params,
            ("u-1", repo.CHAMPIONS_LEAGUE_ID, _MARKET_ID, _SEASON_ID))
        self.assertNotIn("UPDATE", query)
        self.assertNotIn("DELETE", query)
        _assert_long_term_table_names(self, query)

    @patch(_GET_CONN)
    def test_admin_history_season_excludes_other_leagues(
            self, mock_get_conn: MagicMock) -> None:
        foreign_league_id = 7
        _conn, cursor = _mock_connection(
            mock_get_conn, fetchall_results=[[]])
        repo.fetch_admin_long_term_history("u-1", season_id=_SEASON_ID)
        query, params = cursor.execute.call_args_list[-1].args
        self.assertIn("JOIN typer_long_term_markets m", query)
        self.assertIn("m.league_id = %s", query)
        self.assertIn("m.season_id = %s", query)
        self.assertNotIn(f"m.league_id = {foreign_league_id}", query)
        self.assertEqual(
            params, ("u-1", repo.CHAMPIONS_LEAGUE_ID, _SEASON_ID))
        self.assertNotIn(foreign_league_id, params)
        _assert_no_inlined_values(
            self, query, "u-1", repo.CHAMPIONS_LEAGUE_ID, _SEASON_ID)

    def test_admin_history_requires_uuid(self) -> None:
        with self.assertRaises(repo.TyperValidationError):
            repo.fetch_admin_long_term_history("  ")


class TestTeamIdsCsv(unittest.TestCase):
    """CSV snapshots are sorted, unique-order-insensitive and space-free."""

    def test_sorted_csv_without_spaces(self) -> None:
        csv = repo._team_ids_csv([101, 12, 45])
        self.assertEqual(csv, "12,45,101")
        self.assertNotIn(" ", csv)

    def test_parse_round_trip(self) -> None:
        self.assertEqual(
            repo._parse_team_ids_csv(_TEAM_CSV), list(_TEAM_IDS))
        self.assertIsNone(repo._parse_team_ids_csv(None))


_ADMIN_ID = 7
_SETTLED_AT = datetime(2026, 12, 1, 23, 0)


def _standing_row(
        team_id: int,
        *,
        played: int = 8,
        points: int = 12,
        goal_difference: int = 4,
        goals_for: int = 20) -> dict[str, object]:
    return {
        "team_id": team_id,
        "team_name": f"Team {team_id}",
        "team_shortcut": f"T{team_id}",
        "played": played,
        "points": points,
        "goal_difference": goal_difference,
        "goals_for": goals_for
    }


def _settled_market_row() -> dict[str, object]:
    row = _market_lock_row(is_open=0)
    row["settled_at"] = _SETTLED_AT
    row["settled_by"] = _ADMIN_ID
    return row


class TestFetchAutoResult(unittest.TestCase):
    """Auto TOP 8 is a read-only proposal from points, GD and goals."""

    @patch(_GET_CONN)
    def test_standings_sql_sorts_points_gd_goals_and_does_not_write(
            self, mock_get_conn: MagicMock) -> None:
        standings = [
            _standing_row(12, points=20, goal_difference=10, goals_for=30),
            _standing_row(45, points=20, goal_difference=10, goals_for=28)]
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row()],
            fetchall_results=[standings, []])
        document = repo.fetch_auto_result(_MARKET_ID)
        self.assertEqual(document["market_id"], _MARKET_ID)
        self.assertEqual(document["participant_count"], 2)
        self.assertEqual(document["settled_match_count"], 8)
        self.assertEqual(document["min_matches_per_team"], 8)
        self.assertEqual(document["max_matches_per_team"], 8)
        self.assertEqual(document["standings"][0]["team_id"], 12)
        self.assertEqual(document["result_team_ids"], [])
        self.assertIsNone(document["settled_at"])
        market_sql = cursor.execute.call_args_list[0].args[0]
        self.assertNotIn("FOR UPDATE", market_sql)
        query, params = cursor.execute.call_args_list[1].args
        self.assertIn("ORDER BY", query)
        self.assertIn("s.points, 0) DESC", query)
        self.assertIn("s.goal_difference, 0) DESC", query)
        self.assertIn("s.goals_for, 0) DESC", query)
        self.assertIn("BETWEEN 1", query)
        self.assertIn("result IN ('1', 'X', '2')", query)
        self.assertEqual(
            params, (repo.CHAMPIONS_LEAGUE_ID, _SEASON_ID))
        combined = _combined_sql(cursor)
        self.assertNotIn("INSERT INTO typer_long_term_results", combined)
        self.assertNotIn("UPDATE typer_long_term_markets", combined)
        self.assertNotIn("DELETE FROM typer_long_term_results", combined)
        conn.commit.assert_not_called()
        _assert_no_inlined_values(
            self, query, _MARKET_ID, _SEASON_ID, repo.CHAMPIONS_LEAGUE_ID)
        _assert_long_term_table_names(
            self, cursor.execute.call_args_list[0].args[0])
        results_sql = cursor.execute.call_args_list[2].args[0]
        self.assertIn("FROM typer_long_term_results", results_sql)
        _assert_long_term_table_names(self, results_sql)

    @patch(_GET_CONN)
    def test_includes_approved_result_ids_when_settled(
            self, mock_get_conn: MagicMock) -> None:
        standings = [_standing_row(team_id) for team_id in _TEAM_IDS]
        result_rows = [
            {"market_id": _MARKET_ID, "team_id": team_id}
            for team_id in _TEAM_IDS]
        _mock_connection(
            mock_get_conn,
            fetchone_results=[_settled_market_row()],
            fetchall_results=[standings, result_rows])
        document = repo.fetch_auto_result(_MARKET_ID)
        self.assertEqual(document["result_team_ids"], list(_TEAM_IDS))
        self.assertEqual(document["settled_by"], _ADMIN_ID)

    @patch(_GET_CONN)
    def test_missing_market_is_not_found(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn, fetchone_results=[None])
        with self.assertRaises(repo.TyperNotFoundError):
            repo.fetch_auto_result(_MARKET_ID)
        combined = _combined_sql(cursor)
        self.assertNotIn("phase_matches", combined)
        conn.commit.assert_not_called()


class TestSettleMarket(unittest.TestCase):
    """Admin settlement replaces results without touching stored picks."""

    def _settle(
            self,
            mock_get_conn: MagicMock,
            *,
            team_ids: list[int] | None = None,
            candidates: list[dict[str, object]] | None = None,
            is_open: int = 0,
            rowcount: int = 8
            ) -> tuple[MagicMock, MagicMock, dict[str, object]]:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[
                _market_lock_row(is_open=is_open),
                _settled_market_row()],
            fetchall_results=[
                candidates if candidates is not None else _candidate_rows()],
            rowcount=rowcount)
        result = repo.settle_market(
            _MARKET_ID, team_ids or list(_TEAM_IDS), _ADMIN_ID)
        return conn, cursor, result

    @patch(_GET_CONN)
    def test_replaces_results_and_stamps_market_after_deadline(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor, result = self._settle(mock_get_conn)
        self.assertEqual(result["team_ids"], list(_TEAM_IDS))
        self.assertEqual(result["settled_by"], _ADMIN_ID)
        self.assertEqual(result["settled_at"], _SETTLED_AT)
        statements = _sql_statements(cursor)
        self.assertTrue(
            any("FOR UPDATE" in sql for sql in statements))
        delete_sql = next(
            sql for sql in statements
            if "DELETE FROM typer_long_term_results" in sql)
        insert_sql, insert_params = next(
            (call.args[0], call.args[1])
            for call in cursor.execute.call_args_list
            if "INSERT INTO typer_long_term_results" in call.args[0])
        update_sql, update_params = next(
            (call.args[0], call.args[1])
            for call in cursor.execute.call_args_list
            if "UPDATE typer_long_term_markets" in call.args[0])
        self.assertIn("DELETE FROM typer_long_term_results", delete_sql)
        self.assertEqual(
            insert_params, (_MARKET_ID, *_TEAM_IDS))
        self.assertEqual(
            update_params,
            (_ADMIN_ID, _MARKET_ID, repo.CHAMPIONS_LEAGUE_ID))
        self.assertIn("settled_at = NOW()", update_sql)
        combined = _combined_sql(cursor)
        self.assertNotIn("DELETE FROM typer_long_term_picks", combined)
        self.assertNotIn("INSERT INTO typer_long_term_picks", combined)
        self.assertNotIn(
            "INSERT INTO typer_long_term_pick_changes", combined)
        _assert_long_term_table_names(self, insert_sql)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    @patch(_GET_CONN)
    def test_correction_deletes_previous_results(
            self, mock_get_conn: MagicMock) -> None:
        new_ids = [12, 45, 101, 200, 201, 202, 203, 205]
        conn, cursor, result = self._settle(
            mock_get_conn,
            team_ids=new_ids,
            candidates=_candidate_rows([205]))
        self.assertEqual(result["team_ids"], new_ids)
        combined = _combined_sql(cursor)
        self.assertIn("DELETE FROM typer_long_term_results", combined)
        self.assertIn("INSERT INTO typer_long_term_results", combined)
        self.assertNotIn("DELETE FROM typer_long_term_picks", combined)
        conn.commit.assert_called_once()

    @patch(_GET_CONN)
    def test_seven_teams_are_rejected(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row(is_open=0)])
        with self.assertRaises(repo.TyperValidationError):
            repo.settle_market(_MARKET_ID, _TEAM_IDS[:7], _ADMIN_ID)
        combined = _combined_sql(cursor)
        self.assertNotIn("INSERT INTO typer_long_term_results", combined)
        self.assertNotIn("UPDATE typer_long_term_markets", combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_team_outside_league_phase_is_rejected(
            self, mock_get_conn: MagicMock) -> None:
        outsider = [12, 45, 101, 200, 201, 202, 203, 999]
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row(is_open=0)],
            fetchall_results=[_candidate_rows()])
        with self.assertRaises(repo.TyperValidationError):
            repo.settle_market(_MARKET_ID, outsider, _ADMIN_ID)
        combined = _combined_sql(cursor)
        self.assertNotIn("INSERT INTO typer_long_term_results", combined)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()

    @patch(_GET_CONN)
    def test_integrity_error_rolls_back_without_commit(
            self, mock_get_conn: MagicMock) -> None:
        conn, cursor = _mock_connection(
            mock_get_conn,
            fetchone_results=[_market_lock_row(is_open=0)],
            fetchall_results=[_candidate_rows()])
        cursor.execute.side_effect = [
            None,
            None,
            None,
            IntegrityError("Duplicate entry", 1062)]
        with self.assertRaises(repo.TyperConflictError):
            repo.settle_market(
                _MARKET_ID, list(_TEAM_IDS), _ADMIN_ID)
        conn.commit.assert_not_called()
        conn.rollback.assert_called()


if __name__ == "__main__":
    unittest.main()
