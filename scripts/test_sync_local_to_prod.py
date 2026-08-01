"""Unit tests for SZP-21 sync SQL helpers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from datetime import datetime
from datetime import timedelta
from pathlib import Path


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
