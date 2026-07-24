import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
  getSemanticBarColor,
} from "@/lib/chartColors";
import { formatProbability } from "@/lib/format";
import { normalizeProbabilitiesToPercents } from "@/lib/pieSlices";
import type { PredictionPreviewResponse, TeamSummary } from "@/types/api";

export interface ProbabilitySegmentView {
  id: string;
  label: string;
  /** Raw probability from API (0–1), used for text labels. */
  probability: number;
  /** Integer percent for donut geometry (sum 100). */
  percent: number;
  color: string;
  isFavorite: boolean;
}

export interface ProbabilityBarPoint {
  id: string;
  label: string;
  probability: number;
  /** Relative bar length 0–100 (vs max in series). */
  barPercent: number;
  color: string;
  isFavorite: boolean;
}

export interface PredictionChartModel {
  result1x2: ProbabilitySegmentView[];
  btts: ProbabilitySegmentView[];
  overUnder: ProbabilitySegmentView[];
  goalBuckets: ProbabilityBarPoint[];
  exactScores: ProbabilityBarPoint[];
  lambdaHome: number;
  lambdaAway: number;
}

export function teamChartLabel(team: Pick<TeamSummary, "name" | "shortcut">): string {
  const shortcut = team.shortcut?.trim();
  return shortcut ? shortcut : team.name;
}

function markFavoriteSegments(
  segments: Omit<ProbabilitySegmentView, "isFavorite">[],
): ProbabilitySegmentView[] {
  if (segments.length === 0) {
    return [];
  }
  const maxProbability = Math.max(...segments.map((segment) => segment.probability));
  return segments.map((segment) => ({
    ...segment,
    isFavorite: segment.probability === maxProbability && maxProbability > 0,
  }));
}

function markFavoriteBars(
  points: Omit<ProbabilityBarPoint, "isFavorite">[],
): ProbabilityBarPoint[] {
  if (points.length === 0) {
    return [];
  }
  const maxProbability = Math.max(...points.map((point) => point.probability));
  return points.map((point) => ({
    ...point,
    isFavorite: point.probability === maxProbability && maxProbability > 0,
  }));
}

function toDonutSegments(
  items: { id: string; label: string; probability: number; color: string }[],
): ProbabilitySegmentView[] {
  const percents = normalizeProbabilitiesToPercents(
    items.map((item) => item.probability),
  );
  return markFavoriteSegments(
    items.map((item, index) => ({
      id: item.id,
      label: item.label,
      probability: item.probability,
      percent: percents[index] ?? 0,
      color: item.color,
    })),
  );
}

function toRelativeBars(
  items: { id: string; label: string; probability: number; color: string }[],
): ProbabilityBarPoint[] {
  const maxProbability = Math.max(...items.map((item) => item.probability), 0);
  return markFavoriteBars(
    items.map((item) => ({
      id: item.id,
      label: item.label,
      probability: item.probability,
      barPercent:
        maxProbability > 0 ? (item.probability / maxProbability) * 100 : 0,
      color: item.color,
    })),
  );
}

function sortGoalBuckets(
  buckets: Record<string, number>,
): [string, number][] {
  return Object.entries(buckets).sort(([left], [right]) =>
    left.localeCompare(right, "pl", { numeric: true }),
  );
}

export function buildPredictionChartModel(
  response: PredictionPreviewResponse,
  homeLabel: string,
  awayLabel: string,
): PredictionChartModel {
  const result1x2 = toDonutSegments([
    {
      id: "home",
      label: homeLabel,
      probability: response.result.p_home,
      color: CHART_COLOR_POSITIVE,
    },
    {
      id: "draw",
      label: "Remis",
      probability: response.result.p_draw,
      color: CHART_COLOR_DRAW,
    },
    {
      id: "away",
      label: awayLabel,
      probability: response.result.p_away,
      color: CHART_COLOR_NEGATIVE,
    },
  ]);

  const btts = toDonutSegments([
    {
      id: "yes",
      label: "Tak",
      probability: response.btts.p_yes,
      color: getSemanticBarColor("Tak"),
    },
    {
      id: "no",
      label: "Nie",
      probability: response.btts.p_no,
      color: getSemanticBarColor("Nie"),
    },
  ]);

  const overUnder = toDonutSegments([
    {
      id: "over",
      label: "Powyżej",
      probability: response.goals.over_25,
      color: getSemanticBarColor("Powyżej"),
    },
    {
      id: "under",
      label: "Poniżej",
      probability: response.goals.under_25,
      color: getSemanticBarColor("Poniżej"),
    },
  ]);

  const sortedBuckets = sortGoalBuckets(response.goals.total_buckets);
  const goalBuckets = toRelativeBars(
    sortedBuckets.map(([bucket, probability]) => ({
      id: bucket,
      label: bucket,
      probability,
      color: CHART_COLOR_POSITIVE,
    })),
  );

  const exactScores = toRelativeBars(
    response.goals.top_exact_scores.map((score) => ({
      id: score.score,
      label: score.score,
      probability: score.probability,
      color: CHART_COLOR_POSITIVE,
    })),
  );

  return {
    result1x2,
    btts,
    overUnder,
    goalBuckets,
    exactScores,
    lambdaHome: response.goals.lambda_home,
    lambdaAway: response.goals.lambda_away,
  };
}

export function formatSegmentProbability(probability: number): string {
  return formatProbability(probability);
}
