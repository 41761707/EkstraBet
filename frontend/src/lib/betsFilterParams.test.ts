import { describe, expect, it } from "vitest";

import {
  betsFilterPath,
  type BetsFilterValues,
} from "@/lib/betsFilterParams";

function baseFilters(
  overrides: Partial<BetsFilterValues> = {},
): BetsFilterValues {
  return {
    leagueIds: [],
    eventIds: [],
    modelIds: [],
    matchDate: "2026-08-15",
    fromNow: false,
    minOdds: 1.5,
    positiveEvOnly: false,
    applyTax: false,
    settlementStatus: "",
    sortBy: "ev",
    sortOrder: "desc",
    page: 1,
    ...overrides,
  };
}

describe("betsFilterPath", () => {
  it("includes from_now when Tylko od teraz is selected", () => {
    expect(betsFilterPath(baseFilters({ fromNow: true }))).toContain(
      "from_now=true",
    );
  });

  it("omits from_now when the checkbox is off", () => {
    expect(betsFilterPath(baseFilters())).not.toContain("from_now");
  });

  it("keeps from_now when another field such as min odds changes", () => {
    const path = betsFilterPath(
      baseFilters({ fromNow: true, minOdds: 1.4 }),
    );
    expect(path).toContain("from_now=true");
    expect(path).toContain("min_odds=1.4");
  });
});
