import { describe, expect, it } from "vitest";

import { computeSplitStatsFromHistory } from "@/components/matches/matchTeamStatsUtils";
import type { TeamSeasonMatchPoint } from "@/types/api";

function matchPoint(
  overrides: Partial<TeamSeasonMatchPoint>,
): TeamSeasonMatchPoint {
  return {
    match_id: 1,
    match_date: "2026-01-01",
    opponent_shortcut: "OPP",
    opponent_name: "Opponent",
    total_goals: 4,
    btts: true,
    result: "W",
    home_team_name: "Home",
    away_team_name: "Away",
    home_goals: 2,
    away_goals: 2,
    is_home: true,
    team_cards: 0,
    opponent_cards: 0,
    total_cards: 0,
    team_offsides: 0,
    opponent_offsides: 0,
    total_offsides: 0,
    team_corners: 0,
    opponent_corners: 0,
    total_corners: 0,
    team_shots: 0,
    opponent_shots: 0,
    total_shots: 0,
    team_shots_on_target: 0,
    opponent_shots_on_target: 0,
    total_shots_on_target: 0,
    team_fouls: 0,
    opponent_fouls: 0,
    total_fouls: 0,
    ...overrides,
  };
}

describe("computeSplitStatsFromHistory", () => {
  it("awards 3 points for a football win", () => {
    const stats = computeSplitStatsFromHistory([
      matchPoint({ result: "W", home_goals: 2, away_goals: 0 }),
    ]);

    expect(stats.overall.points).toBe(3);
    expect(stats.overall.wins).toBe(1);
    expect(stats.overall.goals_for).toBe(2);
  });

  it("counts a hockey overtime win as 2 points and one extra goal", () => {
    const stats = computeSplitStatsFromHistory(
      [matchPoint({ result: "WPD", home_goals: 2, away_goals: 2 })],
      "hockey",
    );

    expect(stats.overall.wins).toBe(1);
    expect(stats.overall.points).toBe(2);
    expect(stats.overall.goals_for).toBe(3);
    expect(stats.overall.overtime_losses).toBe(0);
    expect(stats.overall.draws).toBe(0);
  });

  it("counts a hockey overtime loss as 1 point in OT", () => {
    const stats = computeSplitStatsFromHistory(
      [matchPoint({ result: "PPD", home_goals: 2, away_goals: 2 })],
      "hockey",
    );

    expect(stats.overall.overtime_losses).toBe(1);
    expect(stats.overall.points).toBe(1);
    expect(stats.overall.losses).toBe(0);
    expect(stats.overall.goals_conceded).toBe(3);
    expect(stats.overall.draws).toBe(0);
  });
});
