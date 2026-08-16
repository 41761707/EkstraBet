import { describe, expect, it } from "vitest";

import {
  areAllOptionsSelected,
  resolveAnalyticsLeagueIds,
  serializeLeagueFilter,
  statsFilterPath,
  visibleLeagueFilterIds,
  type StatsFilterValues,
} from "@/lib/statsFilterParams";

const ALL_LEAGUE_IDS = [1, 2, 3, 4, 5];

function baseFilters(
  overrides: Partial<StatsFilterValues> = {},
): StatsFilterValues {
  return {
    leagueIds: [],
    seasonId: null,
    modelResultIds: [],
    modelOuIds: [],
    modelBttsIds: [],
    dateFrom: "",
    dateTo: "",
    roundFrom: "",
    roundTo: "",
    statType: "all",
    settledOnly: true,
    positiveEvOnly: false,
    applyTax: false,
    groupBy: "none",
    aggregationMetric: "accuracy",
    ...overrides,
  };
}

describe("areAllOptionsSelected", () => {
  it("returns true when every available id is selected", () => {
    expect(areAllOptionsSelected([5, 1, 3, 2, 4], ALL_LEAGUE_IDS)).toBe(true);
  });

  it("returns false when a subset is selected", () => {
    expect(areAllOptionsSelected([1, 2, 3], ALL_LEAGUE_IDS)).toBe(false);
  });
});

describe("visibleLeagueFilterIds", () => {
  it("shows no checkboxes when the filter means all leagues", () => {
    expect(visibleLeagueFilterIds([], ALL_LEAGUE_IDS)).toEqual([]);
    expect(visibleLeagueFilterIds(ALL_LEAGUE_IDS, ALL_LEAGUE_IDS)).toEqual([]);
  });

  it("keeps a partial selection visible", () => {
    expect(visibleLeagueFilterIds([2, 5], ALL_LEAGUE_IDS)).toEqual([2, 5]);
  });
});

describe("resolveAnalyticsLeagueIds", () => {
  it("uses every football league when nothing is selected", () => {
    expect(resolveAnalyticsLeagueIds([], ALL_LEAGUE_IDS)).toEqual(
      ALL_LEAGUE_IDS,
    );
  });

  it("uses every football league when every league is selected", () => {
    expect(
      resolveAnalyticsLeagueIds(ALL_LEAGUE_IDS, ALL_LEAGUE_IDS),
    ).toEqual(ALL_LEAGUE_IDS);
  });

  it("keeps a partial selection for the API", () => {
    expect(resolveAnalyticsLeagueIds([2, 5], ALL_LEAGUE_IDS)).toEqual([
      2, 5,
    ]);
  });
});

describe("serializeLeagueFilter", () => {
  it("omits league_ids when nothing is selected", () => {
    expect(serializeLeagueFilter([], ALL_LEAGUE_IDS)).toBeUndefined();
  });

  it("omits league_ids when every league is selected", () => {
    expect(
      serializeLeagueFilter(ALL_LEAGUE_IDS, ALL_LEAGUE_IDS),
    ).toBeUndefined();
  });

  it("keeps a partial league selection", () => {
    expect(serializeLeagueFilter([2, 5], ALL_LEAGUE_IDS)).toBe("2,5");
  });
});

describe("statsFilterPath", () => {
  it("uses a clean /stats path when all leagues are selected", () => {
    expect(
      statsFilterPath(
        baseFilters({ leagueIds: ALL_LEAGUE_IDS }),
        ALL_LEAGUE_IDS,
      ),
    ).toBe("/stats");
  });

  it("keeps other filters when all leagues are selected", () => {
    const path = statsFilterPath(
      baseFilters({
        leagueIds: ALL_LEAGUE_IDS,
        applyTax: true,
      }),
      ALL_LEAGUE_IDS,
    );
    expect(path).toContain("/stats?");
    expect(path).toContain("apply_tax=true");
    expect(path).not.toContain("league_ids");
  });

  it("includes league_ids for a partial selection", () => {
    const path = statsFilterPath(
      baseFilters({ leagueIds: [1, 5] }),
      ALL_LEAGUE_IDS,
    );
    expect(path).toContain("/stats?");
    expect(path).toContain("league_ids=");
    expect(decodeURIComponent(path)).toContain("league_ids=1,5");
  });
});
