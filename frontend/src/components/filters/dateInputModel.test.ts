import { describe, expect, it } from "vitest";

import {
  buildCalendarGrid,
  formatIsoDatePl,
  formatMonthTitle,
  isIsoDateInRange,
  parseIsoDate,
  shiftCalendarMonth,
} from "@/components/filters/dateInputModel";

describe("parseIsoDate", () => {
  it("parses a valid ISO calendar date", () => {
    expect(parseIsoDate("2026-06-20")).toEqual({
      year: 2026,
      month: 6,
      day: 20,
    });
  });

  it("rejects impossible calendar days", () => {
    expect(parseIsoDate("2026-02-30")).toBeNull();
    expect(parseIsoDate("20.06.2026")).toBeNull();
    expect(parseIsoDate("")).toBeNull();
  });
});

describe("formatIsoDatePl", () => {
  it("formats ISO dates as dd.mm.yyyy without timezone drift", () => {
    expect(formatIsoDatePl("2026-06-20")).toBe("20.06.2026");
  });
});

describe("formatMonthTitle", () => {
  it("capitalizes the Polish month name", () => {
    expect(formatMonthTitle(2026, 6)).toBe("Czerwiec 2026");
  });
});

describe("shiftCalendarMonth", () => {
  it("wraps from December into the next year", () => {
    expect(shiftCalendarMonth(2026, 12, 1)).toEqual({
      year: 2027,
      month: 1,
      day: 1,
    });
  });

  it("shifts by a full year", () => {
    expect(shiftCalendarMonth(2026, 8, -12)).toEqual({
      year: 2025,
      month: 8,
      day: 1,
    });
  });
});

describe("isIsoDateInRange", () => {
  it("includes the min and max boundaries", () => {
    expect(isIsoDateInRange("2026-06-20", "2026-06-01", "2026-06-30")).toBe(
      true,
    );
    expect(isIsoDateInRange("2026-06-20", "2026-06-21")).toBe(false);
    expect(isIsoDateInRange("2026-06-20", undefined, "2026-06-19")).toBe(false);
  });
});

describe("buildCalendarGrid", () => {
  it("starts Monday-first when the month begins on Monday", () => {
    const cells = buildCalendarGrid(2026, 6, "2026-06-20", "2026-08-17");
    expect(cells).toHaveLength(42);
    expect(cells[0]?.isoDate).toBe("2026-06-01");
    expect(cells[19]?.isoDate).toBe("2026-06-20");
    expect(cells[19]?.isSelected).toBe(true);
    expect(cells[0]?.inCurrentMonth).toBe(true);
  });

  it("pads the previous month when the first day is Saturday", () => {
    const cells = buildCalendarGrid(2026, 8, "", "2026-08-17");
    expect(cells[0]?.isoDate).toBe("2026-07-27");
    expect(cells[0]?.inCurrentMonth).toBe(false);
    expect(cells[5]?.isoDate).toBe("2026-08-01");
    expect(cells[5]?.inCurrentMonth).toBe(true);
    expect(cells[21]?.isoDate).toBe("2026-08-17");
    expect(cells[21]?.isToday).toBe(true);
  });
});
