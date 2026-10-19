import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SportStandingsSection } from "@/components/sport-leagues/SportStandingsSection";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type BasketballStandingRow,
  type HockeyStandingRow,
} from "@/types/api";

const hockeyRow: HockeyStandingRow = {
  position: 1,
  team_id: 15,
  team_name: "New York Rangers",
  played: 5,
  wins: 4,
  losses: 1,
  goals_for: 16,
  goals_against: 8,
  goal_difference: 8,
  points: 8,
  overtime_wins: 0,
  overtime_losses: 0,
};

const basketballRow: BasketballStandingRow = {
  position: 1,
  team_id: 8,
  team_name: "Boston Celtics",
  played: 4,
  wins: 3,
  losses: 1,
  points_for: 450,
  points_against: 420,
  point_difference: 30,
  win_percentage: 75,
};

describe("SportStandingsSection", () => {
  it("links an NHL team name to the team page", () => {
    const html = renderToStaticMarkup(
      <SportStandingsSection
        sportId={HOCKEY_SPORT_ID}
        seasonId={9}
        leagueId={3}
        overallHockey={[hockeyRow]}
      />,
    );
    expect(html).toContain(
      'href="/teams/15?season_id=9&amp;league_id=3"',
    );
    expect(html).toContain("New York Rangers");
  });

  it("leaves basketball team names as plain text", () => {
    const html = renderToStaticMarkup(
      <SportStandingsSection
        sportId={BASKETBALL_SPORT_ID}
        seasonId={9}
        leagueId={4}
        overallBasketball={[basketballRow]}
      />,
    );
    expect(html).toContain("Boston Celtics");
    expect(html).not.toContain("/teams/8");
  });
});
