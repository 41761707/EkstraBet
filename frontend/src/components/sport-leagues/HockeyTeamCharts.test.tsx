import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PreferencesProvider } from "@/components/preferences/PreferencesProvider";
import { HockeyTeamCharts } from "@/components/sport-leagues/HockeyTeamCharts";
import {
  DEFAULT_PREFERENCES,
  type PreferencesApi,
  type PreferencesStorage,
} from "@/lib/preferences";
import type { HockeyTeamHistoryPoint } from "@/types/api";

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

function hockeyPoint(
  overrides: Partial<HockeyTeamHistoryPoint> = {},
): HockeyTeamHistoryPoint {
  return {
    match_id: 1,
    match_date: "2024-01-15",
    opponent_shortcut: "BOS",
    opponent_name: "Boston Bruins",
    team_goals: 3,
    opponent_goals: 2,
    total_goals: 5,
    first_period_goals: 1,
    team_shots_on_goal: 30,
    opponent_shots_on_goal: 25,
    result: "W",
    home_team_name: "Toronto Maple Leafs",
    away_team_name: "Boston Bruins",
    home_goals: 3,
    away_goals: 2,
    ...overrides,
  };
}

function renderCharts(
  history: HockeyTeamHistoryPoint[],
  selectedStats: string[],
): string {
  return renderToStaticMarkup(
    <PreferencesProvider
      hasSession={false}
      storage={silentStorage()}
      api={silentApi()}
    >
      <HockeyTeamCharts
        teamName="Toronto Maple Leafs"
        history={history}
        ouLine={5.5}
        selectedStats={selectedStats}
      />
    </PreferencesProvider>,
  );
}

describe("HockeyTeamCharts", () => {
  it("throws outside PreferencesProvider", () => {
    expect(() =>
      renderToStaticMarkup(
        <HockeyTeamCharts
          teamName="Toronto Maple Leafs"
          history={[hockeyPoint()]}
          ouLine={5.5}
          selectedStats={["Bramki"]}
        />,
      ),
    ).toThrow("usePreferences must be used within PreferencesProvider");
  });

  it("uses full opponent names on chart labels by default", () => {
    const html = renderCharts([hockeyPoint()], ["Bramki"]);

    expect(html).toContain("Boston Bruins 2024-01-15");
    expect(html).not.toContain("BOS 2024-01-15");
  });

  it("uses full opponent names in the results list by default", () => {
    const html = renderCharts([hockeyPoint()], ["Rezultaty"]);

    expect(html).toContain("vs Boston Bruins");
    expect(html).not.toContain("vs BOS");
    expect(html).toContain("Toronto Maple Leafs");
  });

  it("keeps the filtered point's own opponent label after dropping matches", () => {
    const html = renderCharts(
      [
        hockeyPoint({
          match_id: 1,
          match_date: "2024-01-10",
          opponent_shortcut: "BOS",
          opponent_name: "Boston Bruins",
          first_period_goals: null,
        }),
        hockeyPoint({
          match_id: 2,
          match_date: "2024-01-15",
          opponent_shortcut: "MTL",
          opponent_name: "Montreal Canadiens",
          first_period_goals: 2,
          away_team_name: "Montreal Canadiens",
        }),
      ],
      ["Bramki w pierwszej tercji"],
    );

    expect(html).toContain("Montreal Canadiens 2024-01-15");
    expect(html).not.toContain("Boston Bruins 2024-01-15");
    expect(html).not.toContain("Boston Bruins 2024-01-10");
  });
});
