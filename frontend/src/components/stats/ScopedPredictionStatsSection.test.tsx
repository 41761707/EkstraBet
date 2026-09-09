import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  ScopedPredictionStatsContent,
  ScopedPredictionStatsSection,
} from "@/components/stats/ScopedPredictionStatsSection";
import {
  createDefaultScopedPredictionStatsFilters,
  EMPTY_SCOPED_PREDICTION_STATS_MESSAGE,
} from "@/components/stats/scopedPredictionStatsModel";
import type { ModelsByFamily } from "@/lib/modelsByFamily";
import type {
  CategoryStatistics,
  ModelAnalyticsResponse,
  PredictionBetBreakdown,
} from "@/types/api";

const FAMILY_MODELS: ModelsByFamily = {
  result: [{ id: 4, label: "Model 1X2" }],
  ou: [{ id: 7, label: "Model OU" }],
  btts: [{ id: 9, label: "Model BTTS" }],
};

function breakdown(total: number): PredictionBetBreakdown {
  return {
    total,
    correct: total > 0 ? 1 : 0,
    accuracy_pct: total > 0 ? 50 : null,
    profit_total: total > 0 ? 1.5 : null,
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

function analyticsWithData(): ModelAnalyticsResponse {
  return {
    categories: {
      ou: category(10, 4),
      btts: category(8, 3),
      result: category(12, 5),
    },
    aggregations: { by_team: null, by_league: null },
    league_comparisons: null,
    model_league_comparisons: null,
    filters_applied: {},
  };
}

function renderContent(
  overrides: Partial<Parameters<typeof ScopedPredictionStatsContent>[0]> = {},
): string {
  return renderToStaticMarkup(
    createElement(ScopedPredictionStatsContent, {
      description: "Podsumowanie predykcji dla ligi X w sezonie Y",
      status: "ready",
      error: null,
      analytics: analyticsWithData(),
      modelsByFamily: FAMILY_MODELS,
      appliedFilters: {
        ...createDefaultScopedPredictionStatsFilters(),
        modelResultIds: [4],
        modelOuIds: [7],
        modelBttsIds: [9],
      },
      onApply: () => undefined,
      ...overrides,
    }),
  );
}

describe("ScopedPredictionStatsSection", () => {
  it("renders a closed expander with heading and idle hint", () => {
    const html = renderToStaticMarkup(
      createElement(ScopedPredictionStatsSection, {
        leagueId: 1,
        seasonId: 13,
        heading: "Statystyki predykcji",
        description: "Podsumowanie predykcji dla ligi X w sezonie Y",
      }),
    );

    expect(html).toContain("Statystyki predykcji");
    expect(html).toContain("Podsumowanie predykcji dla ligi X w sezonie Y");
    expect(html).toContain("Otwórz sekcję, aby pobrać statystyki predykcji.");
    expect(html).not.toContain("Zastosuj filtry");
    expect(html).not.toContain("Ładowanie statystyk predykcji");
  });
});

describe("ScopedPredictionStatsContent", () => {
  it("renders loading spinner and keeps filters visible", () => {
    const html = renderContent({
      status: "loading",
      analytics: null,
    });

    expect(html).toContain("Ładowanie statystyk predykcji");
    expect(html).toContain("Zastosuj filtry");
    expect(html).toContain("Resetuj");
    expect(html).not.toContain("Over/Under");
  });

  it("renders error with filters so Apply/Reset remain available", () => {
    const html = renderContent({
      status: "error",
      error: "timeout",
      analytics: null,
    });

    expect(html).toContain("Nie udało się pobrać statystyk predykcji");
    expect(html).toContain("timeout");
    expect(html).not.toContain("Nie udało się pobrać statystyk predykcji. timeout");
    expect(html).toContain("Zastosuj filtry");
    expect(html).toContain("Resetuj");
    expect(html).not.toContain("Over/Under");
  });

  it("renders empty message with filters", () => {
    const html = renderContent({
      status: "empty",
      analytics: {
        categories: {
          ou: category(0, 0),
          btts: category(0, 0),
          result: category(0, 0),
        },
        aggregations: { by_team: null, by_league: null },
        league_comparisons: null,
        model_league_comparisons: null,
        filters_applied: {},
      },
    });

    expect(html).toContain("Brak statystyk");
    expect(html).toContain(EMPTY_SCOPED_PREDICTION_STATS_MESSAGE);
    expect(html).toContain("Zastosuj filtry");
    expect(html).toContain("Resetuj");
    expect(html).not.toContain("Over/Under");
  });

  it("renders Over/Under, BTTS and 1X2 panels when data is ready", () => {
    const html = renderContent({ status: "ready" });

    expect(html).toContain("Over/Under");
    expect(html).toContain("BTTS");
    expect(html).toContain("1X2");
    expect(html).toContain("Predykcje");
    expect(html).toContain("Zakłady");
    expect(html).toContain("Zastosuj filtry");
    expect(html).not.toContain("kolejka");
  });
});
