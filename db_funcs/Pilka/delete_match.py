"""Delete matches and every related match-level row."""

from __future__ import annotations

import argparse
import sys
import traceback
import db_module
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# Tabele z match_id; dzieci (parlay / final_predictions) kasujemy wcześniej
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
    parlay_sql = (
        "SELECT COUNT(*) FROM parlay_events pe "
        "INNER JOIN bets b ON b.id = pe.bet_id "
        f"WHERE b.match_id IN ({placeholders})")
    counts["parlay_events"] = _scalar_count(cursor, parlay_sql, params)
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


def _affected_parlay_ids(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> list[int]:
    """Return parlay ids that include a bet from the given matches."""
    sql = (
        "SELECT DISTINCT pe.parlay_id FROM parlay_events pe "
        "INNER JOIN bets b ON b.id = pe.bet_id "
        f"WHERE b.match_id IN ({placeholders}) "
        "AND pe.parlay_id IS NOT NULL")
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return [int(row[0]) for row in rows]


def _delete_empty_parlays(cursor: Any, parlay_ids: list[int]) -> None:
    """Delete parlays that have no remaining legs after match cleanup."""
    if not parlay_ids:
        print("Deleted 0 row(s) from gambler_parlays")
        return
    placeholders = _placeholders(parlay_ids)
    sql = (
        f"DELETE FROM gambler_parlays WHERE id IN ({placeholders}) "
        "AND NOT EXISTS ("
        "SELECT 1 FROM parlay_events pe2 "
        "WHERE pe2.parlay_id = gambler_parlays.id)")
    _delete_join(cursor, sql, tuple(parlay_ids), "gambler_parlays")


def _delete_children(
        cursor: Any,
        placeholders: str,
        params: tuple[int, ...]) -> None:
    """Remove rows that reference bets or predictions of these matches."""
    parlay_ids = _affected_parlay_ids(cursor, placeholders, params)
    parlay_sql = (
        "DELETE pe FROM parlay_events pe "
        "INNER JOIN bets b ON b.id = pe.bet_id "
        f"WHERE b.match_id IN ({placeholders})")
    _delete_join(cursor, parlay_sql, params, "parlay_events")
    _delete_empty_parlays(cursor, parlay_ids)
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
            "(odds, predictions, bets, stats, schedule link)."))
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
