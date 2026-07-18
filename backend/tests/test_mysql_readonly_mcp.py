"""Tests for the read-only MySQL MCP server helpers."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from contextlib import redirect_stdout
import io
import unittest

from mcp_servers.mysql_readonly_server import IdentifierValidator
from mcp_servers.mysql_readonly_server import ReadOnlyMcpError
from mcp_servers.mysql_readonly_server import ReadOnlySqlValidator
from mcp_servers.mysql_readonly_server import ResultSerializer
from mcp_servers.mysql_readonly_server import main


class TestReadOnlySqlValidator(unittest.TestCase):
    """Unit tests for read-only SQL validation."""

    def setUp(self) -> None:
        self.validator = ReadOnlySqlValidator()

    def test_accepts_select_statement(self) -> None:
        sql = self.validator.validate("SELECT * FROM matches")

        self.assertEqual(sql, "SELECT * FROM matches")

    def test_accepts_metadata_statements(self) -> None:
        statements = [
            "SHOW TABLES",
            "DESCRIBE teams",
            "DESC teams",
            "EXPLAIN SELECT * FROM matches"
        ]

        for statement in statements:
            with self.subTest(statement=statement):
                self.assertEqual(self.validator.validate(statement), statement)

    def test_rejects_write_statements(self) -> None:
        statements = [
            "UPDATE matches SET home_score = 1",
            "DELETE FROM matches",
            "INSERT INTO teams (name) VALUES ('A')",
            "DROP TABLE teams",
            "ALTER TABLE teams ADD COLUMN x INT",
            "CREATE TABLE unsafe_table (id INT)",
            "TRUNCATE TABLE teams"
        ]

        for statement in statements:
            with self.subTest(statement=statement):
                with self.assertRaises(ReadOnlyMcpError):
                    self.validator.validate(statement)

    def test_rejects_multiple_statements(self) -> None:
        with self.assertRaises(ReadOnlyMcpError):
            self.validator.validate("SELECT 1; DROP TABLE teams")

    def test_rejects_comment_markers(self) -> None:
        with self.assertRaises(ReadOnlyMcpError):
            self.validator.validate("SELECT * FROM matches -- hide")

    def test_rejects_unsafe_select_patterns(self) -> None:
        statements = [
            "SELECT * FROM matches FOR UPDATE",
            "SELECT * FROM matches INTO OUTFILE '/tmp/data.csv'",
            "SELECT LOAD_FILE('/etc/passwd')"
        ]

        for statement in statements:
            with self.subTest(statement=statement):
                with self.assertRaises(ReadOnlyMcpError):
                    self.validator.validate(statement)

    def test_adds_limit_to_select_without_limit(self) -> None:
        sql = self.validator.apply_limit("SELECT * FROM matches", 10, 100)

        self.assertEqual(sql, "SELECT * FROM matches LIMIT 10")

    def test_keeps_existing_limit(self) -> None:
        sql = self.validator.apply_limit(
            "SELECT * FROM matches LIMIT 5",
            10,
            100)

        self.assertEqual(sql, "SELECT * FROM matches LIMIT 5")

    def test_reduces_existing_limit_above_max_rows(self) -> None:
        sql = self.validator.apply_limit(
            "SELECT * FROM matches LIMIT 5000",
            5000,
            100)

        self.assertEqual(sql, "SELECT * FROM matches LIMIT 100")

    def test_bounds_negative_limit(self) -> None:
        limit = self.validator.bounded_limit(-5, 100)

        self.assertEqual(limit, 1)

    def test_does_not_add_limit_to_show(self) -> None:
        sql = self.validator.apply_limit("SHOW TABLES", 10, 100)

        self.assertEqual(sql, "SHOW TABLES")


class TestIdentifierValidator(unittest.TestCase):
    """Unit tests for table identifier validation."""

    def setUp(self) -> None:
        self.validator = IdentifierValidator()

    def test_accepts_plain_table_name(self) -> None:
        self.assertEqual(
            self.validator.validate_table_name("teams"),
            "teams")

    def test_accepts_qualified_table_name(self) -> None:
        self.assertEqual(
            self.validator.validate_table_name("ekstrabet.teams"),
            "ekstrabet.teams")

    def test_rejects_injected_table_name(self) -> None:
        with self.assertRaises(ReadOnlyMcpError):
            self.validator.validate_table_name("teams; DROP TABLE teams")

    def test_quotes_table_name(self) -> None:
        quoted = self.validator.quote_table_name("teams", "ekstrabet")

        self.assertEqual(quoted, "`ekstrabet`.`teams`")


class TestResultSerializer(unittest.TestCase):
    """Unit tests for JSON-friendly result serialization."""

    def setUp(self) -> None:
        self.serializer = ResultSerializer()

    def test_serializes_common_mysql_values(self) -> None:
        row = {
            "created_at": datetime(2026, 7, 7, 5, 0, 0),
            "match_date": date(2026, 7, 7),
            "odds": Decimal("1.85"),
            "payload": b"abc"
        }

        serialized = self.serializer.serialize_row(row)

        self.assertEqual(serialized["created_at"], "2026-07-07T05:00:00")
        self.assertEqual(serialized["match_date"], "2026-07-07")
        self.assertEqual(serialized["odds"], "1.85")
        self.assertEqual(serialized["payload"], "YWJj")


class TestCommandLineHelp(unittest.TestCase):
    """Unit tests for command-line help handling."""

    def test_help_prints_usage(self) -> None:
        stream = io.StringIO()

        with redirect_stdout(stream):
            exit_code = main(["--help"])

        output = stream.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Usage:", output)
        self.assertIn("python mcp_servers/mysql_readonly_server.py", output)
        self.assertIn("Available tools:", output)


if __name__ == "__main__":
    unittest.main()
