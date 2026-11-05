"""Day, week, month and year buckets for settled result facts."""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal
from decimal import ROUND_HALF_UP

from backend.services.tipster_result_calendar import build_result_calendar


def _fact(day: str, profit: float, stake: float) -> dict:
    return {
        "anchor_date": date.fromisoformat(day),
        "profit": profit,
        "stake": stake}


def _cents(value: float) -> Decimal:
    return Decimal(str(value)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


def _assert_totals(
        case: unittest.TestCase,
        result: dict,
        anchor: date) -> None:
    buckets = result["buckets"]
    profit = sum((_cents(item["profit"]) for item in buckets), Decimal("0"))
    stake = sum((_cents(item["stake"]) for item in buckets), Decimal("0"))
    count = sum(item["count"] for item in buckets)
    case.assertIs(result["anchor"], anchor)
    case.assertEqual(_cents(result["profit_total"]), profit)
    case.assertEqual(_cents(result["stake_total"]), stake)
    case.assertEqual(result["count"], count)
    starts = [item["start"] for item in buckets]
    case.assertEqual(starts, sorted(starts))


class TestBuildResultCalendar(unittest.TestCase):
    """Buckets follow the anchor period and drop empty spans."""

    def test_day_keeps_facts_inside_the_anchor_month(self) -> None:
        anchor = date(2023, 4, 15)
        facts = [
            _fact("2023-03-31", 50.0, 10.0),
            _fact("2023-04-01", 0.1, 0.1),
            _fact("2023-04-03", 0.2, 0.2),
            _fact("2023-05-01", 9.0, 9.0)]
        result = build_result_calendar(facts, "day", anchor)
        _assert_totals(self, result, anchor)
        self.assertEqual(result["period_start"], date(2023, 4, 1))
        self.assertEqual(result["period_end"], date(2023, 4, 30))
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["profit_total"], 0.3)
        self.assertEqual(result["stake_total"], 0.3)
        self.assertEqual(
            [(item["start"], item["end"]) for item in result["buckets"]],
            [
                (date(2023, 4, 1), date(2023, 4, 1)),
                (date(2023, 4, 3), date(2023, 4, 3))])

    def test_zero_profit_with_stake_stays(self) -> None:
        anchor = date(2023, 4, 15)
        result = build_result_calendar(
            [_fact("2023-04-02", 0.0, 15.0)], "day", anchor)
        _assert_totals(self, result, anchor)
        self.assertEqual(len(result["buckets"]), 1)
        bucket = result["buckets"][0]
        self.assertEqual(bucket["profit"], 0.0)
        self.assertEqual(bucket["stake"], 15.0)
        self.assertEqual(bucket["count"], 1)
        self.assertEqual(bucket["start"], date(2023, 4, 2))
        self.assertEqual(bucket["end"], date(2023, 4, 2))

    def test_week_merges_monday_through_sunday(self) -> None:
        anchor = date(2023, 4, 15)
        facts = [
            _fact("2023-04-09", 4.0, 5.0),
            _fact("2023-04-03", 6.0, 8.0)]
        result = build_result_calendar(facts, "week", anchor)
        _assert_totals(self, result, anchor)
        self.assertEqual(len(result["buckets"]), 1)
        bucket = result["buckets"][0]
        self.assertEqual(bucket["start"], date(2023, 4, 3))
        self.assertEqual(bucket["end"], date(2023, 4, 9))
        self.assertEqual(bucket["profit"], 10.0)
        self.assertEqual(bucket["stake"], 13.0)
        self.assertEqual(bucket["count"], 2)

    def test_iso_week_on_new_year_belongs_to_the_thursday_year(self) -> None:
        fact = [_fact("2023-01-01", 8.0, 5.0)]
        missed = build_result_calendar(fact, "week", date(2023, 6, 1))
        self.assertEqual(missed["buckets"], [])
        self.assertEqual(missed["count"], 0)
        self.assertEqual(missed["profit_total"], 0.0)
        self.assertEqual(missed["period_start"], date(2023, 1, 2))
        self.assertEqual(missed["period_end"], date(2023, 12, 31))
        anchor = date(2022, 6, 1)
        hit = build_result_calendar(fact, "week", anchor)
        _assert_totals(self, hit, anchor)
        self.assertEqual(hit["period_start"], date(2022, 1, 3))
        self.assertEqual(hit["period_end"], date(2023, 1, 1))
        self.assertEqual(len(hit["buckets"]), 1)
        bucket = hit["buckets"][0]
        self.assertEqual(bucket["start"], date(2022, 12, 26))
        self.assertEqual(bucket["end"], date(2023, 1, 1))
        self.assertEqual(bucket["profit"], 8.0)
        self.assertEqual(bucket["count"], 1)

    def test_month_sums_a_calendar_year_and_drops_other_years(self) -> None:
        anchor = date(2023, 8, 1)
        facts = [
            _fact("2023-04-18", 6.0, 4.0),
            _fact("2022-04-01", 99.0, 99.0),
            _fact("2023-04-01", 4.0, 2.0),
            _fact("2023-01-15", 3.0, 1.0)]
        result = build_result_calendar(facts, "month", anchor)
        _assert_totals(self, result, anchor)
        self.assertEqual(result["period_start"], date(2023, 1, 1))
        self.assertEqual(result["period_end"], date(2023, 12, 31))
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["profit_total"], 13.0)
        january, april = result["buckets"]
        self.assertEqual(january["start"], date(2023, 1, 1))
        self.assertEqual(january["end"], date(2023, 1, 31))
        self.assertEqual(january["profit"], 3.0)
        self.assertEqual(january["count"], 1)
        self.assertEqual(april["start"], date(2023, 4, 1))
        self.assertEqual(april["end"], date(2023, 4, 30))
        self.assertEqual(april["profit"], 10.0)
        self.assertEqual(april["stake"], 6.0)
        self.assertEqual(april["count"], 2)

    def test_year_spans_facts_and_injected_today(self) -> None:
        anchor = date(2023, 4, 1)
        facts = [
            _fact("2024-11-02", 1.5, 4.0),
            _fact("2022-05-01", 7.0, 2.0)]
        result = build_result_calendar(
            facts, "year", anchor, today=date(2026, 6, 1))
        _assert_totals(self, result, anchor)
        self.assertEqual(result["period_start"], date(2022, 1, 1))
        self.assertEqual(result["period_end"], date(2026, 12, 31))
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["profit_total"], 8.5)
        self.assertEqual(
            [(item["start"], item["end"], item["profit"])
             for item in result["buckets"]],
            [
                (date(2022, 1, 1), date(2022, 12, 31), 7.0),
                (date(2024, 1, 1), date(2024, 12, 31), 1.5)])
        later = build_result_calendar(
            facts, "year", anchor, today=date(2031, 3, 1))
        self.assertEqual(later["period_end"], date(2031, 12, 31))
        self.assertEqual(
            [item["start"] for item in later["buckets"]],
            [date(2022, 1, 1), date(2024, 1, 1)])

    def test_year_without_today_reaches_the_machine_year(self) -> None:
        anchor = date(2020, 6, 1)
        result = build_result_calendar(
            [_fact("2020-01-02", 1.0, 1.0)], "year", anchor)
        self.assertEqual(result["period_start"], date(2020, 1, 1))
        self.assertEqual(result["period_end"].month, 12)
        self.assertEqual(result["period_end"].day, 31)
        self.assertGreaterEqual(
            result["period_end"].year, date.today().year)

    def test_bucket_money_rounds_half_up(self) -> None:
        anchor = date(2023, 4, 15)
        # HALF_EVEN z 1.005 dałoby 1.00. Suma 0.014+0.014 to 0.03.
        single = build_result_calendar(
            [_fact("2023-04-01", 1.005, 10.005)], "day", anchor)
        self.assertEqual(single["buckets"][0]["profit"], 1.01)
        self.assertEqual(single["buckets"][0]["stake"], 10.01)
        summed = build_result_calendar(
            [
                _fact("2023-04-02", 0.014, 10.004),
                _fact("2023-04-02", 0.014, 0.014)],
            "day",
            anchor)
        self.assertEqual(summed["buckets"][0]["profit"], 0.03)
        self.assertEqual(summed["buckets"][0]["stake"], 10.02)
        self.assertEqual(summed["profit_total"], 0.03)
        self.assertEqual(summed["stake_total"], 10.02)

    def test_unknown_grain_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_result_calendar([], "decade", date(2023, 4, 1))
