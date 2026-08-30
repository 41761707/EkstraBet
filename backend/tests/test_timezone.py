"""Tests for Warsaw process and MySQL session timezone helpers."""

from __future__ import annotations

import os
import time
import unittest
from datetime import datetime
from datetime import timezone
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from backend.timezone import (
    WARSAW_TIME_ZONE,
    apply_mysql_session_timezone,
    apply_process_timezone,
    mysql_session_time_zone)


_WARSAW = ZoneInfo(WARSAW_TIME_ZONE)


def _restore_process_timezone(previous: str | None) -> None:
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    tzset = getattr(time, "tzset", None)
    if tzset is not None:
        tzset()


class TestMysqlSessionTimeZone(unittest.TestCase):
    """Numeric offsets must follow Warsaw DST without named TZ tables."""

    def test_summer_offset_is_cest(self) -> None:
        at = datetime(2026, 8, 31, 12, 0, tzinfo=_WARSAW)
        self.assertEqual(mysql_session_time_zone(at), "+02:00")

    def test_winter_offset_is_cet(self) -> None:
        at = datetime(2026, 1, 15, 12, 0, tzinfo=_WARSAW)
        self.assertEqual(mysql_session_time_zone(at), "+01:00")

    def test_naive_datetime_is_treated_as_warsaw(self) -> None:
        at = datetime(2026, 8, 31, 12, 0)
        self.assertEqual(mysql_session_time_zone(at), "+02:00")

    def test_utc_instant_converts_to_warsaw_offset(self) -> None:
        at = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(mysql_session_time_zone(at), "+02:00")


class TestApplyMysqlSessionTimezone(unittest.TestCase):
    """Session SET must use a numeric +HH:MM offset."""

    def test_sets_numeric_time_zone_on_connection(self) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        apply_mysql_session_timezone(connection)
        sql, params = cursor.execute.call_args.args
        self.assertIn("time_zone", sql)
        self.assertRegex(params[0], r"^[+-]\d{2}:\d{2}$")
        cursor.close.assert_called_once()


class TestApplyProcessTimezone(unittest.TestCase):
    """Process TZ pin must be explicit and reversible."""

    def test_sets_tz_environment_variable(self) -> None:
        previous = os.environ.get("TZ")
        try:
            os.environ["TZ"] = "Europe/Helsinki"
            tzset = getattr(time, "tzset", None)
            if tzset is not None:
                tzset()
            apply_process_timezone()
            self.assertEqual(os.environ.get("TZ"), WARSAW_TIME_ZONE)
        finally:
            _restore_process_timezone(previous)


if __name__ == "__main__":
    unittest.main()
