import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/apiShared";
import {
  applySavedLongTermPicks,
  applySettledLongTermResult,
  areTeamIdSetsEqual,
  canSaveLongTermPicks,
  canSettleLongTermSelection,
  classifyLongTermPick,
  countLongTermHits,
  defaultAdminResultIds,
  filterLongTermCandidates,
  formatAdminLongTermChangeLine,
  formatLongTermChangeLine,
  formatLongTermCompleteness,
  formatLongTermHitsLabel,
  formatLongTermPointsLabel,
  formatLongTermSelectionCounter,
  formatLongTermStandingLine,
  isLongTermMarketLockedForUi,
  lockLongTermMarket,
  longTermAdminAuditErrorMessage,
  longTermSaveErrorMessage,
  longTermSettleErrorMessage,
  scoreLongTerm,
  toggleLongTermTeamId,
} from "@/lib/typerLmLongTerm";
import type {
  LongTermAutoResultResponse,
  LongTermMarketCard,
  LongTermTeam,
} from "@/types/api";

function sampleTeam(
  teamId: number,
  overrides: Partial<LongTermTeam> = {},
): LongTermTeam {
  return {
    team_id: teamId,
    team_name: `Team ${teamId}`,
    team_shortcut: `T${teamId}`,
    ...overrides,
  };
}

function sampleMarket(
  overrides: Partial<LongTermMarketCard> = {},
): LongTermMarketCard {
  return {
    market_id: 1,
    league_id: 42,
    season_id: 13,
    market_key: "top8_direct_r16",
    title: "TOP 8",
    description: "Wskaż 8 drużyn",
    selection_size: 8,
    points_per_correct: 2,
    settled_at: null,
    deadline_at: "2026-09-16T21:00:00",
    is_locked: false,
    candidates: Array.from({ length: 36 }, (_, index) => sampleTeam(index + 1)),
    picked_team_ids: [],
    result_team_ids: [],
    points: null,
    changes: [],
    ...overrides,
  };
}

function sampleAutoResult(
  overrides: Partial<LongTermAutoResultResponse> = {},
): LongTermAutoResultResponse {
  return {
    market_id: 1,
    league_id: 42,
    season_id: 13,
    market_key: "top8_direct_r16",
    selection_size: 8,
    points_per_correct: 2,
    settled_at: null,
    settled_by_uuid: null,
    settled_by_display_name: null,
    is_complete: true,
    is_proposal: true,
    participant_count: 36,
    settled_match_count: 144,
    min_matches_per_team: 8,
    max_matches_per_team: 8,
    required_participant_count: 36,
    required_matches_per_team: 8,
    required_settled_match_count: 144,
    proposed_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
    proposed_teams: [],
    result_team_ids: [],
    standings: [],
    ...overrides,
  };
}

describe("formatLongTermSelectionCounter", () => {
  it("formats the live n/8 counter", () => {
    expect(formatLongTermSelectionCounter(0, 8)).toBe("0/8");
    expect(formatLongTermSelectionCounter(8, 8)).toBe("8/8");
  });
});

describe("filterLongTermCandidates", () => {
  it("matches name and shortcut regardless of case", () => {
    const teams = [
      sampleTeam(1, { team_name: "Bayern Monachium", team_shortcut: "BAY" }),
      sampleTeam(2, { team_name: "Arsenal", team_shortcut: "ARS" }),
    ];
    expect(filterLongTermCandidates(teams, "bay", "full")).toEqual([teams[0]]);
    expect(filterLongTermCandidates(teams, "ars", "shortcut")).toEqual([
      teams[1],
    ]);
  });
});

describe("toggleLongTermTeamId", () => {
  it("adds, removes and refuses a ninth team", () => {
    const eight = [1, 2, 3, 4, 5, 6, 7, 8];
    expect(toggleLongTermTeamId([], 4, 8)).toEqual([4]);
    expect(toggleLongTermTeamId([4], 4, 8)).toEqual([]);
    expect(toggleLongTermTeamId(eight, 9, 8)).toEqual(eight);
  });
});

describe("areTeamIdSetsEqual", () => {
  it("ignores pick order", () => {
    expect(areTeamIdSetsEqual([8, 1, 3], [1, 3, 8])).toBe(true);
    expect(areTeamIdSetsEqual([1, 2], [1, 3])).toBe(false);
  });
});

describe("long-term lock and save rules", () => {
  const afterKickoff = Date.parse("2026-09-16T19:00:00.000Z");

  it("locks from the server flag or the local Warsaw deadline", () => {
    expect(
      isLongTermMarketLockedForUi(sampleMarket({ is_locked: true })),
    ).toBe(true);
    expect(
      isLongTermMarketLockedForUi(sampleMarket(), afterKickoff),
    ).toBe(true);
    expect(isLongTermMarketLockedForUi(sampleMarket(), null)).toBe(false);
  });

  it("allows save only for a new complete set before the deadline", () => {
    const market = sampleMarket({ picked_team_ids: [1, 2, 3, 4, 5, 6, 7, 8] });
    expect(canSaveLongTermPicks(market, [1, 2, 3, 4, 5, 6, 7], false)).toBe(
      false,
    );
    expect(
      canSaveLongTermPicks(market, [8, 7, 6, 5, 4, 3, 2, 1], false),
    ).toBe(false);
    expect(
      canSaveLongTermPicks(market, [1, 2, 3, 4, 5, 6, 7, 9], false),
    ).toBe(true);
    expect(
      canSaveLongTermPicks(
        sampleMarket({ is_locked: true }),
        [1, 2, 3, 4, 5, 6, 7, 8],
        false,
      ),
    ).toBe(false);
  });

  it("locks the market card after a server 409", () => {
    const locked = lockLongTermMarket(sampleMarket({ is_locked: false }));
    expect(locked.is_locked).toBe(true);
    expect(
      canSaveLongTermPicks(locked, [1, 2, 3, 4, 5, 6, 7, 8], false),
    ).toBe(false);
  });
});

describe("scoring and pick classification", () => {
  it("scores hits times points_per_correct", () => {
    expect(countLongTermHits([1, 2, 3, 4, 5, 6, 7, 8], [1, 9, 3])).toBe(2);
    expect(scoreLongTerm([1, 2, 3, 4, 5, 6, 7, 8], [1, 9, 3], 2)).toBe(4);
    expect(classifyLongTermPick(1, [1, 2])).toBe("hit");
    expect(classifyLongTermPick(3, [1, 2])).toBe("miss");
    expect(classifyLongTermPick(1, [])).toBe("pending");
  });

  it("hides points until the market is settled", () => {
    const open = sampleMarket();
    expect(formatLongTermPointsLabel(open)).toBe(
      "Punkty po zatwierdzeniu admina",
    );
    expect(formatLongTermHitsLabel(open)).toBe("");
    const settled = sampleMarket({
      settled_at: "2027-01-30T12:00:00",
      picked_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      result_team_ids: [1, 2, 3, 4, 5, 6, 7, 9],
      points: 14,
    });
    expect(formatLongTermPointsLabel(settled)).toBe("14.00 pkt");
    expect(formatLongTermHitsLabel(settled)).toBe("7/8 trafień");
  });
});

describe("audit and apply helpers", () => {
  it("labels the first save and later replacements", () => {
    expect(
      formatLongTermChangeLine({
        id: 1,
        market_id: 1,
        user_uuid: "user-1",
        display_name: "Ala",
        previous_team_ids: null,
        new_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
        changed_at: "2026-09-11T18:30:00",
      }),
    ).toContain("pierwszy zapis");
    expect(
      formatLongTermChangeLine({
        id: 2,
        market_id: 1,
        user_uuid: "user-1",
        display_name: "Ala",
        previous_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
        new_team_ids: [1, 2, 3, 4, 5, 6, 7, 9],
        changed_at: "2026-09-11T19:30:00",
      }),
    ).toContain("zmiana zestawu");
  });

  it("applies a saved set and a settled result", () => {
    const market = sampleMarket({ picked_team_ids: [1, 2, 3, 4, 5, 6, 7, 8] });
    const saved = applySavedLongTermPicks(market, {
      market_id: 1,
      team_ids: [1, 2, 3, 4, 5, 6, 7, 9],
      previous_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      audit_written: true,
    });
    expect(saved.picked_team_ids).toEqual([1, 2, 3, 4, 5, 6, 7, 9]);
    const settled = applySettledLongTermResult(saved, {
      market_id: 1,
      team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      settled_by_uuid: "admin-1",
      settled_by_display_name: "Admin",
      settled_at: "2027-01-30T12:00:00",
      result_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
    });
    expect(settled.points).toBe(14);
    expect(settled.result_team_ids).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
  });
});

describe("admin proposal helpers", () => {
  it("prefers the approved result, then the proposal", () => {
    expect(defaultAdminResultIds(null)).toEqual([]);
    expect(defaultAdminResultIds(sampleAutoResult())).toEqual([
      1, 2, 3, 4, 5, 6, 7, 8,
    ]);
    expect(
      defaultAdminResultIds(
        sampleAutoResult({ result_team_ids: [9, 10, 11, 12, 13, 14, 15, 16] }),
      ),
    ).toEqual([9, 10, 11, 12, 13, 14, 15, 16]);
  });

  it("blocks settle until the phase is complete and 8 teams are selected", () => {
    expect(
      canSettleLongTermSelection(sampleAutoResult({ is_complete: false }), [
        1, 2, 3, 4, 5, 6, 7, 8,
      ]),
    ).toBe(false);
    expect(
      canSettleLongTermSelection(sampleAutoResult(), [1, 2, 3, 4, 5, 6, 7]),
    ).toBe(false);
    expect(
      canSettleLongTermSelection(sampleAutoResult(), [1, 2, 3, 4, 5, 6, 7, 8]),
    ).toBe(true);
  });

  it("explains incomplete completeness numbers", () => {
    expect(formatLongTermCompleteness(sampleAutoResult())).toContain(
      "propozycja",
    );
    expect(
      formatLongTermCompleteness(
        sampleAutoResult({
          is_complete: false,
          participant_count: 30,
          min_matches_per_team: 4,
          settled_match_count: 120,
        }),
      ),
    ).toContain("30/36");
    expect(
      formatLongTermStandingLine(
        {
          team_id: 1,
          team_name: "Bayern Monachium",
          team_shortcut: "BAY",
          played: 8,
          points: 18,
          goal_difference: 12,
          goals_for: 30,
        },
        "full",
      ),
    ).toBe("Bayern Monachium · 18 pkt · +12 · 30 bramek");
  });
});

describe("long-term API error messages", () => {
  it("maps save and settle status codes", () => {
    expect(longTermSaveErrorMessage(new ApiError(409, "locked"))).toContain(
      "rozpoczęła",
    );
    expect(longTermSaveErrorMessage(new ApiError(422, "size"))).toContain(
      "wymaganą liczbę",
    );
    expect(longTermSettleErrorMessage(new ApiError(409, "incomplete"))).toContain(
      "kompletna",
    );
    expect(longTermSettleErrorMessage(new Error("boom"))).toContain(
      "zatwierdzić",
    );
  });

  it("maps admin audit 404s and formats the actor line", () => {
    expect(
      longTermAdminAuditErrorMessage(new ApiError(404, "User not found")),
    ).toContain("UUID");
    expect(
      longTermAdminAuditErrorMessage(
        new ApiError(404, "Long-term market not found"),
      ),
    ).toContain("rynku");
    const line = formatAdminLongTermChangeLine({
      id: 11,
      market_id: 1,
      user_uuid: "user-2",
      display_name: "Bartek",
      previous_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      new_team_ids: [1, 2, 3, 4, 5, 6, 7, 9],
      changed_at: "2026-09-11T18:30:00",
    });
    expect(line).toContain("Bartek");
    expect(line).toContain("user-2");
    expect(line).toContain("rynek 1");
    expect(line).toContain("zmiana zestawu");
    expect(line).toContain("1,2,3,4,5,6,7,8 -> 1,2,3,4,5,6,7,9");
  });
});
