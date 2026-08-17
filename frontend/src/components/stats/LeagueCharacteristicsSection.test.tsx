import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { LeagueCharacteristicsSection } from "@/components/stats/LeagueCharacteristicsSection";
import { LeagueComparisonFilters } from "@/components/stats/LeagueComparisonFilters";
import { createDefaultStatsFilterValues } from "@/lib/statsFilterParams";
import type { LeagueComparisons } from "@/types/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: () => undefined,
    refresh: () => undefined,
  }),
}));

const LEAGUES = [
  { id: 1, label: "Ekstraklasa" },
  { id: 2, label: "Premier League" },
];
const SEASONS = [{ id: 11, label: "2025/2026" }];

const SAMPLE_COMPARISONS: LeagueComparisons = {
  leagues: [
    {
      league_id: 1,
      league_name: "Ekstraklasa",
      played_matches: 10,
      btts_yes_pct: 60,
      over_2_5_pct: 50,
      home_win_pct: 40,
      away_win_pct: 30,
    },
    {
      league_id: 2,
      league_name: "Premier League",
      played_matches: 20,
      btts_yes_pct: 50,
      over_2_5_pct: 55,
      home_win_pct: 45,
      away_win_pct: 25,
    },
  ],
  averages: {
    btts_yes_pct: 53.33,
    over_2_5_pct: 53.33,
    home_win_pct: 43.33,
    away_win_pct: 26.67,
  },
};

describe("LeagueCharacteristicsSection", () => {
  it("separates match data from model stats with its own heading", () => {
    const html = renderToStaticMarkup(
      createElement(LeagueCharacteristicsSection, {
        leagues: LEAGUES,
        seasons: SEASONS,
        values: createDefaultStatsFilterValues(),
        comparisons: SAMPLE_COMPARISONS,
        errorMessage: null,
      }),
    );
    expect(html).toContain("Dane z meczów");
    expect(html).toContain("Porównanie lig ze średnią");
    expect(html).toContain("Filtry porównania lig");
    expect(html).toContain("niezależnie od modeli");
    expect(html).toContain("Ekstraklasa");
    expect(html).toContain("BTTS tak (%)");
  });

  it("shows an empty state when fewer than two leagues can be compared", () => {
    const html = renderToStaticMarkup(
      createElement(LeagueCharacteristicsSection, {
        leagues: LEAGUES,
        seasons: SEASONS,
        values: createDefaultStatsFilterValues(),
        comparisons: null,
        errorMessage: null,
      }),
    );
    expect(html).toContain("Za mało lig do porównania");
    expect(html).not.toContain("BTTS tak (%)");
  });
});

describe("LeagueComparisonFilters", () => {
  it("renders league and season controls for the comparison section", () => {
    const html = renderToStaticMarkup(
      createElement(LeagueComparisonFilters, {
        leagues: LEAGUES,
        seasons: SEASONS,
        values: createDefaultStatsFilterValues(),
      }),
    );
    expect(html).toContain("Ligi");
    expect(html).toContain("Najnowszy sezon każdej ligi");
    expect(html).toContain("Zastosuj filtry");
  });
});
