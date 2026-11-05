"""Open a MySQL connection for the migration runner."""

from __future__ import annotations

import os
from typing import Any

import mysql.connector
from mysql.connector import MySQLConnection

from backend.config import get_database_config
from backend.database import DatabaseConnectionError
from backend.db_migrate.errors import MigrationError
from backend.timezone import apply_mysql_session_timezone


def open_migration_connection() -> MySQLConnection:
    """Connect with a DDL account, or with the application account.

    ``DB_MIGRATE_USER`` overrides only this connection. Application
    settings keep ``DB_USER``, so production can reject ``root`` there.
    """
    params = _connect_params()
    try:
        connection = mysql.connector.connect(**params)
    except mysql.connector.Error as exc:
        raise DatabaseConnectionError(
            "Failed to connect to the database") from exc
    try:
        # NOW() w księdze ma być czasem polskim, jak w połączeniu aplikacji
        apply_mysql_session_timezone(connection)
    except mysql.connector.Error as exc:
        connection.close()
        raise DatabaseConnectionError(
            "Failed to set database session timezone") from exc
    return connection


def _connect_params() -> dict[str, Any]:
    """Copy application settings and overlay migrate credentials."""
    # Kopia, żeby podmiana konta DDL nie zmieniła konfiguracji aplikacji
    params = dict(get_database_config())
    migrate_user = os.environ.get("DB_MIGRATE_USER", "")
    if migrate_user == "":
        return params
    password = os.environ.get("DB_MIGRATE_PASSWORD", "")
    if password == "":
        raise MigrationError(
            "DB_MIGRATE_PASSWORD is required when DB_MIGRATE_USER is set")
    params["user"] = migrate_user
    params["password"] = password
    return params
