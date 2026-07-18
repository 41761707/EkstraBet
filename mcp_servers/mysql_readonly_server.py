"""Read-only MySQL MCP server for EkstraBet database inspection."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
import base64
import os
import re
import sys
import textwrap
from typing import Any
from typing import Iterator

import mysql.connector
from mysql.connector import Error as MySqlError
from mysql.connector import MySQLConnection


DEFAULT_MAX_ROWS = 100
DEFAULT_QUERY_TIMEOUT_SECONDS = 10
MAX_ALLOWED_ROWS = 1000
COMMENT_MARKERS = ("--", "#", "/*", "*/")
READONLY_START_KEYWORDS = {"SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN"}
WRITE_PATTERNS = (
    r"\bINTO\s+OUTFILE\b",
    r"\bINTO\s+DUMPFILE\b",
    r"\bFOR\s+UPDATE\b",
    r"\bLOCK\s+IN\s+SHARE\s+MODE\b",
    r"\bLOAD_FILE\s*\(",
)
HELP_TEXT = """
EkstraBet MySQL Readonly MCP Server

Usage:
  python mcp_servers/mysql_readonly_server.py
  python mcp_servers/mysql_readonly_server.py --help

Cursor MCP configuration:
  {
    "mcpServers": {
      "ekstrabet-mysql-readonly": {
        "type": "stdio",
        "command": "python",
        "args": ["mcp_servers/mysql_readonly_server.py"],
        "envFile": "${workspaceFolder}/.env.cursor-mcp"
      }
    }
  }

Required environment variables:
  DB_HOST
  DB_PORT
  DB_NAME
  DB_USER
  DB_PASSWORD

Optional environment variables:
  MCP_MAX_ROWS
  MCP_QUERY_TIMEOUT_SECONDS

Available tools:
  list_tables()
  describe_table(table_name)
  show_create_table(table_name)
  list_indexes(table_name)
  select_query(sql, limit=100)
  current_database()

Security notes:
  Use a dedicated MySQL user with SELECT and SHOW VIEW only.
  The server accepts one read-only SQL statement at a time.
  Write and DDL statements are rejected before reaching MySQL.
"""


class ReadOnlyMcpError(ValueError):
    """Raised when an MCP tool receives unsafe or invalid input."""


@dataclass(frozen=True)
class McpDatabaseSettings:
    """Database settings loaded from environment variables."""

    host: str
    port: int
    database: str
    user: str
    password: str
    max_rows: int = DEFAULT_MAX_ROWS
    query_timeout_seconds: int = DEFAULT_QUERY_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> "McpDatabaseSettings":
        """Return settings loaded from the current process environment."""
        password = os.environ.get("DB_PASSWORD")
        if not password:
            raise ReadOnlyMcpError("DB_PASSWORD is required")

        return cls(
            host=os.environ.get("DB_HOST", "localhost"),
            port=_get_int_env("DB_PORT", 3306),
            database=os.environ.get("DB_NAME", "ekstrabet"),
            user=os.environ.get("DB_USER", "cursor_ro"),
            password=password,
            max_rows=_get_int_env("MCP_MAX_ROWS", DEFAULT_MAX_ROWS),
            query_timeout_seconds=_get_int_env(
                "MCP_QUERY_TIMEOUT_SECONDS",
                DEFAULT_QUERY_TIMEOUT_SECONDS))

    def connection_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments for mysql.connector.connect()."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
            "connection_timeout": self.query_timeout_seconds
        }


class IdentifierValidator:
    """Validate MySQL identifiers used outside parameterized SQL."""

    IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)?$")

    def validate_table_name(self, table_name: str) -> str:
        """Return a validated table name."""
        normalized = table_name.strip()
        if not normalized:
            raise ReadOnlyMcpError("Table name is required")

        if not self.IDENTIFIER_RE.fullmatch(normalized):
            raise ReadOnlyMcpError("Table name contains invalid characters")

        return normalized

    def split_table_name(
        self,
        table_name: str,
        default_schema: str
    ) -> tuple[str, str]:
        """Return schema and table parts for a validated table name."""
        normalized = self.validate_table_name(table_name)
        if "." not in normalized:
            return default_schema, normalized

        schema, table = normalized.split(".", 1)
        return schema, table

    def quote_table_name(self, table_name: str, default_schema: str) -> str:
        """Return a safely quoted qualified table name."""
        schema, table = self.split_table_name(table_name, default_schema)
        return f"`{schema}`.`{table}`"


class ReadOnlySqlValidator:
    """Validate and normalize SQL accepted by the read-only MCP tool."""

    def validate(self, sql: str) -> str:
        """Return normalized SQL when it is safe to execute."""
        normalized = self._normalize(sql)
        self.ensure_single_statement(normalized)
        self.ensure_allowed_statement(normalized)
        self.ensure_no_comment_markers(normalized)
        self.ensure_no_write_patterns(normalized)
        return normalized

    def ensure_single_statement(self, sql: str) -> None:
        """Reject SQL containing more than one statement."""
        without_trailing_semicolon = sql.rstrip(";").strip()
        if ";" in without_trailing_semicolon:
            raise ReadOnlyMcpError("Only one SQL statement is allowed")

    def ensure_allowed_statement(self, sql: str) -> None:
        """Reject SQL statements that do not start with a read-only keyword."""
        first_token_match = re.match(r"^([A-Za-z]+)\b", sql)
        if first_token_match is None:
            raise ReadOnlyMcpError("SQL statement is required")

        first_token = first_token_match.group(1).upper()
        if first_token not in READONLY_START_KEYWORDS:
            raise ReadOnlyMcpError("Only read-only SQL statements are allowed")

    def ensure_no_comment_markers(self, sql: str) -> None:
        """Reject comments because they make text validation ambiguous."""
        if any(marker in sql for marker in COMMENT_MARKERS):
            raise ReadOnlyMcpError("SQL comments are not allowed")

    def ensure_no_write_patterns(self, sql: str) -> None:
        """Reject read-looking SQL forms that can write or access files."""
        for pattern in WRITE_PATTERNS:
            if re.search(pattern, sql, flags=re.IGNORECASE):
                raise ReadOnlyMcpError("Unsafe read-only SQL pattern detected")

    def apply_limit(self, sql: str, limit: int, max_rows: int) -> str:
        """Return SQL with a bounded LIMIT for SELECT statements."""
        bounded_limit = self.bounded_limit(limit, max_rows)
        normalized = sql.rstrip(";").strip()

        if not normalized.upper().startswith("SELECT"):
            return normalized

        limit_match = re.search(
            r"\bLIMIT\s+(\d+)\s*$",
            normalized,
            flags=re.IGNORECASE)
        if limit_match is not None:
            existing_limit = int(limit_match.group(1))
            if existing_limit <= bounded_limit:
                return normalized

            return (
                f"{normalized[:limit_match.start()].rstrip()} "
                f"LIMIT {bounded_limit}")

        if re.search(r"\bLIMIT\b", normalized, flags=re.IGNORECASE):
            return f"SELECT * FROM ({normalized}) AS readonly_query LIMIT {bounded_limit}"

        return f"{normalized} LIMIT {bounded_limit}"

    def bounded_limit(self, limit: int, max_rows: int) -> int:
        """Return a positive limit constrained by server settings."""
        return max(1, min(limit, max_rows, MAX_ALLOWED_ROWS))

    def _normalize(self, sql: str) -> str:
        """Return SQL with surrounding whitespace and final semicolon removed."""
        normalized = " ".join(sql.strip().split())
        normalized = normalized.rstrip(";").strip()
        if not normalized:
            raise ReadOnlyMcpError("SQL statement is required")

        return normalized


class ResultSerializer:
    """Serialize MySQL values into JSON-friendly values."""

    def serialize_value(self, value: Any) -> Any:
        """Return a JSON-friendly representation of a database value."""
        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, bytes):
            return base64.b64encode(value).decode("ascii")

        return value

    def serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Return a serialized dictionary row."""
        return {
            key: self.serialize_value(value)
            for key, value in row.items()
        }

    def serialize_rows(
        self,
        rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Return serialized database rows."""
        return [self.serialize_row(row) for row in rows]


class MySqlReadOnlyClient:
    """Read-only MySQL client used by MCP tools."""

    def __init__(self, settings: McpDatabaseSettings) -> None:
        """Initialize the client."""
        self.settings = settings
        self.identifiers = IdentifierValidator()
        self.sql_validator = ReadOnlySqlValidator()
        self.serializer = ResultSerializer()

    @contextmanager
    def connection(self) -> Iterator[MySQLConnection]:
        """Yield a MySQL connection and close it afterwards."""
        conn = mysql.connector.connect(**self.settings.connection_kwargs())
        try:
            self._apply_session_timeout(conn)
            yield conn
        finally:
            if conn.is_connected():
                conn.close()

    def list_tables(self) -> list[dict[str, Any]]:
        """Return tables and views in the configured database."""
        sql = """
            SELECT TABLE_NAME AS table_name,
                   TABLE_TYPE AS table_type,
                   TABLE_ROWS AS estimated_rows
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
        """
        return self._fetch_all(sql, (self.settings.database,))

    def describe_table(self, table_name: str) -> list[dict[str, Any]]:
        """Return column metadata for a table or view."""
        schema, table = self.identifiers.split_table_name(
            table_name,
            self.settings.database)
        sql = """
            SELECT COLUMN_NAME AS column_name,
                   COLUMN_TYPE AS column_type,
                   IS_NULLABLE AS is_nullable,
                   COLUMN_KEY AS column_key,
                   COLUMN_DEFAULT AS column_default,
                   EXTRA AS extra
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        return self._fetch_all(sql, (schema, table))

    def show_create_table(self, table_name: str) -> dict[str, Any]:
        """Return the CREATE statement for a table or view."""
        quoted_name = self.identifiers.quote_table_name(
            table_name,
            self.settings.database)
        rows = self._fetch_all(f"SHOW CREATE TABLE {quoted_name}")
        if not rows:
            raise ReadOnlyMcpError("Table was not found")

        return rows[0]

    def list_indexes(self, table_name: str) -> list[dict[str, Any]]:
        """Return index metadata for a table."""
        schema, table = self.identifiers.split_table_name(
            table_name,
            self.settings.database)
        sql = """
            SELECT INDEX_NAME AS index_name,
                   COLUMN_NAME AS column_name,
                   NON_UNIQUE AS non_unique,
                   SEQ_IN_INDEX AS sequence_in_index,
                   INDEX_TYPE AS index_type
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        return self._fetch_all(sql, (schema, table))

    def execute_readonly_query(
        self,
        sql: str,
        limit: int
    ) -> dict[str, Any]:
        """Execute a validated read-only query."""
        safe_sql = self.sql_validator.validate(sql)
        limited_sql = self.sql_validator.apply_limit(
            safe_sql,
            limit,
            self.settings.max_rows)
        applied_limit = self.sql_validator.bounded_limit(
            limit,
            self.settings.max_rows)
        rows = self._fetch_all(limited_sql)
        columns = list(rows[0].keys()) if rows else []
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "applied_limit": applied_limit
        }

    def current_database(self) -> dict[str, Any]:
        """Return current connection identity and grants."""
        identity_sql = """
            SELECT DATABASE() AS database_name,
                   CURRENT_USER() AS current_user,
                   USER() AS connected_user,
                   VERSION() AS mysql_version
        """
        identity_rows = self._fetch_all(identity_sql)
        grants = self._fetch_all("SHOW GRANTS FOR CURRENT_USER()")
        identity = identity_rows[0] if identity_rows else {}
        identity["grants"] = grants
        return identity

    def _fetch_all(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch rows from MySQL and serialize them."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor(dictionary=True)
                try:
                    cursor.execute(sql, params or ())
                    rows = cursor.fetchall() if cursor.with_rows else []
                finally:
                    cursor.close()
        except MySqlError as exc:
            raise ReadOnlyMcpError("MySQL read-only query failed") from exc

        return self.serializer.serialize_rows(rows)

    def _apply_session_timeout(self, conn: MySQLConnection) -> None:
        """Best-effort session timeout for SELECT execution."""
        timeout_ms = self.settings.query_timeout_seconds * 1000
        try:
            cursor = conn.cursor()
            try:
                cursor.execute("SET SESSION MAX_EXECUTION_TIME = %s", (timeout_ms,))
            finally:
                cursor.close()
        except MySqlError:
            # Niektore wersje MySQL/MariaDB nie obsluguja tej zmiennej.
            return


def _get_int_env(name: str, default: int) -> int:
    """Return a positive integer from environment variables."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ReadOnlyMcpError(f"{name} must be an integer") from exc

    if value <= 0:
        raise ReadOnlyMcpError(f"{name} must be greater than zero")

    return value


def _client() -> MySqlReadOnlyClient:
    """Return a client configured from environment variables."""
    return MySqlReadOnlyClient(McpDatabaseSettings.from_env())


def list_tables() -> list[dict[str, Any]]:
    """List tables and views in the configured database."""
    return _client().list_tables()


def describe_table(table_name: str) -> list[dict[str, Any]]:
    """Describe columns for a table or view."""
    return _client().describe_table(table_name)


def show_create_table(table_name: str) -> dict[str, Any]:
    """Show the CREATE statement for a table or view."""
    return _client().show_create_table(table_name)


def list_indexes(table_name: str) -> list[dict[str, Any]]:
    """List indexes for a table."""
    return _client().list_indexes(table_name)


def select_query(sql: str, limit: int = DEFAULT_MAX_ROWS) -> dict[str, Any]:
    """Execute one read-only SQL statement with a bounded result size."""
    return _client().execute_readonly_query(sql, limit)


def current_database() -> dict[str, Any]:
    """Return current database connection identity and grants."""
    return _client().current_database()


def build_mcp_server() -> Any:
    """Build and return the FastMCP server."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install the 'mcp' package to run this server") from exc

    mcp = FastMCP("EkstraBet MySQL Readonly")
    mcp.tool()(list_tables)
    mcp.tool()(describe_table)
    mcp.tool()(show_create_table)
    mcp.tool()(list_indexes)
    mcp.tool()(select_query)
    mcp.tool()(current_database)
    return mcp


def main(argv: list[str] | None = None) -> int:
    """Run the MCP server or print command-line help."""
    args = sys.argv[1:] if argv is None else argv
    if args in (["--help"], ["-h"]):
        print(textwrap.dedent(HELP_TEXT).strip())
        return 0

    if args:
        print(
            "Unknown arguments. Use --help for usage instructions.",
            file=sys.stderr)
        return 2

    build_mcp_server().run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
