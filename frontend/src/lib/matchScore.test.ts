import { describe, expect, it } from "vitest";

import { formatMatchScore, resolveMatchScore } from "@/lib/matchScore";
import type { MatchScoreResolution } from "@/types/api";

function resolution(
  overrides: Partial<MatchScoreResolution> = {},
): MatchScoreResolution {
  return {
    has_extra_time: false,
    has_penalties: false,
    post_ot_home_goals: null,
    post_ot_away_goals: null,
    penalties_home_goals: null,
    penalties_away_goals: null,
    ...overrides,
  };
}

describe("resolveMatchScore", () => {
  it("uses post-OT goals for extra time without penalties", () => {
    const result = resolveMatchScore({
      home_goals: 1,
      away_goals: 1,
      is_played: true,
      score_resolution: resolution({
        has_extra_time: true,
        post_ot_home_goals: 2,
        post_ot_away_goals: 1,
      }),
    });

    expect(result).toEqual({ main: "2 : 1", note: "po dogrywce" });
  });

  it("falls back to match goals when post-OT goals are null", () => {
    const result = resolveMatchScore({
      home_goals: 1,
      away_goals: 1,
      is_played: true,
      score_resolution: resolution({
        has_extra_time: true,
        post_ot_home_goals: null,
        post_ot_away_goals: null,
      }),
    });

    expect(result).toEqual({ main: "1 : 1", note: "po dogrywce" });
  });

  it("keeps penalty path: main from post-OT score, note from penalties", () => {
    const result = resolveMatchScore({
      home_goals: 1,
      away_goals: 1,
      is_played: true,
      score_resolution: resolution({
        has_extra_time: true,
        has_penalties: true,
        post_ot_home_goals: 2,
        post_ot_away_goals: 1,
        penalties_home_goals: 5,
        penalties_away_goals: 4,
      }),
    });

    expect(result).toEqual({
      main: "2 : 1",
      note: "(po karnych 5 : 4)",
    });
  });

  it("returns plain score without note when score_resolution is missing", () => {
    const result = resolveMatchScore({
      home_goals: 3,
      away_goals: 0,
      is_played: true,
      score_resolution: null,
    });

    expect(result).toEqual({ main: "3 : 0", note: null });
  });

  it("returns dashes for unplayed match", () => {
    const result = resolveMatchScore({
      home_goals: null,
      away_goals: null,
      is_played: false,
    });

    expect(result).toEqual({ main: "– : –", note: null });
  });

  it("formats OT score with post-OT goals and note", () => {
    const formatted = formatMatchScore({
      home_goals: 1,
      away_goals: 1,
      is_played: true,
      score_resolution: resolution({
        has_extra_time: true,
        post_ot_home_goals: 2,
        post_ot_away_goals: 1,
      }),
    });

    expect(formatted).toBe("2 : 1 po dogrywce");
  });
});
