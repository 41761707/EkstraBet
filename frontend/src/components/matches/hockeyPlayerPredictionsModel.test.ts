import { describe, expect, it } from "vitest";

import {
  buildExpectedGoalBars,
  buildExpectedShotBars,
  buildPlayerProbabilityBars,
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

describe("buildPlayerProbabilityBars", () => {
  it("ranks goal probability and converts percent to a unit share", () => {
    const higher = {
      ...skater(),
      player_id: 2,
      player_name: "Pastrnak D.",
      lines: [
        { event_id: 196, line: 0.5, expected_value: 0.5, probability: 40 },
        { event_id: 192, line: 0.5, expected_value: 0.9, probability: 61 },
      ],
    };
    const bars = buildPlayerProbabilityBars([skater(), higher], "goal");

    expect(bars.map((point) => point.label)).toEqual([
      "Pastrnak D.",
      "Fantilli A.",
    ]);
    expect(bars[0]?.probability).toBeCloseTo(0.4);
    expect(bars[1]?.probability).toBeCloseTo(0.26);
    expect(bars[0]?.barPercent).toBe(100);
    expect(bars[0]?.isFavorite).toBe(true);
    expect(bars[1]?.isFavorite).toBe(false);
  });

  it("ranks assist probability the same way as goals", () => {
    const bars = buildPlayerProbabilityBars([skater()], "assist");

    expect(bars).toHaveLength(1);
    expect(bars[0]?.probability).toBeCloseTo(0.33);
    expect(bars[0]?.isFavorite).toBe(true);
  });

  it("drops a skater who has no line for the metric", () => {
    const bars = buildPlayerProbabilityBars(
      [{ ...skater(), lines: [] }],
      "point",
    );

    expect(bars).toEqual([]);
  });
});

describe("buildExpectedShotBars", () => {
  it("ranks expected shots and ignores a higher goal rate", () => {
    const fewerShots = {
      ...skater(),
      player_id: 2,
      player_name: "Goodrow B.",
      lines: [
        { event_id: 190, line: 2.5, expected_value: 1.1, probability: 20 },
        { event_id: 196, line: 0.5, expected_value: 0.9, probability: 60 },
      ],
    };
    const bars = buildExpectedShotBars([skater(), fewerShots]);

    expect(bars.map((point) => point.label)).toEqual([
      "Fantilli A.",
      "Goodrow B.",
    ]);
    expect(bars[0]?.value).toBeCloseTo(2.4);
    expect(bars[1]?.value).toBeCloseTo(1.1);
    expect(bars[0]?.isFavorite).toBe(true);
  });
});

describe("buildExpectedGoalBars", () => {
  it("ranks the Poisson mean, not the goal probability", () => {
    const lowerRate = {
      ...skater(),
      player_id: 2,
      player_name: "Goodrow B.",
      lines: [
        { event_id: 196, line: 0.5, expected_value: 0.12, probability: 80 },
      ],
    };
    const bars = buildExpectedGoalBars([skater(), lowerRate]);

    expect(bars.map((point) => point.label)).toEqual([
      "Fantilli A.",
      "Goodrow B.",
    ]);
    expect(bars[0]?.value).toBeCloseTo(0.3);
    expect(bars[1]?.value).toBeCloseTo(0.12);
    expect(bars[0]?.barPercent).toBe(100);
    expect(bars[0]?.isFavorite).toBe(true);
    expect(bars[1]?.isFavorite).toBe(false);
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
