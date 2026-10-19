import { describe, expect, it } from "vitest";

import {
  buildHockeyPredictionCharts,
  buildHockeyScoreBars,
} from "@/components/matches/hockeyPredictionChartModel";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import type { HockeyScoreChart, MatchPredictionItem } from "@/types/api";

function row(
  overrides: Partial<MatchPredictionItem> &
    Pick<MatchPredictionItem, "prediction_id" | "event_id" | "model_id">,
): MatchPredictionItem {
  return {
    event_name: "Rynek",
    event_family: null,
    model_name: "HOCKEY_RATINGS_POISSON_V1",
    value: 0.5,
    outcome: null,
    ...overrides,
  };
}

describe("buildHockeyPredictionCharts", () => {
  it("builds a winner donut from the stored side and its complement", () => {
    const charts = buildHockeyPredictionCharts(
      [
        row({
          prediction_id: 1,
          event_id: 235,
          model_id: 21,
          value: 0.607,
        }),
      ],
      "San Jose Sharks",
      "Boston Bruins",
    );

    expect(charts).toHaveLength(1);
    const winner = charts[0]?.winner ?? [];
    expect(winner.map((segment) => segment.label)).toEqual([
      "San Jose Sharks",
      "Boston Bruins",
    ]);
    expect(winner[0]?.probability).toBeCloseTo(0.393);
    expect(winner[1]?.probability).toBeCloseTo(0.607);
    expect(winner[0]?.color).toBe(CHART_COLOR_POSITIVE);
    expect(winner[1]?.color).toBe(CHART_COLOR_NEGATIVE);
    expect(winner.find((segment) => segment.isFavorite)?.id).toBe("away");
    expect(winner.reduce((sum, segment) => sum + segment.percent, 0)).toBe(100);
    expect(charts[0]?.total55).toEqual([]);
    expect(charts[0]?.total65).toEqual([]);
  });

  it("keeps both stored sides of over 5.5 and over 6.5", () => {
    const charts = buildHockeyPredictionCharts(
      [
        row({
          prediction_id: 1,
          event_id: 236,
          model_id: 8,
          model_name: "HOCKEY_GOALS_GBM_V1",
          value: 0.58,
        }),
        row({
          prediction_id: 2,
          event_id: 237,
          model_id: 8,
          model_name: "HOCKEY_GOALS_GBM_V1",
          value: 0.4,
        }),
        row({
          prediction_id: 3,
          event_id: 239,
          model_id: 8,
          model_name: "HOCKEY_GOALS_GBM_V1",
          value: 0.62,
        }),
      ],
      "Gospodarze",
      "Goście",
    );

    const total55 = charts[0]?.total55 ?? [];
    const total65 = charts[0]?.total65 ?? [];
    expect(total55.map((segment) => segment.probability)).toEqual([0.58, 0.4]);
    expect(total55.map((segment) => segment.label)).toEqual([
      "Powyżej",
      "Poniżej",
    ]);
    expect(total65[0]?.probability).toBeCloseTo(0.38);
    expect(total65[1]?.probability).toBeCloseTo(0.62);
    expect(total65.find((segment) => segment.isFavorite)?.id).toBe("under");
  });

  it("splits charts by model and ignores other events", () => {
    const charts = buildHockeyPredictionCharts(
      [
        row({
          prediction_id: 1,
          event_id: 234,
          model_id: 30,
          model_name: "HOCKEY_RATINGS_POISSON_V1",
          value: 0.4,
        }),
        row({
          prediction_id: 2,
          event_id: 234,
          model_id: 8,
          model_name: "HOCKEY_GOALS_GBM_V1",
          value: 0.516,
        }),
        row({
          prediction_id: 3,
          event_id: 244,
          model_id: 8,
          model_name: "HOCKEY_GOALS_GBM_V1",
          value: 0.9,
        }),
      ],
      "SJS",
      "BOS",
    );

    expect(charts.map((chart) => chart.modelName)).toEqual([
      "HOCKEY_GOALS_GBM_V1",
      "HOCKEY_RATINGS_POISSON_V1",
    ]);
    expect(charts[0]?.winner[0]?.probability).toBeCloseTo(0.516);
    expect(charts[1]?.winner[1]?.probability).toBeCloseTo(0.6);
  });

  it("returns nothing when hockey markets are absent", () => {
    expect(
      buildHockeyPredictionCharts(
        [
          row({
            prediction_id: 1,
            event_id: 1,
            model_id: 3,
            model_name: "FOOTBALL_RESULT_V2",
            value: 0.46,
          }),
        ],
        "Gospodarze",
        "Goście",
      ),
    ).toEqual([]);
  });
});

describe("buildHockeyScoreBars", () => {
  it("keeps bucket order and marks the tallest bar", () => {
    const bars = buildHockeyScoreBars(scoreChart());

    expect(bars.home.map((point) => point.label)).toEqual([
      "0",
      "1",
      "2",
      "3",
      "4",
      "5+",
    ]);
    expect(bars.total.map((point) => point.label)).toEqual([
      "≤3",
      "4",
      "5",
      "6",
      "7",
      "8+",
    ]);
    expect(bars.home.find((point) => point.isFavorite)?.label).toBe("3");
    expect(bars.total.find((point) => point.isFavorite)?.label).toBe("6");
    expect(bars.home[0]?.color).toBe(CHART_COLOR_POSITIVE);
    expect(bars.exactScores.map((point) => point.label)).toEqual([
      "4:1",
      "2:3",
    ]);
    expect(bars.exactScores[0]?.isFavorite).toBe(true);
  });
});

function scoreChart(): HockeyScoreChart {
  return {
    model_id: 8,
    model_name: "HOCKEY_GOALS_GBM_V1",
    home_goals: [
      { label: "0", probability: 0.05 },
      { label: "1", probability: 0.12 },
      { label: "2", probability: 0.2 },
      { label: "3", probability: 0.33 },
      { label: "4", probability: 0.18 },
      { label: "5+", probability: 0.12 },
    ],
    away_goals: [
      { label: "0", probability: 0.08 },
      { label: "1", probability: 0.16 },
      { label: "2", probability: 0.28 },
      { label: "3", probability: 0.24 },
      { label: "4", probability: 0.14 },
      { label: "5+", probability: 0.1 },
    ],
    total_goals: [
      { label: "≤3", probability: 0.08 },
      { label: "4", probability: 0.12 },
      { label: "5", probability: 0.18 },
      { label: "6", probability: 0.24 },
      { label: "7", probability: 0.2 },
      { label: "8+", probability: 0.18 },
    ],
    exact_scores: [
      { score: "4:1", probability: 0.14 },
      { score: "2:3", probability: 0.11 },
    ],
  };
}
