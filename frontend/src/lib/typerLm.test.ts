import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/apiShared";
import {
  addPendingMatchId,
  applySavedPrediction,
  canSaveTyperOutcome,
  formatOutcomeTransition,
  formatTyperPointsLabel,
  formatTyperResultLabel,
  formatTyperRoundLabel,
  getTyperPointsStatus,
  isTyperDeadlinePassed,
  isTyperMatchLockedForUi,
  isTyperOddsPlaceholderVisible,
  lockTyperMatch,
  removePendingMatchId,
  selectInitialRoundNumber,
  takeRecentPredictionChanges,
  typerSaveErrorMessage,
  updateDashboardMatch,
} from "@/lib/typerLm";
import type {
  SaveTyperPredictionResponse,
  TyperDashboardResponse,
  TyperMatch,
  TyperPredictionChange,
} from "@/types/api";

function sampleMatch(overrides: Partial<TyperMatch> = {}): TyperMatch {
  return {
    match_id: 101,
    season_id: 13,
    round_number: 1,
    game_date: "2026-09-16T21:00:00",
    published_at: "2026-09-10T12:00:00",
    is_locked: false,
    result: null,
    home_team: { id: 1, name: "Home", shortcut: "HOM" },
    away_team: { id: 2, name: "Away", shortcut: "AWY" },
    odds_home: 1.85,
    odds_draw: 3.4,
    odds_away: 4.2,
    outcome: null,
    points: null,
    changes: [],
    ...overrides,
  };
}

function sampleChange(
  overrides: Partial<TyperPredictionChange> = {},
): TyperPredictionChange {
  return {
    match_id: 101,
    user_uuid: "user-1",
    display_name: "Ala",
    previous_outcome: null,
    new_outcome: "1",
    changed_at: "2026-09-11T18:30:00",
    ...overrides,
  };
}

describe("formatTyperRoundLabel", () => {
  it("labels league-phase rounds 1-8 as kolejka", () => {
    expect(formatTyperRoundLabel(1)).toBe("Kolejka 1");
    expect(formatTyperRoundLabel(8, "8")).toBe("Kolejka 8");
  });

  it("uses special_rounds names and does not crush knockout rounds", () => {
    expect(formatTyperRoundLabel(973, "1/8-FINAŁU")).toBe("1/8-FINAŁU");
    expect(formatTyperRoundLabel(972, "ĆWIERĆFINAŁ")).toBe("ĆWIERĆFINAŁ");
    expect(formatTyperRoundLabel(971, "PÓŁFINAŁ")).toBe("PÓŁFINAŁ");
    expect(formatTyperRoundLabel(970, "FINAŁ")).toBe("FINAŁ");
    expect(formatTyperRoundLabel(900, "Baraże")).toBe("Baraże");
    expect(formatTyperRoundLabel(973, "1/8-FINAŁU")).not.toBe(
      formatTyperRoundLabel(972, "ĆWIERĆFINAŁ"),
    );
  });

  it("falls back to a unique round number label", () => {
    expect(formatTyperRoundLabel(973)).toBe("Runda 973");
    expect(formatTyperRoundLabel(900, "900")).toBe("Runda 900");
    expect(formatTyperRoundLabel(973)).not.toBe(formatTyperRoundLabel(900));
  });
});

describe("selectInitialRoundNumber", () => {
  it("prefers the first round that still has an unlocked match", () => {
    const selected = selectInitialRoundNumber([
      {
        round_number: 1,
        round_label: "1",
        matches: [sampleMatch({ is_locked: true })],
      },
      {
        round_number: 2,
        round_label: "2",
        matches: [sampleMatch({ match_id: 2 })],
      },
    ]);
    expect(selected).toBe(2);
  });

  it("falls back to the last published round when all matches are locked", () => {
    const selected = selectInitialRoundNumber([
      {
        round_number: 1,
        round_label: "1",
        matches: [sampleMatch({ is_locked: true })],
      },
      {
        round_number: 2,
        round_label: "2",
        matches: [sampleMatch({ match_id: 2, is_locked: true })],
      },
    ]);
    expect(selected).toBe(2);
  });

  it("returns null when there are no rounds", () => {
    expect(selectInitialRoundNumber([])).toBeNull();
  });
});

describe("points and odds presentation", () => {
  it("shows the odds placeholder only when every 1X2 price is missing", () => {
    expect(isTyperOddsPlaceholderVisible(sampleMatch({
      odds_home: null,
      odds_draw: null,
      odds_away: null,
    }))).toBe(true);
    expect(isTyperOddsPlaceholderVisible(sampleMatch({
      odds_home: null,
      odds_draw: null,
      odds_away: 3.4,
    }))).toBe(false);
  });

  it("maps hit, miss, unsettled and missing picks", () => {
    expect(getTyperPointsStatus(sampleMatch({ outcome: "1", points: 1.85 }))).toBe(
      "hit",
    );
    expect(getTyperPointsStatus(sampleMatch({ outcome: "X", points: 0 }))).toBe(
      "miss",
    );
    expect(getTyperPointsStatus(sampleMatch({ outcome: "2", points: null }))).toBe(
      "unsettled",
    );
    expect(getTyperPointsStatus(sampleMatch({ outcome: null }))).toBe("none");
  });

  it("formats point labels for the match card", () => {
    expect(formatTyperPointsLabel(sampleMatch({ outcome: "1", points: 1.85 }))).toBe(
      "1.85 pkt",
    );
    expect(formatTyperPointsLabel(sampleMatch({ outcome: "X", points: 0 }))).toBe(
      "0 pkt",
    );
    expect(formatTyperPointsLabel(sampleMatch({ outcome: "2" }))).toBe(
      "Nierozstrzygnięte",
    );
    expect(formatTyperPointsLabel(sampleMatch())).toBe("—");
  });
});

describe("prediction history presentation", () => {
  it("formats first save and later changes", () => {
    expect(formatOutcomeTransition(null, "1")).toBe("— na 1");
    expect(formatOutcomeTransition("1", "X")).toBe("1 na X");
  });

  it("keeps the latest history rows in chronological order", () => {
    const recent = takeRecentPredictionChanges([
      sampleChange({ new_outcome: "1", changed_at: "t1" }),
      sampleChange({
        previous_outcome: "1",
        new_outcome: "X",
        changed_at: "t2",
      }),
      sampleChange({
        previous_outcome: "X",
        new_outcome: "2",
        changed_at: "t3",
      }),
      sampleChange({
        previous_outcome: "2",
        new_outcome: "1",
        changed_at: "t4",
      }),
    ]);
    expect(recent).toHaveLength(3);
    expect(recent[0]?.new_outcome).toBe("X");
    expect(recent[2]?.new_outcome).toBe("1");
  });
});

describe("save helpers", () => {
  const beforeKickoff = 0;

  it("blocks locked matches, pending saves and identical picks", () => {
    expect(
      canSaveTyperOutcome(
        sampleMatch({ is_locked: true }),
        "1",
        false,
        beforeKickoff,
      ),
    ).toBe(false);
    expect(
      canSaveTyperOutcome(
        sampleMatch({ outcome: "1" }),
        "1",
        false,
        beforeKickoff,
      ),
    ).toBe(false);
    expect(canSaveTyperOutcome(sampleMatch(), "1", true, beforeKickoff)).toBe(
      false,
    );
    expect(canSaveTyperOutcome(sampleMatch(), "1", false, beforeKickoff)).toBe(
      true,
    );
  });

  it("appends audit only when the backend wrote a change", () => {
    const saved: SaveTyperPredictionResponse = {
      match_id: 101,
      outcome: "X",
      previous_outcome: "1",
      audit_written: true,
      created_at: "2026-09-11T18:00:00",
      updated_at: "2026-09-11T19:00:00",
    };
    const updated = applySavedPrediction(
      sampleMatch({ outcome: "1" }),
      saved,
      { uuid: "user-1", displayName: "Ala" },
    );
    expect(updated.outcome).toBe("X");
    expect(updated.changes).toHaveLength(1);
    expect(updated.changes[0]?.previous_outcome).toBe("1");
  });

  it("does not duplicate history on a no-op save", () => {
    const saved: SaveTyperPredictionResponse = {
      match_id: 101,
      outcome: "1",
      previous_outcome: "1",
      audit_written: false,
      created_at: "2026-09-11T18:00:00",
      updated_at: "2026-09-11T18:00:00",
    };
    const updated = applySavedPrediction(
      sampleMatch({ outcome: "1", changes: [sampleChange()] }),
      saved,
      { uuid: "user-1", displayName: "Ala" },
    );
    expect(updated.changes).toHaveLength(1);
  });

  it("locks a match after a kick-off conflict", () => {
    expect(lockTyperMatch(sampleMatch()).is_locked).toBe(true);
  });

  it("updates only the targeted match in the dashboard", () => {
    const dashboard: TyperDashboardResponse = {
      season_id: 13,
      rounds: [
        {
          round_number: 1,
          round_label: "1",
          matches: [sampleMatch(), sampleMatch({ match_id: 202 })],
        },
      ],
    };
    const updated = updateDashboardMatch(dashboard, 202, lockTyperMatch);
    expect(updated.rounds[0]?.matches[0]?.is_locked).toBe(false);
    expect(updated.rounds[0]?.matches[1]?.is_locked).toBe(true);
  });

  it("maps API errors to Polish save messages", () => {
    expect(typerSaveErrorMessage(new ApiError(409, "locked"))).toContain(
      "rozpoczął",
    );
    expect(typerSaveErrorMessage(new ApiError(404, "missing"))).toContain(
      "opublikowany",
    );
    expect(typerSaveErrorMessage(new Error("nope"))).toContain("ponownie");
  });
});

describe("formatTyperResultLabel", () => {
  it("hides the result before kick-off", () => {
    expect(formatTyperResultLabel(sampleMatch({ result: "1" }), 0)).toBeNull();
  });

  it("shows the official 1X2 after kick-off", () => {
    expect(
      formatTyperResultLabel(sampleMatch({ is_locked: true, result: "X" }), 0),
    ).toBe("Wynik: X");
  });

  it("waits for a regulation result when the match is locked", () => {
    expect(formatTyperResultLabel(sampleMatch({ is_locked: true }), 0)).toBe(
      "Oczekiwanie na wynik",
    );
  });

  it("treats a passed game_date as locked even when SSR is_locked is false", () => {
    const kickoff = "2026-09-16T21:00:00.000Z";
    const afterKickoff = Date.parse(kickoff) + 1;
    expect(
      formatTyperResultLabel(
        sampleMatch({ is_locked: false, game_date: kickoff }),
        afterKickoff,
      ),
    ).toBe("Oczekiwanie na wynik");
  });
});

describe("presentation deadline lock", () => {
  const kickoff = "2026-09-16T21:00:00.000Z";
  const beforeKickoff = Date.parse(kickoff) - 1;
  const afterKickoff = Date.parse(kickoff) + 1;

  it("locks when game_date has passed, independently of is_locked", () => {
    const match = sampleMatch({ is_locked: false, game_date: kickoff });
    expect(isTyperDeadlinePassed(kickoff, beforeKickoff)).toBe(false);
    expect(isTyperDeadlinePassed(kickoff, afterKickoff)).toBe(true);
    expect(isTyperMatchLockedForUi(match, beforeKickoff)).toBe(false);
    expect(isTyperMatchLockedForUi(match, afterKickoff)).toBe(true);
    expect(canSaveTyperOutcome(match, "1", false, afterKickoff)).toBe(false);
  });

  it("ignores game_date until a client clock is provided", () => {
    const match = sampleMatch({
      is_locked: false,
      game_date: "2020-01-01T12:00:00.000Z",
    });
    expect(isTyperMatchLockedForUi(match)).toBe(false);
    expect(isTyperMatchLockedForUi(match, null)).toBe(false);
    expect(canSaveTyperOutcome(match, "1", false)).toBe(true);
    expect(canSaveTyperOutcome(match, "1", false, null)).toBe(true);
    expect(formatTyperResultLabel(match)).toBeNull();
  });

  it("does not lock on an unparseable game_date", () => {
    expect(isTyperDeadlinePassed("not-a-date", afterKickoff)).toBe(false);
  });
});

describe("pending match id set", () => {
  it("adds and removes ids independently", () => {
    const withFirst = addPendingMatchId(new Set(), 101);
    const withBoth = addPendingMatchId(withFirst, 202);
    expect(withBoth.has(101)).toBe(true);
    expect(withBoth.has(202)).toBe(true);
    const afterFirstDone = removePendingMatchId(withBoth, 101);
    expect(afterFirstDone.has(101)).toBe(false);
    expect(afterFirstDone.has(202)).toBe(true);
  });
});
