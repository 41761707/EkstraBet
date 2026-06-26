"""MySQL connection manager shared by API, services, and tests."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import mysql.connector
from mysql.connector import MySQLConnection

from backend.config import get_database_config


class DatabaseConnectionError(Exception):
    """Raised when a database connection cannot be established."""


class ConnectionManager:
    """Manages MySQL connections using application settings."""

    @classmethod
    def connect(cls) -> MySQLConnection:
        """Open a new MySQL connection."""
        config = get_database_config()
        try:
            return mysql.connector.connect(**config)
        except mysql.connector.Error as exc:
            raise DatabaseConnectionError(
                "Failed to connect to the database"
            ) from exc

    @classmethod
    @contextmanager
    def session(cls) -> Generator[MySQLConnection, None, None]:
        """Yield a connection and close it when the block exits."""
        conn: MySQLConnection | None = None
        try:
            conn = cls.connect()
            yield conn
        finally:
            if conn is not None and conn.is_connected():
                conn.close()

    @classmethod
    def ping(cls) -> bool:
        """Return True when the database accepts a connection."""
        try:
            with cls.session() as conn:
                return conn.is_connected()
        except DatabaseConnectionError:
            return False


def db_connect() -> MySQLConnection:
    """Compatibility alias for legacy db_module.db_connect()."""
    return ConnectionManager.connect()


@contextmanager
def get_db_connection() -> Generator[MySQLConnection, None, None]:
    """Context manager alias used by API utilities."""
    with ConnectionManager.session() as conn:
        yield conn


def test_connection() -> bool:
    """Return True when the database connection test succeeds."""
    return ConnectionManager.ping()
