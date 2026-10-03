import { describe, expect, it } from "vitest";

import {
  formatExpectedShots,
  hasHockeyPlayerPredictions,
  toPropColumns,
} from "@/components/matches/hockeyPlayerPredictionsModel";
import type { HockeyPlayerPrediction } from "@/types/api";

function skater(): HockeyPlayerPrediction {
  return {
    player_id: 1898,
    player_name: "Fantilli A.",
    team_id: 10,
    lines: [
      { event_id: 190, line: 1.5, expected_value: 2.4, probability: 70 },
      { event_id: 190, line: 2.5, expected_value: 2.4, probability: 46 },
      { event_id: 196, line: 0.5, expected_value: 0.3, probability: 26 },
      { event_id: 194, line: 0.5, expected_value: 0.4, probability: 33 },
      { event_id: 192, line: 0.5, expected_value: 0.7, probability: 50.2 },
      { event_id: 192, line: 1.5, expected_value: 0.7, probability: 18 },
    ],
  };
}

describe("toPropColumns", () => {
  it("maps the beta lines and ignores the other shot threshold", () => {
    const columns = toPropColumns(skater());

    expect(columns.expectedShots).toBe(2.4);
    expect(columns.shotsOver25).toBe(46);
    expect(columns.goalProbability).toBe(26);
    expect(columns.assistProbability).toBe(33);
    expect(columns.pointProbability).toBe(50.2);
    expect(columns.twoPointProbability).toBe(18);
  });

  it("leaves a missing line empty", () => {
    const columns = toPropColumns({ ...skater(), lines: [] });

    expect(columns.expectedShots).toBeNull();
    expect(columns.shotsOver25).toBeNull();
    expect(formatExpectedShots(null)).toBe("—");
    expect(formatExpectedShots(2.4)).toBe("2.40");
  });
});

describe("hasHockeyPlayerPredictions", () => {
  it("is false for null and for two empty clubs", () => {
    expect(hasHockeyPlayerPredictions(null)).toBe(false);
    expect(hasHockeyPlayerPredictions({ home: [], away: [] })).toBe(false);
    expect(
      hasHockeyPlayerPredictions({ home: [skater()], away: [] }),
    ).toBe(true);
  });
});
