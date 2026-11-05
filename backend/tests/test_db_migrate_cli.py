"""Tests for the migration command line. No database connection."""

from __future__ import annotations

import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from backend.database import DatabaseConnectionError
from backend.db_migrate.__main__ import main
from backend.db_migrate.errors import MigrationError
from backend.db_migrate.files import MIGRATIONS_DIR
from backend.db_migrate.runner import MigrationRunner
from backend.db_migrate.runner import MigrationStatus


_APPLIED = MigrationStatus(
    version="V001",
    filename="V001__baseline.sql",
    state="applied")
_MISMATCH = MigrationStatus(
    version="V001",
    filename="V001__baseline.sql",
    state="checksum_mismatch")
_USAGE_LINE = (
    "usage: python -m backend.db_migrate "
    "{status,apply,baseline,generate-baseline}\n")
_SCHEMA = ([("teams", "CREATE TABLE `teams` (id INT)")], [])


def _capture(argv: list[str]) -> tuple[int, str, str]:
    """Return the exit code, stdout and stderr of one CLI call."""
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class TestMigrationCli(unittest.TestCase):
    """Stdout lines and exit codes for the four commands."""

    @patch.object(MigrationRunner, "status", return_value=[_APPLIED])
    def test_status_applied_prints_line(self, _status: MagicMock) -> None:
        code, stdout, stderr = _capture(["status"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "V001 V001__baseline.sql applied\n")
        self.assertEqual(stderr, "")

    @patch.object(MigrationRunner, "status", return_value=[_MISMATCH])
    def test_status_checksum_mismatch_returns_one(
            self,
            _status: MagicMock) -> None:
        code, stdout, stderr = _capture(["status"])
        self.assertEqual(code, 1)
        self.assertEqual(
            stdout,
            "V001 V001__baseline.sql checksum_mismatch\n")
        self.assertEqual(stderr, "")

    @patch.object(MigrationRunner, "status", return_value=[])
    def test_status_without_files_returns_one(
            self,
            _status: MagicMock) -> None:
        code, stdout, stderr = _capture(["status"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "No migration files found\n")

    @patch.object(MigrationRunner, "apply", return_value=[])
    def test_apply_with_nothing_pending_prints_none(
            self,
            _apply: MagicMock) -> None:
        code, stdout, stderr = _capture(["apply"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "applied-none\n")
        self.assertEqual(stderr, "")

    @patch.object(MigrationRunner, "apply", return_value=["V001", "V002"])
    def test_apply_prints_each_version(self, _apply: MagicMock) -> None:
        code, stdout, stderr = _capture(["apply"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "applied V001\napplied V002\n")
        self.assertEqual(stderr, "")

    def test_baseline_prints_result_and_version(self) -> None:
        for result in ("baselined", "already-baselined"):
            with self.subTest(result=result):
                with patch.object(
                        MigrationRunner,
                        "baseline",
                        return_value=result):
                    code, stdout, stderr = _capture(["baseline"])
                self.assertEqual(code, 0)
                self.assertEqual(stdout, f"{result} V001\n")
                self.assertEqual(stderr, "")

    @patch("backend.db_migrate.__main__.write_baseline_file")
    @patch(
        "backend.db_migrate.__main__.render_baseline_sql",
        return_value="-- baseline\n")
    @patch(
        "backend.db_migrate.__main__.load_schema_objects",
        return_value=_SCHEMA)
    @patch("backend.db_migrate.__main__.open_migration_connection")
    def test_generate_baseline_writes_under_migrations_dir(
            self,
            open_connection: MagicMock,
            load_objects: MagicMock,
            render: MagicMock,
            write_file: MagicMock) -> None:
        connection = MagicMock()
        open_connection.return_value = connection
        code, stdout, stderr = _capture(["generate-baseline"])
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            "wrote sql/migrations/V001__baseline.sql\n")
        open_connection.assert_called_once_with()
        load_objects.assert_called_once_with(connection)
        render.assert_called_once_with(*load_objects.return_value)
        write_file.assert_called_once_with(
            render.return_value,
            MIGRATIONS_DIR / "V001__baseline.sql")
        destination = write_file.call_args.args[1]
        self.assertEqual(
            destination.relative_to(MIGRATIONS_DIR),
            Path("V001__baseline.sql"))
        connection.close.assert_called_once_with()

    def test_missing_or_unknown_command_returns_two(self) -> None:
        for argv in ([], ["nope"], ["status", "extra"]):
            with self.subTest(argv=argv):
                code, stdout, stderr = _capture(argv)
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, _USAGE_LINE)

    @patch.object(
        MigrationRunner,
        "baseline",
        side_effect=MigrationError("Checksum mismatch for V001"))
    def test_migration_error_prints_stderr(
            self,
            _baseline: MagicMock) -> None:
        code, stdout, stderr = _capture(["baseline"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "Checksum mismatch for V001\n")

    @patch.object(
        MigrationRunner,
        "status",
        side_effect=DatabaseConnectionError(
            "Failed to connect to the database"))
    def test_database_connection_error_prints_stderr(
            self,
            _status: MagicMock) -> None:
        code, stdout, stderr = _capture(["status"])
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(
            stderr,
            "Failed to connect to the database\n")
