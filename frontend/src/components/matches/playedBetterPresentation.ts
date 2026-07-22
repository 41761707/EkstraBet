import type {
  MatchModelAssessment,
  PlayedBetterFinalAssessment,
} from "@/types/api";
import { buildPieSlicesFromSegments } from "@/lib/pieSlices";

export type ReplayCellSide = "home" | "draw" | "away";

export type NarrativeTone = "aligned" | "upset" | "draw_mismatch" | "neutral";

export interface ResultQualityNarrative {
  tone: NarrativeTone;
  text: string;
}

export interface AssessmentDriver {
  key: string;
  label: string;
  value: number;
  favors: "home" | "away" | "neutral";
}

const PLAYED_BETTER_TYPE = "PLAYED_BETTER";

const DRIVER_DEFINITIONS: { key: string; label: string }[] = [
  { key: "xg_diff", label: "Różnica xG" },
  { key: "possession_diff", label: "Posiadanie piłki" },
  { key: "shots_diff", label: "Strzały" },
  { key: "shots_on_goal_diff", label: "Strzały na bramkę" },
];

function parseUpdatedAt(value: string | null): number {
  if (!value) {
    return 0;
  }
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

/** Pick newest PLAYED_BETTER assessment by updated_at. */
export function pickPlayedBetterAssessment(
  assessments: MatchModelAssessment[],
): MatchModelAssessment | null {
  const playedBetter = assessments.filter(
    (item) => item.assessment_type === PLAYED_BETTER_TYPE,
  );
  if (playedBetter.length === 0) {
    return null;
  }
  return playedBetter.reduce((newest, current) => {
    return parseUpdatedAt(current.updated_at) > parseUpdatedAt(newest.updated_at)
      ? current
      : newest;
  });
}

export function allocateReplayCells(
  home: number,
  draw: number,
  away: number,
): ReplayCellSide[] {
  const raw = [
    { side: "home" as const, value: Math.max(0, home) },
    { side: "draw" as const, value: Math.max(0, draw) },
    { side: "away" as const, value: Math.max(0, away) },
  ];
  const total = raw.reduce((sum, item) => sum + item.value, 0);
  if (total <= 0) {
    return Array.from({ length: 100 }, () => "draw" as const);
  }

  const shares = raw.map((item) => {
    const exact = (item.value / total) * 100;
    const floored = Math.floor(exact);
    return {
      side: item.side,
      count: floored,
      remainder: exact - floored,
    };
  });

  let remaining = 100 - shares.reduce((sum, item) => sum + item.count, 0);
  const byRemainder = [...shares].sort((a, b) => b.remainder - a.remainder);
  for (const item of byRemainder) {
    if (remaining <= 0) {
      break;
    }
    item.count += 1;
    remaining -= 1;
  }

  const cells: ReplayCellSide[] = [];
  for (const item of shares) {
    for (let i = 0; i < item.count; i += 1) {
      cells.push(item.side);
    }
  }
  return cells;
}

function resultSide(
  homeGoals: number,
  awayGoals: number,
): "home" | "draw" | "away" {
  if (homeGoals > awayGoals) {
    return "home";
  }
  if (awayGoals > homeGoals) {
    return "away";
  }
  return "draw";
}

function assessmentSide(
  finalAssessment: PlayedBetterFinalAssessment,
): "home" | "draw" | "away" {
  if (finalAssessment === "HOME_PLAYED_BETTER") {
    return "home";
  }
  if (finalAssessment === "AWAY_PLAYED_BETTER") {
    return "away";
  }
  return "draw";
}

export function buildResultQualityNarrative(
  homeGoals: number | null,
  awayGoals: number | null,
  finalAssessment: PlayedBetterFinalAssessment,
  homeName: string,
  awayName: string,
): ResultQualityNarrative | null {
  if (homeGoals === null || awayGoals === null) {
    return null;
  }

  const score = resultSide(homeGoals, awayGoals);
  const quality = assessmentSide(finalAssessment);

  if (score === quality) {
    return { tone: "aligned", text: "Wynik zgodny z obrazem gry" };
  }

  if (score === "draw" && quality !== "draw") {
    const teamName = quality === "home" ? homeName : awayName;
    return {
      tone: "draw_mismatch",
      text: `Remis wyniku przy przewadze jakości ${teamName}`,
    };
  }

  if (quality === "draw" && score !== "draw") {
    return {
      tone: "neutral",
      text: "Zwycięstwo wyniku przy remisie jakości gry",
    };
  }

  const betterTeam = quality === "home" ? homeName : awayName;
  return {
    tone: "upset",
    text: `Lepsza gra, gorszy wynik — ${betterTeam}`,
  };
}

/** Map known feature_snapshot diffs into signed driver bars. */
export function getAssessmentDrivers(
  snapshot: Record<string, number> | null | undefined,
): AssessmentDriver[] {
  if (!snapshot) {
    return [];
  }

  const drivers: AssessmentDriver[] = [];
  for (const definition of DRIVER_DEFINITIONS) {
    const raw = snapshot[definition.key];
    if (typeof raw !== "number" || Number.isNaN(raw)) {
      continue;
    }
    let favors: AssessmentDriver["favors"] = "neutral";
    if (raw > 0) {
      favors = "home";
    } else if (raw < 0) {
      favors = "away";
    }
    drivers.push({
      key: definition.key,
      label: definition.label,
      value: raw,
      favors,
    });
  }
  return drivers;
}

export function verdictLabel(
  finalAssessment: PlayedBetterFinalAssessment,
  homeName: string,
  awayName: string,
): string {
  if (finalAssessment === "HOME_PLAYED_BETTER") {
    return homeName;
  }
  if (finalAssessment === "AWAY_PLAYED_BETTER") {
    return awayName;
  }
  return "Remis";
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function countReplayCells(
  cells: ReplayCellSide[],
): Record<ReplayCellSide, number> {
  return {
    home: cells.filter((cell) => cell === "home").length,
    draw: cells.filter((cell) => cell === "draw").length,
    away: cells.filter((cell) => cell === "away").length,
  };
}

/** Normalized integer percents that always sum to 100. */
export function normalizeReplayPercents(
  home: number,
  draw: number,
  away: number,
): Record<ReplayCellSide, number> {
  return countReplayCells(allocateReplayCells(home, draw, away));
}

export interface PieSlice {
  side: ReplayCellSide;
  percent: number;
  /** SVG path `d` for a donut/pie wedge; null when percent is 0. */
  path: string | null;
  /** Full-circle fill when one side is 100%. */
  isFullCircle: boolean;
}

/** Build SVG pie slices from normalized percents (home/draw/away). */
export function buildPieSlices(
  percents: Record<ReplayCellSide, number>,
  radius = 42,
  cx = 50,
  cy = 50,
): PieSlice[] {
  const order: ReplayCellSide[] = ["home", "draw", "away"];
  return buildPieSlicesFromSegments(
    order.map((side) => ({ id: side, percent: percents[side] })),
    radius,
    cx,
    cy,
  ).map((slice) => ({
    side: slice.id as ReplayCellSide,
    percent: slice.percent,
    path: slice.path,
    isFullCircle: slice.isFullCircle,
  }));
}
