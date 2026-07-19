import { describe, expect, it } from "vitest";

import {
  allocateReplayCells,
  buildPieSlices,
  buildResultQualityNarrative,
  countReplayCells,
  getAssessmentDrivers,
  normalizeReplayPercents,
  pickPlayedBetterAssessment,
} from "@/components/matches/playedBetterPresentation";
import type { MatchModelAssessment } from "@/types/api";

function sampleAssessment(
  overrides: Partial<MatchModelAssessment> = {},
): MatchModelAssessment {
  return {
    model_id: 6,
    model_name: "FOOTBALL_PLAYED_BETTER_V1",
    model_version: "1.0.0",
    assessment_type: "PLAYED_BETTER",
    home_played_better_probability: 0.55,
    draw_probability: 0.25,
    away_played_better_probability: 0.2,
    final_assessment: "HOME_PLAYED_BETTER",
    confidence: 0.3,
    dominance_score: 0.8,
    feature_snapshot: { xg_diff: 1.2 },
    updated_at: "2025-03-16T12:00:00",
    ...overrides,
  };
}

describe("allocateReplayCells", () => {
  it("returns exactly 100 cells matching proportions", () => {
    const cells = allocateReplayCells(0.55, 0.25, 0.2);
    expect(cells).toHaveLength(100);
    const counts = countReplayCells(cells);
    expect(counts.home + counts.draw + counts.away).toBe(100);
    expect(counts.home).toBe(55);
    expect(counts.draw).toBe(25);
    expect(counts.away).toBe(20);
  });

  it("normalizes when probabilities do not sum to one", () => {
    const cells = allocateReplayCells(2, 1, 1);
    expect(cells).toHaveLength(100);
    const counts = countReplayCells(cells);
    expect(counts.home).toBe(50);
    expect(counts.draw).toBe(25);
    expect(counts.away).toBe(25);
    // te same udziały muszą iść do paska 3-way (suma 100)
    expect(counts.home + counts.draw + counts.away).toBe(100);
  });
});

describe("buildResultQualityNarrative", () => {
  it("marks aligned home win", () => {
    const narrative = buildResultQualityNarrative(
      2,
      1,
      "HOME_PLAYED_BETTER",
      "Legia",
      "Lech",
    );
    expect(narrative?.tone).toBe("aligned");
    expect(narrative?.text).toBe("Wynik zgodny z obrazem gry");
  });

  it("marks upset when better team lost", () => {
    const narrative = buildResultQualityNarrative(
      2,
      1,
      "AWAY_PLAYED_BETTER",
      "Legia",
      "Lech",
    );
    expect(narrative?.tone).toBe("upset");
    expect(narrative?.text).toContain("Lech");
  });

  it("marks draw result with quality edge", () => {
    const narrative = buildResultQualityNarrative(
      1,
      1,
      "HOME_PLAYED_BETTER",
      "Legia",
      "Lech",
    );
    expect(narrative?.tone).toBe("draw_mismatch");
    expect(narrative?.text).toContain("Remis wyniku");
    expect(narrative?.text).toContain("Legia");
  });
});

describe("pickPlayedBetterAssessment", () => {
  it("picks newest PLAYED_BETTER row", () => {
    const picked = pickPlayedBetterAssessment([
      sampleAssessment({
        model_id: 6,
        updated_at: "2025-03-16T10:00:00",
      }),
      sampleAssessment({
        model_id: 7,
        model_name: "FOOTBALL_PLAYED_BETTER_NOXG_V1",
        updated_at: "2025-03-16T14:00:00",
      }),
      sampleAssessment({
        assessment_type: "OTHER",
        updated_at: "2025-03-17T14:00:00",
      }),
    ]);
    expect(picked?.model_id).toBe(7);
  });
});

describe("getAssessmentDrivers", () => {
  it("returns only known keys present in snapshot", () => {
    const drivers = getAssessmentDrivers({
      xg_diff: 0.9,
      possession_diff: -5,
      shots_diff: 3,
      corners_diff: 2,
    });
    expect(drivers.map((driver) => driver.key)).toEqual([
      "xg_diff",
      "possession_diff",
      "shots_diff",
    ]);
    expect(drivers[0]?.favors).toBe("home");
    expect(drivers[1]?.favors).toBe("away");
  });
});

describe("normalizeReplayPercents", () => {
  it("returns integer percents that sum to 100", () => {
    const percents = normalizeReplayPercents(0.987, 0.01, 0.003);
    expect(percents.home + percents.draw + percents.away).toBe(100);
  });
});

describe("buildPieSlices", () => {
  it("builds paths for non-zero slices", () => {
    const slices = buildPieSlices({ home: 55, draw: 25, away: 20 });
    expect(slices).toHaveLength(3);
    expect(slices[0]?.path).toContain("A 42 42");
    expect(slices[0]?.isFullCircle).toBe(false);
    expect(slices.every((slice) => slice.percent > 0 && slice.path)).toBe(true);
  });

  it("marks a full circle when one side is 100%", () => {
    const slices = buildPieSlices({ home: 100, draw: 0, away: 0 });
    expect(slices[0]?.isFullCircle).toBe(true);
    expect(slices[0]?.path).toBeNull();
    expect(slices[1]?.path).toBeNull();
    expect(slices[2]?.path).toBeNull();
  });
});
