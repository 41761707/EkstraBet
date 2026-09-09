import { describe, expect, it } from "vitest";

import {
  areScopedDateFiltersValid,
  createDefaultScopedPredictionStatsFilters,
  hasScopedModelOptions,
  isAnalyticsEmpty,
  pickDefaultModelIds,
  resetScopedPredictionStatsFilters,
  scopedPredictionStatsFiltersKey,
  shouldFetchScopedPredictionAnalytics,
  shouldFetchScopedPredictionStats,
  toModelAnalyticsQuery,
  withDefaultScopedModelIds,
  type ScopedPredictionStatsFiltersState,
  type ScopedPredictionStatsScope,
} from "@/components/stats/scopedPredictionStatsModel";
import type { ModelsByFamily } from "@/lib/modelsByFamily";
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

function familyModels(): ModelsByFamily {
  return {
    result: [{ id: 4, label: "Model 1X2" }],
    ou: [{ id: 7, label: "Model OU" }],
    btts: [{ id: 9, label: "Model BTTS" }],
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

describe("scopedPredictionStatsFiltersKey", () => {
  it("is the same for copied objects and copied id arrays", () => {
    const original = filters({ dateFrom: "2025-08-01", applyTax: true });
    const copied = {
      ...original,
      modelResultIds: [...original.modelResultIds],
      modelOuIds: [...original.modelOuIds],
      modelBttsIds: [...original.modelBttsIds],
    };
    expect(scopedPredictionStatsFiltersKey(copied)).toBe(
      scopedPredictionStatsFiltersKey(original),
    );
  });

  it("changes when a filter field changes", () => {
    const withDate = filters({ dateTo: "2026-05-31" });
    expect(scopedPredictionStatsFiltersKey(withDate)).not.toBe(
      scopedPredictionStatsFiltersKey(filters()),
    );
  });
});

describe("withDefaultScopedModelIds", () => {
  it("fills empty family selections with the first model id", () => {
    expect(
      withDefaultScopedModelIds(
        createDefaultScopedPredictionStatsFilters(),
        familyModels(),
      ),
    ).toEqual({
      modelResultIds: [4],
      modelOuIds: [7],
      modelBttsIds: [9],
      dateFrom: "",
      dateTo: "",
      applyTax: false,
    });
  });

  it("keeps an existing selection", () => {
    const next = withDefaultScopedModelIds(
      filters({ modelResultIds: [11], modelOuIds: [7] }),
      {
        result: [
          { id: 4, label: "A" },
          { id: 11, label: "B" },
        ],
        ou: [{ id: 7, label: "OU" }],
        btts: [{ id: 9, label: "BTTS" }],
      },
    );
    expect(next.modelResultIds).toEqual([11]);
    expect(next.modelOuIds).toEqual([7]);
  });
});

describe("resetScopedPredictionStatsFilters", () => {
  it("clears dates and tax and selects the first model of each family", () => {
    expect(resetScopedPredictionStatsFilters(familyModels())).toEqual({
      modelResultIds: [4],
      modelOuIds: [7],
      modelBttsIds: [9],
      dateFrom: "",
      dateTo: "",
      applyTax: false,
    });
  });

  it("leaves a family empty when it has no models", () => {
    expect(
      resetScopedPredictionStatsFilters({
        result: [{ id: 4, label: "A" }],
        ou: [],
        btts: [],
      }),
    ).toEqual({
      modelResultIds: [4],
      modelOuIds: [],
      modelBttsIds: [],
      dateFrom: "",
      dateTo: "",
      applyTax: false,
    });
  });
});

describe("hasScopedModelOptions", () => {
  it("is true when any family has a model", () => {
    expect(hasScopedModelOptions(familyModels())).toBe(true);
    expect(
      hasScopedModelOptions({
        result: [],
        ou: [{ id: 7, label: "OU" }],
        btts: [],
      }),
    ).toBe(true);
  });

  it("is false when every family is empty", () => {
    expect(
      hasScopedModelOptions({ result: [], ou: [], btts: [] }),
    ).toBe(false);
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
  it("is true only on the first expander open before models return", () => {
    expect(shouldFetchScopedPredictionStats(true, false)).toBe(true);
  });

  it("does not fetch models when the expander is closed", () => {
    expect(shouldFetchScopedPredictionStats(false, false)).toBe(false);
    expect(shouldFetchScopedPredictionStats(false, true)).toBe(false);
  });

  it("does not fetch models again after they have returned", () => {
    expect(shouldFetchScopedPredictionStats(true, true)).toBe(false);
  });
});

describe("shouldFetchScopedPredictionAnalytics", () => {
  it("fetches analytics after models return and before analytics complete", () => {
    expect(shouldFetchScopedPredictionAnalytics(true, true, false)).toBe(
      true,
    );
  });

  it("does not fetch analytics before models return", () => {
    expect(shouldFetchScopedPredictionAnalytics(true, false, false)).toBe(
      false,
    );
  });

  it("does not fetch analytics after they have loaded once", () => {
    expect(shouldFetchScopedPredictionAnalytics(true, true, true)).toBe(
      false,
    );
  });
});

describe("scoped prediction stats fetch orchestration", () => {
  it("fetches models when the expander stays open after a scope reset", () => {
    const hasLoadedModels = false;
    const hasLoadedOnce = false;
    expect(shouldFetchScopedPredictionStats(true, hasLoadedModels)).toBe(
      true,
    );
    expect(
      shouldFetchScopedPredictionAnalytics(true, hasLoadedModels, hasLoadedOnce),
    ).toBe(false);
  });

  it("loads analytics again after close during analytics then reopen", () => {
    const hasLoadedModels = true;
    const hasLoadedOnce = false;
    expect(shouldFetchScopedPredictionStats(false, hasLoadedModels)).toBe(
      false,
    );
    expect(
      shouldFetchScopedPredictionAnalytics(false, hasLoadedModels, hasLoadedOnce),
    ).toBe(false);
    expect(shouldFetchScopedPredictionStats(true, hasLoadedModels)).toBe(
      false,
    );
    expect(
      shouldFetchScopedPredictionAnalytics(true, hasLoadedModels, hasLoadedOnce),
    ).toBe(true);
  });

  it("fetches nothing while the expander is closed", () => {
    expect(shouldFetchScopedPredictionStats(false, false)).toBe(false);
    expect(shouldFetchScopedPredictionAnalytics(false, false, false)).toBe(
      false,
    );
    expect(shouldFetchScopedPredictionStats(false, true)).toBe(false);
    expect(shouldFetchScopedPredictionAnalytics(false, true, false)).toBe(
      false,
    );
  });

  it("does not refetch through the lazy-load gates after Apply", () => {
    expect(shouldFetchScopedPredictionStats(true, true)).toBe(false);
    expect(shouldFetchScopedPredictionAnalytics(true, true, true)).toBe(
      false,
    );
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
