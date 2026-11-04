"""Group settled result facts into calendar buckets.

The module does not read the database and does not know the lens
(coupon or single) or the stake unit. Callers pass facts that
already carry an anchor day, a profit and a stake.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from datetime import timedelta
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Any


_MONEY_STEP = Decimal("0.01")
_GRAIN_DAY = "day"
_GRAIN_WEEK = "week"
_GRAIN_MONTH = "month"
_GRAIN_YEAR = "year"
_KNOWN_GRAINS = frozenset({
    _GRAIN_DAY, _GRAIN_WEEK, _GRAIN_MONTH, _GRAIN_YEAR})


def build_result_calendar(
        facts: list[dict[str, Any]],
        grain: str,
        anchor: date,
        today: date | None = None) -> dict[str, Any]:
    """Fold facts into the non-empty buckets of one period.

    ``anchor`` is returned unchanged. Grain ``year`` does not filter
    on it. ``today`` stands in for ``date.today()`` so the year
    period can include the current year without a fact in it. An
    unknown grain raises ``ValueError``.
    """
    _require_grain(grain)
    current = date.today() if today is None else today
    period_start, period_end = _period_bounds(
        grain, anchor, facts, current)
    kept = _facts_inside(facts, period_start, period_end)
    buckets = _buckets_for(kept, grain)
    return {
        "anchor": anchor,
        "period_start": period_start,
        "period_end": period_end,
        "profit_total": _sum_money(
            [item["profit"] for item in buckets]),
        "stake_total": _sum_money(
            [item["stake"] for item in buckets]),
        "count": sum(item["count"] for item in buckets),
        "buckets": buckets}


def _require_grain(grain: str) -> None:
    if grain not in _KNOWN_GRAINS:
        raise ValueError(f"Unknown grain: {grain}")


def _period_bounds(
        grain: str,
        anchor: date,
        facts: list[dict[str, Any]],
        today: date) -> tuple[date, date]:
    if grain == _GRAIN_DAY:
        return _month_bounds(anchor)
    if grain == _GRAIN_WEEK:
        return _iso_year_bounds(anchor.isocalendar().year)
    if grain == _GRAIN_MONTH:
        return _calendar_year_bounds(anchor.year)
    return _history_bounds(facts, today)


def _month_bounds(day: date) -> tuple[date, date]:
    last_day = monthrange(day.year, day.month)[1]
    return (
        date(day.year, day.month, 1),
        date(day.year, day.month, last_day))


def _calendar_year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def _iso_year_bounds(iso_year: int) -> tuple[date, date]:
    # 4 stycznia i 28 grudnia zawsze leżą w skrajnych tygodniach ISO.
    opening = date(iso_year, 1, 4)
    closing = date(iso_year, 12, 28)
    start = opening - timedelta(days=opening.weekday())
    end = closing + timedelta(days=6 - closing.weekday())
    return start, end


def _history_bounds(
        facts: list[dict[str, Any]],
        today: date) -> tuple[date, date]:
    """Span from the earliest fact year through the later end year.

    The end year is the later of the latest fact and ``today``.
    With no facts the span is the calendar year of ``today``.
    Empty years between the ends are not buckets.
    """
    years = [_fact_day(fact).year for fact in facts]
    if not years:
        return _calendar_year_bounds(today.year)
    start_year = min(years)
    end_year = max(max(years), today.year)
    return date(start_year, 1, 1), date(end_year, 12, 31)


def _facts_inside(
        facts: list[dict[str, Any]],
        period_start: date,
        period_end: date) -> list[dict[str, Any]]:
    return [
        fact for fact in facts
        if period_start <= _fact_day(fact) <= period_end]


def _fact_day(fact: dict[str, Any]) -> date:
    return fact["anchor_date"]


def _buckets_for(
        facts: list[dict[str, Any]],
        grain: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, ...], dict[str, Any]] = {}
    for fact in facts:
        day = _fact_day(fact)
        key = _bucket_key(day, grain)
        bucket = grouped.get(key)
        if bucket is None:
            start, end = _bucket_span(day, grain)
            bucket = {
                "start": start,
                "end": end,
                "profit": Decimal("0"),
                "stake": Decimal("0"),
                "count": 0}
            grouped[key] = bucket
        bucket["profit"] += Decimal(str(fact["profit"]))
        bucket["stake"] += Decimal(str(fact["stake"]))
        bucket["count"] += 1
    ordered = sorted(grouped.values(), key=_bucket_start)
    return [_finish_bucket(item) for item in ordered]


def _bucket_start(bucket: dict[str, Any]) -> date:
    return bucket["start"]


def _bucket_key(day: date, grain: str) -> tuple[int, ...]:
    if grain == _GRAIN_DAY:
        return (day.year, day.month, day.day)
    if grain == _GRAIN_WEEK:
        iso = day.isocalendar()
        return (iso.year, iso.week)
    if grain == _GRAIN_MONTH:
        return (day.year, day.month)
    return (day.year,)


def _bucket_span(day: date, grain: str) -> tuple[date, date]:
    if grain == _GRAIN_DAY:
        return day, day
    if grain == _GRAIN_WEEK:
        monday = day - timedelta(days=day.weekday())
        return monday, monday + timedelta(days=6)
    if grain == _GRAIN_MONTH:
        return _month_bounds(day)
    return _calendar_year_bounds(day.year)


def _finish_bucket(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "start": raw["start"],
        "end": raw["end"],
        "profit": _money(raw["profit"]),
        "stake": _money(raw["stake"]),
        "count": raw["count"]}


def _sum_money(amounts: list[float]) -> float:
    total = Decimal("0")
    for amount in amounts:
        total += Decimal(str(amount))
    return _money(total)


def _money(value: Decimal) -> float:
    """Two decimal places, half up, same as the tipster repository."""
    quantized = value.quantize(_MONEY_STEP, rounding=ROUND_HALF_UP)
    return float(quantized)
