"""Build repeatable V001 SQL from SHOW CREATE output."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.db_migrate.errors import MigrationError
from backend.db_migrate.ledger import LEDGER_TABLE


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
_CREATE_TABLE_PREFIX = "CREATE TABLE "
_VIEW_AS_MARKER = " AS "
_SchemaObjects = tuple[list[tuple[str, str]], list[tuple[str, str]]]

_SCHEMA_OBJECTS_SQL = (
    "SELECT TABLE_NAME, TABLE_TYPE "
    "FROM information_schema.tables "
    "WHERE table_schema = DATABASE() "
    "AND TABLE_TYPE IN ('BASE TABLE', 'VIEW') "
    "ORDER BY TABLE_TYPE, TABLE_NAME")


def load_schema_objects(connection: Any) -> _SchemaObjects:
    """Return ``(tables, views)`` as ``(name, show_create)`` pairs.

    Skips the ledger table. An empty table list raises
    ``MigrationError``.
    """
    cursor = connection.cursor()
    try:
        return _collect_schema_objects(cursor)
    finally:
        cursor.close()


def rewrite_table_ddl(show_create: str) -> str:
    """Turn SHOW CREATE TABLE into ``CREATE TABLE IF NOT EXISTS``."""
    if not show_create.startswith(_CREATE_TABLE_PREFIX):
        raise MigrationError("Unexpected SHOW CREATE TABLE output")
    rest = show_create[len(_CREATE_TABLE_PREFIX):]
    return f"CREATE TABLE IF NOT EXISTS {rest}"


def rewrite_view_ddl(name: str, show_create: str) -> str:
    """Drop DEFINER and force ``SQL SECURITY INVOKER``."""
    marker_at = show_create.find(_VIEW_AS_MARKER)
    if marker_at < 0:
        raise MigrationError("Unexpected SHOW CREATE VIEW output")
    select_sql = show_create[marker_at + len(_VIEW_AS_MARKER):]
    return (
        f"CREATE OR REPLACE SQL SECURITY INVOKER VIEW `{name}` AS "
        f"{select_sql}")


def render_baseline_sql(
        tables: list[tuple[str, str]],
        views: list[tuple[str, str]]) -> str:
    """Render V001 text with LF endings and a trailing newline."""
    chunks = [
        "-- EkstraBet schema baseline V001.",
        "-- Structure copied from SHOW CREATE. Rows are not included.",
        "SET FOREIGN_KEY_CHECKS = 0;"]
    for _name, show_create in tables:
        chunks.append(_with_semicolon(rewrite_table_ddl(show_create)))
    for name, show_create in views:
        chunks.append(_with_semicolon(rewrite_view_ddl(name, show_create)))
    chunks.append("SET FOREIGN_KEY_CHECKS = 1;")
    return "\n".join(chunks) + "\n"


def write_baseline_file(sql_text: str, destination: Path) -> None:
    """Write baseline SQL with LF endings. Never overwrite."""
    if destination.exists():
        raise MigrationError("Baseline file already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # LF na Windows i na VPS, żeby checksum pliku był ten sam
    destination.write_text(sql_text, encoding="utf-8", newline="\n")


def _collect_schema_objects(cursor: Any) -> _SchemaObjects:
    """Read SHOW CREATE for each business table and view."""
    cursor.execute(_SCHEMA_OBJECTS_SQL)
    tables: list[tuple[str, str]] = []
    views: list[tuple[str, str]] = []
    for raw_name, raw_type in cursor.fetchall():
        if raw_name == LEDGER_TABLE:
            continue
        name = _require_identifier(raw_name)
        show_create = _show_create(cursor, name)
        if raw_type == "BASE TABLE":
            tables.append((name, show_create))
            continue
        if raw_type == "VIEW":
            views.append((name, show_create))
    if not tables:
        raise MigrationError("No tables found")
    return tables, views


def _require_identifier(name: object) -> str:
    """Reject names that cannot be quoted as a plain identifier."""
    text = str(name)
    if _IDENTIFIER_RE.match(text) is None:
        raise MigrationError("Unsupported identifier")
    return text


def _show_create(cursor: Any, name: str) -> str:
    """Return column 1 from SHOW CREATE TABLE or VIEW."""
    cursor.execute(f"SHOW CREATE TABLE `{name}`")
    row = cursor.fetchone()
    if row is None or len(row) < 2 or not isinstance(row[1], str):
        raise MigrationError("Unexpected SHOW CREATE TABLE output")
    return row[1]


def _with_semicolon(ddl: str) -> str:
    """Put the closing semicolon on the last line of a statement."""
    # Splitter migracji odrzuca średnik, który nie jest końcem linii
    return ddl.rstrip() + ";"
