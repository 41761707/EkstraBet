/** Educational settlement calculator for the /o-modelach interactive example. */

export const MIN_EXAMPLE_GOALS = 0;
export const MAX_EXAMPLE_GOALS = 20;

export type ExampleMarketId =
  | "result_1x2"
  | "btts"
  | "over_under_25"
  | "goals_bucket"
  | "exact_score";

export type ResultPick = "home" | "draw" | "away";
export type BttsPick = "yes" | "no";
export type OverUnderPick = "over" | "under";

export interface ExactScoreProbability {
  score: string;
  probability: number;
}

export interface PredictionExampleFixture {
  homeTeamLabel: string;
  awayTeamLabel: string;
  result: {
    p_home: number;
    p_draw: number;
    p_away: number;
  };
  btts: {
    p_yes: number;
    p_no: number;
  };
  goals: {
    lambda_home: number;
    lambda_away: number;
    total_buckets: Record<string, number>;
    over_25: number;
    under_25: number;
    top_exact_scores: ExactScoreProbability[];
  };
  /**
   * Explicit final selections (argmax at fixture creation time).
   * Score changes must not recompute these picks.
   */
  picks: {
    result: ResultPick;
    btts: BttsPick;
    overUnder: OverUnderPick;
    goalsBucket: string;
    exactScore: string;
  };
  baselineCorrect: number;
  baselineTotal: number;
}

export interface PredictionSettlement {
  marketId: ExampleMarketId;
  marketLabel: string;
  predictedKey: string;
  predictedLabel: string;
  actualKey: string;
  actualLabel: string;
  probability: number;
  outcome: "hit" | "miss";
}

export interface AccuracyChange {
  correctBefore: number;
  totalBefore: number;
  accuracyBefore: number | null;
  correctAfter: number;
  totalAfter: number;
  accuracyAfter: number | null;
  hitsAdded: number;
  missesAdded: number;
}

export type GoalsValidationResult =
  | { valid: true; homeGoals: number; awayGoals: number }
  | { valid: false; message: string };

/**
 * Stable educational fixture: probabilities stay fixed; only Hit/Miss
 * and sample accuracy react to the entered score.
 */
export const DEFAULT_PREDICTION_EXAMPLE_FIXTURE: PredictionExampleFixture = {
  homeTeamLabel: "Gospodarze",
  awayTeamLabel: "Goście",
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
  // jawny argmax — nie przeliczamy przy zmianie wyniku
  picks: {
    result: "home",
    btts: "yes",
    overUnder: "under",
    goalsBucket: "2",
    exactScore: "1:1",
  },
  baselineCorrect: 10,
  baselineTotal: 20,
};

function isIntegerInRange(value: number): boolean {
  return (
    Number.isInteger(value) &&
    value >= MIN_EXAMPLE_GOALS &&
    value <= MAX_EXAMPLE_GOALS
  );
}

/** Validate interactive goal inputs (integers 0–20). */
export function validateExampleGoals(
  homeGoals: number,
  awayGoals: number,
): GoalsValidationResult {
  if (!Number.isFinite(homeGoals) || !Number.isFinite(awayGoals) || !isIntegerInRange(homeGoals) || !isIntegerInRange(awayGoals)) {
    return {
      valid: false,
      message: "Podaj liczby całkowite goli w zakresie 0–20.",
    };
  }
  return { valid: true, homeGoals, awayGoals };
}

export function actualResultPick(
  homeGoals: number,
  awayGoals: number,
): ResultPick {
  if (homeGoals > awayGoals) {
    return "home";
  }
  if (homeGoals < awayGoals) {
    return "away";
  }
  return "draw";
}

export function actualBttsPick(homeGoals: number, awayGoals: number): BttsPick {
  return homeGoals > 0 && awayGoals > 0 ? "yes" : "no";
}

export function actualOverUnderPick(
  homeGoals: number,
  awayGoals: number,
): OverUnderPick {
  return homeGoals + awayGoals >= 3 ? "over" : "under";
}

export function actualGoalsBucket(
  homeGoals: number,
  awayGoals: number,
): string {
  const total = homeGoals + awayGoals;
  return total >= 6 ? "6+" : String(total);
}

export function actualExactScore(
  homeGoals: number,
  awayGoals: number,
): string {
  return `${homeGoals}:${awayGoals}`;
}

function resultLabel(
  pick: ResultPick,
  fixture: PredictionExampleFixture,
): string {
  if (pick === "home") {
    return fixture.homeTeamLabel;
  }
  if (pick === "away") {
    return fixture.awayTeamLabel;
  }
  return "Remis";
}

function bttsLabel(pick: BttsPick): string {
  return pick === "yes" ? "BTTS tak" : "BTTS nie";
}

function overUnderLabel(pick: OverUnderPick): string {
  return pick === "over" ? "Over 2.5" : "Under 2.5";
}

function goalsBucketLabel(bucket: string): string {
  return bucket === "6+" ? "Suma goli 6+" : `Suma goli ${bucket}`;
}

function exactScoreLabel(score: string): string {
  return `Dokładny wynik ${score}`;
}

function resultProbability(
  pick: ResultPick,
  fixture: PredictionExampleFixture,
): number {
  if (pick === "home") {
    return fixture.result.p_home;
  }
  if (pick === "away") {
    return fixture.result.p_away;
  }
  return fixture.result.p_draw;
}

function bttsProbability(
  pick: BttsPick,
  fixture: PredictionExampleFixture,
): number {
  return pick === "yes" ? fixture.btts.p_yes : fixture.btts.p_no;
}

function overUnderProbability(
  pick: OverUnderPick,
  fixture: PredictionExampleFixture,
): number {
  return pick === "over" ? fixture.goals.over_25 : fixture.goals.under_25;
}

function goalsBucketProbability(
  bucket: string,
  fixture: PredictionExampleFixture,
): number {
  return fixture.goals.total_buckets[bucket] ?? 0;
}

function exactScoreProbability(
  score: string,
  fixture: PredictionExampleFixture,
): number {
  const match = fixture.goals.top_exact_scores.find(
    (entry) => entry.score === score,
  );
  return match?.probability ?? 0;
}

function toSettlement(
  marketId: ExampleMarketId,
  marketLabel: string,
  predictedKey: string,
  predictedLabel: string,
  actualKey: string,
  actualLabel: string,
  probability: number,
): PredictionSettlement {
  return {
    marketId,
    marketLabel,
    predictedKey,
    predictedLabel,
    actualKey,
    actualLabel,
    probability,
    outcome: predictedKey === actualKey ? "hit" : "miss",
  };
}

/**
 * Settle fixed fixture picks against an entered score.
 * Probabilities and picks stay unchanged — only Hit/Miss updates.
 */
export function settleExamplePredictions(
  homeGoals: number,
  awayGoals: number,
  fixture: PredictionExampleFixture = DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
): PredictionSettlement[] {
  const validation = validateExampleGoals(homeGoals, awayGoals);
  if (!validation.valid) {
    throw new Error(validation.message);
  }

  const actualResult = actualResultPick(homeGoals, awayGoals);
  const actualBtts = actualBttsPick(homeGoals, awayGoals);
  const actualOverUnder = actualOverUnderPick(homeGoals, awayGoals);
  const actualBucket = actualGoalsBucket(homeGoals, awayGoals);
  const actualExact = actualExactScore(homeGoals, awayGoals);

  return [
    toSettlement(
      "result_1x2",
      "Wynik 1X2",
      fixture.picks.result,
      resultLabel(fixture.picks.result, fixture),
      actualResult,
      resultLabel(actualResult, fixture),
      resultProbability(fixture.picks.result, fixture),
    ),
    toSettlement(
      "btts",
      "BTTS",
      fixture.picks.btts,
      bttsLabel(fixture.picks.btts),
      actualBtts,
      bttsLabel(actualBtts),
      bttsProbability(fixture.picks.btts, fixture),
    ),
    toSettlement(
      "over_under_25",
      "Over/Under 2.5",
      fixture.picks.overUnder,
      overUnderLabel(fixture.picks.overUnder),
      actualOverUnder,
      overUnderLabel(actualOverUnder),
      overUnderProbability(fixture.picks.overUnder, fixture),
    ),
    toSettlement(
      "goals_bucket",
      "Suma goli",
      fixture.picks.goalsBucket,
      goalsBucketLabel(fixture.picks.goalsBucket),
      actualBucket,
      goalsBucketLabel(actualBucket),
      goalsBucketProbability(fixture.picks.goalsBucket, fixture),
    ),
    toSettlement(
      "exact_score",
      "Exact score",
      fixture.picks.exactScore,
      exactScoreLabel(fixture.picks.exactScore),
      actualExact,
      exactScoreLabel(actualExact),
      exactScoreProbability(fixture.picks.exactScore, fixture),
    ),
  ];
}

function ratioOrNull(correct: number, total: number): number | null {
  if (total <= 0) {
    return null;
  }
  return correct / total;
}

/**
 * Show sample accuracy before/after settlement without persisting data.
 */
export function calculateAccuracy(
  correctBefore: number,
  totalBefore: number,
  settlements: PredictionSettlement[],
): AccuracyChange {
  if (
    !Number.isFinite(correctBefore) ||
    !Number.isFinite(totalBefore) ||
    correctBefore < 0 ||
    totalBefore < 0 ||
    correctBefore > totalBefore
  ) {
    throw new Error("Invalid accuracy baseline values");
  }

  const hitsAdded = settlements.filter(
    (settlement) => settlement.outcome === "hit",
  ).length;
  const missesAdded = settlements.length - hitsAdded;
  const correctAfter = correctBefore + hitsAdded;
  const totalAfter = totalBefore + settlements.length;

  return {
    correctBefore,
    totalBefore,
    accuracyBefore: ratioOrNull(correctBefore, totalBefore),
    correctAfter,
    totalAfter,
    accuracyAfter: ratioOrNull(correctAfter, totalAfter),
    hitsAdded,
    missesAdded,
  };
}
