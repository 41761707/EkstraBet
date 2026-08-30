"""Pin process and MySQL session clocks to Europe/Warsaw."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


WARSAW_TIME_ZONE = "Europe/Warsaw"
_WARSAW = ZoneInfo(WARSAW_TIME_ZONE)


def apply_process_timezone() -> None:
    """Set TZ so naive local time follows Warsaw on POSIX hosts."""
    os.environ["TZ"] = WARSAW_TIME_ZONE
    tzset = getattr(time, "tzset", None)
    if tzset is not None:
        tzset()


def mysql_session_time_zone(at: datetime | None = None) -> str:
    """Return a numeric MySQL time_zone offset for Warsaw.

    Named zones need mysql.time_zone tables; this deployment does not
    load them, so CONVERT_TZ(..., 'Europe/Warsaw') is NULL.
    """
    moment = _warsaw_moment(at)
    offset = moment.utcoffset()
    if offset is None:
        raise RuntimeError("Europe/Warsaw UTC offset is unavailable")
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def apply_mysql_session_timezone(connection: Any) -> None:
    """Set session time_zone so NOW() matches Polish match dates."""
    offset = mysql_session_time_zone()
    cursor = connection.cursor()
    try:
        cursor.execute("SET time_zone = %s", (offset,))
    finally:
        cursor.close()


def _warsaw_moment(at: datetime | None) -> datetime:
    if at is None:
        return datetime.now(_WARSAW)
    if at.tzinfo is None:
        return at.replace(tzinfo=_WARSAW)
    return at.astimezone(_WARSAW)
