"""Split a migration script into statements and run them."""

from __future__ import annotations

from typing import Any

import mysql.connector

from backend.db_migrate.errors import MigrationError
from backend.db_migrate.errors import MigrationSqlError


def split_sql_script(script: str) -> list[str]:
    """Split a migration script into statements without a SQL parser.

    A semicolon is allowed only as the last non-whitespace character of a
    line. Pieces of one statement are joined with a single space. Blank
    lines and full-line ``--`` comments are ignored.
    """
    statements: list[str] = []
    parts: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if ";" in stripped[:-1]:
            raise MigrationError(
                "Semicolon is allowed only at the end of a line")
        if stripped.endswith(";"):
            _close_statement(statements, parts, stripped[:-1].strip())
            continue
        parts.append(stripped)
    if parts:
        raise MigrationError("Migration script ended without a semicolon")
    return statements


def execute_statements(cursor: Any, statements: list[str]) -> None:
    """Run statements in order and stop at the first MySQL error.

    Does not commit. ``MigrationSqlError.index`` is 1-based.
    """
    for index, statement in enumerate(statements, start=1):
        try:
            cursor.execute(statement)
        except mysql.connector.Error as exc:
            raise MigrationSqlError(index, str(exc)) from exc


def _close_statement(
        statements: list[str],
        parts: list[str],
        piece: str) -> None:
    """Append the closing line and emit the statement when it has text."""
    if piece:
        parts.append(piece)
    statement = " ".join(parts).strip()
    parts.clear()
    if statement:
        statements.append(statement)
