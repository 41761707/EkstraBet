import { describe, expect, it } from "vitest";

import { addIsoCalendarDays, getWarsawDateIso } from "@/lib/date";

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

describe("addIsoCalendarDays", () => {
  it("adds calendar days without timezone drift", () => {
    expect(addIsoCalendarDays("2026-07-26", 1)).toBe("2026-07-27");
    expect(addIsoCalendarDays("2026-07-26", 6)).toBe("2026-08-01");
  });
});
