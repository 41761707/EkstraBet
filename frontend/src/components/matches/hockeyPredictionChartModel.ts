import {
  toDonutSegments,
  toRelativeBars,
  type ProbabilityBarPoint,
  type ProbabilitySegmentView,
} from "@/components/predictions/predictionChartModel";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
  getSemanticBarColor,
} from "@/lib/chartColors";
import type {
  HockeyExactScoreChance,
  HockeyGoalBucket,
  HockeyScoreChart,
  MatchPredictionItem,
} from "@/types/api";

/** Event ids from backend.sports.hockey.markets.HOCKEY_MARKET_RULES. */
const MONEYLINE_HOME_EVENT_ID = 234;
const MONEYLINE_AWAY_EVENT_ID = 235;
const OVER_55_EVENT_ID = 236;
const UNDER_55_EVENT_ID = 237;
const OVER_65_EVENT_ID = 238;
const UNDER_65_EVENT_ID = 239;

export interface HockeyModelDonuts {
  modelId: number;
  modelName: string;
  winner: ProbabilitySegmentView[];
  total55: ProbabilitySegmentView[];
  total65: ProbabilitySegmentView[];
}

/**
 * Donuts for each model on the match page.
 *
 * Final rows keep only the higher side of a binary market. The other
 * side is the complement, because moneyline and these totals have no draw.
 */
export function buildHockeyPredictionCharts(
  predictions: MatchPredictionItem[],
  homeLabel: string,
  awayLabel: string,
): HockeyModelDonuts[] {
  return [...groupByModel(predictions).entries()]
    .sort(([leftId], [rightId]) => leftId - rightId)
    .map(([modelId, rows]) =>
      toModelDonuts(modelId, rows, homeLabel, awayLabel),
    )
    .filter(hasAnyDonut);
}

function groupByModel(
  predictions: MatchPredictionItem[],
): Map<number, MatchPredictionItem[]> {
  const groups = new Map<number, MatchPredictionItem[]>();
  for (const prediction of predictions) {
    const current = groups.get(prediction.model_id);
    if (current) {
      current.push(prediction);
    } else {
      groups.set(prediction.model_id, [prediction]);
    }
  }
  return groups;
}

function toModelDonuts(
  modelId: number,
  rows: MatchPredictionItem[],
  homeLabel: string,
  awayLabel: string,
): HockeyModelDonuts {
  const winner = complementaryPair(
    rows,
    MONEYLINE_HOME_EVENT_ID,
    MONEYLINE_AWAY_EVENT_ID,
  );
  const total55 = complementaryPair(
    rows,
    OVER_55_EVENT_ID,
    UNDER_55_EVENT_ID,
  );
  const total65 = complementaryPair(
    rows,
    OVER_65_EVENT_ID,
    UNDER_65_EVENT_ID,
  );
  return {
    modelId,
    modelName: modelLabel(rows, modelId),
    winner: winner
      ? toDonutSegments([
          {
            id: "home",
            label: homeLabel,
            probability: winner.left,
            color: CHART_COLOR_POSITIVE,
          },
          {
            id: "away",
            label: awayLabel,
            probability: winner.right,
            color: CHART_COLOR_NEGATIVE,
          },
        ])
      : [],
    total55: totalSegments(total55),
    total65: totalSegments(total65),
  };
}

function totalSegments(
  pair: { left: number; right: number } | null,
): ProbabilitySegmentView[] {
  if (!pair) {
    return [];
  }
  return toDonutSegments([
    {
      id: "over",
      label: "Powyżej",
      probability: pair.left,
      color: getSemanticBarColor("Powyżej"),
    },
    {
      id: "under",
      label: "Poniżej",
      probability: pair.right,
      color: getSemanticBarColor("Poniżej"),
    },
  ]);
}

function complementaryPair(
  rows: MatchPredictionItem[],
  leftEventId: number,
  rightEventId: number,
): { left: number; right: number } | null {
  const left = storedProbability(rows, leftEventId);
  const right = storedProbability(rows, rightEventId);
  if (left != null && right != null) {
    return { left, right };
  }
  if (left != null) {
    return { left, right: 1 - left };
  }
  if (right != null) {
    return { left: 1 - right, right };
  }
  return null;
}

function storedProbability(
  rows: MatchPredictionItem[],
  eventId: number,
): number | null {
  const row = rows.find(
    (item) =>
      item.event_id === eventId &&
      item.value != null &&
      Number.isFinite(item.value),
  );
  if (!row || row.value == null) {
    return null;
  }
  return clampUnit(row.value);
}

function clampUnit(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function modelLabel(rows: MatchPredictionItem[], modelId: number): string {
  const name = rows.find((row) => row.model_name)?.model_name;
  return name && name.trim() ? name : `Model ${modelId}`;
}

function hasAnyDonut(chart: HockeyModelDonuts): boolean {
  return (
    chart.winner.length > 0 ||
    chart.total55.length > 0 ||
    chart.total65.length > 0
  );
}

export interface HockeyScoreBars {
  home: ProbabilityBarPoint[];
  total: ProbabilityBarPoint[];
  away: ProbabilityBarPoint[];
  exactScores: ProbabilityBarPoint[];
}

/** Bars keep the API order. The five is already sorted by probability. */
export function buildHockeyScoreBars(chart: HockeyScoreChart): HockeyScoreBars {
  return {
    home: toGoalBars(chart.home_goals),
    total: toGoalBars(chart.total_goals),
    away: toGoalBars(chart.away_goals),
    exactScores: toExactBars(chart.exact_scores),
  };
}

function toGoalBars(buckets: HockeyGoalBucket[]): ProbabilityBarPoint[] {
  return toRelativeBars(
    buckets.map((bucket) => ({
      id: bucket.label,
      label: bucket.label,
      probability: bucket.probability,
      color: CHART_COLOR_POSITIVE,
    })),
  );
}

function toExactBars(scores: HockeyExactScoreChance[]): ProbabilityBarPoint[] {
  return toRelativeBars(
    scores.map((score) => ({
      id: score.score,
      label: score.score,
      probability: score.probability,
      color: CHART_COLOR_POSITIVE,
    })),
  );
}
