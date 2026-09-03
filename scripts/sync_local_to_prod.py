"""Incremental local -> production MySQL sync (SZP-21).

Strategies:
  - dictionary: id > max(id) on prod; optional full reconcile
  - window: matches by game_date window (+ new ids); children by match_id
  - append: id > max(id) on prod only

Production MySQL stays private: default transport is SSH + docker compose exec.
Does not sync users / gamblers / parlays (handled separately).
"""

from __future__ import annotations

import argparse
import base64
import getpass
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Protocol

import mysql.connector
from mysql.connector.connection import MySQLConnection


_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.timezone import apply_mysql_session_timezone

_DEFAULT_DB_NAME = "ekstrabet"
_DEFAULT_WINDOW_DAYS = 3
_DEFAULT_BATCH_SIZE = 200
_EXCLUDED_TABLES = frozenset({
    "users",
    "gamblers",
    "gambler_parlays",
    "parlay_events",
    "model_training_runs"})


class SyncKind(str, Enum):
    """How rows for a table are selected for sync."""

    DICTIONARY = "dictionary"
    WINDOW = "window"
    WINDOW_CHILD = "window_child"
    APPEND = "append"


@dataclass(frozen=True)
class TableSpec:
    """Sync policy for one base table."""

    name: str
    kind: SyncKind
    # Dla WINDOW_CHILD: kolumna FK do matches (zwykle match_id)
    match_fk: str | None = None
    # final_predictions laczy sie przez predictions
    via_predictions: bool = False


# Kolejnosc ma znaczenie (rodzice FK przed dziecmi).
_TABLE_SPECS: tuple[TableSpec, ...] = (
    # --- slowniki ---
    TableSpec("sports", SyncKind.DICTIONARY),
    TableSpec("countries", SyncKind.DICTIONARY),
    TableSpec("seasons", SyncKind.DICTIONARY),
    TableSpec("special_rounds", SyncKind.DICTIONARY),
    TableSpec("leagues", SyncKind.DICTIONARY),
    TableSpec("conferences", SyncKind.DICTIONARY),
    TableSpec("divisions", SyncKind.DICTIONARY),
    TableSpec("conference_divisions", SyncKind.DICTIONARY),
    TableSpec("teams", SyncKind.DICTIONARY),
    TableSpec("division_teams", SyncKind.DICTIONARY),
    TableSpec("players", SyncKind.DICTIONARY),
    TableSpec("bookmakers", SyncKind.DICTIONARY),
    TableSpec("events", SyncKind.DICTIONARY),
    TableSpec("event_families", SyncKind.DICTIONARY),
    TableSpec("event_family_mappings", SyncKind.DICTIONARY),
    TableSpec("event_model_families", SyncKind.DICTIONARY),
    TableSpec("models", SyncKind.DICTIONARY),
    TableSpec("season_projection_runs", SyncKind.DICTIONARY),
    TableSpec("season_projection_team_rows", SyncKind.DICTIONARY),
    TableSpec("schedule", SyncKind.DICTIONARY),
    # male tabele "stan biezacy" — append + --full-dict
    TableSpec("basketball_current_roster", SyncKind.DICTIONARY),
    TableSpec("hockey_rosters", SyncKind.DICTIONARY),
    TableSpec("player_name_mappings", SyncKind.DICTIONARY),
    # --- mecze (okno daty) ---
    TableSpec("matches", SyncKind.WINDOW),
    # --- dzieci meczow ---
    TableSpec("odds", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "basketball_matches_add", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "hockey_matches_add", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "basketball_match_roster", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "basketball_match_player_stats",
        SyncKind.WINDOW_CHILD,
        match_fk="match_id"),
    TableSpec(
        "hockey_match_rosters", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "hockey_match_player_stats",
        SyncKind.WINDOW_CHILD,
        match_fk="match_id"),
    TableSpec(
        "hockey_match_events", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "football_player_stats", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "football_special_round_add",
        SyncKind.WINDOW_CHILD,
        match_fk="match_id"),
    TableSpec(
        "player_props_lines", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec("predictions", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "final_predictions", SyncKind.WINDOW_CHILD, via_predictions=True),
    TableSpec("bets", SyncKind.WINDOW_CHILD, match_fk="match_id"),
    TableSpec(
        "match_model_assessments",
        SyncKind.WINDOW_CHILD,
        match_fk="match_id"),
    # --- append-only ---
    TableSpec("transfers", SyncKind.APPEND))


@dataclass(frozen=True)
class DbConfig:
    """MySQL connection settings."""

    host: str
    port: str
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class SshTransportConfig:
    """SSH + Compose path to production MySQL."""

    ssh_host: str
    remote_repo: str
    compose_file: str
    mysql_service: str
    remote_mysql_env: str
    mysql_user: str | None
    mysql_password: str | None
    mysql_database: str


@dataclass(frozen=True)
class SyncSettings:
    """Runtime sync policy and transport."""

    transport: str
    window_days: int
    batch_size: int
    full_dict: bool
    apply: bool
    table_filter: frozenset[str] | None
    local_db: DbConfig
    ssh: SshTransportConfig | None
    prod_direct: DbConfig | None


class ProdMysql(Protocol):
    """Production MySQL access (direct or via SSH)."""

    def scalar(self, sql: str) -> Any:
        """Return a single scalar from a read-only query."""

    def execute_script(self, sql: str) -> None:
        """Execute one or more SQL statements (writes)."""


def _configure_stdio_utf8() -> None:
    """Configure stdin/stdout/stderr streams to use UTF-8."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _load_env_file(env_path: Path) -> dict[str, str]:
    """Load key=value pairs from an env file into a dictionary."""
    values: dict[str, str] = {}
    if not env_path.is_file():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value
    return values


def _env_value(
        key: str,
        file_values: dict[str, str],
        default: str = "") -> str:
    """Return a config value from process env, then file, then default."""
    return os.environ.get(key) or file_values.get(key, default)


def _resolve_local_db(file_values: dict[str, str]) -> DbConfig:
    """Build local MySQL settings from .env / environment."""
    password = _env_value("DB_PASSWORD", file_values)
    if not password:
        password = getpass.getpass("Local MySQL password: ")
    return DbConfig(
        host=_env_value("DB_HOST", file_values, "localhost"),
        port=_env_value("DB_PORT", file_values, "3306"),
        user=_env_value("DB_USER", file_values, "root"),
        password=password,
        database=_env_value("DB_NAME", file_values, _DEFAULT_DB_NAME))


def _resolve_prod_direct(file_values: dict[str, str]) -> DbConfig:
    """Build direct production MySQL settings (tunnel / direct)."""
    password = _env_value("PROD_DB_PASSWORD", file_values)
    if not password:
        password = getpass.getpass("Production MySQL password: ")
    return DbConfig(
        host=_env_value("PROD_DB_HOST", file_values, "127.0.0.1"),
        port=_env_value("PROD_DB_PORT", file_values, "3306"),
        user=_env_value("PROD_DB_USER", file_values, "root"),
        password=password,
        database=_env_value("PROD_DB_NAME", file_values, _DEFAULT_DB_NAME))


def _resolve_ssh_transport(file_values: dict[str, str]) -> SshTransportConfig:
    """Build SSH transport settings for private Compose MySQL."""
    ssh_host = _env_value("SYNC_SSH_HOST", file_values)
    remote_repo = _env_value("SYNC_REMOTE_REPO", file_values)
    if not ssh_host or not remote_repo:
        raise ValueError(
            "SYNC_SSH_HOST and SYNC_REMOTE_REPO are required for "
            "SYNC_TRANSPORT=ssh")
    return SshTransportConfig(
        ssh_host=ssh_host,
        remote_repo=remote_repo,
        compose_file=_env_value(
            "SYNC_COMPOSE_FILE", file_values, "compose.production.yml"),
        mysql_service=_env_value("SYNC_MYSQL_SERVICE", file_values, "mysql"),
        remote_mysql_env=_env_value(
            "SYNC_REMOTE_MYSQL_ENV", file_values, "/etc/ekstrabet/mysql.env"),
        mysql_user=_env_value("SYNC_REMOTE_MYSQL_USER", file_values) or None,
        mysql_password=(
            _env_value("SYNC_REMOTE_MYSQL_PASSWORD", file_values) or None),
        mysql_database=_env_value(
            "SYNC_REMOTE_MYSQL_DATABASE", file_values, _DEFAULT_DB_NAME))


def _connect(db: DbConfig) -> MySQLConnection:
    """Open a MySQL connection from DbConfig."""
    conn = mysql.connector.connect(
        host=db.host,
        port=int(db.port),
        user=db.user,
        password=db.password,
        database=db.database,
        charset="utf8mb4",
        use_unicode=True,
        autocommit=False)
    apply_mysql_session_timezone(conn)
    return conn


class DirectProdMysql:
    """Production access through a direct (or tunneled) TCP connection."""

    def __init__(self, db: DbConfig) -> None:
        self._db = db
        self._conn = _connect(db)

    def scalar(self, sql: str) -> Any:
        """Return a single scalar from a read-only query."""
        cursor = self._conn.cursor()
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            return None if row is None else row[0]
        finally:
            cursor.close()

    def execute_script(self, sql: str) -> None:
        """Execute one or more SQL statements (writes)."""
        cursor = self._conn.cursor()
        try:
            for statement in _split_sql_statements(sql):
                cursor.execute(statement)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()


class SshDockerProdMysql:
    """Production access via SSH + docker compose exec mysql."""

    def __init__(self, config: SshTransportConfig) -> None:
        self._config = config

    def scalar(self, sql: str) -> Any:
        """Return a single scalar from a read-only query."""
        # -N: bez naglowkow; SQL przez stdin (bezpieczne cudzyslowy)
        output = self._run_mysql(mysql_extra=["-N"], sql=sql)
        text = output.strip()
        if not text or text.upper() == "NULL":
            return None
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
        try:
            return float(text)
        except ValueError:
            return text

    def execute_script(self, sql: str) -> None:
        """Execute one or more SQL statements (writes)."""
        self._run_mysql(mysql_extra=[], sql=sql)

    def _run_mysql(self, mysql_extra: list[str], sql: str) -> str:
        """Run mysql client inside the Compose mysql service over SSH."""
        cfg = self._config
        remote = _build_remote_mysql_bash(cfg, mysql_extra, sql)
        command = ["ssh", cfg.ssh_host, "bash", "-s"]
        # bajty + LF: text=True na Windows wysyla CR LF i psuje pipefail
        result = subprocess.run(
            command,
            input=_unix_utf8_bytes(remote),
            capture_output=True,
            check=False)
        stdout = _decode_ssh_output(result.stdout)
        stderr = _decode_ssh_output(result.stderr)
        if result.returncode != 0:
            detail = (stderr or stdout).strip()
            raise RuntimeError(
                f"Remote MySQL via SSH failed (exit {result.returncode}): "
                f"{detail or 'no details'}")
        return stdout


def _build_remote_mysql_bash(
        cfg: SshTransportConfig,
        mysql_extra: list[str],
        sql: str) -> str:
    """Build a remote bash snippet that runs mysql in the Compose service."""
    repo = shlex.quote(cfg.remote_repo)
    compose = shlex.quote(cfg.compose_file)
    service = shlex.quote(cfg.mysql_service)
    env_file = shlex.quote(cfg.remote_mysql_env)
    database = shlex.quote(cfg.mysql_database)
    extra = " ".join(shlex.quote(part) for part in mysql_extra)
    # SQL w base64 — unikamy heredoc/quoting i kolizji ze stdin bash -s
    encoded = base64.b64encode(sql.encode("utf-8")).decode("ascii")
    encoded_q = shlex.quote(encoded)

    if cfg.mysql_user and cfg.mysql_password:
        user = shlex.quote(cfg.mysql_user)
        # haslo w env sesji bash na VPS, nie w lokalnym ps
        password_q = shlex.quote(cfg.mysql_password)
        auth = (
            f"export MYSQL_USER={user}\n"
            f"export MYSQL_PWD={password_q}\n")
    else:
        auth = (
            "export MYSQL_USER=root\n"
            'export MYSQL_PWD="${MYSQL_ROOT_PASSWORD}"\n')

    # APP_ORIGIN wymagane przez interpolacje compose.production.yml
    # MYSQL_PWD musi byc w env: compose exec -e MYSQL_PWD czyta proces
    script = f"""set -euo pipefail
set -a
# shellcheck disable=SC1090
source {env_file}
set +a
export APP_ORIGIN="${{APP_ORIGIN:-https://localhost}}"
{auth}
if [ -z "${{MYSQL_PWD}}" ]; then
  echo "MYSQL_PWD is empty after loading {env_file}" >&2
  exit 1
fi
cd {repo}
printf '%s' {encoded_q} | base64 -d | docker compose -f {compose} exec -T \\
  -e MYSQL_PWD \\
  {service} mysql -u"$MYSQL_USER" {database} {extra}
"""
    return script.replace("\r\n", "\n").replace("\r", "\n")


def _unix_utf8_bytes(text: str) -> bytes:
    """Encode text as UTF-8 with LF-only newlines for remote bash."""
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _decode_ssh_output(payload: bytes | None) -> str:
    """Decode captured SSH stdout/stderr as UTF-8 text."""
    return (payload or b"").decode("utf-8", errors="replace")


def _split_sql_statements(sql: str) -> list[str]:
    """Split a simple multi-statement script on semicolons."""
    parts: list[str] = []
    for chunk in sql.split(";"):
        statement = chunk.strip()
        if statement:
            parts.append(statement)
    return parts


def _quote_ident(name: str) -> str:
    """Quote a MySQL identifier with backticks."""
    return "`" + name.replace("`", "``") + "`"


def _sql_literal(value: Any) -> str:
    """Render a Python value as a MySQL literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, datetime):
        return "'" + value.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(value, date):
        return "'" + value.strftime("%Y-%m-%d") + "'"
    if isinstance(value, bytes):
        return "0x" + value.hex()
    text = str(value)
    escaped = (
        text.replace("\\", "\\\\")
        .replace("'", "''")
        .replace("\x00", "\\0")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\x1a", "\\Z"))
    return "'" + escaped + "'"


def build_upsert_sql(
        table: str,
        columns: list[str],
        rows: list[tuple[Any, ...]],
        pk_column: str) -> str:
    """Build INSERT ... ON DUPLICATE KEY UPDATE for a batch of rows."""
    if not rows:
        return ""
    if not columns:
        raise ValueError(f"No columns for table {table}")

    col_sql = ", ".join(_quote_ident(col) for col in columns)
    values_sql = ", ".join(
        "(" + ", ".join(_sql_literal(v) for v in row) + ")"
        for row in rows)
    # aktualizujemy wszystkie kolumny poza PK (skladnia MySQL 8.0.19+)
    updates = [
        f"{_quote_ident(col)}=new.{_quote_ident(col)}"
        for col in columns
        if col.lower() != pk_column.lower()]
    if not updates:
        # tabela tylko z PK — INSERT IGNORE wystarczy przy kolizji
        return (
            f"INSERT IGNORE INTO {_quote_ident(table)} ({col_sql}) "
            f"VALUES {values_sql}")
    return (
        f"INSERT INTO {_quote_ident(table)} ({col_sql}) VALUES {values_sql} "
        f"AS new ON DUPLICATE KEY UPDATE " + ", ".join(updates))


def _table_exists(conn: MySQLConnection, table: str) -> bool:
    """Return True when the table exists in the connected database."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s LIMIT 1",
            (table,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def _primary_key_column(conn: MySQLConnection, table: str) -> str:
    """Return the single-column primary key name for a table."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT column_name FROM information_schema.key_column_usage "
            "WHERE table_schema = DATABASE() AND table_name = %s "
            "AND constraint_name = 'PRIMARY' "
            "ORDER BY ordinal_position",
            (table,))
        rows = cursor.fetchall()
    finally:
        cursor.close()
    if not rows:
        raise RuntimeError(f"Table {table} has no PRIMARY KEY")
    if len(rows) > 1:
        raise RuntimeError(
            f"Table {table} has a composite PRIMARY KEY; not supported")
    return str(rows[0][0])


def _table_columns(conn: MySQLConnection, table: str) -> list[str]:
    """Return ordered column names for a table."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s "
            "ORDER BY ordinal_position",
            (table,))
        return [str(row[0]) for row in cursor.fetchall()]
    finally:
        cursor.close()


def _prod_max_id(prod: ProdMysql, table: str, pk_column: str) -> int:
    """Read COALESCE(MAX(pk), 0) from production."""
    sql = (
        f"SELECT COALESCE(MAX({_quote_ident(pk_column)}), 0) "
        f"FROM {_quote_ident(table)}")
    value = prod.scalar(sql)
    return int(value or 0)


def _fetch_rows(
        conn: MySQLConnection,
        sql: str,
        params: tuple[Any, ...] | None = None) -> list[tuple[Any, ...]]:
    """Fetch all rows for a parameterized SELECT."""
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or ())
        return list(cursor.fetchall())
    finally:
        cursor.close()


def _window_cutoff(window_days: int) -> date:
    """Return the inclusive lower bound date for the mutable match window."""
    return date.today() - timedelta(days=window_days)


def _select_dictionary_rows(
        conn: MySQLConnection,
        table: str,
        columns: list[str],
        pk_column: str,
        max_id: int,
        full_dict: bool) -> list[tuple[Any, ...]]:
    """Select dictionary rows (new ids, or full table when full_dict)."""
    col_sql = ", ".join(_quote_ident(c) for c in columns)
    if full_dict:
        sql = (
            f"SELECT {col_sql} FROM {_quote_ident(table)} "
            f"ORDER BY {_quote_ident(pk_column)}")
        return _fetch_rows(conn, sql)
    sql = (
        f"SELECT {col_sql} FROM {_quote_ident(table)} "
        f"WHERE {_quote_ident(pk_column)} > %s "
        f"ORDER BY {_quote_ident(pk_column)}")
    return _fetch_rows(conn, sql, (max_id,))


def _select_append_rows(
        conn: MySQLConnection,
        table: str,
        columns: list[str],
        pk_column: str,
        max_id: int) -> list[tuple[Any, ...]]:
    """Select append-only rows with id greater than production max."""
    col_sql = ", ".join(_quote_ident(c) for c in columns)
    sql = (
        f"SELECT {col_sql} FROM {_quote_ident(table)} "
        f"WHERE {_quote_ident(pk_column)} > %s "
        f"ORDER BY {_quote_ident(pk_column)}")
    return _fetch_rows(conn, sql, (max_id,))


def _select_matches_window_rows(
        conn: MySQLConnection,
        columns: list[str],
        pk_column: str,
        max_id: int,
        cutoff: date) -> list[tuple[Any, ...]]:
    """Select matches in the date window or with id newer than prod max."""
    col_sql = ", ".join(_quote_ident(c) for c in columns)
    sql = (
        f"SELECT {col_sql} FROM {_quote_ident('matches')} "
        f"WHERE {_quote_ident(pk_column)} > %s "
        f"OR DATE({_quote_ident('game_date')}) >= %s "
        f"ORDER BY {_quote_ident(pk_column)}")
    return _fetch_rows(conn, sql, (max_id, cutoff))


def _select_window_child_rows(
        conn: MySQLConnection,
        spec: TableSpec,
        columns: list[str],
        pk_column: str,
        max_id: int,
        cutoff: date) -> list[tuple[Any, ...]]:
    """Select child rows for window matches or new ids."""
    col_sql = ", ".join(
        f"t.{_quote_ident(c)}" for c in columns)
    if spec.via_predictions:
        sql = (
            f"SELECT {col_sql} FROM {_quote_ident(spec.name)} t "
            f"INNER JOIN {_quote_ident('predictions')} p "
            f"ON p.{_quote_ident('id')} = t.{_quote_ident('predictions_id')} "
            f"INNER JOIN {_quote_ident('matches')} m "
            f"ON m.{_quote_ident('id')} = p.{_quote_ident('match_id')} "
            f"WHERE t.{_quote_ident(pk_column)} > %s "
            f"OR DATE(m.{_quote_ident('game_date')}) >= %s "
            f"ORDER BY t.{_quote_ident(pk_column)}")
        return _fetch_rows(conn, sql, (max_id, cutoff))

    if not spec.match_fk:
        raise ValueError(
            f"WINDOW_CHILD table {spec.name} needs match_fk "
            "or via_predictions")
    fk = spec.match_fk
    sql = (
        f"SELECT {col_sql} FROM {_quote_ident(spec.name)} t "
        f"INNER JOIN {_quote_ident('matches')} m "
        f"ON m.{_quote_ident('id')} = t.{_quote_ident(fk)} "
        f"WHERE t.{_quote_ident(pk_column)} > %s "
        f"OR DATE(m.{_quote_ident('game_date')}) >= %s "
        f"ORDER BY t.{_quote_ident(pk_column)}")
    return _fetch_rows(conn, sql, (max_id, cutoff))


def _apply_batches(
        prod: ProdMysql,
        table: str,
        columns: list[str],
        pk_column: str,
        rows: list[tuple[Any, ...]],
        batch_size: int,
        apply: bool) -> int:
    """Upsert rows in batches; return number of rows processed."""
    if not rows:
        return 0
    if not apply:
        return len(rows)

    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        upsert = build_upsert_sql(table, columns, batch, pk_column)
        # jedna sesja SSH/MySQL: FK off + upsert + FK on
        script = (
            "SET FOREIGN_KEY_CHECKS=0;\n"
            f"{upsert};\n"
            "SET FOREIGN_KEY_CHECKS=1;\n")
        prod.execute_script(script)
    return len(rows)


def _selected_specs(
        table_filter: frozenset[str] | None) -> list[TableSpec]:
    """Return table specs, optionally filtered by name."""
    specs = [spec for spec in _TABLE_SPECS if spec.name not in _EXCLUDED_TABLES]
    if table_filter is None:
        return specs
    unknown = sorted(table_filter - {spec.name for spec in specs})
    if unknown:
        raise ValueError(
            "Unknown or excluded table(s): " + ", ".join(unknown))
    return [spec for spec in specs if spec.name in table_filter]


def sync_table(
        local: MySQLConnection,
        prod: ProdMysql,
        spec: TableSpec,
        settings: SyncSettings,
        cutoff: date) -> tuple[str, int, int]:
    """Sync one table; return (name, prod_max_id, row_count)."""
    if not _table_exists(local, spec.name):
        print(f"SKIP {spec.name}: missing on local", flush=True)
        return spec.name, 0, 0

    pk_column = _primary_key_column(local, spec.name)
    columns = _table_columns(local, spec.name)
    max_id = _prod_max_id(prod, spec.name, pk_column)

    if spec.kind == SyncKind.DICTIONARY:
        rows = _select_dictionary_rows(
            local, spec.name, columns, pk_column, max_id, settings.full_dict)
    elif spec.kind == SyncKind.APPEND:
        rows = _select_append_rows(
            local, spec.name, columns, pk_column, max_id)
    elif spec.kind == SyncKind.WINDOW:
        rows = _select_matches_window_rows(
            local, columns, pk_column, max_id, cutoff)
    elif spec.kind == SyncKind.WINDOW_CHILD:
        rows = _select_window_child_rows(
            local, spec, columns, pk_column, max_id, cutoff)
    else:
        raise RuntimeError(f"Unhandled sync kind: {spec.kind}")

    count = _apply_batches(
        prod,
        spec.name,
        columns,
        pk_column,
        rows,
        settings.batch_size,
        settings.apply)
    mode = "APPLY" if settings.apply else "DRY-RUN"
    print(
        f"{mode} {spec.name} [{spec.kind.value}]: "
        f"prod_max_{pk_column}={max_id}, rows={count}",
        flush=True)
    return spec.name, max_id, count


def run_sync(settings: SyncSettings) -> int:
    """Run the full sync pipeline; return process exit code."""
    specs = _selected_specs(settings.table_filter)
    cutoff = _window_cutoff(settings.window_days)
    local = _connect(settings.local_db)
    prod: ProdMysql
    direct: DirectProdMysql | None = None

    try:
        if settings.transport == "direct":
            if settings.prod_direct is None:
                raise ValueError("PROD_DB_* required for transport=direct")
            direct = DirectProdMysql(settings.prod_direct)
            prod = direct
        else:
            if settings.ssh is None:
                raise ValueError("SSH config required for transport=ssh")
            prod = SshDockerProdMysql(settings.ssh)

        print(
            f"Sync start: transport={settings.transport}, "
            f"window_days={settings.window_days}, cutoff={cutoff}, "
            f"full_dict={settings.full_dict}, apply={settings.apply}",
            flush=True)
        total = 0
        for spec in specs:
            _, _, count = sync_table(local, prod, spec, settings, cutoff)
            total += count
        print(f"Done. Total rows considered: {total}", flush=True)
        return 0
    finally:
        local.close()
        if direct is not None:
            direct.close()


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "SZP-21: incremental sync from local MySQL to production "
            "(append / date window / dictionaries)"))
    parser.add_argument(
        "--sync-env",
        default="",
        help="Path to sync.env (default: SYNC_ENV_FILE or deploy/sync.env)")
    parser.add_argument(
        "--window-days",
        type=int,
        default=None,
        help=f"Mutable match window in days (default {_DEFAULT_WINDOW_DAYS})")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"Upsert batch size (default {_DEFAULT_BATCH_SIZE})")
    parser.add_argument(
        "--full-dict",
        action="store_true",
        help="Full upsert of dictionary tables (not only id > max)")
    parser.add_argument(
        "--tables",
        default="",
        help="Comma-separated table subset (default: all managed tables)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write to production (default is dry-run)")
    return parser


def _resolve_settings(args: argparse.Namespace) -> SyncSettings:
    """Merge CLI flags with .env and sync.env into SyncSettings."""
    repo_env = _load_env_file(_REPO_ROOT / ".env")
    sync_env_path = (
        Path(args.sync_env)
        if args.sync_env
        else Path(
            os.environ.get("SYNC_ENV_FILE")
            or str(_REPO_ROOT / "deploy" / "sync.env")))
    sync_values = _load_env_file(sync_env_path)
    merged = {**repo_env, **sync_values}

    transport = _env_value("SYNC_TRANSPORT", merged, "ssh").lower()
    window_days = args.window_days
    if window_days is None:
        window_days = int(
            _env_value("SYNC_WINDOW_DAYS", merged, str(_DEFAULT_WINDOW_DAYS)))
    batch_size = args.batch_size
    if batch_size is None:
        batch_size = int(
            _env_value("SYNC_BATCH_SIZE", merged, str(_DEFAULT_BATCH_SIZE)))

    table_filter: frozenset[str] | None = None
    if args.tables.strip():
        table_filter = frozenset(
            part.strip() for part in args.tables.split(",") if part.strip())

    ssh: SshTransportConfig | None = None
    prod_direct: DbConfig | None = None
    if transport == "ssh":
        ssh = _resolve_ssh_transport(merged)
    elif transport == "direct":
        prod_direct = _resolve_prod_direct(merged)
    else:
        raise ValueError(
            f"Unsupported SYNC_TRANSPORT={transport!r} "
            "(use ssh or direct)")

    return SyncSettings(
        transport=transport,
        window_days=window_days,
        batch_size=batch_size,
        full_dict=args.full_dict,
        apply=args.apply,
        table_filter=table_filter,
        local_db=_resolve_local_db(merged),
        ssh=ssh,
        prod_direct=prod_direct)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for SZP-21 local -> production sync."""
    _configure_stdio_utf8()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        settings = _resolve_settings(args)
        return run_sync(settings)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except mysql.connector.Error as exc:
        print(f"MySQL error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
