"""Tests for migration file discovery and checksums."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.db_migrate.errors import MigrationError
from backend.db_migrate.files import file_checksum
from backend.db_migrate.files import list_migration_files
from backend.db_migrate.files import parse_migration_filename


_IGNORED_NAMES = ("README.md", "V2__x.sql", "V001_x.sql", "V001__Bad.sql")


class TestParseMigrationFilename(unittest.TestCase):
    """Filename pattern for versioned SQL migrations."""

    def test_baseline_name_has_version_and_number(self) -> None:
        parsed = parse_migration_filename("V001__baseline.sql")
        if parsed is None:
            self.fail("V001__baseline.sql should parse")
        self.assertEqual(parsed.version, "V001")
        self.assertEqual(parsed.number, 1)
        self.assertEqual(parsed.filename, "V001__baseline.sql")
        self.assertEqual(parsed.path, Path("V001__baseline.sql"))

    def test_non_matching_names_return_none(self) -> None:
        for name in _IGNORED_NAMES:
            self.assertIsNone(parse_migration_filename(name))


class TestListMigrationFiles(unittest.TestCase):
    """Directory listing, duplicates and numeric order."""

    def test_non_matching_names_are_ignored(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            for name in _IGNORED_NAMES:
                (directory / name).write_text("x", encoding="utf-8")
            (directory / "V001__baseline.sql").write_text(
                "SELECT 1;\n",
                encoding="utf-8")
            found = list_migration_files(directory)
        filenames = [item.filename for item in found]
        self.assertEqual(filenames, ["V001__baseline.sql"])
        self.assertEqual(found[0].version, "V001")
        self.assertEqual(found[0].number, 1)
        self.assertEqual(found[0].path, directory / "V001__baseline.sql")

    def test_duplicate_version_raises(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            (directory / "V002__a.sql").write_text("a;\n", encoding="utf-8")
            (directory / "V002__b.sql").write_text("b;\n", encoding="utf-8")
            with self.assertRaises(MigrationError) as caught:
                list_migration_files(directory)
        self.assertEqual(
            str(caught.exception),
            "Duplicate migration version V002")

    def test_sorts_by_version_number(self) -> None:
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            (directory / "V010__later.sql").write_text(
                "b;\n",
                encoding="utf-8")
            (directory / "V002__earlier.sql").write_text(
                "a;\n",
                encoding="utf-8")
            found = list_migration_files(directory)
        self.assertEqual([item.version for item in found], ["V002", "V010"])
        self.assertEqual([item.number for item in found], [2, 10])


class TestFileChecksum(unittest.TestCase):
    """SHA-256 stays the same when CRLF is normalized to LF."""

    def test_crlf_matches_lf(self) -> None:
        payload = b"CREATE TABLE teams (id INT);\n"
        expected = hashlib.sha256(payload).hexdigest()
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            lf_path = directory / "lf.sql"
            crlf_path = directory / "crlf.sql"
            lf_path.write_bytes(payload)
            crlf_path.write_bytes(payload.replace(b"\n", b"\r\n"))
            lf_digest = file_checksum(lf_path)
            crlf_digest = file_checksum(crlf_path)
        self.assertEqual(lf_digest, expected)
        self.assertEqual(crlf_digest, expected)
        self.assertEqual(lf_digest, crlf_digest)
        self.assertEqual(lf_digest, lf_digest.lower())


if __name__ == "__main__":
    unittest.main()
