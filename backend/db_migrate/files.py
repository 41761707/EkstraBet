"""Read versioned SQL migration files and their checksums."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from backend.config import REPO_ROOT
from backend.db_migrate.errors import MigrationError


MIGRATIONS_DIR: Path = REPO_ROOT / "sql" / "migrations"

_MIGRATION_FILENAME_RE = re.compile(r"^V(\d{3})__[a-z0-9_]+\.sql$")


@dataclass(frozen=True)
class MigrationFile:
    """One versioned SQL file discovered in the migrations directory."""

    version: str
    number: int
    filename: str
    path: Path


def parse_migration_filename(filename: str) -> MigrationFile | None:
    """Return a parsed migration, or None if the name does not match."""
    match = _MIGRATION_FILENAME_RE.match(filename)
    if match is None:
        return None
    digits = match.group(1)
    return MigrationFile(
        version=f"V{digits}",
        number=int(digits),
        filename=filename,
        path=Path(filename))


def list_migration_files(directory: Path) -> list[MigrationFile]:
    """Return matching migration files sorted by version number.

    Names that do not match the migration pattern are ignored. Two files
    with the same version number raise ``MigrationError``.
    """
    by_number: dict[int, MigrationFile] = {}
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        parsed = parse_migration_filename(entry.name)
        if parsed is None:
            continue
        if parsed.number in by_number:
            raise MigrationError(
                f"Duplicate migration version {parsed.version}")
        by_number[parsed.number] = MigrationFile(
            version=parsed.version,
            number=parsed.number,
            filename=parsed.filename,
            path=entry)
    return [by_number[number] for number in sorted(by_number)]


def file_checksum(path: Path) -> str:
    """Return lowercase SHA-256 hex after replacing CRLF with LF."""
    # CRLF na Windows i LF na VPS mają dać ten sam checksum
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()
