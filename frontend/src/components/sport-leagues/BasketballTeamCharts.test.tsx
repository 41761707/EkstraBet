import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import { BasketballTeamCharts } from "@/components/sport-leagues/BasketballTeamCharts";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";
import type { BasketballTeamHistoryPoint } from "@/types/api";

function silentStorage(): PreferencesStorage {
  return {
    load: () => ({ ...DEFAULT_PREFERENCES }),
    save: () => undefined,
  };
}

function silentApi(): PreferencesApi {
  return {
    get: async () => ({ status: "no-session" }),
    put: async () => ({ ...DEFAULT_PREFERENCES }),
  };
}

function basketballPoint(
  overrides: Partial<BasketballTeamHistoryPoint> = {},
): BasketballTeamHistoryPoint {
  return {
    match_id: 1,
    match_date: "2024-02-03",
    opponent_shortcut: "LAL",
    opponent_name: "Los Angeles Lakers",
    team_points: 110,
    opponent_points: 104,
    total_points: 214,
    result: "W",
    home_team_name: "Golden State Warriors",
    away_team_name: "Los Angeles Lakers",
    home_points: 110,
    away_points: 104,
    ...overrides,
  };
}

function renderCharts(
  history: BasketballTeamHistoryPoint[],
  selectedStats: string[],
): string {
  return renderToStaticMarkup(
    <PreferencesProvider
      hasSession={false}
      storage={silentStorage()}
      api={silentApi()}
    >
      <BasketballTeamCharts
        teamName="Golden State Warriors"
        history={history}
        ouLine={220.5}
        selectedStats={selectedStats}
      />
    </PreferencesProvider>,
  );
}

describe("BasketballTeamCharts", () => {
  it("throws outside PreferencesProvider", () => {
    expect(() =>
      renderToStaticMarkup(
        <BasketballTeamCharts
          teamName="Golden State Warriors"
          history={[basketballPoint()]}
          ouLine={220.5}
          selectedStats={["Punkty"]}
        />,
      ),
    ).toThrow("usePreferences must be used within PreferencesProvider");
  });

  it("uses full opponent names on chart labels by default", () => {
    const html = renderCharts([basketballPoint()], ["Punkty"]);

    expect(html).toContain("Los Angeles Lakers 2024-02-03");
    expect(html).not.toContain("LAL 2024-02-03");
  });

  it("uses full opponent names in the results list by default", () => {
    const html = renderCharts([basketballPoint()], ["Rezultaty"]);

    expect(html).toContain("vs Los Angeles Lakers");
    expect(html).not.toContain("vs LAL");
    expect(html).toContain("Golden State Warriors");
  });
});
