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
  displayedRankedTeamIds,
  filterLongTermCandidates,
  formatAdminLongTermChangeLine,
  formatLongTermChangeLine,
  formatLongTermCompleteness,
  formatLongTermHitsLabel,
  formatLongTermPointsLabel,
  formatLongTermSelectionCounter,
  formatLongTermStandingLine,
  formatLongTermStandingStats,
  isLongTermMarketLockedForUi,
  isLongTermMarketSettled,
  lockLongTermMarket,
  longTermAdminAuditErrorMessage,
  longTermSaveErrorMessage,
  longTermSettleErrorMessage,
  longTermUnsavedPickStatus,
  scoreLongTerm,
  toggleLongTermTeamId,
  updateLongTermDashboardMarket,
} from "@/lib/typerLmLongTerm";
import type {
  LongTermAutoResultResponse,
  LongTermMarketCard,
  LongTermPickChange,
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
    market_key: "league_phase_table",
    title: "Tabela fazy ligowej",
    description: "Z 36 drużyn wybierz te, które zajmą miejsca 1–8 oraz 29–36 w fazie ligowej",
    selection_size: 8,
    points_per_correct: 2,
    points_per_exact_position: 2,
    market_kind: "ranked_team_table",
    scoring_kind: "zone_and_position",
    top_zone_size: 8,
    bot_zone_size: 8,
    settled_at: null,
    deadline_at: "2026-09-16T21:00:00",
    is_locked: false,
    candidates: Array.from({ length: 36 }, (_, index) => sampleTeam(index + 1)),
    picked_team_ids: [],
    result_team_ids: [],
    picked_subject_text: null,
    result_subject_texts: [],
    picked_is_text_correct: null,
    result_is_text_correct: null,
    points: null,
    changes: [],
    ...overrides,
  };
}

function sampleChange(
  overrides: Partial<LongTermPickChange> = {},
): LongTermPickChange {
  return {
    id: 1,
    market_id: 1,
    user_uuid: "user-1",
    display_name: "Ala",
    previous_team_ids: null,
    new_team_ids: [],
    previous_subject_text: null,
    new_subject_text: null,
    previous_is_text_correct: null,
    new_is_text_correct: null,
    changed_at: "2026-09-11T18:30:00",
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
    market_key: "league_phase_table",
    selection_size: 8,
    points_per_correct: 2,
    points_per_exact_position: 2,
    top_zone_size: 8,
    bot_zone_size: 8,
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
    proposed_top_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
    proposed_bot_team_ids: [],
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

  it("allows save only for a new complete sequence before the deadline", () => {
    const market = sampleMarket({ picked_team_ids: [1, 2, 3, 4, 5, 6, 7, 8] });
    expect(canSaveLongTermPicks(market, [1, 2, 3, 4, 5, 6, 7], false)).toBe(
      false,
    );
    expect(
      canSaveLongTermPicks(market, [1, 2, 3, 4, 5, 6, 7, 8], false),
    ).toBe(false);
    expect(
      canSaveLongTermPicks(market, [8, 7, 6, 5, 4, 3, 2, 1], false),
    ).toBe(true);
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

  it("shows the saved ranking after lock or settle, not a local draft", () => {
    const saved = [1, 2, 3, 4, 5, 6, 7, 8];
    const draft = [8, 7, 6, 5, 4, 3, 2, 1];
    const market = sampleMarket({ picked_team_ids: saved });
    expect(displayedRankedTeamIds(market, draft, false)).toEqual(draft);
    expect(displayedRankedTeamIds(market, draft, true)).toEqual(saved);
    expect(
      displayedRankedTeamIds(
        sampleMarket({ picked_team_ids: [] }),
        draft,
        true,
      ),
    ).toEqual(sampleMarket().candidates.map((team) => team.team_id));
  });

  it("shows the official table after settle when no pick was saved", () => {
    const result = [8, 7, 6, 5, 4, 3, 2, 1];
    const draft = [1, 2, 3, 4, 5, 6, 7, 8];
    const market = sampleMarket({
      picked_team_ids: [],
      settled_at: "2027-01-30T12:00:00",
      result_team_ids: result,
    });
    expect(displayedRankedTeamIds(market, draft, true)).toEqual(result);
  });

  it("labels a locked market without a saved pick", () => {
    const open = sampleMarket({ picked_team_ids: [] });
    const locked = sampleMarket({ picked_team_ids: [], is_locked: true });
    const saved = sampleMarket({
      picked_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      is_locked: true,
    });
    expect(longTermUnsavedPickStatus(open, false)).toBeNull();
    expect(longTermUnsavedPickStatus(locked, true)).toBe("Nie zapisano typu");
    expect(longTermUnsavedPickStatus(saved, true)).toBeNull();
  });

  it("labels locked exact-subject cards from the matching pick field", () => {
    const textLocked = sampleMarket({
      market_kind: "free_text",
      selection_size: 1,
      picked_subject_text: null,
    });
    const textSaved = sampleMarket({
      market_kind: "free_text",
      selection_size: 1,
      picked_subject_text: "Harry Kane",
    });
    const yesNoLocked = sampleMarket({
      market_kind: "yes_no",
      selection_size: 1,
      picked_is_text_correct: null,
    });
    const yesNoSavedNo = sampleMarket({
      market_kind: "yes_no",
      selection_size: 1,
      picked_is_text_correct: false,
    });
    const singleLocked = sampleMarket({
      market_kind: "single_team",
      selection_size: 1,
      picked_team_ids: [],
    });
    const singleSaved = sampleMarket({
      market_kind: "single_team",
      selection_size: 1,
      picked_team_ids: [6],
    });
    expect(longTermUnsavedPickStatus(textLocked, true)).toBe(
      "Nie zapisano typu",
    );
    expect(longTermUnsavedPickStatus(textSaved, true)).toBeNull();
    expect(longTermUnsavedPickStatus(yesNoLocked, true)).toBe(
      "Nie zapisano typu",
    );
    expect(longTermUnsavedPickStatus(yesNoSavedNo, true)).toBeNull();
    expect(longTermUnsavedPickStatus(singleLocked, true)).toBe(
      "Nie zapisano typu",
    );
    expect(longTermUnsavedPickStatus(singleSaved, true)).toBeNull();
  });

  it("keeps sibling market picks when two updaters run in sequence", () => {
    const dashboard = {
      season_id: 13,
      markets: [
        sampleMarket({ market_id: 1, picked_team_ids: [] }),
        sampleMarket({
          market_id: 2,
          market_kind: "free_text",
          selection_size: 1,
          picked_subject_text: null,
          picked_team_ids: [],
        }),
      ],
    };
    const afterFirst = updateLongTermDashboardMarket(
      dashboard,
      1,
      (market) => ({ ...market, picked_team_ids: [1, 2, 3, 4, 5, 6, 7, 8] }),
    );
    const afterBoth = updateLongTermDashboardMarket(
      afterFirst,
      2,
      (market) => ({ ...market, picked_subject_text: "Harry Kane" }),
    );
    expect(afterBoth.markets[0]?.picked_team_ids).toEqual([
      1, 2, 3, 4, 5, 6, 7, 8,
    ]);
    expect(afterBoth.markets[1]?.picked_subject_text).toBe("Harry Kane");
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
      formatLongTermChangeLine(
        sampleChange({
          new_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
        }),
      ),
    ).toContain("pierwszy zapis");
    expect(
      formatLongTermChangeLine(
        sampleChange({
          id: 2,
          previous_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
          new_team_ids: [1, 2, 3, 4, 5, 6, 7, 9],
          changed_at: "2026-09-11T19:30:00",
        }),
      ),
    ).toContain("zmiana zestawu");
  });

  it("does not treat a later free-text or yes_no edit as a first save", () => {
    expect(
      formatLongTermChangeLine(
        sampleChange({
          new_subject_text: "Lewandowski",
        }),
      ),
    ).toContain("pierwszy zapis");
    expect(
      formatLongTermChangeLine(
        sampleChange({
          previous_subject_text: "Lewandowski",
          new_subject_text: "Harry Kane",
        }),
      ),
    ).toContain("zmiana wpisu");
    expect(
      formatLongTermChangeLine(
        sampleChange({
          previous_subject_text: "Lewandowski",
          new_subject_text: "Harry Kane",
        }),
      ),
    ).not.toContain("pierwszy zapis");
    expect(
      formatLongTermChangeLine(
        sampleChange({
          previous_is_text_correct: false,
          new_is_text_correct: true,
        }),
      ),
    ).toContain("zmiana TAK/NIE");
    expect(
      formatLongTermChangeLine(
        sampleChange({
          previous_is_text_correct: false,
          new_is_text_correct: true,
        }),
      ),
    ).not.toContain("pierwszy zapis");
  });

  it("applies a saved sequence and zone-and-position points", () => {
    const pickFillers = Array.from({ length: 36 }, (_, index) => 201 + index);
    const resultFillers = Array.from({ length: 36 }, (_, index) => 301 + index);
    const picks = [...pickFillers];
    picks[5] = 6;
    const results = [...resultFillers];
    results[5] = 6;
    const market = sampleMarket({
      selection_size: 36,
      picked_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
    });
    const saved = applySavedLongTermPicks(market, {
      market_id: 1,
      team_ids: picks,
      previous_team_ids: [1, 2, 3, 4, 5, 6, 7, 8],
      subject_texts: [],
      previous_subject_text: null,
      is_text_correct: null,
      previous_is_text_correct: null,
      audit_written: true,
    });
    expect(saved.picked_team_ids).toEqual(picks);
    const settled = applySettledLongTermResult(saved, {
      market_id: 1,
      team_ids: results,
      subject_texts: [],
      is_text_correct: null,
      settled_by_uuid: "admin-1",
      settled_by_display_name: "Admin",
      settled_at: "2027-01-30T12:00:00",
      result_team_ids: results,
    });
    expect(settled.points).toBe(4);
    expect(settled.result_team_ids).toEqual(results);
  });

  it("applies exact_subject points for a tied free-text result set", () => {
    const market = sampleMarket({
      market_key: "top_scorer",
      market_kind: "free_text",
      scoring_kind: "exact_subject",
      selection_size: 1,
      points_per_exact_position: 0,
      top_zone_size: -1,
      bot_zone_size: -1,
      picked_subject_text: "  Robert   Lewandowski ",
      candidates: [],
    });
    const saved = applySavedLongTermPicks(market, {
      market_id: 1,
      team_ids: [],
      previous_team_ids: null,
      subject_texts: ["  Robert   Lewandowski "],
      previous_subject_text: null,
      is_text_correct: null,
      previous_is_text_correct: null,
      audit_written: true,
    });
    expect(saved.picked_subject_text).toBe("  Robert   Lewandowski ");
    const settled = applySettledLongTermResult(saved, {
      market_id: 1,
      team_ids: [],
      subject_texts: ["Robert Lewandowski", "Harry Kane"],
      is_text_correct: null,
      settled_by_uuid: "admin-1",
      settled_by_display_name: "Admin",
      settled_at: "2027-01-30T12:00:00",
      result_team_ids: [],
    });
    expect(settled.points).toBe(2);
    expect(settled.result_subject_texts).toEqual([
      "Robert Lewandowski",
      "Harry Kane",
    ]);
    expect(isLongTermMarketSettled(settled)).toBe(true);
  });

  it("applies exact_subject points for yes_no and single_team remis", () => {
    const yesNo = applySettledLongTermResult(
      sampleMarket({
        market_kind: "yes_no",
        scoring_kind: "exact_subject",
        picked_is_text_correct: false,
        candidates: [],
      }),
      {
        market_id: 1,
        team_ids: [],
        subject_texts: [],
        is_text_correct: false,
        settled_by_uuid: "admin-1",
        settled_by_display_name: "Admin",
        settled_at: "2027-01-30T12:00:00",
        result_team_ids: [],
      },
    );
    expect(yesNo.points).toBe(2);
    expect(isLongTermMarketSettled(yesNo)).toBe(true);

    const singleTeam = applySettledLongTermResult(
      sampleMarket({
        market_kind: "single_team",
        scoring_kind: "exact_subject",
        selection_size: 1,
        picked_team_ids: [6],
      }),
      {
        market_id: 1,
        team_ids: [6, 9],
        subject_texts: [],
        is_text_correct: null,
        settled_by_uuid: "admin-1",
        settled_by_display_name: "Admin",
        settled_at: "2027-01-30T12:00:00",
        result_team_ids: [6, 9],
      },
    );
    expect(singleTeam.points).toBe(2);
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
      formatLongTermStandingStats({
        team_id: 1,
        team_name: "Bayern Monachium",
        team_shortcut: "BAY",
        played: 8,
        points: 18,
        goal_difference: 12,
        goals_for: 30,
      }),
    ).toBe("18 pkt · +12 · 30 bramek");
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
    expect(
      longTermSaveErrorMessage(new ApiError(422, "text"), "free_text"),
    ).toContain("imię i nazwisko");
    expect(
      longTermSaveErrorMessage(new ApiError(422, "flag"), "yes_no"),
    ).toContain("TAK albo NIE");
    expect(
      longTermSaveErrorMessage(new ApiError(422, "team"), "single_team"),
    ).toContain("jedną drużynę");
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
      previous_subject_text: null,
      new_subject_text: null,
      previous_is_text_correct: null,
      new_is_text_correct: null,
      changed_at: "2026-09-11T18:30:00",
    });
    expect(line).toContain("Bartek");
    expect(line).toContain("user-2");
    expect(line).toContain("rynek 1");
    expect(line).toContain("zmiana zestawu");
    expect(line).toContain("1,2,3,4,5,6,7,8 -> 1,2,3,4,5,6,7,9");
    expect(
      formatAdminLongTermChangeLine(
        sampleChange({
          user_uuid: "user-2",
          display_name: "Bartek",
          previous_subject_text: "Lewandowski",
          new_subject_text: "Harry Kane",
        }),
      ),
    ).toContain("zmiana wpisu (Lewandowski -> Harry Kane)");
  });
});
