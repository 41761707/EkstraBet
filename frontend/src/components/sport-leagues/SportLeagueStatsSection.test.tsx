import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SportLeagueStatsSection } from "@/components/sport-leagues/SportLeagueStatsSection";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type SportLeagueStatsResponse,
} from "@/types/api";

function payload(category: string): SportLeagueStatsResponse {
  return {
    league_id: 1,
    season_id: 1,
    sport_id: HOCKEY_SPORT_ID,
    category,
    rows: [],
    distribution: null,
    goals_distribution: null,
  };
}

describe("SportLeagueStatsSection", () => {
  it("adds Special teams only on the NHL tabs", () => {
    const hockey = renderToStaticMarkup(
      <SportLeagueStatsSection
        sportId={HOCKEY_SPORT_ID}
        stats={{
          shots: payload("shots"),
          goals: payload("goals"),
          over_under: payload("over_under"),
          special_teams: payload("special_teams"),
        }}
      />,
    );
    expect(hockey).toContain("Strzały");
    expect(hockey).toContain("Special teams");

    const basketball = renderToStaticMarkup(
      <SportLeagueStatsSection sportId={BASKETBALL_SPORT_ID} stats={{}} />,
    );
    expect(basketball).toContain("Rzuty");
    expect(basketball).not.toContain("Special teams");
  });
});
