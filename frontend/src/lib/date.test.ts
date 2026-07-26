import { describe, expect, it } from "vitest";

import {
  addIsoCalendarDays,
  getWarsawDateIso,
  getWarsawDateTimeIso,
  hasWarsawNaiveDateTimePassed,
  normalizeWarsawNaiveDateTime,
} from "@/lib/date";

describe("getWarsawDateIso", () => {
  it("keeps Warsaw calendar day when UTC is still previous evening", () => {
    // 2026-07-25 22:30 UTC = 2026-07-26 00:30 in Warsaw (CEST)
    expect(getWarsawDateIso(new Date("2026-07-25T22:30:00.000Z"))).toBe(
      "2026-07-26",
    );
  });

  it("stays on Warsaw day before UTC midnight rollover", () => {
    // 2026-07-26 21:30 UTC = 2026-07-26 23:30 in Warsaw (CEST)
    expect(getWarsawDateIso(new Date("2026-07-26T21:30:00.000Z"))).toBe(
      "2026-07-26",
    );
  });

  it("rolls to next Warsaw day after local midnight", () => {
    // 2026-07-26 22:30 UTC = 2026-07-27 00:30 in Warsaw (CEST)
    expect(getWarsawDateIso(new Date("2026-07-26T22:30:00.000Z"))).toBe(
      "2026-07-27",
    );
  });
});

describe("getWarsawDateTimeIso", () => {
  it("formats Warsaw wall clock including CEST offset", () => {
    // 2026-07-26 16:00 UTC = 18:00 in Warsaw (CEST)
    expect(getWarsawDateTimeIso(new Date("2026-07-26T16:00:00.000Z"))).toBe(
      "2026-07-26T18:00:00",
    );
  });
});

describe("normalizeWarsawNaiveDateTime", () => {
  it("pads missing seconds for lexical compare", () => {
    expect(normalizeWarsawNaiveDateTime("2026-07-26T18:00")).toBe(
      "2026-07-26T18:00:00",
    );
  });

  it("returns null for invalid values", () => {
    expect(normalizeWarsawNaiveDateTime("not-a-date")).toBeNull();
  });
});

describe("hasWarsawNaiveDateTimePassed", () => {
  it("treats naive kick-off as Warsaw local, not UTC", () => {
    // 17:30 UTC = 19:30 Warsaw — kick-off 18:00 Warsaw already passed
    expect(
      hasWarsawNaiveDateTimePassed(
        "2026-07-26T18:00:00",
        new Date("2026-07-26T17:30:00.000Z"),
      ),
    ).toBe(true);

    // 15:30 UTC = 17:30 Warsaw — kick-off 18:00 Warsaw still ahead
    expect(
      hasWarsawNaiveDateTimePassed(
        "2026-07-26T18:00:00",
        new Date("2026-07-26T15:30:00.000Z"),
      ),
    ).toBe(false);
  });

  it("is true when Warsaw wall clock equals kick-off", () => {
    expect(
      hasWarsawNaiveDateTimePassed(
        "2026-07-26T18:00:00",
        new Date("2026-07-26T16:00:00.000Z"),
      ),
    ).toBe(true);
  });
});

describe("addIsoCalendarDays", () => {
  it("adds calendar days without timezone drift", () => {
    expect(addIsoCalendarDays("2026-07-26", 1)).toBe("2026-07-27");
    expect(addIsoCalendarDays("2026-07-26", 6)).toBe("2026-08-01");
  });
});
