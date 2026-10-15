import { describe, expect, it } from "vitest";

import {
  averageHighlights,
  goalBucketViews,
  integerShares,
  over55Count,
  over65Count,
} from "@/lib/hockeyLeagueStatsModel";
import type {
  HockeyGoalsDistribution,
  SportLeagueStatRow,
} from "@/types/api";

function row(
  name: string,
  avgFor: number,
  avgAgainst: number,
): SportLeagueStatRow {
  return {
    team_name: name,
    team_shortcut: name.slice(0, 3).toUpperCase(),
    avg_for: avgFor,
    avg_against: avgAgainst,
    matches_played: 4,
  };
}

const distribution: HockeyGoalsDistribution = {
  total_matches: 10,
  under_5: 2,
  exactly_5: 1,
  exactly_6: 3,
  exactly_7: 2,
  over_7: 2,
};

describe("hockey league stats model", () => {
  it("averages team shot rates the way the old league cards did", () => {
    const highlights = averageHighlights(
      [row("A", 30, 28), row("B", 20, 22)],
      "shots",
    );
    const league = highlights.find((item) =>
      item.label.includes("Średnia ligowa"),
    );
    expect(league?.value).toBe("25.00");
    expect(highlights[0]?.detail).toBe("A");
    expect(highlights[1]?.detail).toBe("B");
  });

  it("counts over 5.5 as matches with at least 6 goals", () => {
    expect(over55Count(distribution)).toBe(7);
    expect(over65Count(distribution)).toBe(4);
  });

  it("builds pie shares that sum to 100", () => {
    const buckets = goalBucketViews(distribution);
    const sum = buckets.reduce((total, bucket) => total + bucket.piePercent, 0);
    expect(sum).toBe(100);
    expect(buckets.map((bucket) => bucket.count)).toEqual([2, 1, 3, 2, 2]);
    const thirds = integerShares([1, 1, 1]);
    expect(thirds.reduce((total, share) => total + share, 0)).toBe(100);
  });
});
