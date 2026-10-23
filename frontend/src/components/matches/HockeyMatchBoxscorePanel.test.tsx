import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HockeyMatchBoxscorePanel } from "@/components/matches/HockeyMatchBoxscorePanel";
import type {
  HockeyGameRating,
  HockeyGoalieBoxscoreRow,
  HockeyMatchBoxscore,
  HockeySkaterBoxscoreRow,
} from "@/types/api";

const ZERO_PARTS = {
  production: 0,
  empty_net: 0,
  shots: 0,
  teammate_goals: 0,
  faceoffs: 0,
  goals_against: 0,
  penalties: 0,
  blocks: 0,
  goaltending: 0,
};

function skater(playerId: number, name: string): HockeySkaterBoxscoreRow {
  return {
    player_id: playerId,
    player_name: name,
    team_id: 1,
    team_name: "Ottawa Senators",
    goals: 1,
    assists: 0,
    points: 1,
    plus_minus: 0,
    penalty_minutes: 0,
    shots_on_goal: 2,
    time_on_ice: "12:00",
  };
}

function goalie(playerId: number): HockeyGoalieBoxscoreRow {
  return {
    player_id: playerId,
    player_name: "Sogaard M.",
    team_id: 1,
    team_name: "Ottawa Senators",
    points: 0,
    penalty_minutes: 0,
    time_on_ice: "60:00",
    shots_against: 30,
    shots_saved: 30,
    saves_accuracy: 100,
  };
}

function boxscore(): HockeyMatchBoxscore {
  return {
    goalies: [goalie(8)],
    skaters: [skater(1, "Konecny T."), skater(2, "Halliday S.")],
  };
}

function rating(): HockeyGameRating {
  return {
    teams: [
      {
        team_id: 1,
        team_name: "Ottawa Senators",
        players: [
          {
            player_id: 1,
            player_name: "Konecny T.",
            group: "forward",
            offense: 3.3,
            defense: 0,
            total: 3.3,
            parts: { ...ZERO_PARTS, production: 3.3 },
          },
          {
            player_id: 8,
            player_name: "Sogaard M.",
            group: "goalie",
            offense: 0,
            defense: 2.8,
            total: 2.8,
            parts: { ...ZERO_PARTS, goaltending: 2.8 },
          },
        ],
      },
    ],
  };
}

describe("HockeyMatchBoxscorePanel rating column", () => {
  it("shows the match rating after points and a dash when a player has none", () => {
    const html = renderToStaticMarkup(
      <HockeyMatchBoxscorePanel boxscore={boxscore()} rating={rating()} />,
    );

    expect(html.indexOf(">Pkt<")).toBeLessThan(html.indexOf(">Ocena<"));
    expect(html).toContain("+3.3");
    expect(html).toContain("bg-success-bg");
    expect(html).toContain("+2.8");
    expect(html).toContain(">—<");
  });

  it("keeps the rating column and dashes every cell when the rating is null", () => {
    const html = renderToStaticMarkup(
      <HockeyMatchBoxscorePanel boxscore={boxscore()} rating={null} />,
    );

    expect(html).toContain("Ocena");
    expect(html).not.toContain("+3.3");
    expect(html).toContain(">—<");
  });
});
