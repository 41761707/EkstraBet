import { describe, expect, it } from "vitest";

import {
  canSaveLongTermExactPicks,
  classifyExactSubjectPick,
  classifyFreeTextPick,
  normalizeSubjectText,
  scoreExactSubject,
  SUBJECT_TEXT_MAX_LENGTH,
} from "@/lib/typerLmLongTermExact";
import type { LongTermMarketCard, LongTermTeam } from "@/types/api";

function sampleTeam(teamId: number): LongTermTeam {
  return {
    team_id: teamId,
    team_name: `Team ${teamId}`,
    team_shortcut: `T${teamId}`,
  };
}

function sampleExactMarket(
  overrides: Partial<LongTermMarketCard> = {},
): LongTermMarketCard {
  return {
    market_id: 2,
    league_id: 42,
    season_id: 13,
    market_key: "top_scorer",
    title: "Najlepszy strzelec",
    description: null,
    selection_size: 1,
    points_per_correct: 2,
    points_per_exact_position: 0,
    market_kind: "free_text",
    scoring_kind: "exact_subject",
    top_zone_size: -1,
    bot_zone_size: -1,
    settled_at: null,
    deadline_at: "2026-09-16T21:00:00",
    is_locked: false,
    candidates: [],
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

describe("normalizeSubjectText", () => {
  it("trims, collapses spaces and lowercases", () => {
    expect(normalizeSubjectText("  Robert   Lewandowski ")).toBe(
      "robert lewandowski",
    );
    expect(normalizeSubjectText("LEWANDOWSKI")).toBe("lewandowski");
  });

  it("treats whitespace-only input as empty", () => {
    expect(normalizeSubjectText("   ")).toBe("");
  });
});

describe("scoreExactSubject and classifyExactSubjectPick", () => {
  it("scores a hit as points_per_correct and a miss as 0", () => {
    expect(
      scoreExactSubject(["robert lewandowski"], ["robert lewandowski"], 2),
    ).toBe(2);
    expect(
      scoreExactSubject(["lewandowski"], ["robert lewandowski"], 2),
    ).toBe(0);
  });

  it("scores a remis when the pick is one of two results", () => {
    expect(
      scoreExactSubject(
        ["robert lewandowski"],
        ["harry kane", "robert lewandowski"],
        2,
      ),
    ).toBe(2);
    expect(scoreExactSubject([6], [6, 9], 2)).toBe(2);
    expect(
      classifyExactSubjectPick("robert lewandowski", [
        "harry kane",
        "robert lewandowski",
      ]),
    ).toBe("hit");
  });

  it("labels pending, hit and miss on already-normalized values", () => {
    expect(classifyExactSubjectPick("x", [])).toBe("pending");
    expect(classifyExactSubjectPick("x", ["x"])).toBe("hit");
    expect(classifyExactSubjectPick("x", ["y"])).toBe("miss");
    expect(classifyExactSubjectPick(true, [false])).toBe("miss");
    expect(classifyExactSubjectPick(false, [false])).toBe("hit");
    expect(
      classifyExactSubjectPick("Robert Lewandowski", ["robert lewandowski"]),
    ).toBe("miss");
  });
});

describe("classifyFreeTextPick", () => {
  it("normalizes both sides before comparing", () => {
    expect(
      classifyFreeTextPick("  Robert   Lewandowski ", ["Robert Lewandowski"]),
    ).toBe("hit");
    expect(
      classifyFreeTextPick("Lewandowski", ["Robert Lewandowski"]),
    ).toBe("miss");
    expect(
      classifyFreeTextPick("Robert Lewandowski", [
        "Harry Kane",
        "robert lewandowski",
      ]),
    ).toBe("hit");
  });
});

describe("canSaveLongTermExactPicks", () => {
  const afterKickoff = Date.parse("2026-09-16T19:00:00.000Z");

  it("requires a non-empty normalized free-text pick different from saved", () => {
    const market = sampleExactMarket({
      picked_subject_text: "Robert Lewandowski",
    });
    expect(
      canSaveLongTermExactPicks(market, { subjectText: "   " }, false),
    ).toBe(false);
    expect(
      canSaveLongTermExactPicks(
        market,
        { subjectText: "  Robert   Lewandowski " },
        false,
      ),
    ).toBe(false);
    expect(
      canSaveLongTermExactPicks(market, { subjectText: "Harry Kane" }, false),
    ).toBe(true);
  });

  it("rejects free-text longer than 160 stripped or normalized characters", () => {
    const market = sampleExactMarket();
    const tooLong = "a".repeat(SUBJECT_TEXT_MAX_LENGTH + 1);
    const atLimit = "a".repeat(SUBJECT_TEXT_MAX_LENGTH);
    expect(
      canSaveLongTermExactPicks(market, { subjectText: tooLong }, false),
    ).toBe(false);
    expect(
      canSaveLongTermExactPicks(market, { subjectText: atLimit }, false),
    ).toBe(true);
  });

  it("requires a yes_no choice different from the saved flag", () => {
    const market = sampleExactMarket({
      market_key: "any_team_win_all",
      market_kind: "yes_no",
    });
    expect(canSaveLongTermExactPicks(market, {}, false)).toBe(false);
    expect(
      canSaveLongTermExactPicks(market, { isTextCorrect: true }, false),
    ).toBe(true);
    expect(
      canSaveLongTermExactPicks(
        sampleExactMarket({
          market_kind: "yes_no",
          picked_is_text_correct: false,
        }),
        { isTextCorrect: false },
        false,
      ),
    ).toBe(false);
  });

  it("requires exactly one new single_team id", () => {
    const market = sampleExactMarket({
      market_key: "most_goals_scored",
      market_kind: "single_team",
      candidates: [sampleTeam(1), sampleTeam(2)],
      picked_team_ids: [1],
    });
    expect(canSaveLongTermExactPicks(market, { teamIds: [] }, false)).toBe(
      false,
    );
    expect(canSaveLongTermExactPicks(market, { teamIds: [1, 2] }, false)).toBe(
      false,
    );
    expect(canSaveLongTermExactPicks(market, { teamIds: [1] }, false)).toBe(
      false,
    );
    expect(canSaveLongTermExactPicks(market, { teamIds: [2] }, false)).toBe(
      true,
    );
  });

  it("blocks save when locked or pending", () => {
    const draft = { subjectText: "Harry Kane" };
    expect(
      canSaveLongTermExactPicks(
        sampleExactMarket({ is_locked: true }),
        draft,
        false,
      ),
    ).toBe(false);
    expect(
      canSaveLongTermExactPicks(sampleExactMarket(), draft, true),
    ).toBe(false);
    expect(
      canSaveLongTermExactPicks(sampleExactMarket(), draft, false, afterKickoff),
    ).toBe(false);
  });
});
