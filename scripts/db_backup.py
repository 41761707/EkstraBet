"""CLI helper for MySQL database backup and restore."""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DB_NAME = "ekstrabet"
_BACKUP_NAME_PREFIX = "ekstrabet_backup_"
_BACKUP_NAME_SUFFIX = ".sql"
_DATE_FORMAT = "%d_%m_%Y"


def _configure_stdio_utf8() -> None:
    """Configure stdin/stdout/stderr streams to use UTF-8."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _load_env_file(env_path: Path) -> dict[str, str]:
    """Load key=value pairs from a .env file into a dictionary."""
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


def _env_value(key: str, file_values: dict[str, str], default: str = "") -> str:
    """Return a config value from process env, then .env, then default."""
    return os.environ.get(key) or file_values.get(key, default)


def _resolve_db_config(file_values: dict[str, str]) -> dict[str, str]:
    """Build MySQL connection settings from environment values."""
    password = _env_value("DB_PASSWORD", file_values)
    if not password:
        password = getpass.getpass("MySQL password: ")

    return {
        "host": _env_value("DB_HOST", file_values, "localhost"),
        "port": _env_value("DB_PORT", file_values, "3306"),
        "user": _env_value("DB_USER", file_values, "root"),
        "password": password,
        "database": _env_value("DB_NAME", file_values, _DEFAULT_DB_NAME)}


def _resolve_backup_dir(file_values: dict[str, str]) -> Path:
    """Return the backup directory configured via BACKUP_DIR."""
    raw_dir = _env_value("BACKUP_DIR", file_values)
    if not raw_dir:
        raise ValueError(
            "BACKUP_DIR is not set. Add it to .env or the environment.")

    backup_dir = Path(raw_dir)
    if not backup_dir.is_absolute():
        backup_dir = _REPO_ROOT / backup_dir
    return backup_dir.resolve()


def _build_backup_filename(day: datetime | None = None) -> str:
    """Build a dated backup filename matching the project convention."""
    stamp = (day or datetime.now()).strftime(_DATE_FORMAT)
    return f"{_BACKUP_NAME_PREFIX}{stamp}{_BACKUP_NAME_SUFFIX}"


def _mysql_base_args(db_config: dict[str, str]) -> list[str]:
    """Return shared mysqldump/mysql connection arguments."""
    return [
        "-h", db_config["host"],
        "-P", db_config["port"],
        "-u", db_config["user"],
        f"--password={db_config['password']}"]


def backup_database(db_config: dict[str, str], backup_dir: Path) -> Path:
    """Dump the database into a dated SQL file under BACKUP_DIR."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / _build_backup_filename()

    command = [
        "mysqldump",
        *_mysql_base_args(db_config),
        db_config["database"]]

    # zapis przez stdout, żeby uniknąć shellowego przekierowania
    with backup_path.open("w", encoding="utf-8", newline="\n") as handle:
        result = subprocess.run(
            command,
            stdout=handle,
            stderr=subprocess.PIPE,
            text=True,
            check=False)

    if result.returncode != 0:
        if backup_path.exists() and backup_path.stat().st_size == 0:
            backup_path.unlink(missing_ok=True)
        detail = (result.stderr or "").strip() or "unknown mysqldump error"
        raise RuntimeError(f"Backup failed: {detail}")

    return backup_path


def _resolve_restore_path(backup_dir: Path, target: str) -> Path:
    """Resolve a restore target to an existing SQL file path."""
    candidate = Path(target)
    if not candidate.is_absolute():
        candidate = backup_dir / candidate

    candidate = candidate.resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"Backup file not found: {candidate}")
    return candidate


def restore_database(
        db_config: dict[str, str],
        backup_dir: Path,
        target: str) -> Path:
    """Restore the database from a SQL dump under BACKUP_DIR."""
    backup_path = _resolve_restore_path(backup_dir, target)
    command = [
        "mysql",
        *_mysql_base_args(db_config),
        db_config["database"]]

    with backup_path.open("r", encoding="utf-8") as handle:
        result = subprocess.run(
            command,
            stdin=handle,
            stderr=subprocess.PIPE,
            text=True,
            check=False)

    if result.returncode != 0:
        detail = (result.stderr or "").strip() or "unknown mysql error"
        raise RuntimeError(f"Restore failed: {detail}")

    return backup_path


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Backup and restore the EkstraBet MySQL database")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "backup",
        help="Create a dated SQL dump in BACKUP_DIR")

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore the database from a SQL dump in BACKUP_DIR")
    restore_parser.add_argument(
        "file",
        help=(
            "Backup filename or path "
            "(relative paths are resolved against BACKUP_DIR)"))
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run backup or restore based on CLI arguments."""
    _configure_stdio_utf8()
    parser = _build_parser()
    args = parser.parse_args(argv)

    file_values = _load_env_file(_REPO_ROOT / ".env")
    try:
        db_config = _resolve_db_config(file_values)
        backup_dir = _resolve_backup_dir(file_values)
        if args.command == "backup":
            path = backup_database(db_config, backup_dir)
            print(f"Backup created: {path}")
            return 0

        path = restore_database(db_config, backup_dir, args.file)
        print(f"Database restored from: {path}")
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
