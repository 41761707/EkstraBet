import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/apiShared";
import { formatMatchDateTime } from "@/lib/format";
import {
  adminCandidateLoadErrorMessage,
  canPublishSelection,
  candidateOddsLabel,
  defaultSelectedMatchIds,
  formatAdminPredictionChangeLine,
  GROUP_STAGE_MATCH_COUNT,
  parseKnockoutRoundNumber,
  parseOptionalPositiveInt,
  publicationCounterLabel,
  selectKnockoutRounds,
  shouldApplyAdminLoad,
  toggleSelectedMatchId,
  tryBeginAdminMutation,
  typerAdminAuditErrorMessage,
  typerAdminPublicationErrorMessage,
} from "@/lib/typerLmAdmin";
import type { TyperAdminCandidate } from "@/types/api";

function sampleCandidate(
  overrides: Partial<TyperAdminCandidate> = {},
): TyperAdminCandidate {
  return {
    match_id: 101,
    season_id: 13,
    round_number: 1,
    game_date: "2026-09-16T21:00:00",
    home_team: { id: 1, name: "Home", shortcut: "HOM" },
    away_team: { id: 2, name: "Away", shortcut: "AWY" },
    is_published: false,
    has_complete_superbet_odds: false,
    ...overrides,
  };
}

function groupCandidates(count: number): TyperAdminCandidate[] {
  return Array.from({ length: count }, (_, index) =>
    sampleCandidate({ match_id: 101 + index }),
  );
}

describe("admin publication selection", () => {
  it("starts group-stage selection empty and knockout fully selected", () => {
    const unpublished = groupCandidates(4);
    expect(defaultSelectedMatchIds(unpublished, 1)).toEqual([]);
    expect(defaultSelectedMatchIds(unpublished, 900)).toEqual([
      101, 102, 103, 104,
    ]);
  });

  it("does not preselect already published knockout matches", () => {
    const candidates = [
      sampleCandidate({ match_id: 101, is_published: true }),
      sampleCandidate({ match_id: 102 }),
    ];
    expect(defaultSelectedMatchIds(candidates, 973)).toEqual([102]);
  });

  it("blocks an incomplete group-stage set even without odds", () => {
    const candidates = groupCandidates(9);
    expect(canPublishSelection(candidates, [101, 102], 1)).toBe(false);
    expect(
      canPublishSelection(
        candidates,
        candidates.map((row) => row.match_id),
        1,
      ),
    ).toBe(true);
  });

  it("requires remaining group-stage slots after a partial publication", () => {
    const candidates = [
      ...groupCandidates(5).map((row) => ({ ...row, is_published: true })),
      sampleCandidate({ match_id: 201 }),
      sampleCandidate({ match_id: 202 }),
      sampleCandidate({ match_id: 203 }),
      sampleCandidate({ match_id: 204 }),
    ];
    expect(canPublishSelection(candidates, [201, 202, 203], 1)).toBe(false);
    expect(
      canPublishSelection(candidates, [201, 202, 203, 204], 1),
    ).toBe(true);
  });

  it("requires every unpublished knockout match and ignores missing odds", () => {
    const candidates = [
      sampleCandidate({ match_id: 301, has_complete_superbet_odds: false }),
      sampleCandidate({ match_id: 302, has_complete_superbet_odds: false }),
    ];
    expect(canPublishSelection(candidates, [301], 900)).toBe(false);
    expect(canPublishSelection(candidates, [301, 302], 900)).toBe(true);
  });
});

describe("admin publication labels", () => {
  it("shows the 0/9 group-stage counter", () => {
    expect(publicationCounterLabel(groupCandidates(9), [], 1)).toBe(
      `0/${GROUP_STAGE_MATCH_COUNT}`,
    );
    expect(publicationCounterLabel(groupCandidates(9), [101, 102], 1)).toBe(
      "2/9",
    );
  });

  it("counts already published matches in the group-stage counter", () => {
    const candidates = [
      ...groupCandidates(5).map((row) => ({ ...row, is_published: true })),
      sampleCandidate({ match_id: 201 }),
      sampleCandidate({ match_id: 202 }),
      sampleCandidate({ match_id: 203 }),
      sampleCandidate({ match_id: 204 }),
    ];
    expect(publicationCounterLabel(candidates, [], 1)).toBe("5/9");
    expect(
      publicationCounterLabel(candidates, [201, 202, 203, 204], 1),
    ).toBe("9/9");
  });

  it("uses the configured group-stage limit from the API", () => {
    expect(publicationCounterLabel(groupCandidates(8), [], 1, 8)).toBe("0/8");
    expect(
      canPublishSelection(groupCandidates(8), [101, 102], 1, 8),
    ).toBe(false);
  });

  it("marks incomplete Superbet odds as informational", () => {
    expect(candidateOddsLabel(sampleCandidate())).toContain("nie blokuje");
    expect(
      candidateOddsLabel(
        sampleCandidate({ has_complete_superbet_odds: true }),
      ),
    ).toContain("kompletne");
  });
});

describe("admin form helpers", () => {
  it("toggles selected match ids", () => {
    expect(toggleSelectedMatchId([101], 102)).toEqual([101, 102]);
    expect(toggleSelectedMatchId([101, 102], 101)).toEqual([102]);
  });

  it("parses optional positive integers", () => {
    expect(parseOptionalPositiveInt("")).toBeUndefined();
    expect(parseOptionalPositiveInt(" 12 ")).toBe(12);
    expect(parseOptionalPositiveInt("0")).toBeUndefined();
  });

  it("accepts only knockout round numbers from 900", () => {
    expect(parseKnockoutRoundNumber("899")).toBeUndefined();
    expect(parseKnockoutRoundNumber("973")).toBe(973);
  });

  it("maps publication API errors without using audit 404 copy", () => {
    expect(
      typerAdminPublicationErrorMessage(new ApiError(422, "count")),
    ).toContain("9 meczów");
    expect(
      typerAdminPublicationErrorMessage(new ApiError(422, "count"), 8),
    ).toContain("8 meczów");
    expect(
      typerAdminPublicationErrorMessage(new ApiError(409, "conflict")),
    ).toContain("typy");
    expect(
      typerAdminPublicationErrorMessage(new ApiError(404, "User not found")),
    ).toContain("rundy");
    expect(typerAdminPublicationErrorMessage(new Error("nope"))).toContain(
      "ponownie",
    );
  });

  it("treats candidate-load 404 as an empty round, not an error banner", () => {
    expect(
      adminCandidateLoadErrorMessage(new ApiError(404, "missing")),
    ).toBeNull();
    expect(
      adminCandidateLoadErrorMessage(new ApiError(403, "forbidden")),
    ).toContain("uprawnień");
    expect(adminCandidateLoadErrorMessage(new Error("network"))).toContain(
      "ponownie",
    );
  });

  it("maps audit 404s to UUID, match and season copy", () => {
    expect(
      typerAdminAuditErrorMessage(new ApiError(404, "User not found")),
    ).toContain("UUID");
    expect(
      typerAdminAuditErrorMessage(
        new ApiError(404, "Published match not found"),
      ),
    ).toContain("meczu");
    expect(
      typerAdminAuditErrorMessage(new ApiError(404, "Season not found")),
    ).toContain("sezonu");
    expect(typerAdminAuditErrorMessage(new Error("nope"))).toContain("audytu");
  });

  it("rejects a second admin mutation while one is in flight", () => {
    const inFlight = { current: false };
    expect(tryBeginAdminMutation(inFlight)).toBe(true);
    expect(tryBeginAdminMutation(inFlight)).toBe(false);
    inFlight.current = false;
    expect(tryBeginAdminMutation(inFlight)).toBe(true);
  });

  it("formats an audit row with actor, match, transition and time", () => {
    const changedAt = "2026-09-11T18:30:00";
    const line = formatAdminPredictionChangeLine({
      match_id: 101,
      user_uuid: "user-2",
      display_name: "Bartek",
      previous_outcome: "1",
      new_outcome: "X",
      changed_at: changedAt,
    });
    expect(line).toContain("Bartek");
    expect(line).toContain("user-2");
    expect(line).toContain("mecz 101");
    expect(line).toContain("1 na X");
    expect(line).toContain(formatMatchDateTime(changedAt));
  });

  it("keeps knockout rounds with dictionary labels and drops group stage", () => {
    const knockout = selectKnockoutRounds([
      { round_number: 1, round_label: "1", game_date: "2026-09-16" },
      {
        round_number: 973,
        round_label: "1/8-FINAŁU",
        game_date: "2027-03-10",
      },
      {
        round_number: 972,
        round_label: "ĆWIERĆFINAŁ",
        game_date: "2027-04-14",
      },
    ]);
    expect(knockout.map((round) => round.round_number)).toEqual([973, 972]);
    expect(knockout[0]?.round_label).toBe("1/8-FINAŁU");
  });

  it("applies only the latest in-flight admin load", () => {
    expect(shouldApplyAdminLoad(1, 2)).toBe(false);
    expect(shouldApplyAdminLoad(2, 2)).toBe(true);
  });
});
