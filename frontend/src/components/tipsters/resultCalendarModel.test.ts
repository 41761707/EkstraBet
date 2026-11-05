import { describe, expect, it } from "vitest";

import {
  canShiftForward,
  dayGrid,
  intensityStep,
  monthSlots,
  periodTitle,
  shiftAnchor,
  weekSlots,
  yearSlots,
} from "@/components/tipsters/resultCalendarModel";
import type { ResultCalendarBucket } from "@/types/api";

function bucket(
  start: string,
  end: string,
  profit = 1,
): ResultCalendarBucket {
  return { start, end, profit, stake: 10, count: 1 };
}

describe("dayGrid", () => {
  it("starts April 2023 on Saturday in a Monday-first week", () => {
    const april = bucket("2023-04-01", "2023-04-01", 4);
    const slots = dayGrid("2023-04-15", [april]);

    expect(slots.slice(0, 5).every((slot) => slot.start === null)).toBe(true);
    expect(slots[5]?.start).toBe("2023-04-01");
    expect(slots[5]?.bucket).toBe(april);
    expect(slots[6]?.start).toBe("2023-04-02");
    expect(slots[6]?.bucket).toBeNull();
    expect(slots[slots.length - 1]?.start).toBe("2023-04-30");
    expect(slots.length % 7).toBe(0);
  });

  it("pads the week after a month that ends before Sunday", () => {
    const slots = dayGrid("2023-02-01", []);

    expect(slots[2]?.start).toBe("2023-02-01");
    expect(slots.filter((slot) => slot.start !== null)).toHaveLength(28);
    expect(slots[slots.length - 1]?.start).toBeNull();
    expect(slots.length % 7).toBe(0);
  });
});

describe("weekSlots", () => {
  it("lists the ISO weeks of 2023 and places 1 April on 27 March", () => {
    const slots = weekSlots("2023-04-01", []);

    expect(slots).toHaveLength(52);
    expect(slots.some((slot) => slot.start === "2023-03-27")).toBe(true);
    expect(slots.every((slot) => slot.bucket === null)).toBe(true);
  });

  it("keeps 1 January 2023 in ISO year 2022", () => {
    const slots = weekSlots("2023-01-01", []);

    expect(slots).toHaveLength(52);
    expect(slots.some((slot) => slot.start === "2022-12-26")).toBe(true);
    expect(slots.some((slot) => slot.start === "2023-01-02")).toBe(false);
  });
});

describe("monthSlots", () => {
  it("keeps all twelve months and attaches April", () => {
    const april = bucket("2023-04-01", "2023-04-30", 12);
    const slots = monthSlots("2023-04-15", [april]);

    expect(slots).toHaveLength(12);
    expect(slots[0]).toEqual({ start: "2023-01-01", bucket: null });
    expect(slots[3]?.bucket).toBe(april);
    expect(slots[11]?.start).toBe("2023-12-01");
  });
});

describe("yearSlots", () => {
  it("fills the gap between 2022 and 2024 and reaches today", () => {
    const slots = yearSlots(
      [
        bucket("2022-01-01", "2022-12-31"),
        bucket("2024-01-01", "2024-12-31"),
      ],
      "2023-06-01",
    );

    expect(slots.map((slot) => slot.start)).toEqual([
      "2022-01-01",
      "2023-01-01",
      "2024-01-01",
    ]);
    expect(slots[1]?.bucket).toBeNull();
    expect(slots[0]?.bucket?.start).toBe("2022-01-01");
  });

  it("reaches back and forward to the year of today", () => {
    const slots = yearSlots(
      [bucket("2024-01-01", "2024-12-31")],
      "2022-06-01",
    );

    expect(slots.map((slot) => slot.start)).toEqual([
      "2022-01-01",
      "2023-01-01",
      "2024-01-01",
    ]);
    expect(slots[0]?.bucket).toBeNull();
    expect(slots[2]?.bucket?.start).toBe("2024-01-01");
    expect(yearSlots([], "2026-06-01")).toEqual([
      { start: "2026-01-01", bucket: null },
    ]);
  });
});

describe("canShiftForward", () => {
  it("blocks the current month and allows an earlier one", () => {
    expect(canShiftForward("day", "2023-04-01", "2023-04-15")).toBe(false);
    expect(canShiftForward("day", "2023-04-01", "2023-05-01")).toBe(true);
  });

  it("compares ISO years for weeks and never steps a year grain", () => {
    expect(canShiftForward("week", "2023-01-01", "2023-06-01")).toBe(true);
    expect(canShiftForward("month", "2022-04-15", "2023-04-15")).toBe(true);
    expect(canShiftForward("month", "2023-04-15", "2023-01-01")).toBe(false);
    expect(canShiftForward("year", "2020-01-01", "2023-06-01")).toBe(false);
  });
});

describe("shiftAnchor", () => {
  it("moves a day into May 2023 and a month into 2022", () => {
    expect(shiftAnchor("day", "2023-04-15", 1)).toBe("2023-05-15");
    expect(shiftAnchor("month", "2023-04-15", -1)).toBe("2022-04-15");
  });

  it("clamps the day and steps a week by ISO year", () => {
    expect(shiftAnchor("day", "2023-01-31", 1)).toBe("2023-02-28");
    expect(shiftAnchor("week", "2023-01-01", 1)).toBe("2023-12-31");
    expect(shiftAnchor("week", "2020-12-31", 1)).toBe("2021-12-30");
    expect(shiftAnchor("year", "2023-04-15", 1)).toBe("2023-04-15");
  });
});

describe("intensityStep", () => {
  it("maps zero and the thirds of the scale", () => {
    expect(intensityStep(0, 10)).toBe(0);
    expect(intensityStep(1, 9)).toBe(1);
    expect(intensityStep(9, 9)).toBe(3);
  });
});

describe("periodTitle", () => {
  it("names the month, the ISO year and the whole history", () => {
    expect(periodTitle("day", "2023-04-15")).toBe("Kwiecień 2023");
    expect(periodTitle("week", "2023-04-15")).toBe("2023");
    expect(periodTitle("week", "2023-01-01")).toBe("2022");
    expect(periodTitle("month", "2023-04-15")).toBe("2023");
    expect(periodTitle("year", "2023-04-15")).toBe("Wszystkie lata");
  });
});
