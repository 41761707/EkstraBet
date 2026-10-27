"""Copy system-user coupons from local MySQL to production.

Identity is the system username, the stored calendar day, and the set of
(match_id, event_ids). Production assigns coupon, leg, and leg-event ids.
Human coupons are never read or written. Bankrolls are not copied.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import mysql.connector


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SYNC_DIR = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_SYNC_DIR) not in sys.path:
    sys.path.insert(0, str(_SYNC_DIR))

from mysql_transport import ConnectionSettings
from mysql_transport import configure_stdio_utf8
from mysql_transport import connect
from mysql_transport import fetch_rows
from mysql_transport import load_connection_settings
from mysql_transport import open_prod
from mysql_transport import quote_ident
from mysql_transport import sql_literal


_LOCAL_COUPON_SQL = """
    SELECT
        u.username,
        c.id,
        c.stake_amount,
        c.stake_units,
        c.stake_input_mode,
        c.combined_odds,
        c.settled,
        c.outcome,
        c.profit,
        c.created_at
    FROM tipster_coupons c
    INNER JOIN users u ON u.id = c.user_id
    WHERE u.is_system = 1
    ORDER BY c.created_at, c.id
"""

_LOCAL_LEG_SQL = """
    SELECT
        l.coupon_id,
        l.id,
        l.match_id,
        l.odds,
        l.bookmaker_id,
        l.source,
        l.outcome
    FROM tipster_coupon_legs l
    INNER JOIN tipster_coupons c ON c.id = l.coupon_id
    INNER JOIN users u ON u.id = c.user_id
    WHERE u.is_system = 1
    ORDER BY l.coupon_id, l.match_id, l.id
"""

_LOCAL_EVENT_SQL = """
    SELECT e.leg_id, e.event_id
    FROM tipster_coupon_leg_events e
    INNER JOIN tipster_coupon_legs l ON l.id = e.leg_id
    INNER JOIN tipster_coupons c ON c.id = l.coupon_id
    INNER JOIN users u ON u.id = c.user_id
    WHERE u.is_system = 1
    ORDER BY e.leg_id, e.event_id
"""

_PROD_COUPON_SQL = """
    SELECT
        u.username,
        c.id,
        c.user_id,
        c.created_at
    FROM tipster_coupons c
    INNER JOIN users u ON u.id = c.user_id
    WHERE u.is_system = 1
    ORDER BY c.created_at, c.id
"""

_PROD_LEG_SQL = """
    SELECT l.coupon_id, l.id, l.match_id
    FROM tipster_coupon_legs l
    INNER JOIN tipster_coupons c ON c.id = l.coupon_id
    INNER JOIN users u ON u.id = c.user_id
    WHERE u.is_system = 1
    ORDER BY l.coupon_id, l.match_id, l.id
"""

_PROD_EVENT_SQL = """
    SELECT e.leg_id, e.event_id
    FROM tipster_coupon_leg_events e
    INNER JOIN tipster_coupon_legs l ON l.id = e.leg_id
    INNER JOIN tipster_coupons c ON c.id = l.coupon_id
    INNER JOIN users u ON u.id = c.user_id
    WHERE u.is_system = 1
    ORDER BY e.leg_id, e.event_id
"""


@dataclass(frozen=True)
class LegPayload:
    """One coupon leg identified by match and its catalog events."""

    match_id: int
    event_ids: tuple[int, ...]
    odds: str
    bookmaker_id: int | None
    source: str
    outcome: int | None


@dataclass(frozen=True)
class CouponPayload:
    """A system coupon without any surrogate id."""

    username: str
    created_at: datetime
    stake_amount: str
    stake_units: str | None
    stake_input_mode: str
    combined_odds: str
    settled: int
    outcome: int | None
    profit: str | None
    legs: tuple[LegPayload, ...]


@dataclass(frozen=True)
class ProdLeg:
    """A production leg id used only in UPDATE ... WHERE."""

    leg_id: int
    match_id: int
    event_ids: tuple[int, ...]


@dataclass(frozen=True)
class ProdCoupon:
    """A production system coupon located by content, not by local id."""

    coupon_id: int
    user_id: int
    username: str
    created_at: datetime
    legs: tuple[ProdLeg, ...]


@dataclass(frozen=True)
class ProdAccount:
    """Production user resolved by username."""

    user_id: int
    is_system: bool
    has_bankroll: bool


@dataclass(frozen=True)
class CouponAction:
    """One planned insert, settlement update, or refusal."""

    kind: str
    reason: str
    coupon: CouponPayload
    prod_coupon_id: int | None = None
    prod_user_id: int | None = None
    prod_legs: tuple[ProdLeg, ...] = ()


def coupon_key(
        username: str,
        created_at: datetime,
        legs: tuple[tuple[int, tuple[int, ...]], ...]
        ) -> tuple[str, str, tuple[tuple[int, tuple[int, ...]], ...]]:
    """Return the identity shared by a local coupon and its prod copy."""
    day = created_at.strftime("%Y-%m-%d")
    ordered = tuple(sorted(legs, key=lambda item: (item[0], item[1])))
    return (username, day, ordered)


def _payload_key(
        coupon: CouponPayload
        ) -> tuple[str, str, tuple[tuple[int, tuple[int, ...]], ...]]:
    legs = tuple(
        (leg.match_id, leg.event_ids) for leg in coupon.legs)
    return coupon_key(coupon.username, coupon.created_at, legs)


def _prod_key(
        coupon: ProdCoupon
        ) -> tuple[str, str, tuple[tuple[int, tuple[int, ...]], ...]]:
    legs = tuple(
        (leg.match_id, leg.event_ids) for leg in coupon.legs)
    return coupon_key(coupon.username, coupon.created_at, legs)


def _leg_signature(legs: tuple[ProdLeg, ...]) -> dict[
        tuple[int, tuple[int, ...]], ProdLeg]:
    found: dict[tuple[int, tuple[int, ...]], ProdLeg] = {}
    for leg in legs:
        found[(leg.match_id, leg.event_ids)] = leg
    return found


def _skip(coupon: CouponPayload, reason: str) -> CouponAction:
    return CouponAction(kind="skip", reason=reason, coupon=coupon)


def _plan_one(
        coupon: CouponPayload,
        accounts: dict[str, ProdAccount],
        prod_by_key: dict[Any, list[ProdCoupon]],
        seen: set[Any]) -> CouponAction:
    """Decide insert, update, or skip for one local system coupon."""
    key = _payload_key(coupon)
    if key in seen:
        return _skip(coupon, "duplicate_local")
    seen.add(key)
    if not coupon.legs or not coupon.stake_input_mode:
        return _skip(coupon, "invalid_coupon")
    account = accounts.get(coupon.username)
    if account is None:
        return _skip(coupon, "missing_user")
    if not account.is_system:
        return _skip(coupon, "not_system")
    if not account.has_bankroll:
        return _skip(coupon, "missing_bankroll")
    matches = prod_by_key.get(key, [])
    if len(matches) > 1:
        return _skip(coupon, "duplicate_prod")
    if not matches:
        return CouponAction(
            kind="insert",
            reason="new",
            coupon=coupon,
            prod_user_id=account.user_id)
    prod_coupon = matches[0]
    prod_legs = _leg_signature(prod_coupon.legs)
    for leg in coupon.legs:
        if (leg.match_id, leg.event_ids) not in prod_legs:
            return _skip(coupon, "leg_mismatch")
    return CouponAction(
        kind="update",
        reason="settlement",
        coupon=coupon,
        prod_coupon_id=prod_coupon.coupon_id,
        prod_user_id=prod_coupon.user_id,
        prod_legs=prod_coupon.legs)


def plan_coupon_sync(
        local_coupons: list[CouponPayload],
        prod_coupons: list[ProdCoupon],
        accounts: dict[str, ProdAccount]) -> list[CouponAction]:
    """Plan writes. Production ids are used only when a content key matches."""
    prod_by_key: dict[Any, list[ProdCoupon]] = {}
    for coupon in prod_coupons:
        prod_by_key.setdefault(_prod_key(coupon), []).append(coupon)
    seen: set[Any] = set()
    return [
        _plan_one(coupon, accounts, prod_by_key, seen)
        for coupon in local_coupons]


def _system_user_guard(user_id: int, username: str) -> str:
    """SQL predicate: this id is the named system account."""
    return (
        "EXISTS (SELECT 1 FROM "
        + quote_ident("users")
        + " u WHERE u."
        + quote_ident("id")
        + " = "
        + sql_literal(user_id)
        + " AND u."
        + quote_ident("is_system")
        + " = 1 AND u."
        + quote_ident("username")
        + " = "
        + sql_literal(username)
        + ")")


def _insert_statements(action: CouponAction) -> list[str]:
    """INSERT a coupon graph. Surrogate ids come from LAST_INSERT_ID."""
    coupon = action.coupon
    user_id = action.prod_user_id
    if user_id is None:
        raise ValueError("Insert requires the production user id")
    columns = (
        "user_id",
        "stake_amount",
        "stake_units",
        "stake_input_mode",
        "combined_odds",
        "settled",
        "outcome",
        "profit",
        "created_at")
    values = (
        user_id,
        coupon.stake_amount,
        coupon.stake_units,
        coupon.stake_input_mode,
        coupon.combined_odds,
        coupon.settled,
        coupon.outcome,
        coupon.profit,
        coupon.created_at)
    col_sql = ", ".join(quote_ident(name) for name in columns)
    val_sql = ", ".join(sql_literal(value) for value in values)
    statements = [
        "INSERT INTO "
        + quote_ident("tipster_coupons")
        + " ("
        + col_sql
        + ") VALUES ("
        + val_sql
        + ")",
        "SET @coupon_id = LAST_INSERT_ID()"]
    for leg in sorted(coupon.legs, key=lambda item: item.match_id):
        statements.extend(_insert_leg_statements(leg))
    return statements


def _insert_leg_statements(leg: LegPayload) -> list[str]:
    columns = (
        "coupon_id",
        "match_id",
        "odds",
        "bookmaker_id",
        "source",
        "outcome")
    values = (
        "@coupon_id",
        sql_literal(leg.match_id),
        sql_literal(leg.odds),
        sql_literal(leg.bookmaker_id),
        sql_literal(leg.source),
        sql_literal(leg.outcome))
    # coupon_id jest zmienną sesji, nie literałem
    rendered = ["@coupon_id"]
    rendered.extend(values[1:])
    col_sql = ", ".join(quote_ident(name) for name in columns)
    statements = [
        "INSERT INTO "
        + quote_ident("tipster_coupon_legs")
        + " ("
        + col_sql
        + ") VALUES ("
        + ", ".join(rendered)
        + ")",
        "SET @leg_id = LAST_INSERT_ID()"]
    for event_id in leg.event_ids:
        statements.append(
            "INSERT INTO "
            + quote_ident("tipster_coupon_leg_events")
            + " ("
            + quote_ident("leg_id")
            + ", "
            + quote_ident("event_id")
            + ") VALUES (@leg_id, "
            + sql_literal(event_id)
            + ")")
    return statements


def _update_statements(action: CouponAction) -> list[str]:
    """Refresh stake and settlement on the already matched production rows."""
    coupon = action.coupon
    coupon_id = action.prod_coupon_id
    user_id = action.prod_user_id
    if coupon_id is None or user_id is None:
        raise ValueError("Update requires production coupon and user ids")
    guard = _system_user_guard(user_id, coupon.username)
    assignments = ", ".join([
        quote_ident("stake_amount") + " = " + sql_literal(coupon.stake_amount),
        quote_ident("stake_units") + " = " + sql_literal(coupon.stake_units),
        quote_ident("stake_input_mode")
        + " = "
        + sql_literal(coupon.stake_input_mode),
        quote_ident("combined_odds")
        + " = "
        + sql_literal(coupon.combined_odds),
        quote_ident("settled") + " = " + sql_literal(coupon.settled),
        quote_ident("outcome") + " = " + sql_literal(coupon.outcome),
        quote_ident("profit") + " = " + sql_literal(coupon.profit)])
    statements = [
        "UPDATE "
        + quote_ident("tipster_coupons")
        + " SET "
        + assignments
        + " WHERE "
        + quote_ident("id")
        + " = "
        + sql_literal(coupon_id)
        + " AND "
        + quote_ident("user_id")
        + " = "
        + sql_literal(user_id)
        + " AND "
        + guard]
    prod_legs = _leg_signature(action.prod_legs)
    for leg in coupon.legs:
        prod_leg = prod_legs[(leg.match_id, leg.event_ids)]
        statements.append(_update_leg_sql(leg, prod_leg, coupon_id, guard))
    return statements


def _update_leg_sql(
        leg: LegPayload,
        prod_leg: ProdLeg,
        coupon_id: int,
        guard: str) -> str:
    assignments = ", ".join([
        quote_ident("odds") + " = " + sql_literal(leg.odds),
        quote_ident("bookmaker_id") + " = " + sql_literal(leg.bookmaker_id),
        quote_ident("source") + " = " + sql_literal(leg.source),
        quote_ident("outcome") + " = " + sql_literal(leg.outcome)])
    return (
        "UPDATE "
        + quote_ident("tipster_coupon_legs")
        + " SET "
        + assignments
        + " WHERE "
        + quote_ident("id")
        + " = "
        + sql_literal(prod_leg.leg_id)
        + " AND "
        + quote_ident("coupon_id")
        + " = "
        + sql_literal(coupon_id)
        + " AND "
        + quote_ident("match_id")
        + " = "
        + sql_literal(leg.match_id)
        + " AND "
        + guard)


def build_apply_sql(actions: list[CouponAction]) -> str:
    """Build one transaction. Skipped coupons contribute no statements."""
    statements: list[str] = []
    for action in actions:
        if action.kind == "insert":
            statements.extend(_insert_statements(action))
        elif action.kind == "update":
            statements.extend(_update_statements(action))
    if not statements:
        return ""
    body = ";\n".join(statements)
    return "START TRANSACTION;\n" + body + ";\nCOMMIT;\n"


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value).strip()
    return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")


def _as_decimal_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return format(Decimal(str(value)), "f")


def _as_int(value: Any) -> int:
    return int(value)


def _as_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _events_by_leg(
        rows: list[tuple[Any, ...]]) -> dict[int, tuple[int, ...]]:
    grouped: dict[int, list[int]] = {}
    for row in rows:
        grouped.setdefault(_as_int(row[0]), []).append(_as_int(row[1]))
    return {
        leg_id: tuple(sorted(set(event_ids)))
        for leg_id, event_ids in grouped.items()}


def assemble_local_coupons(
        coupon_rows: list[tuple[Any, ...]],
        leg_rows: list[tuple[Any, ...]],
        event_rows: list[tuple[Any, ...]]) -> list[CouponPayload]:
    """Build payloads. Local coupon and leg ids are join keys only."""
    events = _events_by_leg(event_rows)
    legs_by_coupon: dict[int, list[LegPayload]] = {}
    incomplete: set[int] = set()
    for row in leg_rows:
        coupon_id = _as_int(row[0])
        leg_id = _as_int(row[1])
        event_ids = events.get(leg_id, ())
        odds = _as_decimal_text(row[3])
        if odds is None or not event_ids:
            incomplete.add(coupon_id)
            continue
        legs_by_coupon.setdefault(coupon_id, []).append(LegPayload(
            match_id=_as_int(row[2]),
            event_ids=event_ids,
            odds=odds,
            bookmaker_id=_as_optional_int(row[4]),
            source=str(row[5] or ""),
            outcome=_as_optional_int(row[6])))
    payloads: list[CouponPayload] = []
    for row in coupon_rows:
        local_id = _as_int(row[1])
        stake = _as_decimal_text(row[2])
        combined = _as_decimal_text(row[5])
        legs = tuple(legs_by_coupon.get(local_id, []))
        if (
                local_id in incomplete
                or stake is None
                or combined is None
                or not legs):
            continue
        payloads.append(CouponPayload(
            username=str(row[0]),
            created_at=_as_datetime(row[9]),
            stake_amount=stake,
            stake_units=_as_decimal_text(row[3]),
            stake_input_mode=str(row[4] or ""),
            combined_odds=combined,
            settled=_as_int(row[6]),
            outcome=_as_optional_int(row[7]),
            profit=_as_decimal_text(row[8]),
            legs=legs))
    return payloads


def assemble_prod_coupons(
        coupon_rows: list[tuple[Any, ...]],
        leg_rows: list[tuple[Any, ...]],
        event_rows: list[tuple[Any, ...]]) -> list[ProdCoupon]:
    """Build production coupons. Ids stay the ones production assigned."""
    events = _events_by_leg(event_rows)
    legs_by_coupon: dict[int, list[ProdLeg]] = {}
    for row in leg_rows:
        coupon_id = _as_int(row[0])
        leg_id = _as_int(row[1])
        legs_by_coupon.setdefault(coupon_id, []).append(ProdLeg(
            leg_id=leg_id,
            match_id=_as_int(row[2]),
            event_ids=events.get(leg_id, ())))
    coupons: list[ProdCoupon] = []
    for row in coupon_rows:
        coupon_id = _as_int(row[1])
        coupons.append(ProdCoupon(
            coupon_id=coupon_id,
            user_id=_as_int(row[2]),
            username=str(row[0]),
            created_at=_as_datetime(row[3]),
            legs=tuple(legs_by_coupon.get(coupon_id, ()))))
    return coupons


def assemble_accounts(
        rows: list[tuple[Any, ...]]) -> dict[str, ProdAccount]:
    """Map username to the production account. Ids come from production."""
    accounts: dict[str, ProdAccount] = {}
    for row in rows:
        accounts[str(row[1])] = ProdAccount(
            user_id=_as_int(row[0]),
            is_system=_as_int(row[2]) == 1,
            has_bankroll=_as_int(row[3]) == 1)
    return accounts


def account_lookup_sql(usernames: list[str]) -> str:
    """Look up production users by username, including non-system rows."""
    if not usernames:
        raise ValueError("At least one username is required")
    listed = ", ".join(sql_literal(name) for name in usernames)
    return (
        "SELECT u."
        + quote_ident("id")
        + ", u."
        + quote_ident("username")
        + ", u."
        + quote_ident("is_system")
        + ", tb."
        + quote_ident("user_id")
        + " IS NOT NULL FROM "
        + quote_ident("users")
        + " u LEFT JOIN "
        + quote_ident("tipster_bankrolls")
        + " tb ON tb."
        + quote_ident("user_id")
        + " = u."
        + quote_ident("id")
        + " WHERE u."
        + quote_ident("username")
        + " IN ("
        + listed
        + ")")


def _filtered_sql(
        sql: str,
        username: str | None) -> tuple[str, tuple[Any, ...]]:
    if username is None:
        return sql, ()
    filtered = sql.replace(
        "WHERE u.is_system = 1",
        "WHERE u.is_system = 1 AND u.username = %s")
    return filtered, (username,)


def load_local_coupons(
        conn: Any,
        username: str | None) -> list[CouponPayload]:
    """Read system coupons from the local database."""
    coupon_sql, params = _filtered_sql(_LOCAL_COUPON_SQL, username)
    leg_sql, leg_params = _filtered_sql(_LOCAL_LEG_SQL, username)
    event_sql, event_params = _filtered_sql(_LOCAL_EVENT_SQL, username)
    return assemble_local_coupons(
        fetch_rows(conn, coupon_sql, params),
        fetch_rows(conn, leg_sql, leg_params),
        fetch_rows(conn, event_sql, event_params))


def load_prod_state(
        prod: Any,
        usernames: list[str]
        ) -> tuple[list[ProdCoupon], dict[str, ProdAccount]]:
    """Read production system coupons and the accounts named locally."""
    coupons = assemble_prod_coupons(
        list(prod.query(_PROD_COUPON_SQL)),
        list(prod.query(_PROD_LEG_SQL)),
        list(prod.query(_PROD_EVENT_SQL)))
    if not usernames:
        return coupons, {}
    lookup = account_lookup_sql(usernames)
    accounts = assemble_accounts(list(prod.query(lookup)))
    return coupons, accounts


def format_action(action: CouponAction) -> str:
    """One human-readable line for dry-run and apply logs."""
    day = action.coupon.created_at.strftime("%Y-%m-%d")
    name = action.coupon.username
    if action.kind == "insert":
        return (
            f"INSERT {name} {day} legs={len(action.coupon.legs)} "
            f"prod_user_id={action.prod_user_id}")
    if action.kind == "update":
        return (
            f"UPDATE {name} {day} prod_coupon_id={action.prod_coupon_id}")
    return f"SKIP {name} {day} {action.reason}"


def _counts(actions: list[CouponAction]) -> dict[str, int]:
    counts = {"insert": 0, "update": 0, "skip": 0}
    for action in actions:
        counts[action.kind] = counts.get(action.kind, 0) + 1
    return counts


def run_coupon_sync(
        settings: ConnectionSettings,
        apply: bool,
        username: str | None) -> int:
    """Read local system coupons and write SQL when apply is set."""
    local = connect(settings.local_db)
    prod, direct = open_prod(settings)
    try:
        local_coupons = load_local_coupons(local, username)
        names = sorted({coupon.username for coupon in local_coupons})
        prod_coupons, accounts = load_prod_state(prod, names)
        actions = plan_coupon_sync(local_coupons, prod_coupons, accounts)
        for action in actions:
            print(format_action(action), flush=True)
        counts = _counts(actions)
        mode = "APPLY" if apply else "DRY-RUN"
        print(
            f"{mode} insert={counts['insert']} "
            f"update={counts['update']} skip={counts['skip']}",
            flush=True)
        sql = build_apply_sql(actions)
        if apply and sql:
            prod.execute_script(sql, abort_on_error=True)
        if any(action.kind == "skip" for action in actions):
            return 1
        return 0
    finally:
        local.close()
        if direct is not None:
            direct.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Copy system-user coupons to production without surrogate ids"))
    parser.add_argument(
        "--sync-env",
        default="",
        help="Path to sync.env (default: SYNC_ENV_FILE or deploy/sync.env)")
    parser.add_argument(
        "--username",
        default="",
        help="Only this system username (default: every is_system account)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write to production (default is dry-run)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Dry-run is the default."""
    configure_stdio_utf8()
    parser = _build_parser()
    args = parser.parse_args(argv)
    username = args.username.strip() or None
    try:
        settings = load_connection_settings(_REPO_ROOT, args.sync_env)
        return run_coupon_sync(settings, args.apply, username)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except mysql.connector.Error as exc:
        print(f"MySQL error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
