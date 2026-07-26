/**
 * Deterministic statistical market assessment for chat tools.
 * Hit rate is historical support, not a calibrated model probability.
 */

import type {
  FootballPlayerMatchStat,
  TeamProfile,
  TeamSeasonMatchPoint,
} from "@/types/api";

import type {
  MarketDirection,
  MarketStat,
  MarketSubject,
  MarketVerdict,
  ParsedMarket,
  StatisticalMarketAssessment,
} from "./markets";
import { FOOTBALL_SPORT_ID } from "./types";

const MIN_SAMPLE_SIZE = 5;
const HIGH_SAMPLE_SIZE = 10;
const PLAYER_LINEUP_WARNING =
  "Historyczna liczba występów nie potwierdza obecności zawodnika w składzie na analizowany mecz.";
const STATISTICAL_EVENT_LABEL =
  "zdarzenie statystyczne — sprawdź dostępność i kurs u bukmachera";

export type TeamMarketStat = Extract<
  MarketStat,
  | "goals"
  | "shots"
  | "shots_on_target"
  | "corners"
  | "cards"
  | "fouls"
  | "offsides"
>;

export type PlayerMarketStat = Extract<
  MarketStat,
  | "goals"
  | "assists"
  | "shots"
  | "shots_on_target"
  | "fouls_conceded"
  | "yellow_cards"
>;

interface LineGrid {
  total: number[];
  team: number[];
}

/** Half-point football lines used for automatic candidate generation. */
export const STATISTICAL_MARKET_CONFIG: Readonly<
  Record<TeamMarketStat, LineGrid>
> = {
  goals: { total: [1.5, 2.5, 3.5], team: [0.5, 1.5, 2.5] },
  shots: {
    total: [17.5, 21.5, 25.5, 29.5, 33.5],
    team: [7.5, 9.5, 11.5, 13.5, 15.5],
  },
  shots_on_target: {
    total: [5.5, 7.5, 9.5, 11.5, 13.5],
    team: [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
  },
  corners: {
    total: [6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5],
    team: [2.5, 3.5, 4.5, 5.5, 6.5, 7.5],
  },
  cards: {
    total: [2.5, 3.5, 4.5, 5.5, 6.5, 7.5],
    team: [0.5, 1.5, 2.5, 3.5, 4.5],
  },
  fouls: {
    total: [18.5, 20.5, 22.5, 24.5, 26.5, 28.5, 30.5],
    team: [7.5, 9.5, 11.5, 13.5, 15.5],
  },
  offsides: {
    total: [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
    team: [0.5, 1.5, 2.5, 3.5],
  },
};

const TEAM_MARKET_STATS = Object.keys(
  STATISTICAL_MARKET_CONFIG,
) as TeamMarketStat[];

interface SeriesEvaluation {
  hitRate: number;
  pushRate: number;
  average: number;
  sampleSize: number;
}

interface BuildStatisticalCandidatesConfig {
  sportId?: number;
  limit?: number;
  maxPerStat?: number;
}

/**
 * Assess a team/total market using independent home and away historical series.
 */
export function assessTeamMarket(
  profileA: TeamProfile,
  profileB: TeamProfile,
  market: ParsedMarket,
  limit: number = 10,
): StatisticalMarketAssessment {
  if (
    !market.stat ||
    !market.direction ||
    market.line === null ||
    market.subject === null ||
    market.subject === "player" ||
    !isTeamMarketStat(market.stat)
  ) {
    return insufficientAssessment(market, [
      "Brakuje jednoznacznej statystyki, podmiotu (gospodarz/gość/suma), kierunku lub linii dla oceny drużynowej.",
    ]);
  }

  const series = buildTeamSeries(
    profileA.season_matches,
    profileB.season_matches,
    market.stat,
    market.subject,
    limit,
  );
  return finalizeTeamAssessment(market, series);
}

/**
 * Assess a player prop from match logs. Always warns about lineup uncertainty.
 */
export function assessPlayerMarket(
  matches: FootballPlayerMatchStat[],
  market: ParsedMarket,
  limit: number = 10,
): StatisticalMarketAssessment {
  const warnings = [PLAYER_LINEUP_WARNING];

  if (
    !market.stat ||
    !market.direction ||
    market.line === null ||
    market.subject !== "player" ||
    !isPlayerMarketStat(market.stat)
  ) {
    return insufficientAssessment(market, [
      ...warnings,
      "Brakuje jednoznacznej statystyki, kierunku lub linii dla oceny zawodnika.",
    ]);
  }

  const values = matches
    .slice(0, limit)
    .map((match) => match[market.stat as PlayerMarketStat])
    .filter((value): value is number => typeof value === "number");

  if (values.length < MIN_SAMPLE_SIZE) {
    return insufficientAssessment(market, warnings, {
      primary_sample_size: values.length,
      primary_average: average(values),
    });
  }

  const primary = evaluateSeries(values, market.direction, market.line);
  const confidence = resolvePlayerConfidence(primary.sampleSize);
  const verdict = resolveVerdict(
    primary.hitRate,
    primary.hitRate,
    null,
  );

  return {
    stat: market.stat,
    subject: "player",
    direction: market.direction,
    line: market.line,
    projection: round1(primary.average),
    primary_sample_size: primary.sampleSize,
    opponent_sample_size: 0,
    primary_average: round1(primary.average),
    opponent_average: null,
    primary_hit_rate: round3(primary.hitRate),
    opponent_hit_rate: null,
    combined_hit_rate: round3(primary.hitRate),
    push_rate: round3(primary.pushRate),
    confidence,
    verdict,
    warnings,
    label: STATISTICAL_EVENT_LABEL,
  };
}

/**
 * Generate non-contradictory statistical candidates for a football matchup.
 */
export function buildStatisticalCandidates(
  profileA: TeamProfile,
  profileB: TeamProfile,
  config: BuildStatisticalCandidatesConfig = {},
): StatisticalMarketAssessment[] {
  const sportId = config.sportId ?? FOOTBALL_SPORT_ID;
  if (sportId !== FOOTBALL_SPORT_ID) {
    return [];
  }

  const lookback = config.limit ?? 10;
  const candidates: StatisticalMarketAssessment[] = [];

  for (const stat of TEAM_MARKET_STATS) {
    const grid = STATISTICAL_MARKET_CONFIG[stat];
    const subjects: MarketSubject[] = ["home", "away", "total"];
    for (const subject of subjects) {
      const lines = subject === "total" ? grid.total : grid.team;
      for (const line of lines) {
        for (const direction of ["over", "under"] as MarketDirection[]) {
          const assessment = assessTeamMarket(
            profileA,
            profileB,
            {
              eventQuery: `${stat} ${subject} ${direction} ${line}`,
              stat,
              subject,
              playerQuery: null,
              direction,
              line,
            },
            lookback,
          );
          if (isViableCandidate(assessment)) {
            candidates.push(assessment);
          }
        }
      }
    }
  }

  return pickBestCandidatesPerStat(candidates);
}

function buildTeamSeries(
  matchesA: TeamSeasonMatchPoint[],
  matchesB: TeamSeasonMatchPoint[],
  stat: TeamMarketStat,
  subject: MarketSubject,
  limit: number,
): { primary: number[]; opponent: number[] } {
  const seriesA = matchesA.slice(0, limit);
  const seriesB = matchesB.slice(0, limit);

  if (subject === "home") {
    return {
      primary: seriesA.map((match) => teamForValue(match, stat)),
      opponent: seriesB.map((match) => teamAgainstValue(match, stat)),
    };
  }

  if (subject === "away") {
    return {
      primary: seriesB.map((match) => teamForValue(match, stat)),
      opponent: seriesA.map((match) => teamAgainstValue(match, stat)),
    };
  }

  return {
    primary: seriesA.map((match) => totalValue(match, stat)),
    opponent: seriesB.map((match) => totalValue(match, stat)),
  };
}

function finalizeTeamAssessment(
  market: ParsedMarket,
  series: { primary: number[]; opponent: number[] },
): StatisticalMarketAssessment {
  const direction = market.direction!;
  const line = market.line!;

  if (
    series.primary.length < MIN_SAMPLE_SIZE ||
    series.opponent.length < MIN_SAMPLE_SIZE
  ) {
    return insufficientAssessment(market, [
      `Niewystarczająca próba (wymagane min. ${MIN_SAMPLE_SIZE}+${MIN_SAMPLE_SIZE} meczów).`,
    ], {
      primary_sample_size: series.primary.length,
      opponent_sample_size: series.opponent.length,
      primary_average: average(series.primary),
      opponent_average: average(series.opponent),
    });
  }

  const primary = evaluateSeries(series.primary, direction, line);
  const opponent = evaluateSeries(series.opponent, direction, line);
  const combinedHitRate = (primary.hitRate + opponent.hitRate) / 2;
  const pushRate = (primary.pushRate + opponent.pushRate) / 2;
  const projection = (primary.average + opponent.average) / 2;
  const confidence = resolveTeamConfidence(
    primary.sampleSize,
    opponent.sampleSize,
    primary.hitRate,
    opponent.hitRate,
  );
  const verdict = resolveVerdict(
    combinedHitRate,
    primary.hitRate,
    opponent.hitRate,
  );

  return {
    stat: market.stat,
    subject: market.subject,
    direction,
    line,
    projection: round1(projection),
    primary_sample_size: primary.sampleSize,
    opponent_sample_size: opponent.sampleSize,
    primary_average: round1(primary.average),
    opponent_average: round1(opponent.average),
    primary_hit_rate: round3(primary.hitRate),
    opponent_hit_rate: round3(opponent.hitRate),
    combined_hit_rate: round3(combinedHitRate),
    push_rate: round3(pushRate),
    confidence,
    verdict,
    warnings: [],
    label: STATISTICAL_EVENT_LABEL,
  };
}

function evaluateSeries(
  values: number[],
  direction: MarketDirection,
  line: number,
): SeriesEvaluation {
  let hits = 0;
  let pushes = 0;
  let decisive = 0;

  for (const value of values) {
    if (Number.isInteger(line) && value === line) {
      pushes += 1;
      continue;
    }
    decisive += 1;
    const isHit =
      direction === "over" ? value > line : value < line;
    if (isHit) {
      hits += 1;
    }
  }

  return {
    hitRate: decisive > 0 ? hits / decisive : 0,
    pushRate: values.length > 0 ? pushes / values.length : 0,
    average: average(values),
    sampleSize: values.length,
  };
}

function resolveVerdict(
  combinedHitRate: number,
  primaryHitRate: number,
  opponentHitRate: number | null,
): MarketVerdict {
  const bothSidesOk =
    opponentHitRate === null
      ? primaryHitRate >= 0.55
      : primaryHitRate >= 0.55 && opponentHitRate >= 0.55;

  if (combinedHitRate >= 0.65 && bothSidesOk) {
    return "positive";
  }
  if (combinedHitRate >= 0.55) {
    return "lean_positive";
  }
  if (combinedHitRate >= 0.45) {
    return "neutral";
  }
  if (combinedHitRate >= 0.35) {
    return "lean_negative";
  }
  return "negative";
}

function resolveTeamConfidence(
  primarySize: number,
  opponentSize: number,
  primaryHitRate: number,
  opponentHitRate: number,
): "high" | "medium" | "low" {
  const hitDiff = Math.abs(primaryHitRate - opponentHitRate);
  if (
    primarySize >= HIGH_SAMPLE_SIZE &&
    opponentSize >= HIGH_SAMPLE_SIZE &&
    hitDiff <= 0.2
  ) {
    return "high";
  }
  if (
    primarySize >= MIN_SAMPLE_SIZE &&
    opponentSize >= MIN_SAMPLE_SIZE &&
    hitDiff <= 0.35
  ) {
    return "medium";
  }
  return "low";
}

function resolvePlayerConfidence(
  sampleSize: number,
): "high" | "medium" | "low" {
  if (sampleSize >= HIGH_SAMPLE_SIZE) {
    return "high";
  }
  if (sampleSize >= MIN_SAMPLE_SIZE) {
    return "medium";
  }
  return "low";
}

function isViableCandidate(assessment: StatisticalMarketAssessment): boolean {
  if (assessment.verdict === "insufficient_data") {
    return false;
  }
  if (assessment.confidence === "low") {
    return false;
  }
  if (
    assessment.primary_sample_size < MIN_SAMPLE_SIZE ||
    assessment.opponent_sample_size < MIN_SAMPLE_SIZE
  ) {
    return false;
  }
  const rate = assessment.combined_hit_rate;
  return rate >= 0.6 && rate <= 0.9;
}

function pickBestCandidatesPerStat(
  candidates: StatisticalMarketAssessment[],
): StatisticalMarketAssessment[] {
  const byStat = new Map<string, StatisticalMarketAssessment[]>();
  for (const candidate of candidates) {
    const key = String(candidate.stat);
    const bucket = byStat.get(key) ?? [];
    bucket.push(candidate);
    byStat.set(key, bucket);
  }

  const selected: StatisticalMarketAssessment[] = [];
  for (const bucket of byStat.values()) {
    bucket.sort(compareCandidates);
    const best = bucket[0];
    if (best) {
      selected.push(best);
    }
  }

  return selected.sort(compareCandidates);
}

function compareCandidates(
  left: StatisticalMarketAssessment,
  right: StatisticalMarketAssessment,
): number {
  const confidenceRank = { high: 0, medium: 1, low: 2 } as const;
  const confidenceDiff =
    confidenceRank[left.confidence] - confidenceRank[right.confidence];
  if (confidenceDiff !== 0) {
    return confidenceDiff;
  }

  // bliżej 0.50 = mniej skrajna, ale ranking chce informacyjną wartość:
  // plan: confidence → odległość od 0.50 → zgodność perspektyw
  const leftDistance = Math.abs(left.combined_hit_rate - 0.5);
  const rightDistance = Math.abs(right.combined_hit_rate - 0.5);
  if (leftDistance !== rightDistance) {
    return rightDistance - leftDistance;
  }

  const leftAgreement = perspectiveAgreement(left);
  const rightAgreement = perspectiveAgreement(right);
  return rightAgreement - leftAgreement;
}

function perspectiveAgreement(assessment: StatisticalMarketAssessment): number {
  if (assessment.opponent_hit_rate === null) {
    return 0;
  }
  return 1 - Math.abs(assessment.primary_hit_rate - assessment.opponent_hit_rate);
}

function teamForValue(match: TeamSeasonMatchPoint, stat: TeamMarketStat): number {
  if (stat === "goals") {
    return match.is_home ? match.home_goals : match.away_goals;
  }
  const key = `team_${stat}` as keyof TeamSeasonMatchPoint;
  const value = match[key];
  return typeof value === "number" ? value : 0;
}

function teamAgainstValue(
  match: TeamSeasonMatchPoint,
  stat: TeamMarketStat,
): number {
  if (stat === "goals") {
    return match.is_home ? match.away_goals : match.home_goals;
  }
  const key = `opponent_${stat}` as keyof TeamSeasonMatchPoint;
  const value = match[key];
  return typeof value === "number" ? value : 0;
}

function totalValue(match: TeamSeasonMatchPoint, stat: TeamMarketStat): number {
  if (stat === "goals") {
    return match.total_goals;
  }
  const key = `total_${stat}` as keyof TeamSeasonMatchPoint;
  const value = match[key];
  return typeof value === "number" ? value : 0;
}

function insufficientAssessment(
  market: ParsedMarket,
  warnings: string[],
  extras: Partial<StatisticalMarketAssessment> = {},
): StatisticalMarketAssessment {
  return {
    stat: market.stat,
    subject: market.subject,
    direction: market.direction ?? "over",
    line: market.line ?? 0,
    projection: extras.projection ?? 0,
    primary_sample_size: extras.primary_sample_size ?? 0,
    opponent_sample_size: extras.opponent_sample_size ?? 0,
    primary_average: extras.primary_average ?? 0,
    opponent_average: extras.opponent_average ?? null,
    primary_hit_rate: extras.primary_hit_rate ?? 0,
    opponent_hit_rate: extras.opponent_hit_rate ?? null,
    combined_hit_rate: extras.combined_hit_rate ?? 0,
    push_rate: extras.push_rate ?? 0,
    confidence: "low",
    verdict: "insufficient_data",
    warnings,
    label: STATISTICAL_EVENT_LABEL,
  };
}

function isTeamMarketStat(stat: MarketStat): stat is TeamMarketStat {
  return TEAM_MARKET_STATS.includes(stat as TeamMarketStat);
}

function isPlayerMarketStat(stat: MarketStat): stat is PlayerMarketStat {
  return (
    stat === "goals" ||
    stat === "assists" ||
    stat === "shots" ||
    stat === "shots_on_target" ||
    stat === "fouls_conceded" ||
    stat === "yellow_cards"
  );
}

function average(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function round3(value: number): number {
  return Math.round(value * 1000) / 1000;
}
