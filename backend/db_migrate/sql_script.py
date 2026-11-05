"""Split a migration script into statements and run them."""

from __future__ import annotations

from typing import Any

import mysql.connector

from backend.db_migrate.errors import MigrationError
from backend.db_migrate.errors import MigrationSqlError


def split_sql_script(script: str) -> list[str]:
    """Split a migration script into statements without a SQL parser.

    A semicolon ends a statement only as the last character of a line
    and only outside a single-quoted literal. ``''`` inside a literal
    is one quote. Pieces of one statement are joined with one space.
    Blank lines and full-line ``--`` comments are ignored outside
    literals.
    """
    statements: list[str] = []
    parts: list[str] = []
    in_string = False
    for line in script.splitlines():
        stripped = line.strip()
        if _should_skip_line(stripped, in_string):
            continue
        in_string, closes = _scan_sql_line(stripped, in_string)
        if closes:
            _close_statement(statements, parts, stripped[:-1].strip())
            continue
        parts.append(stripped)
    if parts or in_string:
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


def _should_skip_line(stripped: str, in_string: bool) -> bool:
    """Ignore blanks and full-line comments outside a literal."""
    if in_string:
        return False
    return not stripped or stripped.startswith("--")


def _scan_sql_line(line: str, in_string: bool) -> tuple[bool, bool]:
    """Return whether the literal stays open and the line closes SQL.

    A semicolon outside a single-quoted literal must be the last
    character of the line. ``''`` stays inside the literal.
    """
    # Średnik w COMMENT zostaje. Liczy się tylko ten poza literałem.
    index = 0
    closes = False
    while index < len(line):
        char = line[index]
        if char == "'":
            index, in_string = _step_quote(line, index, in_string)
            continue
        if char == ";" and not in_string:
            if index != len(line) - 1:
                raise MigrationError(
                    "Semicolon is allowed only at the end of a line")
            closes = True
        index += 1
    return in_string, closes


def _step_quote(line: str, index: int, in_string: bool) -> tuple[int, bool]:
    """Move past one quote. ``''`` is an escaped quote, not the end."""
    if in_string and index + 1 < len(line) and line[index + 1] == "'":
        return index + 2, True
    return index + 1, not in_string


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
