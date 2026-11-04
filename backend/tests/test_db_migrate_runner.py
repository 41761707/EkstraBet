"""Tests for migration status, apply and baseline on a fake connection."""

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from mysql.connector.errors import Error as MySQLError

from backend.db_migrate.errors import MigrationError
from backend.db_migrate.errors import MigrationSqlError
from backend.db_migrate.files import file_checksum
from backend.db_migrate.runner import MigrationRunner
from backend.db_migrate.runner import MigrationStatus


_TEAMS_SQL = "CREATE TABLE teams (\n    id INT\n);\n"
_PLAYERS_SQL = "CREATE TABLE players (\n    id INT\n);\n"
_BOTH_SQL = _TEAMS_SQL + _PLAYERS_SQL
_APPLIED_AT = datetime(2026, 1, 1)
_EXISTING_TABLES_MESSAGE = (
    "V001 is pending but tables already exist. "
    "On an existing EkstraBet database run baseline. "
    "On a failed fresh install, drop the database and apply again.")


class _Store:
    """Shared ledger and the SQL text sent by every cursor."""

    def __init__(self) -> None:
        self.ledger_exists = False
        self.business_tables = 0
        self.rows: dict[str, tuple[str, str, datetime]] = {}
        self.executed: list[str] = []
        self.fail_sql_containing: str | None = None
        self.connections_closed = 0
        self.cursors_closed = 0


class _Cursor:
    """Answers ledger SQL and records statements taken from a file."""

    def __init__(self, store: _Store) -> None:
        self._store = store
        self._row: tuple[Any, ...] | None = None
        self._rows: list[tuple[Any, ...]] = []

    def execute(
            self,
            statement: str,
            params: tuple[Any, ...] | None = None) -> None:
        self._store.executed.append(statement)
        self._row = None
        self._rows = []
        if "GET_LOCK" in statement or "RELEASE_LOCK" in statement:
            self._row = (1,)
            return
        if "information_schema" in statement:
            self._read_information_schema(statement)
            return
        if statement.startswith("INSERT INTO schema_migrations"):
            self._insert_applied(params)
            return
        if statement.startswith("SELECT version"):
            self._rows = [
                (version, filename, checksum, applied_at)
                for version, (filename, checksum, applied_at)
                in self._store.rows.items()]
            return
        if statement.startswith("CREATE TABLE") and (
                "schema_migrations" in statement):
            self._store.ledger_exists = True
            return
        self._run_file_statement(statement)

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)

    def close(self) -> None:
        self._store.cursors_closed += 1

    def _read_information_schema(self, statement: str) -> None:
        if "COUNT(*)" in statement:
            self._row = (self._store.business_tables,)
            return
        if self._store.ledger_exists:
            self._row = (1,)

    def _insert_applied(self, params: tuple[Any, ...] | None) -> None:
        if params is None:
            raise AssertionError("ledger insert without parameters")
        version, filename, checksum = params
        self._store.rows[str(version)] = (
            str(filename),
            str(checksum),
            _APPLIED_AT)
        self._store.ledger_exists = True

    def _run_file_statement(self, statement: str) -> None:
        needle = self._store.fail_sql_containing
        if needle is not None and needle in statement:
            raise MySQLError("statement failed")


class _Connection:
    """Fake connection. Each cursor shares the store."""

    def __init__(self, store: _Store) -> None:
        self._store = store

    def cursor(self) -> _Cursor:
        return _Cursor(self._store)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        self._store.connections_closed += 1


class _MigrationRunnerCase(unittest.TestCase):
    """Temp migration directory and a connect factory for one store."""

    def setUp(self) -> None:
        self._temporary = TemporaryDirectory()
        self.directory = Path(self._temporary.name)
        self.store = _Store()

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def connect(self) -> _Connection:
        return _Connection(self.store)

    def runner(self) -> MigrationRunner:
        return MigrationRunner(
            migrations_dir=self.directory,
            connect=self.connect)

    def write(self, filename: str, sql: str) -> Path:
        path = self.directory / filename
        path.write_text(sql, encoding="utf-8", newline="\n")
        return path

    def seed(self, version: str, filename: str, checksum: str) -> None:
        self.store.rows[version] = (filename, checksum, _APPLIED_AT)
        self.store.ledger_exists = True

    def executed_contains(self, fragment: str) -> bool:
        return any(
            fragment in statement for statement in self.store.executed)

    def assert_closed(self, times: int = 1) -> None:
        self.assertEqual(self.store.connections_closed, times)
        self.assertEqual(self.store.cursors_closed, times)


class TestMigrationStatus(_MigrationRunnerCase):
    """status reads the ledger and does not create it."""

    def test_missing_ledger_is_pending_without_create(self) -> None:
        self.write("V001__baseline.sql", _TEAMS_SQL)
        self.write("V002__add_players.sql", _PLAYERS_SQL)
        statuses = self.runner().status()
        self.assertEqual(statuses, [
            MigrationStatus(
                "V001",
                "V001__baseline.sql",
                "pending"),
            MigrationStatus(
                "V002",
                "V002__add_players.sql",
                "pending")])
        self.assertFalse(self.executed_contains("CREATE TABLE"))
        self.assertFalse(self.executed_contains("GET_LOCK"))
        self.assert_closed()

    def test_ledger_rows_set_applied_pending_and_mismatch(self) -> None:
        baseline = self.write("V001__baseline.sql", _TEAMS_SQL)
        self.write("V002__add_players.sql", _PLAYERS_SQL)
        self.write("V003__add_view.sql", "CREATE VIEW upcoming AS SELECT 1;\n")
        self.seed("V001", baseline.name, file_checksum(baseline))
        self.seed("V002", "V002__add_players.sql", "0" * 64)
        statuses = self.runner().status()
        self.assertEqual(
            [item.state for item in statuses],
            ["applied", "checksum_mismatch", "pending"])
        self.assertFalse(self.executed_contains("CREATE TABLE"))
        self.assertFalse(self.executed_contains("GET_LOCK"))
        self.assert_closed()


class TestMigrationApply(_MigrationRunnerCase):
    """apply runs pending files or refuses an already populated database."""

    def test_empty_database_applies_v001_and_inserts_ledger_row(self) -> None:
        path = self.write("V001__baseline.sql", _TEAMS_SQL)
        self.store.business_tables = 0
        applied = self.runner().apply()
        self.assertEqual(applied, ["V001"])
        self.assertTrue(self.executed_contains("CREATE TABLE teams"))
        self.assertTrue(
            self.executed_contains("INSERT INTO schema_migrations"))
        self.assertEqual(self.store.rows["V001"][0], path.name)
        self.assertEqual(self.store.rows["V001"][1], file_checksum(path))
        self.assert_closed()

    def test_existing_tables_without_v001_require_baseline(self) -> None:
        self.write("V001__baseline.sql", _TEAMS_SQL)
        self.store.business_tables = 4
        with self.assertRaises(MigrationError) as caught:
            self.runner().apply()
        self.assertEqual(str(caught.exception), _EXISTING_TABLES_MESSAGE)
        self.assertFalse(self.executed_contains("teams"))
        self.assertFalse(
            self.executed_contains("INSERT INTO schema_migrations"))
        self.assert_closed()

    def test_second_file_runs_when_v001_is_already_applied(self) -> None:
        baseline = self.write("V001__baseline.sql", _TEAMS_SQL)
        self.write("V002__add_players.sql", _PLAYERS_SQL)
        self.seed("V001", baseline.name, file_checksum(baseline))
        self.store.business_tables = 4
        applied = self.runner().apply()
        self.assertEqual(applied, ["V002"])
        self.assertTrue(self.executed_contains("CREATE TABLE players"))
        self.assertFalse(self.executed_contains("CREATE TABLE teams"))
        self.assert_closed()

    def test_checksum_mismatch_blocks_the_next_file(self) -> None:
        path = self.write("V001__baseline.sql", _TEAMS_SQL)
        self.write("V002__add_players.sql", _PLAYERS_SQL)
        self.seed("V001", path.name, "0" * 64)
        with self.assertRaises(MigrationError) as caught:
            self.runner().apply()
        self.assertEqual(
            str(caught.exception),
            "Checksum mismatch for V001")
        self.assertFalse(self.executed_contains("players"))
        self.assertFalse(self.executed_contains("teams"))
        self.assertFalse(
            self.executed_contains("INSERT INTO schema_migrations"))
        self.assert_closed()

    def test_statement_error_does_not_record_the_version(self) -> None:
        self.write("V001__baseline.sql", _BOTH_SQL)
        self.store.fail_sql_containing = "players"
        self.store.business_tables = 0
        with self.assertRaises(MigrationSqlError) as caught:
            self.runner().apply()
        self.assertEqual(caught.exception.index, 2)
        self.assertNotIn("V001", self.store.rows)
        self.assertTrue(self.executed_contains("CREATE TABLE teams"))
        self.assertFalse(
            self.executed_contains("INSERT INTO schema_migrations"))
        self.assert_closed()


class TestMigrationBaseline(_MigrationRunnerCase):
    """baseline records V001 and does not execute the file."""

    def test_baseline_inserts_v001_without_running_the_file(self) -> None:
        path = self.write("V001__baseline.sql", _TEAMS_SQL)
        runner = self.runner()
        self.assertEqual(runner.baseline(), "baselined")
        self.assertFalse(self.executed_contains("teams"))
        self.assertTrue(
            self.executed_contains(
                "CREATE TABLE IF NOT EXISTS schema_migrations"))
        self.assertEqual(self.store.rows["V001"][0], path.name)
        self.assertEqual(self.store.rows["V001"][1], file_checksum(path))
        self.assertEqual(runner.baseline(), "already-baselined")
        self.assertEqual(list(self.store.rows), ["V001"])
        self.assertEqual(
            sum(
                statement.startswith("INSERT")
                for statement in self.store.executed),
            1)
        self.assert_closed(times=2)

    def test_later_ledger_version_is_rejected(self) -> None:
        self.write("V001__baseline.sql", _TEAMS_SQL)
        self.seed("V002", "V002__add_players.sql", "ab" * 32)
        with self.assertRaises(MigrationError) as caught:
            self.runner().baseline()
        self.assertEqual(
            str(caught.exception),
            "Cannot baseline after later migrations")
        self.assertNotIn("V001", self.store.rows)
        self.assertFalse(self.executed_contains("teams"))
        self.assert_closed()


if __name__ == "__main__":
    unittest.main()
