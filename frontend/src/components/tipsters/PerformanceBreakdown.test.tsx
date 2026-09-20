import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  PERFORMANCE_AVG_ODDS_LABEL,
  PERFORMANCE_AVG_PROFIT_LABEL,
  PERFORMANCE_EMPTY_TITLE,
  PERFORMANCE_STAKE_LABEL,
  PERFORMANCE_TITLE,
  PERFORMANCE_WON_LABEL,
  PerformanceBreakdown,
} from "@/components/tipsters/PerformanceBreakdown";
import type { PerformanceItem } from "@/types/api";

function sampleItem(overrides: Partial<PerformanceItem> = {}): PerformanceItem {
  return {
    event_family_id: 1,
    event_family_name: "BTTS",
    league_id: 48,
    league_name: "Ekstraklasa",
    league_tier: 1,
    count: 8,
    won: 5,
    accuracy: 62.5,
    stake_total: 80,
    profit_total: 12.5,
    avg_profit: 1.56,
    avg_odds: 1.9,
    roi_pct: 15.63,
    ...overrides,
  };
}

describe("PerformanceBreakdown", () => {
  it("renders average odds, average profit, stake and wins", () => {
    const item = sampleItem();
    const html = renderToStaticMarkup(
      <PerformanceBreakdown
        data={{
          by_event_family: [item],
          by_league: [],
          by_league_tier: [],
          best_event_family: item,
          worst_event_family: item,
          best_league: null,
          worst_league: null,
          best_league_tier: null,
          worst_league_tier: null,
        }}
        currency="PLN"
      />,
    );

    expect(html).toContain(PERFORMANCE_TITLE);
    expect(html).toContain(PERFORMANCE_WON_LABEL);
    expect(html).toContain(PERFORMANCE_STAKE_LABEL);
    expect(html).toContain(PERFORMANCE_AVG_PROFIT_LABEL);
    expect(html).toContain(PERFORMANCE_AVG_ODDS_LABEL);
    expect(html).toContain("BTTS");
    expect(html).toContain("5");
    expect(html).toContain("80.00 PLN");
    expect(html).toContain("+12.50 PLN");
    expect(html).toContain("+1.56 PLN");
    expect(html).toContain("1.90");
    expect(html).toContain("text-success");
  });

  it("shows a dash when average odds and profit are missing", () => {
    const html = renderToStaticMarkup(
      <PerformanceBreakdown
        data={{
          by_event_family: [
            sampleItem({
              count: 0,
              won: 0,
              accuracy: null,
              stake_total: 0,
              profit_total: 0,
              avg_profit: null,
              avg_odds: null,
              roi_pct: null,
            }),
          ],
          by_league: [],
          by_league_tier: [],
          best_event_family: null,
          worst_event_family: null,
          best_league: null,
          worst_league: null,
          best_league_tier: null,
          worst_league_tier: null,
        }}
        currency="PLN"
      />,
    );

    expect(html).toContain("—");
    expect(html).not.toContain(PERFORMANCE_EMPTY_TITLE);
  });
});
