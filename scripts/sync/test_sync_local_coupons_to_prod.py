"""Tests for system-coupon copy without surrogate ids."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path


_DIR = Path(__file__).resolve().parent
_SCRIPT = _DIR / "sync_local_coupons_to_prod.py"
_TRANSPORT = _DIR / "mysql_transport.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_coupon():
    _load(_TRANSPORT, "mysql_transport")
    return _load(_SCRIPT, "sync_local_coupons_to_prod")


def _leg(mod, match_id: int, event_ids: tuple[int, ...]):
    return mod.LegPayload(
        match_id=match_id,
        event_ids=event_ids,
        odds="1.80",
        bookmaker_id=2,
        source="catalog",
        outcome=None)


def _coupon(mod, username: str = "agent-kuponowy"):
    return mod.CouponPayload(
        username=username,
        created_at=datetime(2026, 8, 1, 12, 0, 0),
        stake_amount="10.00",
        stake_units="1.0000",
        stake_input_mode="units",
        combined_odds="1.80",
        settled=0,
        outcome=None,
        profit=None,
        legs=(_leg(mod, 10, (7,)),))


def _account(mod, user_id: int = 9, is_system: bool = True):
    return mod.ProdAccount(
        user_id=user_id,
        is_system=is_system,
        has_bankroll=True)


def _insert_heads(sql: str) -> list[str]:
    heads: list[str] = []
    for statement in sql.split(";"):
        text = " ".join(statement.split())
        if text.startswith("INSERT INTO"):
            heads.append(text.split(" VALUES ", 1)[0])
    return heads


def test_insert_uses_prod_user_and_omits_surrogate_ids() -> None:
    """A new coupon is inserted under the production user, without ids."""
    mod = _load_coupon()
    local = _coupon(mod)
    actions = mod.plan_coupon_sync(
        [local],
        [],
        {"agent-kuponowy": _account(mod, user_id=9)})
    assert actions[0].kind == "insert"
    assert actions[0].prod_user_id == 9
    sql = mod.build_apply_sql(actions)
    assert "INSERT INTO `tipster_coupons`" in sql
    for head in _insert_heads(sql):
        assert "`id`" not in head
    assert "`user_id`" in sql
    assert "(9," in sql or "(9)" in sql
    assert "WHERE `id` = 5" not in sql
    assert "@coupon_id" in sql
    assert "@leg_id" in sql


def test_update_targets_prod_coupon_not_a_human_id() -> None:
    """Settlement update uses the production coupon id from the content key."""
    mod = _load_coupon()
    local = _coupon(mod)
    prod = mod.ProdCoupon(
        coupon_id=40,
        user_id=9,
        username="agent-kuponowy",
        created_at=local.created_at,
        legs=(mod.ProdLeg(leg_id=100, match_id=10, event_ids=(7,)),))
    actions = mod.plan_coupon_sync(
        [local],
        [prod],
        {"agent-kuponowy": _account(mod)})
    assert actions[0].kind == "update"
    assert actions[0].prod_coupon_id == 40
    sql = mod.build_apply_sql(actions)
    assert "INSERT INTO `tipster_coupons`" not in sql
    assert "WHERE `id` = 40" in sql
    assert "WHERE `id` = 100" in sql
    assert "`user_id` = 9" in sql
    assert "u.`is_system` = 1" in sql
    assert "WHERE `id` = 5" not in sql


def test_human_account_and_missing_bankroll_are_not_written() -> None:
    """A non-system username and a system user without bankroll produce no SQL."""
    mod = _load_coupon()
    human = _coupon(mod, username="radek")
    bare = _coupon(mod, username="agent-kuponowy")
    accounts = {
        "radek": mod.ProdAccount(
            user_id=5, is_system=False, has_bankroll=True),
        "agent-kuponowy": mod.ProdAccount(
            user_id=9, is_system=True, has_bankroll=False)}
    actions = mod.plan_coupon_sync([human, bare], [], accounts)
    assert [action.reason for action in actions] == [
        "not_system",
        "missing_bankroll"]
    assert mod.build_apply_sql(actions) == ""


def test_duplicate_local_key_inserts_once() -> None:
    """Two local coupons with the same identity do not both insert."""
    mod = _load_coupon()
    first = _coupon(mod)
    second = _coupon(mod)
    actions = mod.plan_coupon_sync(
        [first, second],
        [],
        {"agent-kuponowy": _account(mod)})
    assert [action.kind for action in actions] == ["insert", "skip"]
    assert actions[1].reason == "duplicate_local"
    sql = mod.build_apply_sql(actions)
    assert sql.count("INSERT INTO `tipster_coupons`") == 1


def test_parse_batch_rows_keeps_nulls() -> None:
    """mysql batch NULL is backslash-N, not the Python None word."""
    transport = _load(_TRANSPORT, "mysql_transport")
    rows = transport.parse_batch_rows("9\tagent-kuponowy\t1\t\\N\n")
    assert rows == [("9", "agent-kuponowy", "1", None)]
