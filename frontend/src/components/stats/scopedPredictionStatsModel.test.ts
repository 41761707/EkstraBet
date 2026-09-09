import { describe, expect, it } from "vitest";

import {
  areScopedDateFiltersValid,
  createDefaultScopedPredictionStatsFilters,
  isAnalyticsEmpty,
  pickDefaultModelIds,
  shouldFetchScopedPredictionStats,
  toModelAnalyticsQuery,
  type ScopedPredictionStatsFiltersState,
  type ScopedPredictionStatsScope,
} from "@/components/stats/scopedPredictionStatsModel";
import type {
  CategoryStatistics,
  ModelAnalyticsResponse,
  PredictionBetBreakdown,
} from "@/types/api";

function leagueScope(
  overrides: Partial<ScopedPredictionStatsScope> = {},
): ScopedPredictionStatsScope {
  return {
    leagueId: 1,
    seasonId: 13,
    heading: "Statystyki predykcji",
    description: "Podsumowanie predykcji dla ligi X w sezonie Y",
    ...overrides,
  };
}

function filters(
  overrides: Partial<ScopedPredictionStatsFiltersState> = {},
): ScopedPredictionStatsFiltersState {
  return {
    ...createDefaultScopedPredictionStatsFilters(),
    modelResultIds: [4],
    modelOuIds: [7],
    modelBttsIds: [9],
    ...overrides,
  };
}

function breakdown(total: number): PredictionBetBreakdown {
  return {
    total,
    correct: 0,
    accuracy_pct: null,
    profit_total: null,
    by_type: [],
    charts: {
      distribution: { labels: [], values: [], percentages: [] },
      comparison: { labels: [], correct: [], incorrect: [] },
    },
  };
}

function category(
  predictionTotal: number,
  betTotal: number,
): CategoryStatistics {
  return {
    predictions: breakdown(predictionTotal),
    bets: breakdown(betTotal),
  };
}

function analytics(
  categories: Record<string, CategoryStatistics>,
): ModelAnalyticsResponse {
  return {
    categories,
    aggregations: { by_team: null, by_league: null },
    league_comparisons: null,
    model_league_comparisons: null,
    filters_applied: {},
  };
}

describe("createDefaultScopedPredictionStatsFilters", () => {
  it("starts with empty dates, no tax and no selected models", () => {
    expect(createDefaultScopedPredictionStatsFilters()).toEqual({
      modelResultIds: [],
      modelOuIds: [],
      modelBttsIds: [],
      dateFrom: "",
      dateTo: "",
      applyTax: false,
    });
  });
});

describe("pickDefaultModelIds", () => {
  it("returns the first family id when nothing is selected", () => {
    expect(pickDefaultModelIds([], [{ id: 4 }, { id: 11 }])).toEqual([4]);
  });

  it("keeps an existing selection", () => {
    expect(pickDefaultModelIds([11, 4], [{ id: 4 }, { id: 11 }])).toEqual([
      11, 4,
    ]);
  });

  it("omits the family when it has no models", () => {
    expect(pickDefaultModelIds([], [])).toBeUndefined();
  });
});

describe("areScopedDateFiltersValid", () => {
  it("accepts empty and one-sided dates", () => {
    expect(areScopedDateFiltersValid("", "")).toBe(true);
    expect(areScopedDateFiltersValid("2025-08-01", "")).toBe(true);
    expect(areScopedDateFiltersValid("", "2026-05-31")).toBe(true);
  });

  it("accepts equal or ordered Od/Do", () => {
    expect(areScopedDateFiltersValid("2025-08-01", "2025-08-01")).toBe(true);
    expect(areScopedDateFiltersValid("2025-08-01", "2026-05-31")).toBe(true);
  });

  it("rejects Od later than Do", () => {
    expect(areScopedDateFiltersValid("2026-05-31", "2025-08-01")).toBe(false);
  });
});

describe("toModelAnalyticsQuery", () => {
  it("keeps season and league and omits empty dates", () => {
    expect(toModelAnalyticsQuery(leagueScope(), filters())).toEqual({
      statType: "all",
      settledOnly: true,
      leagueIds: [1],
      seasonId: 13,
      applyTax: false,
      modelResultIds: [4],
      modelOuIds: [7],
      modelBttsIds: [9],
    });
  });

  it("adds teamId for a team page", () => {
    const query = toModelAnalyticsQuery(
      leagueScope({ teamId: 490 }),
      filters(),
    );
    expect(query.teamId).toBe(490);
    expect(query.leagueIds).toEqual([1]);
    expect(query.seasonId).toBe(13);
  });

  it("includes non-empty dates and tax", () => {
    expect(
      toModelAnalyticsQuery(
        leagueScope(),
        filters({
          dateFrom: "2025-08-01",
          dateTo: "2026-05-31",
          applyTax: true,
        }),
      ),
    ).toMatchObject({
      dateFrom: "2025-08-01",
      dateTo: "2026-05-31",
      applyTax: true,
    });
  });

  it("omits empty model id lists so a missing family is not queried", () => {
    const query = toModelAnalyticsQuery(
      leagueScope(),
      filters({
        modelResultIds: [],
        modelOuIds: [],
        modelBttsIds: [],
      }),
    );
    expect(query).not.toHaveProperty("modelResultIds");
    expect(query).not.toHaveProperty("modelOuIds");
    expect(query).not.toHaveProperty("modelBttsIds");
  });
});

describe("shouldFetchScopedPredictionStats", () => {
  it("is true only on the first expander open", () => {
    expect(shouldFetchScopedPredictionStats(true, false)).toBe(true);
  });

  it("does not fetch when the expander is closed", () => {
    expect(shouldFetchScopedPredictionStats(false, false)).toBe(false);
    expect(shouldFetchScopedPredictionStats(false, true)).toBe(false);
  });

  it("does not fetch again after the first load", () => {
    expect(shouldFetchScopedPredictionStats(true, true)).toBe(false);
  });
});

describe("isAnalyticsEmpty", () => {
  it("treats missing categories as empty", () => {
    expect(isAnalyticsEmpty(analytics({}))).toBe(true);
  });

  it("is empty when every family has zero prediction and bet totals", () => {
    expect(
      isAnalyticsEmpty(
        analytics({
          ou: category(0, 0),
          btts: category(0, 0),
          result: category(0, 0),
        }),
      ),
    ).toBe(true);
  });

  it("is not empty when any family has a positive total", () => {
    expect(
      isAnalyticsEmpty(
        analytics({
          ou: category(0, 0),
          btts: category(3, 0),
          result: category(0, 0),
        }),
      ),
    ).toBe(false);
    expect(
      isAnalyticsEmpty(
        analytics({
          ou: category(0, 2),
          btts: category(0, 0),
          result: category(0, 0),
        }),
      ),
    ).toBe(false);
  });
});
