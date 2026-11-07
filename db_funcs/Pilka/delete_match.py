"""Delete matches and every related match-level row."""

from __future__ import annotations

import argparse
import sys
import traceback
from decimal import ROUND_HALF_UP
from decimal import Decimal
from pathlib import Path
from typing import Any

import db_module

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# Tabele z match_id; dzieci (zdarzenia kuponu / final_predictions) kasujemy wcześniej
_MATCH_ID_TABLES = ("bets",
    "odds",
    "predictions",
    "player_props_lines",
    "football_special_round_add",
    "match_model_assessments",
    "basketball_match_roster",
    "basketball_matches_add",
    "hockey_match_rosters")


def _placeholders(id_list: list[int]) -> str:
    """Return SQL placeholders for the given id list."""
    return ",".join(["%s"] * len(id_list))


def _scalar_count(cursor: Any, sql: str, params: tuple[Any, ...]) -> int:
    """Execute a COUNT query and return the integer result."""
    cursor.execute(sql, params)
    row = cursor.fetchone()
    if row is None:
        return 0
    value = row[0] if not isinstance(row, dict) else next(iter(row.values()))
    return int(value)


def _count_by_match_id(
        cursor: Any,
        table_name: str,
        placeholders: str,
        params: tuple[int, ...]) -> int:
    """Count rows in a table that reference the given match ids."""
    sql = (
        f"SELECT COUNT(*) FROM {table_name} "
        f"WHERE match_id IN ({placeholders})")
    return _scalar_count(cursor, sql, params)


def fetch_match_summaries(
        cursor: Any,
        id_list: list[int]) -> list[tuple[Any, ...]]:
    """Return identity rows for matches about to be deleted."""
    placeholders = _placeholders(id_list)
    sql = (
        "SELECT m.id, s.name, l.name, th.name, ta.name, "
        "m.game_date, m.result "
        "FROM matches m "
        "LEFT JOIN sports s ON s.id = m.sport_id "
        "LEFT JOIN leagues l ON l.id = m.league "
        "LEFT JOIN teams th ON th.id = m.home_team "
        "LEFT JOIN teams ta ON ta.id = m.away_team "
        f"WHERE m.id IN ({placeholders})")
    cursor.execute(sql, tuple(id_list))
    return list(cursor.fetchall())


def collect_related_counts(
        cursor: Any,
        id_list: list[int]) -> dict[str, int]:
    """Count related rows that a match delete would remove or unlink."""
    placeholders = _placeholders(id_list)
    params = tuple(id_list)
    counts: dict[str, int] = {}
    counts["tipster_coupon_leg_events"] = _count_leg_events(
        cursor, placeholders, params)
    counts["tipster_coupon_legs"] = _count_by_match_id(
        cursor, "tipster_coupon_legs", placeholders, params)
    counts["tipster_coupons_repriced"] = _count_coupons_to_reprice(
        cursor, placeholders, params)
    counts["betting_recommendations"] = _count_recommendations(
        cursor, placeholders, params)
    final_sql = (
        "SELECT COUNT(*) FROM final_predictions fp "
        "INNER JOIN predictions p ON p.id = fp.predictions_id "
        f"WHERE p.match_id IN ({placeholders})")
    counts["final_predictions"] = _scalar_count(cursor, final_sql, params)
    for table_name in _MATCH_ID_TABLES:
        counts[table_name] = _count_by_match_id(
            cursor, table_name, placeholders, params)
    counts["schedule_unlinked"] = _count_by_match_id(
        cursor, "schedule", placeholders, params)
    matches_sql = f"SELECT COUNT(*) FROM matches WHERE id IN ({placeholders})"
    counts["matches"] = _scalar_count(cursor, matches_sql, params)
    return counts


def _delete_join(
        cursor: Any,
        sql: str,
        params: tuple[int, ...],
        label: str) -> int:
    """Run a DELETE and print how many rows were removed."""
    cursor.execute(sql, params)
    deleted = int(cursor.rowcount)
    print(f"Deleted {deleted} row(s) from {label}")
    return deleted


def _affected_coupon_ids(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> list[int]:
    """Return coupon ids that have a leg on the given matches."""
    sql = (
        "SELECT DISTINCT coupon_id FROM tipster_coupon_legs "
        f"WHERE match_id IN ({placeholders})")
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return [int(row[0]) for row in rows]


def _delete_empty_coupons(cursor: Any, coupon_ids: list[int]) -> None:
    """Delete coupons that have no remaining legs after match cleanup."""
    if not coupon_ids:
        print("Deleted 0 row(s) from tipster_coupons")
        return
    placeholders = _placeholders(coupon_ids)
    sql = (
        f"DELETE FROM tipster_coupons WHERE id IN ({placeholders}) "
        "AND NOT EXISTS ("
        "SELECT 1 FROM tipster_coupon_legs l "
        "WHERE l.coupon_id = tipster_coupons.id)")
    _delete_join(cursor, sql, tuple(coupon_ids), "tipster_coupons")


def _count_coupons_to_reprice(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> int:
    """Count coupons that keep a leg after this match is removed."""
    sql = (
        "SELECT COUNT(DISTINCT kept.coupon_id) "
        "FROM tipster_coupon_legs kept "
        "INNER JOIN tipster_coupon_legs removed "
        "ON removed.coupon_id = kept.coupon_id "
        f"WHERE removed.match_id IN ({placeholders}) "
        f"AND kept.match_id NOT IN ({placeholders})")
    return _scalar_count(cursor, sql, params + params)


def _reprice_surviving_coupons(
        cursor: Any,
        coupon_ids: list[int]) -> None:
    """Write the product of the legs that are still on the coupon."""
    if not coupon_ids:
        print("Repriced 0 tipster coupon(s)")
        return
    products = _remaining_odds_products(cursor, coupon_ids)
    updated = 0
    for coupon_id, combined in products.items():
        updated += _write_coupon_odds(cursor, coupon_id, combined)
    print(f"Repriced {updated} tipster coupon(s)")


def _remaining_odds_products(
        cursor: Any,
        coupon_ids: list[int]) -> dict[int, Decimal]:
    """Product of odds still stored on each of the given coupons."""
    placeholders = _placeholders(coupon_ids)
    sql = (
        "SELECT l.coupon_id, l.odds FROM tipster_coupon_legs l "
        f"WHERE l.coupon_id IN ({placeholders})")
    cursor.execute(sql, tuple(coupon_ids))
    grouped: dict[int, list[Any]] = {}
    for row in cursor.fetchall():
        grouped.setdefault(int(row[0]), []).append(row[1])
    return {
        coupon_id: _odds_product(values)
        for coupon_id, values in grouped.items()}


def _odds_product(values: list[Any]) -> Decimal:
    """Product of leg odds, rounded to the coupon column scale."""
    product = Decimal("1")
    for value in values:
        product *= Decimal(str(value))
    return product.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _write_coupon_odds(
        cursor: Any,
        coupon_id: int,
        combined: Decimal) -> int:
    """Store the new combined odds and the win profit that depends on it."""
    sql = (
        "UPDATE tipster_coupons "
        "SET combined_odds = %s, "
        "profit = IF(settled = 1 AND outcome = 1, "
        "ROUND(stake_amount * (%s - 1), 2), profit) "
        "WHERE id = %s")
    odds = format(combined, "f")
    cursor.execute(sql, (odds, odds, coupon_id))
    return int(cursor.rowcount)


def _count_leg_events(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> int:
    """Count catalog events on coupon legs of the given matches."""
    sql = (
        "SELECT COUNT(*) FROM tipster_coupon_leg_events e "
        "INNER JOIN tipster_coupon_legs l ON l.id = e.leg_id "
        f"WHERE l.match_id IN ({placeholders})")
    return _scalar_count(cursor, sql, params)


def _count_recommendations(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> int:
    """Count verdicts whose prediction or odds row belongs to the matches."""
    sql = (
        "SELECT COUNT(*) FROM betting_recommendations br "
        "LEFT JOIN predictions p ON p.id = br.prediction_id "
        "LEFT JOIN odds o ON o.id = br.odds_id "
        f"WHERE p.match_id IN ({placeholders}) "
        f"OR o.match_id IN ({placeholders})")
    return _scalar_count(cursor, sql, params + params)


def _delete_leg_events(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> None:
    """Remove catalog events before the coupon leg itself."""
    sql = (
        "DELETE e FROM tipster_coupon_leg_events e "
        "INNER JOIN tipster_coupon_legs l ON l.id = e.leg_id "
        f"WHERE l.match_id IN ({placeholders})")
    _delete_join(cursor, sql, params, "tipster_coupon_leg_events")


def _delete_recommendations(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> None:
    """Remove verdicts before predictions and odds, which they reference."""
    sql = (
        "DELETE br FROM betting_recommendations br "
        "LEFT JOIN predictions p ON p.id = br.prediction_id "
        "LEFT JOIN odds o ON o.id = br.odds_id "
        f"WHERE p.match_id IN ({placeholders}) "
        f"OR o.match_id IN ({placeholders})")
    _delete_join(
        cursor, sql, params + params, "betting_recommendations")


def _delete_children(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> None:
    """Remove rows that reference bets, predictions or tipster legs."""
    coupon_ids = _affected_coupon_ids(cursor, placeholders, params)
    _delete_leg_events(cursor, placeholders, params)
    legs_sql = (
        f"DELETE FROM tipster_coupon_legs "
        f"WHERE match_id IN ({placeholders})")
    _delete_join(cursor, legs_sql, params, "tipster_coupon_legs")
    _delete_empty_coupons(cursor, coupon_ids)
    _reprice_surviving_coupons(cursor, coupon_ids)
    _delete_recommendations(cursor, placeholders, params)
    final_sql = (
        "DELETE fp FROM final_predictions fp "
        "INNER JOIN predictions p ON p.id = fp.predictions_id "
        f"WHERE p.match_id IN ({placeholders})")
    _delete_join(cursor, final_sql, params, "final_predictions")


def _delete_match_rows(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> None:
    """Remove direct match_id rows, unlink schedule, then delete matches."""
    for table_name in _MATCH_ID_TABLES:
        sql = (
            f"DELETE FROM {table_name} "
            f"WHERE match_id IN ({placeholders})")
        _delete_join(cursor, sql, params, table_name)
    unlink_sql = (
        f"UPDATE schedule SET match_id = NULL "
        f"WHERE match_id IN ({placeholders})")
    cursor.execute(unlink_sql, params)
    unlinked = int(cursor.rowcount)
    print(f"Unlinked {unlinked} schedule row(s)")
    matches_sql = f"DELETE FROM matches WHERE id IN ({placeholders})"
    _delete_join(cursor, matches_sql, params, "matches")


def _print_preview(
        matches: list[tuple[Any, ...]],
        counts: dict[str, int]) -> None:
    """Print match identities and related-row counts."""
    if not matches:
        print("No matching rows found in matches.")
        print("Related rows still referencing these IDs:")
        for name, count in counts.items():
            print(f"  {name}: {count}")
        return
    print("Matches to delete:")
    for row in matches:
        match_id, sport, league, home, away, game_date, result = row
        print(
            f"  id={match_id} {sport}/{league}: "
            f"{home} vs {away} at {game_date} result={result}")
    print("Related rows:")
    for name, count in counts.items():
        print(f"  {name}: {count}")


def delete_match_by_ids(
        id_list: list[int],
        dry_run: bool = False) -> None:
    """Delete matches and all related match-level data.

    Args:
        id_list: Match identifiers to delete.
        dry_run: When True, only print the impact and do not write.

    Returns:
        None
    """
    if not id_list:
        print("No match IDs were provided.")
        return
    conn = None
    try:
        conn = db_module.db_connect()
        host = getattr(conn, "server_host", "?")
        database = getattr(conn, "database", "?")
        print(f"Connected to {host}/{database}")
        cursor = conn.cursor()
        matches = fetch_match_summaries(cursor, id_list)
        counts = collect_related_counts(cursor, id_list)
        _print_preview(matches, counts)
        if dry_run:
            print("Dry run: no rows were changed.")
            return
        if not matches:
            print("Nothing to delete.")
            return
        placeholders = _placeholders(id_list)
        params = tuple(id_list)
        _delete_children(cursor, placeholders, params)
        _delete_match_rows(cursor, placeholders, params)
        conn.commit()
        printed = ", ".join(str(item) for item in id_list)
        print(f"Deleted matches and related rows for IDs: {printed}")
    except Exception:
        if conn is not None:
            conn.rollback()
        print("Failed to delete matches and related rows:")
        traceback.print_exc()
    finally:
        if conn is not None:
            conn.close()


def _parse_ids(raw_ids: str) -> list[int]:
    """Parse a comma-separated ID string into integers."""
    id_list: list[int] = []
    invalid_ids: list[str] = []
    for item in raw_ids.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        try:
            id_list.append(int(stripped))
        except ValueError:
            invalid_ids.append(stripped)
    if invalid_ids:
        joined = ", ".join(invalid_ids)
        print(f"Invalid match IDs: {joined}. Provide integers only.")
    return id_list


def main() -> None:
    """Parse CLI arguments and delete the requested matches."""
    parser = argparse.ArgumentParser(
        description=(
            "Delete matches and all related match-level data "
            "(odds, predictions, bets, tipster coupons, "
            "betting recommendations, stats, schedule link)."))
    parser.add_argument(
        "--ids",
        type=str,
        required=True,
        help='Match IDs separated by commas, e.g. "123,456,789"')
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print related-row counts without deleting anything")
    args = parser.parse_args()
    id_list = _parse_ids(args.ids)
    if not id_list:
        print("No valid match IDs to delete.")
        return
    delete_match_by_ids(id_list, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
