"""SSH and direct MySQL transport shared by the local-to-prod sync scripts."""

from __future__ import annotations

import base64
import getpass
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Protocol

import mysql.connector
from mysql.connector.connection import MySQLConnection


_DEFAULT_DB_NAME = "ekstrabet"


def ensure_repo_on_path(repo_root: Path) -> None:
    """Allow `backend` imports when a script lives under scripts/sync."""
    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)


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
class ConnectionSettings:
    """How this process reaches local MySQL and production MySQL."""

    transport: str
    local_db: DbConfig
    ssh: SshTransportConfig | None
    prod_direct: DbConfig | None
    file_values: dict[str, str]


class ProdMysql(Protocol):
    """Production MySQL access (direct or via SSH)."""

    def scalar(self, sql: str) -> Any:
        """Return a single scalar from a read-only query."""

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Return rows from a read-only query."""

    def execute_script(
            self,
            sql: str,
            abort_on_error: bool = False) -> None:
        """Execute one or more SQL statements (writes)."""


def configure_stdio_utf8() -> None:
    """Configure stdin/stdout/stderr streams to use UTF-8."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def load_env_file(env_path: Path) -> dict[str, str]:
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


def env_value(
        key: str,
        file_values: dict[str, str],
        default: str = "") -> str:
    """Return a config value from process env, then file, then default."""
    return os.environ.get(key) or file_values.get(key, default)


def resolve_local_db(file_values: dict[str, str]) -> DbConfig:
    """Build local MySQL settings from .env / environment."""
    password = env_value("DB_PASSWORD", file_values)
    if not password:
        password = getpass.getpass("Local MySQL password: ")
    return DbConfig(
        host=env_value("DB_HOST", file_values, "localhost"),
        port=env_value("DB_PORT", file_values, "3306"),
        user=env_value("DB_USER", file_values, "root"),
        password=password,
        database=env_value("DB_NAME", file_values, _DEFAULT_DB_NAME))


def resolve_prod_direct(file_values: dict[str, str]) -> DbConfig:
    """Build direct production MySQL settings (tunnel / direct)."""
    password = env_value("PROD_DB_PASSWORD", file_values)
    if not password:
        password = getpass.getpass("Production MySQL password: ")
    return DbConfig(
        host=env_value("PROD_DB_HOST", file_values, "127.0.0.1"),
        port=env_value("PROD_DB_PORT", file_values, "3306"),
        user=env_value("PROD_DB_USER", file_values, "root"),
        password=password,
        database=env_value("PROD_DB_NAME", file_values, _DEFAULT_DB_NAME))


def resolve_ssh_transport(file_values: dict[str, str]) -> SshTransportConfig:
    """Build SSH transport settings for private Compose MySQL."""
    ssh_host = env_value("SYNC_SSH_HOST", file_values)
    remote_repo = env_value("SYNC_REMOTE_REPO", file_values)
    if not ssh_host or not remote_repo:
        raise ValueError(
            "SYNC_SSH_HOST and SYNC_REMOTE_REPO are required for "
            "SYNC_TRANSPORT=ssh")
    return SshTransportConfig(
        ssh_host=ssh_host,
        remote_repo=remote_repo,
        compose_file=env_value(
            "SYNC_COMPOSE_FILE", file_values, "compose.production.yml"),
        mysql_service=env_value("SYNC_MYSQL_SERVICE", file_values, "mysql"),
        remote_mysql_env=env_value(
            "SYNC_REMOTE_MYSQL_ENV",
            file_values,
            "/etc/ekstrabet/mysql.env"),
        mysql_user=env_value("SYNC_REMOTE_MYSQL_USER", file_values) or None,
        mysql_password=(
            env_value("SYNC_REMOTE_MYSQL_PASSWORD", file_values) or None),
        mysql_database=env_value(
            "SYNC_REMOTE_MYSQL_DATABASE", file_values, _DEFAULT_DB_NAME))


def load_connection_settings(
        repo_root: Path,
        sync_env_arg: str) -> ConnectionSettings:
    """Read .env and sync.env into connection settings."""
    repo_env = load_env_file(repo_root / ".env")
    if sync_env_arg:
        sync_env_path = Path(sync_env_arg)
    else:
        sync_env_path = Path(
            os.environ.get("SYNC_ENV_FILE")
            or str(repo_root / "deploy" / "sync.env"))
    merged = {**repo_env, **load_env_file(sync_env_path)}
    transport = env_value("SYNC_TRANSPORT", merged, "ssh").lower()
    ssh: SshTransportConfig | None = None
    prod_direct: DbConfig | None = None
    if transport == "ssh":
        ssh = resolve_ssh_transport(merged)
    elif transport == "direct":
        prod_direct = resolve_prod_direct(merged)
    else:
        raise ValueError(
            f"Unsupported SYNC_TRANSPORT={transport!r} "
            "(use ssh or direct)")
    return ConnectionSettings(
        transport=transport,
        local_db=resolve_local_db(merged),
        ssh=ssh,
        prod_direct=prod_direct,
        file_values=merged)


def connect(db: DbConfig) -> MySQLConnection:
    """Open a MySQL connection from DbConfig."""
    from backend.timezone import apply_mysql_session_timezone

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


def quote_ident(name: str) -> str:
    """Quote a MySQL identifier with backticks."""
    return "`" + name.replace("`", "``") + "`"


def sql_literal(value: Any) -> str:
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


def split_sql_statements(sql: str) -> list[str]:
    """Split a simple multi-statement script on semicolons."""
    parts: list[str] = []
    for chunk in sql.split(";"):
        statement = chunk.strip()
        if statement:
            parts.append(statement)
    return parts


def parse_batch_rows(output: str) -> list[tuple[str | None, ...]]:
    """Parse mysql --batch --raw output. NULL is the two-character \\N."""
    text = output.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    if not text:
        return []
    rows: list[tuple[str | None, ...]] = []
    for line in text.split("\n"):
        if line == "":
            continue
        cells: list[str | None] = []
        for cell in line.split("\t"):
            if cell == "\\N":
                cells.append(None)
            else:
                cells.append(cell)
        rows.append(tuple(cells))
    return rows


def unix_utf8_bytes(text: str) -> bytes:
    """Encode text as UTF-8 with LF-only newlines for remote bash."""
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def decode_ssh_output(payload: bytes | None) -> str:
    """Decode captured SSH stdout/stderr as UTF-8 text."""
    return (payload or b"").decode("utf-8", errors="replace")


def build_remote_mysql_bash(
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


def fetch_rows(
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


class DirectProdMysql:
    """Production access through a direct (or tunneled) TCP connection."""

    def __init__(self, db: DbConfig) -> None:
        self._db = db
        self._conn = connect(db)

    def scalar(self, sql: str) -> Any:
        """Return a single scalar from a read-only query."""
        cursor = self._conn.cursor()
        try:
            cursor.execute(sql)
            row = cursor.fetchone()
            return None if row is None else row[0]
        finally:
            cursor.close()

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Return rows, then end the read transaction."""
        cursor = self._conn.cursor()
        try:
            cursor.execute(sql)
            rows = list(cursor.fetchall())
            self._conn.rollback()
            return rows
        finally:
            cursor.close()

    def execute_script(
            self,
            sql: str,
            abort_on_error: bool = False) -> None:
        """Execute statements. A failure rolls the connection back."""
        # abort_on_error dotyczy klienta mysql po SSH; tu wyjątek wystarcza
        del abort_on_error
        cursor = self._conn.cursor()
        try:
            for statement in split_sql_statements(sql):
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

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Return batch rows. Cells stay strings; NULL is None."""
        output = self._run_mysql(
            mysql_extra=["-B", "-N", "--raw"],
            sql=sql)
        return parse_batch_rows(output)

    def execute_script(
            self,
            sql: str,
            abort_on_error: bool = False) -> None:
        """Execute one or more SQL statements (writes)."""
        # SQL idzie na stdin (tryb batch). Klient konczy prace przy
        # pierwszym bledzie SQL, o ile nie podamy --force. Flaga
        # --abort-source-on-error jest tylko w MariaDB; mysql:8.4
        # odrzuca ja jako unknown option i nie wykonuje skryptu.
        del abort_on_error
        self._run_mysql(mysql_extra=[], sql=sql)

    def _run_mysql(self, mysql_extra: list[str], sql: str) -> str:
        """Run mysql client inside the Compose mysql service over SSH."""
        cfg = self._config
        remote = build_remote_mysql_bash(cfg, mysql_extra, sql)
        command = ["ssh", cfg.ssh_host, "bash", "-s"]
        # bajty + LF: text=True na Windows wysyla CR LF i psuje pipefail
        result = subprocess.run(
            command,
            input=unix_utf8_bytes(remote),
            capture_output=True,
            check=False)
        stdout = decode_ssh_output(result.stdout)
        stderr = decode_ssh_output(result.stderr)
        if result.returncode != 0:
            detail = (stderr or stdout).strip()
            raise RuntimeError(
                f"Remote MySQL via SSH failed (exit {result.returncode}): "
                f"{detail or 'no details'}")
        return stdout


def open_prod(
        settings: ConnectionSettings
        ) -> tuple[ProdMysql, DirectProdMysql | None]:
    """Open the production client. The second item needs close()."""
    if settings.transport == "direct":
        if settings.prod_direct is None:
            raise ValueError("PROD_DB_* required for transport=direct")
        direct = DirectProdMysql(settings.prod_direct)
        return direct, direct
    if settings.ssh is None:
        raise ValueError("SSH config required for transport=ssh")
    return SshDockerProdMysql(settings.ssh), None
