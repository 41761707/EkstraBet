"""Tests for splitting and executing migration SQL scripts."""

from __future__ import annotations

import unittest

from mysql.connector.errors import Error as MySQLError

from backend.db_migrate.errors import MigrationError
from backend.db_migrate.errors import MigrationSqlError
from backend.db_migrate.sql_script import execute_statements
from backend.db_migrate.sql_script import split_sql_script


class _StoppingCursor:
    """Records statements and fails on a chosen 1-based call."""

    def __init__(self, fail_at: int, message: str) -> None:
        self.calls: list[str] = []
        self._fail_at = fail_at
        self._message = message

    def execute(self, statement: str) -> None:
        self.calls.append(statement)
        if len(self.calls) == self._fail_at:
            raise MySQLError(self._message)


class TestSplitSqlScript(unittest.TestCase):
    """Line-oriented statement splitting."""

    def test_comment_separates_two_statements(self) -> None:
        script = "SELECT 1;\n-- between\n\nSELECT 2;\n"
        self.assertEqual(split_sql_script(script), ["SELECT 1", "SELECT 2"])

    def test_multiline_statement_is_joined_with_spaces(self) -> None:
        script = "CREATE TABLE teams (\n    id INT\n);\n"
        self.assertEqual(
            split_sql_script(script),
            ["CREATE TABLE teams ( id INT )"])

    def test_empty_statement_is_skipped(self) -> None:
        script = ";\nSELECT 1;\n;\n"
        self.assertEqual(split_sql_script(script), ["SELECT 1"])

    def test_semicolon_inside_a_line_raises(self) -> None:
        script = "SELECT 1; SELECT 2;\n"
        with self.assertRaises(MigrationError) as caught:
            split_sql_script(script)
        self.assertEqual(
            str(caught.exception),
            "Semicolon is allowed only at the end of a line")
        self.assertNotIsInstance(caught.exception, MigrationSqlError)

    def test_missing_closing_semicolon_raises(self) -> None:
        script = "SELECT 1;\nSELECT 2\n"
        with self.assertRaises(MigrationError) as caught:
            split_sql_script(script)
        self.assertEqual(
            str(caught.exception),
            "Migration script ended without a semicolon")


class TestExecuteStatements(unittest.TestCase):
    """MySQL errors stop the remaining statements."""

    def test_second_failure_does_not_run_the_third(self) -> None:
        cursor = _StoppingCursor(fail_at=2, message="syntax error")
        statements = ["SELECT 1", "SELECT 2", "SELECT 3"]
        with self.assertRaises(MigrationSqlError) as caught:
            execute_statements(cursor, statements)
        self.assertEqual(caught.exception.index, 2)
        self.assertEqual(caught.exception.detail, "syntax error")
        self.assertEqual(cursor.calls, ["SELECT 1", "SELECT 2"])


if __name__ == "__main__":
    unittest.main()
