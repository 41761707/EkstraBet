import { describe, expect, it } from "vitest";

import {
  summarizeDisplayedHeadToHead,
} from "@/components/matches/prematchHeadToHeadSummary";
import type { MatchSummary } from "@/types/api";

function meeting(
  id: number,
  homeId: number,
  awayId: number,
  homeGoals: number | null,
  awayGoals: number | null,
): MatchSummary {
  return {
    id,
    league_id: 1,
    season_id: 10,
    round: id,
    round_label: String(id),
    game_date: "2026-01-01T18:00:00",
    home_team: { id: homeId, name: `Home ${homeId}`, shortcut: "HOM" },
    away_team: { id: awayId, name: `Away ${awayId}`, shortcut: "AWY" },
    home_goals: homeGoals,
    away_goals: awayGoals,
    result: "1",
    is_played: homeGoals != null && awayGoals != null,
    score_resolution: null,
  };
}

describe("summarizeDisplayedHeadToHead", () => {
  it("counts only the displayed football meetings, including over 2.5", () => {
    const stats = summarizeDisplayedHeadToHead(
      1,
      [
        meeting(1, 1, 2, 2, 1),
        meeting(2, 2, 1, 0, 0),
        meeting(3, 1, 2, 0, 1),
        meeting(4, 2, 1, 3, 2),
        meeting(5, 1, 2, null, null),
      ],
      false,
    );

    expect(stats.played).toBe(4);
    expect(stats.wins).toBe(1);
    expect(stats.draws).toBe(1);
    expect(stats.losses).toBe(2);
    expect(stats.goalsFor).toBe(4);
    expect(stats.goalsConceded).toBe(5);
    expect(stats.bttsPercentage).toBe(50);
    expect(stats.overPercentage).toBe(50);
  });

  it("uses over 6.5 for hockey totals", () => {
    const stats = summarizeDisplayedHeadToHead(
      1,
      [
        meeting(1, 1, 2, 4, 3),
        meeting(2, 1, 2, 3, 3),
      ],
      true,
    );

    expect(stats.played).toBe(2);
    expect(stats.overPercentage).toBe(50);
    expect(stats.bttsPercentage).toBe(100);
  });

  it("returns zeros when the selected window has no scored meetings", () => {
    const stats = summarizeDisplayedHeadToHead(1, [], false);

    expect(stats.played).toBe(0);
    expect(stats.bttsPercentage).toBe(0);
    expect(stats.overPercentage).toBe(0);
  });
});
