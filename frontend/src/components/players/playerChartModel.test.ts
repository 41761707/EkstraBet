import { describe, expect, it } from "vitest";

import {
  averageStoredRating,
  buildChartLabel,
  playerChartPoints,
  playerPlayedAway,
} from "@/components/players/PlayerPanel";
import type { HockeyPlayerMatchStat } from "@/types/api";

describe("buildChartLabel", () => {
  it("glues @ to the opponent when that club hosted the match", () => {
    expect(
      buildChartLabel(
        {
          opponent_name: "Vegas Golden Knights",
          opponent_shortcut: "VGK",
          home_team: "Vegas Golden Knights",
          match_date: "03.10",
        },
        "shortcut",
      ),
    ).toBe("@VGK 03.10");
  });

  it("leaves a home-game opponent unmarked", () => {
    expect(
      buildChartLabel(
        {
          opponent_name: "Florida Panthers",
          opponent_shortcut: "FLA",
          home_team: "Anaheim Ducks",
          match_date: "05.10",
        },
        "shortcut",
      ),
    ).toBe("FLA 05.10");
  });
});

describe("playerPlayedAway", () => {
  it("marks the opponent when that club hosted the match", () => {
    expect(
      playerPlayedAway({
        opponent_name: "Los Angeles Kings",
        home_team: "Los Angeles Kings",
      }),
    ).toBe(true);
  });

  it("leaves the opponent unmarked when the player's club was home", () => {
    expect(
      playerPlayedAway({
        opponent_name: "Toronto Maple Leafs",
        home_team: "San Jose Sharks",
      }),
    ).toBe(false);
  });

  it("does not mark a match with an empty opponent name", () => {
    expect(
      playerPlayedAway({
        opponent_name: "",
        home_team: "",
      }),
    ).toBe(false);
  });
});

describe("player rating points", () => {
  it("skips a match without a stored rating and keeps the mean of the rest", () => {
    const missing = hockeyMatch(2, null);
    const rated = hockeyMatch(1, -1.4);
    const points = playerChartPoints([missing, rated], "rating", "full");

    expect(points).toHaveLength(1);
    expect(points[0]?.value).toBe(3.6);
    expect(averageStoredRating([missing, rated])).toBe(-1.4);
    expect(averageStoredRating([missing])).toBeNull();
  });
});

function hockeyMatch(
  matchId: number,
  rating: number | null,
): HockeyPlayerMatchStat {
  return {
    match_id: matchId,
    home_team: "Los Angeles Kings",
    away_team: "Ottawa Senators",
    match_date: "02.01",
    opponent_shortcut: "OTT",
    opponent_name: "Ottawa Senators",
    toi: "18:00",
    toi_minutes: 18,
    points: 1,
    goals: 0,
    assists: 1,
    plus_minus: 1,
    penalty_minutes: 0,
    sog: 2,
    shots_against: null,
    shots_saved: null,
    saves_acc: null,
    rating,
  };
}
