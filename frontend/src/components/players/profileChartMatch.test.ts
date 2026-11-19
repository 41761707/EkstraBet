import { describe, expect, it } from "vitest";

import { buildChartLabel } from "@/components/players/PlayerPanel";
import { toProfileChartMatch } from "@/components/players/profileChartMatch";
import type { HockeyPlayerSliceMatch } from "@/types/api";

describe("toProfileChartMatch", () => {
  it("marks an away opponent and keeps the day.month label", () => {
    const chartMatch = toProfileChartMatch(
      sliceMatch({
        venue: "away",
        game_date: "2024-10-03",
        opponent_name: "Vegas Golden Knights",
        opponent_shortcut: "VGK",
      }),
    );

    expect(buildChartLabel(chartMatch, "shortcut")).toBe("@VGK 03.10");
    expect(chartMatch.home_team).toBe("Vegas Golden Knights");
  });

  it("leaves a home game unmarked", () => {
    const chartMatch = toProfileChartMatch(
      sliceMatch({
        venue: "home",
        game_date: "2024-10-05",
        opponent_name: "Florida Panthers",
        opponent_shortcut: "FLA",
      }),
    );

    expect(buildChartLabel(chartMatch, "shortcut")).toBe("FLA 05.10");
    expect(chartMatch.rating).toBe(1.5);
  });
});

function sliceMatch(
  overrides: Partial<HockeyPlayerSliceMatch>,
): HockeyPlayerSliceMatch {
  return {
    match_id: 10,
    game_date: "2024-10-03",
    season_id: 7,
    season_years: "2024/2025",
    own_team_id: 4,
    own_team_name: "Anaheim Ducks",
    opponent_team_id: 3,
    opponent_name: "Vegas Golden Knights",
    opponent_shortcut: "VGK",
    venue: "away",
    home_goals: 2,
    away_goals: 1,
    result: "A",
    toi: "18:00",
    toi_minutes: 18,
    points: 1,
    goals: 1,
    assists: 0,
    plus_minus: 1,
    penalty_minutes: 0,
    sog: 4,
    shots_against: null,
    shots_saved: null,
    saves_acc: null,
    power_play_goals: 0,
    empty_net_goals: 0,
    rating: 1.5,
    ...overrides,
  };
}
