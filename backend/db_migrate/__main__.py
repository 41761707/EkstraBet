"""Command-line entry for the migration runner."""

from __future__ import annotations

import sys

from backend.database import DatabaseConnectionError
from backend.db_migrate.baseline import load_schema_objects
from backend.db_migrate.baseline import render_baseline_sql
from backend.db_migrate.baseline import write_baseline_file
from backend.db_migrate.connection import open_migration_connection
from backend.db_migrate.errors import MigrationError
from backend.db_migrate.files import MIGRATIONS_DIR
from backend.db_migrate.runner import MigrationRunner


_USAGE = (
    "usage: python -m backend.db_migrate "
    "{status,apply,baseline,generate-baseline}")


def main(argv: list[str] | None = None) -> int:
    """Run one migration command and return a process exit code."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return _usage()
    try:
        return _dispatch(args[0])
    except (MigrationError, DatabaseConnectionError) as exc:
        print(exc, file=sys.stderr)
        return 1


def _usage() -> int:
    """Print the command list and return the usage exit code."""
    print(_USAGE, file=sys.stderr)
    return 2


def _dispatch(command: str) -> int:
    """Run a known command, or usage when the name is unknown."""
    if command == "status":
        return _print_status()
    if command == "apply":
        return _print_apply()
    if command == "baseline":
        return _print_baseline()
    if command == "generate-baseline":
        return _generate_baseline()
    return _usage()


def _print_status() -> int:
    """Print one line per file. Mismatch or an empty catalog fails."""
    rows = MigrationRunner().status()
    if not rows:
        print("No migration files found", file=sys.stderr)
        return 1
    for row in rows:
        print(f"{row.version} {row.filename} {row.state}")
    if any(row.state == "checksum_mismatch" for row in rows):
        return 1
    return 0


def _print_apply() -> int:
    """Print each version committed in this run."""
    versions = MigrationRunner().apply()
    if not versions:
        print("applied-none")
        return 0
    for version in versions:
        print(f"applied {version}")
    return 0


def _print_baseline() -> int:
    """Print the baseline result for V001."""
    result = MigrationRunner().baseline()
    print(f"{result} V001")
    return 0


def _generate_baseline() -> int:
    """Write V001 from the live schema. Does not apply the file."""
    connection = open_migration_connection()
    try:
        tables, views = load_schema_objects(connection)
    finally:
        # SHOW CREATE nie potrzebuje otwartej sesji przy zapisie pliku
        connection.close()
    sql_text = render_baseline_sql(tables, views)
    destination = MIGRATIONS_DIR / "V001__baseline.sql"
    write_baseline_file(sql_text, destination)
    print("wrote sql/migrations/V001__baseline.sql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
