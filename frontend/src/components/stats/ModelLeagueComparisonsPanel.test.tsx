import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  ModelFamilyPills,
  ModelLeagueComparisonsPanel,
} from "@/components/stats/ModelLeagueComparisonsPanel";
import { SignedLeagueProfitChart } from "@/components/stats/SignedLeagueProfitChart";
import type { ModelLeagueComparisons } from "@/types/api";

function sampleComparisons(
  overrides: Partial<ModelLeagueComparisons> = {},
): ModelLeagueComparisons {
  return {
    predictions: {
      ou: [
        {
          model_id: 1,
          model_name: "Alpha",
          average_accuracy_pct: 33.33,
          leagues: [
            {
              league_id: 1,
              league_name: "Ekstraklasa",
              total: 10,
              correct: 1,
              accuracy_pct: 10.0,
            },
            {
              league_id: 2,
              league_name: "Premier League",
              total: 20,
              correct: 9,
              accuracy_pct: 45.0,
            },
          ],
        },
        {
          model_id: 2,
          model_name: "Beta",
          average_accuracy_pct: 50.0,
          leagues: [
            {
              league_id: 1,
              league_name: "Ekstraklasa",
              total: 10,
              correct: 8,
              accuracy_pct: 80.0,
            },
            {
              league_id: 2,
              league_name: "Premier League",
              total: 10,
              correct: 2,
              accuracy_pct: 20.0,
            },
          ],
        },
      ],
      btts: [
        {
          model_id: 3,
          model_name: "Gamma",
          average_accuracy_pct: 60.0,
          leagues: [
            {
              league_id: 1,
              league_name: "Ekstraklasa",
              total: 5,
              correct: 3,
              accuracy_pct: 60.0,
            },
            {
              league_id: 2,
              league_name: "Premier League",
              total: 5,
              correct: 3,
              accuracy_pct: 60.0,
            },
          ],
        },
      ],
      result: [],
    },
    bet_profits: {
      ou: [
        {
          model_id: 1,
          model_name: "Alpha",
          total_profit: 0.7,
          leagues: [
            {
              league_id: 1,
              league_name: "Ekstraklasa",
              total_bets: 4,
              profit: 1.2,
            },
            {
              league_id: 2,
              league_name: "Premier League",
              total_bets: 6,
              profit: -0.5,
            },
          ],
        },
      ],
      btts: [],
      result: [],
    },
    ...overrides,
  };
}

describe("ModelLeagueComparisonsPanel", () => {
  it("renders family names and model names", () => {
    const html = renderToStaticMarkup(
      createElement(ModelLeagueComparisonsPanel, {
        comparisons: sampleComparisons(),
      }),
    );
    expect(html).toContain("Skuteczność predykcji per liga");
    expect(html).toContain("Profit zakładów per liga");
    expect(html).toContain("Over/Under");
    expect(html).toContain("BTTS");
    expect(html).toContain("Alpha");
    expect(html).toContain("Beta");
    expect(html).toContain("Gamma");
  });

  it("selects the first model of a family by default", () => {
    const html = renderToStaticMarkup(
      createElement(ModelLeagueComparisonsPanel, {
        comparisons: sampleComparisons(),
      }),
    );
    expect(html).toContain("Średnia modelu: 33.3%");
    expect(html).toContain("10.0%");
    expect(html).toContain("45.0%");
    expect(html).not.toContain("Średnia modelu: 50.0%");
    expect(html).not.toContain("80.0%");
  });

  it("marks the default model pill as pressed", () => {
    const html = renderToStaticMarkup(
      createElement(ModelLeagueComparisonsPanel, {
        comparisons: sampleComparisons(),
      }),
    );
    expect(html).toMatch(/aria-pressed="true"[^>]*>Alpha</);
    expect(html).toMatch(/aria-pressed="false"[^>]*>Beta</);
  });

  it("can press a different model pill", () => {
    const html = renderToStaticMarkup(
      createElement(ModelFamilyPills, {
        models: [
          { model_id: 1, model_name: "Alpha" },
          { model_id: 2, model_name: "Beta" },
        ],
        selectedModelId: 2,
        onSelect: () => undefined,
      }),
    );
    expect(html).toMatch(/aria-pressed="false"[^>]*>Alpha</);
    expect(html).toMatch(/aria-pressed="true"[^>]*>Beta</);
  });

  it("shows positive and negative profit with bet counts", () => {
    const html = renderToStaticMarkup(
      createElement(ModelLeagueComparisonsPanel, {
        comparisons: sampleComparisons(),
      }),
    );
    expect(html).toContain("+1.20 u");
    expect(html).toContain("-0.50 u");
    expect(html).toContain("4 zakł.");
    expect(html).toContain("6 zakł.");
    expect(html).toContain("Suma: +0.70 u");
  });

  it("does not render empty family or empty sections", () => {
    const html = renderToStaticMarkup(
      createElement(ModelLeagueComparisonsPanel, {
        comparisons: sampleComparisons({
          predictions: { ou: [], btts: [], result: [] },
          bet_profits: {
            ou: [],
            btts: [
              {
                model_id: 3,
                model_name: "Gamma",
                total_profit: 0,
                leagues: [
                  {
                    league_id: 1,
                    league_name: "Ekstraklasa",
                    total_bets: 2,
                    profit: 0,
                  },
                  {
                    league_id: 2,
                    league_name: "Premier League",
                    total_bets: 3,
                    profit: 0,
                  },
                ],
              },
            ],
            result: [],
          },
        }),
      }),
    );
    expect(html).not.toContain("Skuteczność predykcji per liga");
    expect(html).not.toContain("Over/Under");
    expect(html).not.toContain("1X2");
    expect(html).toContain("Profit zakładów per liga");
    expect(html).toContain("BTTS");
    expect(html).toContain("0.00 u");
  });
});

describe("SignedLeagueProfitChart", () => {
  it("renders zero, positive and negative values against a shared axis", () => {
    const html = renderToStaticMarkup(
      createElement(SignedLeagueProfitChart, {
        title: "Profit (unit)",
        totalProfit: 0.5,
        points: [
          { leagueName: "Ekstraklasa", profit: 1.5, totalBets: 3 },
          { leagueName: "Premier League", profit: -1.0, totalBets: 2 },
          { leagueName: "Championship", profit: 0, totalBets: 1 },
        ],
      }),
    );
    expect(html).toContain("+1.50 u");
    expect(html).toContain("-1.00 u");
    expect(html).toContain("0.00 u");
    expect(html).toContain("title=\"Zero\"");
    expect(html).toContain("left:50%");
  });
});
