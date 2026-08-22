"""Unit tests for SZP-21 sync SQL helpers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


_SCRIPT = Path(__file__).resolve().parent / "sync_local_to_prod.py"


def _load_module():
    """Load sync_local_to_prod.py as a module without package install."""
    spec = importlib.util.spec_from_file_location(
        "sync_local_to_prod", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sql_literal_and_upsert_batch() -> None:
    """Upsert SQL should escape values and update non-PK columns."""
    mod = _load_module()
    assert mod._sql_literal(None) == "NULL"
    assert mod._sql_literal(True) == "1"
    assert mod._sql_literal("O'Brien") == "'O''Brien'"
    assert mod._sql_literal(date(2026, 8, 1)) == "'2026-08-01'"
    assert (
        mod._sql_literal(datetime(2026, 8, 1, 12, 30, 0))
        == "'2026-08-01 12:30:00'")

    sql = mod.build_upsert_sql(
        "matches",
        ["id", "result", "home_team_goals"],
        [(1, "1", 2), (2, "X", 0)],
        "id")
    assert "INSERT INTO `matches`" in sql
    assert "AS new ON DUPLICATE KEY UPDATE" in sql
    assert "`result`=new.`result`" in sql
    assert "`id`=new.`id`" not in sql
    assert "(1, '1', 2), (2, 'X', 0)" in sql


def test_window_cutoff_days() -> None:
    """Window cutoff should be today minus configured days."""
    mod = _load_module()
    assert mod._window_cutoff(3) == date.today() - timedelta(days=3)


def test_excluded_and_table_order() -> None:
    """Users/gamblers stay excluded; dictionaries precede matches."""
    mod = _load_module()
    names = [spec.name for spec in mod._selected_specs(None)]
    assert "users" not in names
    assert "gamblers" not in names
    assert names.index("teams") < names.index("matches")
    assert names.index("matches") < names.index("odds")
    assert names.index("predictions") < names.index("final_predictions")


def _sample_ssh_config(mod):
    """Build a minimal SSH transport config for bash-snippet tests."""
    return mod.SshTransportConfig(
        ssh_host="user@host",
        remote_repo="/repo",
        compose_file="compose.production.yml",
        mysql_service="mysql",
        remote_mysql_env="/etc/ekstrabet/mysql.env",
        mysql_user=None,
        mysql_password=None,
        mysql_database="ekstrabet")


def test_remote_bash_uses_unix_newlines() -> None:
    """Remote bash must use LF only; CR breaks set -o pipefail."""
    mod = _load_module()
    script = mod._build_remote_mysql_bash(
        _sample_ssh_config(mod), ["-N"], "SELECT 1")
    assert "\r" not in script
    assert script.startswith("set -euo pipefail\n")
    assert 'export MYSQL_PWD="${MYSQL_ROOT_PASSWORD}"' in script
    assert "export MYSQL_USER=root" in script
    encoded = mod._unix_utf8_bytes("set -euo pipefail\r\nset -a\r")
    assert encoded == b"set -euo pipefail\nset -a\n"
    assert b"\r" not in encoded


def test_run_mysql_sends_binary_lf_stdin() -> None:
    """SSH stdin must be LF bytes; text mode on Windows injects CR."""
    mod = _load_module()
    captured: dict[str, object] = {}

    def fake_run(*_args, **kwargs):
        captured["input"] = kwargs.get("input")
        captured["text"] = kwargs.get("text")
        return SimpleNamespace(returncode=0, stdout=b"1\n", stderr=b"")

    prod = mod.SshDockerProdMysql(_sample_ssh_config(mod))
    with patch.object(mod.subprocess, "run", fake_run):
        value = prod.scalar("SELECT 1")

    payload = captured["input"]
    assert captured["text"] in (None, False)
    assert isinstance(payload, bytes)
    assert b"\r" not in payload
    assert payload.startswith(b"set -euo pipefail\n")
    assert value == 1


def test_remote_bash_exports_explicit_mysql_password() -> None:
    """Explicit SYNC_REMOTE_MYSQL_* credentials must also be exported."""
    mod = _load_module()
    cfg = mod.SshTransportConfig(
        ssh_host="user@host",
        remote_repo="/repo",
        compose_file="compose.production.yml",
        mysql_service="mysql",
        remote_mysql_env="/etc/ekstrabet/mysql.env",
        mysql_user="ekstrabet_sync",
        mysql_password="secret",
        mysql_database="ekstrabet")
    script = mod._build_remote_mysql_bash(cfg, [], "SELECT 1")
    assert "export MYSQL_USER=ekstrabet_sync" in script
    assert "export MYSQL_PWD=secret" in script
