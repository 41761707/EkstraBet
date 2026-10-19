import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyLeagueStatsPanels } from "@/components/sport-leagues/HockeyLeagueStatsPanels";
import type {
  HockeyGoalsDistribution,
  SportLeagueStatRow,
} from "@/types/api";

const distribution: HockeyGoalsDistribution = {
  total_matches: 10,
  under_5: 1,
  exactly_5: 2,
  exactly_6: 3,
  exactly_7: 2,
  over_7: 2,
};

const rows: SportLeagueStatRow[] = [
  {
    team_name: "New York Rangers",
    team_shortcut: "NYR",
    matches_played: 5,
    over_5_5_pct: 80,
  },
  {
    team_name: "Boston Bruins",
    team_shortcut: "BOS",
    matches_played: 4,
    over_5_5_pct: 25,
  },
];

describe("HockeyLeagueStatsPanels", () => {
  it("shows the goal pie and over 5.5 cards", () => {
    const html = renderToStaticMarkup(
      <HockeyLeagueStatsPanels
        category="over_under"
        rows={rows}
        goalsDistribution={distribution}
      />,
    );
    expect(html).toContain("Rozkład bramek w meczach");
    expect(html).toContain("Dokładnie 6");
    expect(html).toContain("Over 5.5 w meczach ligi");
    expect(html).toContain("Over 6.5 w meczach ligi");
    expect(html).toContain("Procent meczów Over 5.5");
    expect(html).toContain("NYR");
  });

  it("shows power play, penalty kill and the Hitchcock sum", () => {
    const html = renderToStaticMarkup(
      <HockeyLeagueStatsPanels
        category="special_teams"
        rows={[
          {
            team_name: "Boston Bruins",
            team_shortcut: "BOS",
            matches_played: 10,
            pp_goals: 8,
            pp_opportunities: 40,
            pp_pct: 20,
            pk_kills: 36,
            pk_opportunities: 40,
            pk_pct: 90,
            hitchcock: 110,
          },
          {
            team_name: "New York Rangers",
            team_shortcut: "NYR",
            matches_played: 10,
            pp_goals: 4,
            pp_opportunities: 40,
            pp_pct: 10,
            pk_kills: 28,
            pk_opportunities: 40,
            pk_pct: 70,
            hitchcock: 80,
          },
        ]}
      />,
    );
    expect(html).toContain("Power play (PP)");
    expect(html).toContain("Penalty kill (PK)");
    expect(html).toContain("Ken Hitchcock 100 Rule");
    expect(html).toContain("Reguła: 100");
    expect(html).toContain("8/40");
    expect(html).toContain("36/40");
  });
});
