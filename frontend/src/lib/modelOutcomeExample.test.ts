import { describe, expect, it } from "vitest";

import {
  actualBttsPick,
  actualExactScore,
  actualGoalsBucket,
  actualOverUnderPick,
  actualResultPick,
  calculateAccuracy,
  DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
  settleExamplePredictions,
  validateExampleGoals,
  type PredictionSettlement,
} from "@/lib/modelOutcomeExample";

function settlementByMarket(
  settlements: PredictionSettlement[],
  marketId: PredictionSettlement["marketId"],
): PredictionSettlement {
  const match = settlements.find((entry) => entry.marketId === marketId);
  if (!match) {
    throw new Error(`Missing settlement for ${marketId}`);
  }
  return match;
}

describe("validateExampleGoals", () => {
  it("accepts integers in 0–20", () => {
    expect(validateExampleGoals(0, 0)).toEqual({
      valid: true,
      homeGoals: 0,
      awayGoals: 0,
    });
    expect(validateExampleGoals(20, 7)).toEqual({
      valid: true,
      homeGoals: 20,
      awayGoals: 7,
    });
  });

  it("rejects non-integers and out-of-range values", () => {
    expect(validateExampleGoals(1.5, 0).valid).toBe(false);
    expect(validateExampleGoals(-1, 0).valid).toBe(false);
    expect(validateExampleGoals(0, 21).valid).toBe(false);
    expect(validateExampleGoals(Number.NaN, 1).valid).toBe(false);
  });
});

describe("market mapping helpers", () => {
  it("maps 1X2 for home win, away win and draws", () => {
    expect(actualResultPick(2, 1)).toBe("home");
    expect(actualResultPick(0, 3)).toBe("away");
    expect(actualResultPick(0, 0)).toBe("draw");
    expect(actualResultPick(2, 2)).toBe("draw");
  });

  it("maps BTTS yes/no", () => {
    expect(actualBttsPick(0, 0)).toBe("no");
    expect(actualBttsPick(1, 0)).toBe("no");
    expect(actualBttsPick(0, 2)).toBe("no");
    expect(actualBttsPick(1, 1)).toBe("yes");
  });

  it("maps Over/Under 2.5 on the 2 vs 3 boundary", () => {
    expect(actualOverUnderPick(1, 1)).toBe("under");
    expect(actualOverUnderPick(2, 0)).toBe("under");
    expect(actualOverUnderPick(2, 1)).toBe("over");
    expect(actualOverUnderPick(3, 0)).toBe("over");
  });

  it("maps goal buckets including 6+", () => {
    expect(actualGoalsBucket(0, 0)).toBe("0");
    expect(actualGoalsBucket(2, 1)).toBe("3");
    expect(actualGoalsBucket(3, 2)).toBe("5");
    expect(actualGoalsBucket(3, 3)).toBe("6+");
    expect(actualGoalsBucket(5, 4)).toBe("6+");
  });

  it("formats exact score as home:away", () => {
    expect(actualExactScore(0, 0)).toBe("0:0");
    expect(actualExactScore(2, 1)).toBe("2:1");
  });
});

describe("settleExamplePredictions", () => {
  const fixture = DEFAULT_PREDICTION_EXAMPLE_FIXTURE;

  it("settles 0:0 — draw, no BTTS, under, bucket 0, exact miss vs 1:1", () => {
    const settlements = settleExamplePredictions(0, 0, fixture);

    expect(settlementByMarket(settlements, "result_1x2").outcome).toBe("miss");
    expect(settlementByMarket(settlements, "result_1x2").actualKey).toBe(
      "draw",
    );
    expect(settlementByMarket(settlements, "btts").outcome).toBe("miss");
    expect(settlementByMarket(settlements, "btts").actualKey).toBe("no");
    expect(settlementByMarket(settlements, "over_under_25").outcome).toBe(
      "hit",
    );
    expect(settlementByMarket(settlements, "goals_bucket").outcome).toBe(
      "miss",
    );
    expect(settlementByMarket(settlements, "goals_bucket").actualKey).toBe(
      "0",
    );
    expect(settlementByMarket(settlements, "exact_score").outcome).toBe(
      "miss",
    );
    expect(settlementByMarket(settlements, "exact_score").actualKey).toBe(
      "0:0",
    );
  });

  it("settles a scoring draw 2:2", () => {
    const settlements = settleExamplePredictions(2, 2, fixture);

    expect(settlementByMarket(settlements, "result_1x2").actualKey).toBe(
      "draw",
    );
    expect(settlementByMarket(settlements, "result_1x2").outcome).toBe("miss");
    expect(settlementByMarket(settlements, "btts").outcome).toBe("hit");
    expect(settlementByMarket(settlements, "over_under_25").outcome).toBe(
      "miss",
    );
    expect(settlementByMarket(settlements, "over_under_25").actualKey).toBe(
      "over",
    );
    expect(settlementByMarket(settlements, "goals_bucket").actualKey).toBe(
      "4",
    );
  });

  it("settles home win 2:1 with BTTS and Over 2.5", () => {
    const settlements = settleExamplePredictions(2, 1, fixture);

    expect(settlementByMarket(settlements, "result_1x2").outcome).toBe("hit");
    expect(settlementByMarket(settlements, "btts").outcome).toBe("hit");
    expect(settlementByMarket(settlements, "over_under_25").outcome).toBe(
      "miss",
    );
    expect(settlementByMarket(settlements, "goals_bucket").actualKey).toBe(
      "3",
    );
    expect(settlementByMarket(settlements, "exact_score").outcome).toBe(
      "miss",
    );
  });

  it("settles away win 0:2", () => {
    const settlements = settleExamplePredictions(0, 2, fixture);

    expect(settlementByMarket(settlements, "result_1x2").actualKey).toBe(
      "away",
    );
    expect(settlementByMarket(settlements, "result_1x2").outcome).toBe("miss");
    expect(settlementByMarket(settlements, "btts").outcome).toBe("miss");
    expect(settlementByMarket(settlements, "over_under_25").outcome).toBe(
      "hit",
    );
    expect(settlementByMarket(settlements, "goals_bucket").actualKey).toBe(
      "2",
    );
    expect(settlementByMarket(settlements, "goals_bucket").outcome).toBe(
      "hit",
    );
  });

  it("hits exact score when result matches the fixed pick 1:1", () => {
    const settlements = settleExamplePredictions(1, 1, fixture);

    expect(settlementByMarket(settlements, "exact_score").outcome).toBe("hit");
    expect(settlementByMarket(settlements, "result_1x2").outcome).toBe("miss");
    expect(settlementByMarket(settlements, "btts").outcome).toBe("hit");
    expect(settlementByMarket(settlements, "over_under_25").outcome).toBe(
      "hit",
    );
    expect(settlementByMarket(settlements, "goals_bucket").outcome).toBe(
      "hit",
    );
  });

  it("maps bucket 6+ for high-scoring matches", () => {
    const settlements = settleExamplePredictions(4, 3, fixture);

    expect(settlementByMarket(settlements, "goals_bucket").actualKey).toBe(
      "6+",
    );
    expect(settlementByMarket(settlements, "goals_bucket").outcome).toBe(
      "miss",
    );
    expect(settlementByMarket(settlements, "over_under_25").actualKey).toBe(
      "over",
    );
    expect(settlementByMarket(settlements, "btts").outcome).toBe("hit");
  });

  it("keeps predicted picks and probabilities unchanged across scores", () => {
    const low = settleExamplePredictions(0, 0, fixture);
    const high = settleExamplePredictions(5, 5, fixture);

    for (let index = 0; index < low.length; index += 1) {
      expect(high[index]?.predictedKey).toBe(low[index]?.predictedKey);
      expect(high[index]?.probability).toBe(low[index]?.probability);
    }
  });

  it("throws for invalid goal inputs", () => {
    expect(() => settleExamplePredictions(1.2, 0, fixture)).toThrow(
      /0–20/,
    );
  });
});

describe("calculateAccuracy", () => {
  it("updates correct/total/accuracy from Hit/Miss settlements", () => {
    // 1:1 against default picks -> hit on btts, under, bucket 2, exact; miss 1x2
    const settlements = settleExamplePredictions(
      1,
      1,
      DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
    );
    const change = calculateAccuracy(10, 20, settlements);

    expect(change.hitsAdded).toBe(4);
    expect(change.missesAdded).toBe(1);
    expect(change.correctBefore).toBe(10);
    expect(change.totalBefore).toBe(20);
    expect(change.accuracyBefore).toBe(0.5);
    expect(change.correctAfter).toBe(14);
    expect(change.totalAfter).toBe(25);
    expect(change.accuracyAfter).toBe(14 / 25);
  });

  it("handles empty settlements without changing totals", () => {
    const change = calculateAccuracy(3, 5, []);

    expect(change.correctAfter).toBe(3);
    expect(change.totalAfter).toBe(5);
    expect(change.hitsAdded).toBe(0);
    expect(change.accuracyAfter).toBe(0.6);
  });

  it("returns null accuracy when total is zero before settlement", () => {
    const settlements = settleExamplePredictions(
      2,
      1,
      DEFAULT_PREDICTION_EXAMPLE_FIXTURE,
    );
    const change = calculateAccuracy(0, 0, settlements);

    expect(change.accuracyBefore).toBeNull();
    expect(change.totalAfter).toBe(settlements.length);
    expect(change.accuracyAfter).toBe(
      change.hitsAdded / settlements.length,
    );
  });
});
