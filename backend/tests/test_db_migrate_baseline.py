"""Tests for V001 baseline rendering. No database connection."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from backend.db_migrate.baseline import load_schema_objects
from backend.db_migrate.baseline import render_baseline_sql
from backend.db_migrate.baseline import rewrite_table_ddl
from backend.db_migrate.baseline import rewrite_view_ddl
from backend.db_migrate.baseline import write_baseline_file
from backend.db_migrate.errors import MigrationError
from backend.db_migrate.sql_script import split_sql_script


_TABLE_SHOW_CREATE = (
    "CREATE TABLE `teams` (\n"
    "  `id` int NOT NULL AUTO_INCREMENT,\n"
    "  PRIMARY KEY (`id`)\n"
    ") ENGINE=InnoDB AUTO_INCREMENT=41")
_VIEW_SHOW_CREATE = (
    "CREATE ALGORITHM=UNDEFINED "
    "DEFINER=`root`@`localhost` "
    "SQL SECURITY DEFINER "
    "VIEW `matches_pretty_print` AS "
    "select `m`.`id` AS `id` from `matches` `m`")


class TestRewriteTableDdl(unittest.TestCase):
    """SHOW CREATE TABLE becomes safe to repeat on an empty database."""

    def test_adds_if_not_exists_and_keeps_the_rest(self) -> None:
        rewritten = rewrite_table_ddl(_TABLE_SHOW_CREATE)
        prefix = "CREATE TABLE IF NOT EXISTS "
        self.assertTrue(rewritten.startswith(prefix))
        self.assertEqual(
            rewritten.removeprefix(prefix),
            _TABLE_SHOW_CREATE.removeprefix("CREATE TABLE "))
        self.assertIn("AUTO_INCREMENT=41", rewritten)
        self.assertIn("PRIMARY KEY (`id`)", rewritten)

    def test_unexpected_prefix_raises(self) -> None:
        with self.assertRaises(MigrationError) as caught:
            rewrite_table_ddl("CREATE VIEW `teams` AS select 1")
        self.assertEqual(
            str(caught.exception),
            "Unexpected SHOW CREATE TABLE output")


class TestRewriteViewDdl(unittest.TestCase):
    """DEFINER from SHOW CREATE VIEW does not enter the file."""

    def test_invoker_security_and_no_definer(self) -> None:
        rewritten = rewrite_view_ddl(
            "matches_pretty_print",
            _VIEW_SHOW_CREATE)
        self.assertIn("SQL SECURITY INVOKER", rewritten)
        self.assertNotIn("DEFINER", rewritten)
        self.assertTrue(rewritten.startswith(
            "CREATE OR REPLACE SQL SECURITY INVOKER "
            "VIEW `matches_pretty_print` AS "))
        self.assertTrue(rewritten.endswith(
            "AS select `m`.`id` AS `id` from `matches` `m`"))

    def test_missing_as_marker_raises(self) -> None:
        with self.assertRaises(MigrationError) as caught:
            rewrite_view_ddl("matches_pretty_print", "CREATE VIEW only")
        self.assertEqual(
            str(caught.exception),
            "Unexpected SHOW CREATE VIEW output")


class TestRenderBaselineSql(unittest.TestCase):
    """Header, foreign-key toggles, tables, then views."""

    def test_checks_order_and_no_data_statements(self) -> None:
        sql = render_baseline_sql(
            [("teams", _TABLE_SHOW_CREATE)],
            [("matches_pretty_print", _VIEW_SHOW_CREATE)])
        checks_off = sql.index("SET FOREIGN_KEY_CHECKS = 0")
        table_at = sql.index("CREATE TABLE IF NOT EXISTS")
        view_at = sql.index("VIEW `matches_pretty_print`")
        checks_on = sql.index("SET FOREIGN_KEY_CHECKS = 1")
        self.assertLess(checks_off, table_at)
        self.assertLess(table_at, view_at)
        self.assertLess(view_at, checks_on)
        upper = sql.upper()
        self.assertNotIn("INSERT", upper)
        self.assertNotIn("DROP", upper)
        self.assertNotIn("DEFINER", sql)
        self.assertNotIn("\r", sql)
        self.assertTrue(sql.endswith("\n"))
        lines = sql.splitlines()
        self.assertTrue(lines[0].startswith("--"))
        self.assertTrue(lines[1].startswith("--"))
        statements = split_sql_script(sql)
        self.assertEqual(statements[0], "SET FOREIGN_KEY_CHECKS = 0")
        self.assertEqual(statements[-1], "SET FOREIGN_KEY_CHECKS = 1")
        self.assertEqual(len(statements), 4)
        self.assertIn("CREATE TABLE IF NOT EXISTS `teams`", statements[1])

    def test_comment_semicolon_is_one_statement(self) -> None:
        show_create = (
            "CREATE TABLE `prefs` (\n"
            "  `updated_at` datetime NOT NULL COMMENT 'a; b',\n"
            "  PRIMARY KEY (`updated_at`)\n"
            ") ENGINE=InnoDB COMMENT='a; b'")
        sql = render_baseline_sql([("prefs", show_create)], [])
        statements = split_sql_script(sql)
        creates = [
            item for item in statements
            if item.startswith("CREATE TABLE IF NOT EXISTS")]
        self.assertEqual(len(creates), 1)
        self.assertIn("COMMENT 'a; b'", creates[0])
        self.assertIn("COMMENT='a; b'", creates[0])


class TestWriteBaselineFile(unittest.TestCase):
    """Existing destination stays byte for byte."""

    def test_existing_file_raises_and_keeps_bytes(self) -> None:
        original = b"keep-me\r\n"
        with TemporaryDirectory() as raw:
            destination = Path(raw) / "V001__baseline.sql"
            destination.write_bytes(original)
            with self.assertRaises(MigrationError) as caught:
                write_baseline_file("new;\n", destination)
            self.assertEqual(
                str(caught.exception),
                "Baseline file already exists")
            self.assertEqual(destination.read_bytes(), original)

    def test_creates_parent_and_writes_lf(self) -> None:
        with TemporaryDirectory() as raw:
            destination = Path(raw) / "migrations" / "V001__baseline.sql"
            write_baseline_file("SET a = 1;\n", destination)
            self.assertEqual(destination.read_bytes(), b"SET a = 1;\n")


class _Cursor:
    """information_schema rows, then SHOW CREATE column 1."""

    def __init__(
            self,
            rows: list[tuple[str, str]],
            creates: dict[str, str]) -> None:
        self.statements: list[str] = []
        self.closed = False
        self._rows = rows
        self._creates = creates
        self._pending_all: list[tuple[Any, ...]] = []
        self._pending_one: tuple[Any, ...] | None = None

    def execute(
            self,
            statement: str,
            params: tuple[Any, ...] | None = None) -> None:
        if params is not None:
            raise AssertionError(params)
        self.statements.append(statement)
        if "information_schema" in statement:
            self._pending_all = list(self._rows)
            self._pending_one = None
            return
        if statement.startswith("SHOW CREATE TABLE `") and (
                statement.endswith("`")):
            name = statement[len("SHOW CREATE TABLE `"):-1]
            ddl = self._creates[name]
            self._pending_one = ("not-the-ddl", ddl, "utf8mb4")
            self._pending_all = []
            return
        raise AssertionError(statement)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._pending_all)

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._pending_one

    def close(self) -> None:
        self.closed = True


class _Connection:
    """Hands out one fake cursor."""

    def __init__(self, cursor: _Cursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _Cursor:
        return self._cursor


class TestLoadSchemaObjects(unittest.TestCase):
    """Fake cursor: one table, one view, ledger row ignored."""

    def test_skips_ledger_and_reads_show_create_column(self) -> None:
        cursor = _Cursor(
            rows=[
                ("schema_migrations", "BASE TABLE"),
                ("teams", "BASE TABLE"),
                ("matches_pretty_print", "VIEW")],
            creates={
                "teams": _TABLE_SHOW_CREATE,
                "matches_pretty_print": _VIEW_SHOW_CREATE})
        tables, views = load_schema_objects(_Connection(cursor))
        self.assertEqual(tables, [("teams", _TABLE_SHOW_CREATE)])
        self.assertEqual(
            views,
            [("matches_pretty_print", _VIEW_SHOW_CREATE)])
        show_sql = [
            statement for statement in cursor.statements
            if statement.startswith("SHOW CREATE")]
        self.assertEqual(show_sql, [
            "SHOW CREATE TABLE `teams`",
            "SHOW CREATE TABLE `matches_pretty_print`"])
        self.assertTrue(cursor.closed)

    def test_ledger_only_raises_no_tables(self) -> None:
        cursor = _Cursor(
            rows=[("schema_migrations", "BASE TABLE")],
            creates={})
        with self.assertRaises(MigrationError) as caught:
            load_schema_objects(_Connection(cursor))
        self.assertEqual(str(caught.exception), "No tables found")
        self.assertTrue(cursor.closed)
        self.assertFalse(any(
            statement.startswith("SHOW CREATE")
            for statement in cursor.statements))

    def test_unsupported_identifier_raises(self) -> None:
        cursor = _Cursor(
            rows=[("bad-name", "BASE TABLE")],
            creates={})
        with self.assertRaises(MigrationError) as caught:
            load_schema_objects(_Connection(cursor))
        self.assertEqual(str(caught.exception), "Unsupported identifier")
        self.assertFalse(any(
            statement.startswith("SHOW CREATE")
            for statement in cursor.statements))


if __name__ == "__main__":
    unittest.main()
