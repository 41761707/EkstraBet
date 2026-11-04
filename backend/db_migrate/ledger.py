"""Migration ledger table and the MySQL advisory lock around it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.db_migrate.errors import MigrationError
from backend.db_migrate.files import MigrationFile


LEDGER_TABLE = "schema_migrations"
LOCK_NAME = "ekstrabet_db_migrate"
LOCK_TIMEOUT_SECONDS = 30

_CREATE_LEDGER_SQL = (
    "CREATE TABLE IF NOT EXISTS schema_migrations ("
    "version VARCHAR(32) NOT NULL, "
    "filename VARCHAR(255) NOT NULL, "
    "checksum CHAR(64) NOT NULL, "
    "applied_at DATETIME NOT NULL, "
    "PRIMARY KEY (version))"
)
_LEDGER_EXISTS_SQL = (
    "SELECT 1 FROM information_schema.tables "
    "WHERE table_schema = DATABASE() AND table_name = %s"
)
_COUNT_BUSINESS_TABLES_SQL = (
    "SELECT COUNT(*) FROM information_schema.tables "
    "WHERE table_schema = DATABASE() "
    "AND table_type = 'BASE TABLE' "
    "AND table_name <> %s"
)
_FETCH_APPLIED_SQL = (
    "SELECT version, filename, checksum, applied_at "
    "FROM schema_migrations"
)
_RECORD_APPLIED_SQL = (
    "INSERT INTO schema_migrations "
    "(version, filename, checksum, applied_at) "
    "VALUES (%s, %s, %s, NOW())"
)


@dataclass(frozen=True)
class AppliedMigration:
    """One version already stored in schema_migrations."""

    version: str
    filename: str
    checksum: str
    applied_at: datetime


def ensure_ledger(cursor: Any) -> None:
    """Create schema_migrations when it is missing. Does not commit."""
    cursor.execute(_CREATE_LEDGER_SQL)


def ledger_exists(cursor: Any) -> bool:
    """Return whether schema_migrations exists in the current database."""
    cursor.execute(_LEDGER_EXISTS_SQL, (LEDGER_TABLE,))
    return cursor.fetchone() is not None


def acquire_lock(cursor: Any) -> None:
    """Take the migration advisory lock or fail without changing data."""
    cursor.execute(
        "SELECT GET_LOCK(%s, %s)",
        (LOCK_NAME, LOCK_TIMEOUT_SECONDS))
    row = cursor.fetchone()
    granted = None if row is None else row[0]
    # NULL z GET_LOCK to błąd serwera, nie przyznana blokada
    if granted is None or int(granted) != 1:
        raise MigrationError("Could not acquire migration lock")


def release_lock(cursor: Any) -> None:
    """Release the migration advisory lock and consume the result."""
    cursor.execute("SELECT RELEASE_LOCK(%s)", (LOCK_NAME,))
    cursor.fetchone()


def count_business_tables(cursor: Any) -> int:
    """Count base tables in the current database except the ledger."""
    cursor.execute(_COUNT_BUSINESS_TABLES_SQL, (LEDGER_TABLE,))
    row = cursor.fetchone()
    return int(row[0])


def fetch_applied(cursor: Any) -> dict[str, AppliedMigration]:
    """Return applied versions keyed by version. Does not create the table."""
    cursor.execute(_FETCH_APPLIED_SQL)
    applied: dict[str, AppliedMigration] = {}
    for row in cursor.fetchall():
        recorded = AppliedMigration(
            version=str(row[0]),
            filename=str(row[1]),
            checksum=str(row[2]),
            applied_at=row[3])
        applied[recorded.version] = recorded
    return applied


def record_applied(
        cursor: Any,
        migration: MigrationFile,
        checksum: str) -> None:
    """Insert one applied version. The caller commits."""
    # NOW() zostaje w SQL, żeby applied_at szło ze strefy sesji
    cursor.execute(
        _RECORD_APPLIED_SQL,
        (migration.version, migration.filename, checksum))
