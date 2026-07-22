import { describe, expect, it } from "vitest";

import {
  buildPredictionChartModel,
  teamChartLabel,
} from "@/components/predictions/predictionChartModel";
import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import type { PredictionPreviewResponse } from "@/types/api";

const sampleResponse: PredictionPreviewResponse = {
  result: { p_home: 0.444, p_draw: 0.287, p_away: 0.269 },
  btts: { p_yes: 0.536, p_no: 0.464 },
  goals: {
    lambda_home: 1.42,
    lambda_away: 1.18,
    total_buckets: {
      "0": 0.081,
      "1": 0.203,
      "2": 0.256,
      "3": 0.215,
      "4": 0.135,
      "5": 0.068,
      "6+": 0.043,
    },
    over_25: 0.461,
    under_25: 0.539,
    top_exact_scores: [
      { score: "1:1", probability: 0.123 },
      { score: "1:0", probability: 0.12 },
      { score: "2:1", probability: 0.092 },
    ],
  },
};

describe("teamChartLabel", () => {
  it("prefers shortcut when present", () => {
    expect(teamChartLabel({ name: "GKS Katowice", shortcut: "KAT" })).toBe("KAT");
  });

  it("falls back to full name when shortcut is missing", () => {
    expect(teamChartLabel({ name: "GKS Katowice", shortcut: null })).toBe(
      "GKS Katowice",
    );
    expect(teamChartLabel({ name: "GKS Katowice", shortcut: "  " })).toBe(
      "GKS Katowice",
    );
  });
});

describe("buildPredictionChartModel", () => {
  it("builds donut segments with favorite highlight and away in red", () => {
    const model = buildPredictionChartModel(sampleResponse, "KAT", "WIS");

    expect(model.result1x2).toHaveLength(3);
    expect(model.result1x2.map((segment) => segment.label)).toEqual([
      "KAT",
      "Remis",
      "WIS",
    ]);
    expect(model.result1x2[0]?.color).toBe(CHART_COLOR_POSITIVE);
    expect(model.result1x2[1]?.color).toBe(CHART_COLOR_DRAW);
    expect(model.result1x2[2]?.color).toBe(CHART_COLOR_NEGATIVE);
    expect(model.result1x2.find((segment) => segment.isFavorite)?.id).toBe(
      "home",
    );
    expect(
      model.result1x2.reduce((sum, segment) => sum + segment.percent, 0),
    ).toBe(100);
  });

  it("sorts goal buckets and scales exact bars relative to max", () => {
    const model = buildPredictionChartModel(sampleResponse, "KAT", "WIS");

    expect(model.goalBuckets.map((point) => point.label)).toEqual([
      "0",
      "1",
      "2",
      "3",
      "4",
      "5",
      "6+",
    ]);
    expect(model.goalBuckets.find((point) => point.isFavorite)?.id).toBe("2");
    expect(model.exactScores[0]?.barPercent).toBe(100);
    expect(model.exactScores.find((point) => point.isFavorite)?.id).toBe("1:1");
    expect(model.overUnder.find((segment) => segment.isFavorite)?.id).toBe(
      "under",
    );
  });
});
