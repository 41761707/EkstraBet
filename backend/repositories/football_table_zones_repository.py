"""Read football table zones for one league and season."""

from __future__ import annotations

import logging
import re

import pandas as pd
from mysql.connector.errors import Error as MySQLError
from pandas.errors import DatabaseError as PandasDatabaseError

from backend.database import get_db_connection
from backend.sports.football.table_zones import TableZone
from backend.sports.football.table_zones import TableZoneSet
from backend.sports.football.table_zones import aggregate_zones
from backend.sports.football.table_zones import zone_label


logger = logging.getLogger(__name__)

# Pandas wkleja całe SQL do komunikatu, więc samo "doesn't exist"
# złapałoby też awarię tabeli leagues. Liczy się fraza sterownika.
_MISSING_ZONES_TABLE = re.compile(
    r"football_table_zones'\s+doesn't exist",
    re.IGNORECASE)

_ZONES_SQL = """
    SELECT
        zones.position_from AS position_from,
        zones.position_to AS position_to,
        zones.zone_kind AS zone_kind,
        zones.band AS band,
        zones.stage AS stage,
        zones.target_league_id AS target_league_id,
        target_league.name AS target_league_name,
        zones.sort_order AS sort_order
    FROM football_table_zones zones
    LEFT JOIN leagues target_league
        ON target_league.id = zones.target_league_id
    WHERE zones.league_id = %s
        AND zones.season_id = %s
    ORDER BY zones.sort_order, zones.position_from
"""


def fetch_table_zones(
        league_id: int,
        season_id: int,
        table_size: int) -> TableZoneSet | None:
    """Return validated zones for one league season.

    ``None`` means the rows are invalid or ``football_table_zones``
    is not in the database yet. No rows are a valid set with both
    slot counts equal to 0.
    """
    frame = _read_zone_frame(league_id, season_id)
    if frame is None:
        return None
    zone_set = aggregate_zones(_map_zones(frame), table_size)
    if zone_set is None:
        logger.warning(
            "Invalid football table zones for league_id=%s season_id=%s",
            league_id,
            season_id)
    return zone_set


def _read_zone_frame(
        league_id: int,
        season_id: int) -> pd.DataFrame | None:
    """Load zone rows, or None when the zones table is absent."""
    try:
        with get_db_connection() as connection:
            return pd.read_sql(
                _ZONES_SQL,
                connection,
                params=(league_id, season_id))
    except (MySQLError, PandasDatabaseError) as exc:
        if _is_missing_zones_table(exc):
            logger.warning(
                "football_table_zones is missing for "
                "league_id=%s season_id=%s",
                league_id,
                season_id)
            return None
        raise


def _is_missing_zones_table(exc: BaseException) -> bool:
    """True when this error says the zones table does not exist."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if _MISSING_ZONES_TABLE.search(str(current)):
            return True
        current = current.__cause__
    return False


def _map_zones(frame: pd.DataFrame) -> list[TableZone]:
    return [_map_zone(row) for _, row in frame.iterrows()]


def _map_zone(row: pd.Series) -> TableZone:
    zone_kind = str(row["zone_kind"])
    stage = _optional_text(row["stage"])
    target_league_name = _optional_text(row["target_league_name"])
    return TableZone(
        position_from=int(row["position_from"]),
        position_to=int(row["position_to"]),
        zone_kind=zone_kind,
        band=str(row["band"]),
        stage=stage,
        target_league_id=_optional_int(row["target_league_id"]),
        target_league_name=target_league_name,
        sort_order=int(row["sort_order"]),
        label=zone_label(zone_kind, stage, target_league_name))


def _optional_text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)
