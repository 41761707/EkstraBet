"""Run status, apply and baseline for versioned SQL migrations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import TypeVar

from mysql.connector import MySQLConnection

from backend.db_migrate.connection import open_migration_connection
from backend.db_migrate.errors import MigrationError
from backend.db_migrate.files import MIGRATIONS_DIR
from backend.db_migrate.files import MigrationFile
from backend.db_migrate.files import file_checksum
from backend.db_migrate.files import list_migration_files
from backend.db_migrate.ledger import AppliedMigration
from backend.db_migrate.ledger import acquire_lock
from backend.db_migrate.ledger import count_business_tables
from backend.db_migrate.ledger import ensure_ledger
from backend.db_migrate.ledger import fetch_applied
from backend.db_migrate.ledger import ledger_exists
from backend.db_migrate.ledger import record_applied
from backend.db_migrate.ledger import release_lock
from backend.db_migrate.sql_script import execute_statements
from backend.db_migrate.sql_script import split_sql_script


_T = TypeVar("_T")

_BASELINE_VERSION = "V001"

_EXISTING_TABLES_MESSAGE = (
    "V001 is pending but tables already exist. "
    "On an existing EkstraBet database run baseline. "
    "On a failed fresh install, drop the database and apply again.")


@dataclass(frozen=True)
class MigrationStatus:
    """One migration file compared with the ledger.

    ``state`` is ``pending``, ``applied`` or ``checksum_mismatch``.
    """

    version: str
    filename: str
    state: str


def _release_without_masking(cursor: Any, failed: bool) -> None:
    """Release the lock. A release error must not hide an earlier one."""
    try:
        release_lock(cursor)
    except Exception:
        # Zerwana sesja nie może zastąpić błędu, który przerwał migrację
        if not failed:
            raise


class MigrationRunner:
    """Apply versioned SQL files and record them in the ledger."""

    def __init__(
            self,
            migrations_dir: Path | None = None,
            connect: Callable[[], MySQLConnection] | None = None) -> None:
        self._migrations_dir = (
            MIGRATIONS_DIR if migrations_dir is None else migrations_dir)
        self._connect = (
            open_migration_connection if connect is None else connect)

    def status(self) -> list[MigrationStatus]:
        """Report each file without a lock and without creating the ledger."""
        connection = self._connect()
        try:
            cursor = connection.cursor()
            try:
                return self._collect_status(cursor)
            finally:
                cursor.close()
        finally:
            # Runner sam otwiera połączenie, więc sam je zamyka
            connection.close()

    def apply(self) -> list[str]:
        """Run pending files. Return versions committed in this call."""
        return self._run_locked(self._apply_pending)

    def baseline(self) -> str:
        """Record V001 without executing the baseline script."""
        return self._run_locked(self._guard_baseline)

    def _run_locked(
            self,
            action: Callable[[Any, Any], _T]) -> _T:
        connection = self._connect()
        try:
            cursor = connection.cursor()
            try:
                return self._locked_action(connection, cursor, action)
            finally:
                cursor.close()
        finally:
            connection.close()

    def _locked_action(
            self,
            connection: Any,
            cursor: Any,
            action: Callable[[Any, Any], _T]) -> _T:
        failed = False
        try:
            acquire_lock(cursor)
            ensure_ledger(cursor)
            connection.commit()
            return action(connection, cursor)
        except Exception:
            failed = True
            _rollback_quietly(connection)
            raise
        finally:
            _release_without_masking(cursor, failed)

    def _collect_status(self, cursor: Any) -> list[MigrationStatus]:
        files = list_migration_files(self._migrations_dir)
        if not ledger_exists(cursor):
            return [self._status_row(item, "pending") for item in files]
        applied = fetch_applied(cursor)
        return [self._status_for(item, applied) for item in files]

    def _status_for(
            self,
            migration: MigrationFile,
            applied: dict[str, AppliedMigration]) -> MigrationStatus:
        recorded = applied.get(migration.version)
        if recorded is None:
            return self._status_row(migration, "pending")
        checksum = file_checksum(migration.path)
        if recorded.checksum != checksum:
            return self._status_row(migration, "checksum_mismatch")
        return self._status_row(migration, "applied")

    def _status_row(
            self,
            migration: MigrationFile,
            state: str) -> MigrationStatus:
        return MigrationStatus(
            version=migration.version,
            filename=migration.filename,
            state=state)

    def _apply_pending(self, connection: Any, cursor: Any) -> list[str]:
        """Execute pending files in order and commit each version."""
        files = list_migration_files(self._migrations_dir)
        applied = fetch_applied(cursor)
        completed: list[str] = []
        for migration in files:
            version = self._apply_one(connection, cursor, migration, applied)
            if version is not None:
                completed.append(version)
        return completed

    def _apply_one(
            self,
            connection: Any,
            cursor: Any,
            migration: MigrationFile,
            applied: dict[str, AppliedMigration]) -> str | None:
        checksum = file_checksum(migration.path)
        recorded = applied.get(migration.version)
        if recorded is not None:
            if recorded.checksum != checksum:
                raise MigrationError(
                    f"Checksum mismatch for {migration.version}")
            return None
        self._refuse_existing_database(cursor, migration)
        self._execute_file(cursor, migration)
        record_applied(cursor, migration, checksum)
        connection.commit()
        return migration.version

    def _refuse_existing_database(
            self,
            cursor: Any,
            migration: MigrationFile) -> None:
        if migration.number != 1:
            return
        if count_business_tables(cursor) == 0:
            return
        # V001 na bazie z tabelami nadpisałoby schemat; właściwe jest baseline
        raise MigrationError(_EXISTING_TABLES_MESSAGE)

    def _execute_file(self, cursor: Any, migration: MigrationFile) -> None:
        script = migration.path.read_text(encoding="utf-8")
        execute_statements(cursor, split_sql_script(script))

    def _guard_baseline(self, connection: Any, cursor: Any) -> str:
        """Record V001, or refuse when the ledger is already ahead."""
        migration = self._require_baseline_file()
        applied = fetch_applied(cursor)
        self._refuse_later_migrations(applied)
        return self._record_baseline(connection, cursor, migration, applied)

    def _require_baseline_file(self) -> MigrationFile:
        files = list_migration_files(self._migrations_dir)
        for migration in files:
            if migration.version == _BASELINE_VERSION:
                return migration
        raise MigrationError(
            f"Baseline file {_BASELINE_VERSION} is missing")

    def _refuse_later_migrations(
            self,
            applied: dict[str, AppliedMigration]) -> None:
        for version in applied:
            if version != _BASELINE_VERSION:
                raise MigrationError(
                    "Cannot baseline after later migrations")

    def _record_baseline(
            self,
            connection: Any,
            cursor: Any,
            migration: MigrationFile,
            applied: dict[str, AppliedMigration]) -> str:
        checksum = file_checksum(migration.path)
        recorded = applied.get(_BASELINE_VERSION)
        if recorded is None:
            record_applied(cursor, migration, checksum)
            connection.commit()
            return "baselined"
        if recorded.checksum != checksum:
            raise MigrationError(
                f"Checksum mismatch for {_BASELINE_VERSION}")
        return "already-baselined"


def _rollback_quietly(connection: Any) -> None:
    """Roll back the open transaction without hiding the cause."""
    try:
        connection.rollback()
    except Exception:
        # Nieudany rollback nie zastępuje przyczyny przerwania migracji
        return
