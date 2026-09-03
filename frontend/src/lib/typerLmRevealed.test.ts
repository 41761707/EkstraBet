import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/apiShared";
import {
  buildRevealedPickLookup,
  formatRevealedPickLabel,
  revealedPredictionsLoadErrorMessage,
} from "@/lib/typerLmRevealed";
import type { TyperRevealedMatch } from "@/types/api";

function sampleRevealedMatch(
  overrides: Partial<TyperRevealedMatch> = {},
): TyperRevealedMatch {
  return {
    match_id: 101,
    game_date: "2026-09-16T21:00:00",
    home_team: { id: 1, name: "Bayern Monachium", shortcut: "BAY" },
    away_team: { id: 2, name: "Arsenal", shortcut: "ARS" },
    picks: [],
    ...overrides,
  };
}

describe("formatRevealedPickLabel", () => {
  it("appends the 1X2 marker to full team names and Remis", () => {
    const match = sampleRevealedMatch();

    expect(formatRevealedPickLabel(match, "1", "full")).toBe(
      "Bayern Monachium (1)",
    );
    expect(formatRevealedPickLabel(match, "X", "full")).toBe("Remis (X)");
    expect(formatRevealedPickLabel(match, "2", "full")).toBe("Arsenal (2)");
  });

  it("uses team shortcuts when the user prefers them", () => {
    const match = sampleRevealedMatch();

    expect(formatRevealedPickLabel(match, "1", "shortcut")).toBe("BAY (1)");
    expect(formatRevealedPickLabel(match, "X", "shortcut")).toBe("Remis (X)");
    expect(formatRevealedPickLabel(match, "2", "shortcut")).toBe("ARS (2)");
  });

  it("falls back to the full name when a shortcut is missing", () => {
    const match = sampleRevealedMatch({
      home_team: { id: 1, name: "Bayern Monachium", shortcut: "" },
    });

    expect(formatRevealedPickLabel(match, "1", "shortcut")).toBe(
      "Bayern Monachium (1)",
    );
  });
});

describe("buildRevealedPickLookup", () => {
  it("returns undefined for a missing match-user cell", () => {
    const lookup = buildRevealedPickLookup([
      sampleRevealedMatch({
        picks: [{ user_uuid: "user-1", outcome: "1" }],
      }),
    ]);

    expect(lookup.get(101)?.get("user-1")).toBe("1");
    expect(lookup.get(101)?.get("user-missing")).toBeUndefined();
    expect(lookup.get(999)?.get("user-1")).toBeUndefined();
  });

  it("does not mix the same user across different matches", () => {
    const lookup = buildRevealedPickLookup([
      sampleRevealedMatch({
        match_id: 101,
        picks: [
          { user_uuid: "user-1", outcome: "1" },
          { user_uuid: "user-2", outcome: "X" },
        ],
      }),
      sampleRevealedMatch({
        match_id: 202,
        picks: [{ user_uuid: "user-1", outcome: "2" }],
      }),
    ]);

    expect(lookup.get(101)?.get("user-1")).toBe("1");
    expect(lookup.get(101)?.get("user-2")).toBe("X");
    expect(lookup.get(202)?.get("user-1")).toBe("2");
    expect(lookup.get(202)?.get("user-2")).toBeUndefined();
  });
});

describe("revealedPredictionsLoadErrorMessage", () => {
  it("maps 401 and 422, then falls back for other errors", () => {
    expect(
      revealedPredictionsLoadErrorMessage(new ApiError(401, "no session")),
    ).toContain("Sesja wygasła");
    expect(
      revealedPredictionsLoadErrorMessage(new ApiError(422, "round")),
    ).toContain("nie jest obsługiwana");
    expect(
      revealedPredictionsLoadErrorMessage(new Error("network")),
    ).toContain("Spróbuj ponownie");
  });
});
