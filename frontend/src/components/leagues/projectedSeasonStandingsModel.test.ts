import { describe, expect, it } from "vitest";

import {
  availableSeasonProjectionModes,
  defaultSeasonProjectionMode,
  formatProjectionPoints,
  hasAnyProjectionMode,
  probabilityForTablePosition,
  shouldFetchProjectionModes,
  shouldFetchSeasonProjection,
  shouldShowBotColumn,
  shouldShowTopColumn,
  sortStandingsByExpectedPosition,
} from "@/components/leagues/projectedSeasonStandingsModel";
import type { SeasonProjectionStandingRow } from "@/types/api";

function standing(
  overrides: Partial<SeasonProjectionStandingRow> &
    Pick<SeasonProjectionStandingRow, "team_id" | "team_name">,
): SeasonProjectionStandingRow {
  return {
    current_position: 1,
    current_points: 10,
    expected_position: 1.5,
    most_likely_position: 1,
    position_min: 1,
    position_max: 3,
    expected_points: 42.5,
    points_variance: 4,
    points_stddev: 2,
    points_p05: 38,
    points_p50: 42,
    points_p95: 47,
    points_min: 30,
    points_max: 55,
    expected_goal_difference: 8,
    position_probabilities: [0.5, 0.3, 0.2],
    champion_probability: 0.5,
    top_probability: null,
    bot_probability: null,
    ...overrides,
  };
}

describe("projectedSeasonStandingsModel", () => {
  it("does not fetch modes before the expander is open", () => {
    expect(shouldFetchProjectionModes(false, false)).toBe(false);
    expect(shouldFetchProjectionModes(false, true)).toBe(false);
  });

  it("fetches modes only on first open", () => {
    expect(shouldFetchProjectionModes(true, false)).toBe(true);
    expect(shouldFetchProjectionModes(true, true)).toBe(false);
  });

  it("fetches projection only for a selected mode without cache", () => {
    expect(shouldFetchSeasonProjection(true, null, false)).toBe(false);
    expect(shouldFetchSeasonProjection(true, "from_now", false)).toBe(true);
    expect(shouldFetchSeasonProjection(true, "from_now", true)).toBe(false);
  });

  it("picks default mode from available flags", () => {
    expect(
      defaultSeasonProjectionMode({
        from_now: true,
        from_season_start: true,
      }),
    ).toBe("from_now");
    expect(
      defaultSeasonProjectionMode({
        from_now: false,
        from_season_start: true,
      }),
    ).toBe("from_season_start");
    expect(
      defaultSeasonProjectionMode({
        from_now: false,
        from_season_start: false,
      }),
    ).toBeNull();
  });

  it("lists only available modes", () => {
    expect(
      availableSeasonProjectionModes({
        from_now: false,
        from_season_start: true,
      }),
    ).toEqual(["from_season_start"]);
    expect(
      hasAnyProjectionMode({ from_now: false, from_season_start: false }),
    ).toBe(false);
  });

  it("reads probability for the displayed table position", () => {
    expect(probabilityForTablePosition([0.5, 0.3, 0.2], 1)).toBe(0.5);
    expect(probabilityForTablePosition([0.5, 0.3, 0.2], 2)).toBe(0.3);
    expect(probabilityForTablePosition([0.5, 0.3, 0.2], 9)).toBeNull();
  });

  it("sorts standings by expected_position then team_id", () => {
    const sorted = sortStandingsByExpectedPosition([
      standing({
        team_id: 3,
        team_name: "C",
        expected_position: 2,
      }),
      standing({
        team_id: 1,
        team_name: "A",
        expected_position: 1,
      }),
      standing({
        team_id: 2,
        team_name: "B",
        expected_position: 2,
      }),
    ]);
    expect(sorted.map((row) => row.team_id)).toEqual([1, 2, 3]);
  });

  it("formats points", () => {
    expect(formatProjectionPoints(42.56)).toBe("42.6");
  });

  it("shows Top and Spadek columns only when slots are positive", () => {
    expect(shouldShowTopColumn(null)).toBe(false);
    expect(shouldShowBotColumn(null)).toBe(false);
    expect(shouldShowTopColumn({ top_slots: 4, bot_slots: 3 })).toBe(true);
    expect(shouldShowBotColumn({ top_slots: 4, bot_slots: 3 })).toBe(true);
    expect(shouldShowTopColumn({ top_slots: 0, bot_slots: 3 })).toBe(false);
    expect(shouldShowBotColumn({ top_slots: 4, bot_slots: 0 })).toBe(false);
  });
});
