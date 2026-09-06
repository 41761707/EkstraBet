import { describe, expect, it } from "vitest";

import {
  areTeamIdSequencesEqual,
  classifyRankedPick,
  moveTeamInRanking,
  scoreZoneAndPosition,
  zoneForPosition,
} from "@/lib/typerLmLongTermRanking";

const TABLE_SIZE = 36;
const TOP_ZONE = 8;
const BOT_ZONE = 8;
const POINTS_ZONE = 2;
const POINTS_EXACT = 2;
const BARCELONA_ID = 6;
const PICK_FILLERS = Array.from({ length: TABLE_SIZE }, (_, index) => 201 + index);
const RESULT_FILLERS = Array.from(
  { length: TABLE_SIZE },
  (_, index) => 301 + index,
);

function tableWithTeamAt(
  fillers: readonly number[],
  teamId: number,
  position: number,
): number[] {
  const table = [...fillers];
  table[position - 1] = teamId;
  return table;
}

function scoreRanked(pickPosition: number, resultPosition: number): number {
  return scoreZoneAndPosition(
    tableWithTeamAt(PICK_FILLERS, BARCELONA_ID, pickPosition),
    tableWithTeamAt(RESULT_FILLERS, BARCELONA_ID, resultPosition),
    POINTS_ZONE,
    POINTS_EXACT,
    TOP_ZONE,
    BOT_ZONE,
  );
}

describe("zoneForPosition", () => {
  it("maps TOP 8, middle and BOT 8 slots", () => {
    expect(zoneForPosition(1, TABLE_SIZE, TOP_ZONE, BOT_ZONE)).toBe("top");
    expect(zoneForPosition(8, TABLE_SIZE, TOP_ZONE, BOT_ZONE)).toBe("top");
    expect(zoneForPosition(9, TABLE_SIZE, TOP_ZONE, BOT_ZONE)).toBe("middle");
    expect(zoneForPosition(28, TABLE_SIZE, TOP_ZONE, BOT_ZONE)).toBe("middle");
    expect(zoneForPosition(29, TABLE_SIZE, TOP_ZONE, BOT_ZONE)).toBe("bot");
    expect(zoneForPosition(36, TABLE_SIZE, TOP_ZONE, BOT_ZONE)).toBe("bot");
  });
});

describe("moveTeamInRanking", () => {
  it("reorders a tile without dropping the rest", () => {
    expect(moveTeamInRanking([1, 2, 3, 4], 0, 2)).toEqual([2, 3, 1, 4]);
    expect(moveTeamInRanking([1, 2, 3, 4], 3, 0)).toEqual([4, 1, 2, 3]);
    expect(moveTeamInRanking([1, 2, 3, 4], 1, 1)).toEqual([1, 2, 3, 4]);
  });

  it("returns a copy when the index is out of range", () => {
    const original = [1, 2, 3];
    expect(moveTeamInRanking(original, -1, 1)).toEqual(original);
    expect(moveTeamInRanking(original, 0, 9)).toEqual(original);
    expect(moveTeamInRanking(original, 0, 1)).not.toBe(original);
  });
});

describe("areTeamIdSequencesEqual", () => {
  it("treats order as part of the pick", () => {
    expect(areTeamIdSequencesEqual([8, 1, 3], [8, 1, 3])).toBe(true);
    expect(areTeamIdSequencesEqual([8, 1, 3], [1, 3, 8])).toBe(false);
    expect(areTeamIdSequencesEqual([1, 2], [1, 2, 3])).toBe(false);
  });
});

describe("scoreZoneAndPosition", () => {
  it("scores Barcelona 0 / zone / exact for official 13 / 2 / 6", () => {
    expect(scoreRanked(6, 13)).toBe(0);
    expect(scoreRanked(6, 2)).toBe(POINTS_ZONE);
    expect(scoreRanked(6, 6)).toBe(POINTS_ZONE + POINTS_EXACT);
  });

  it("scores BOT 8 the same way", () => {
    expect(scoreRanked(36, 20)).toBe(0);
    expect(scoreRanked(36, 30)).toBe(POINTS_ZONE);
    expect(scoreRanked(36, 36)).toBe(POINTS_ZONE + POINTS_EXACT);
  });

  it("does not score a middle pick even when the team finished in TOP 8", () => {
    expect(scoreRanked(9, 2)).toBe(0);
  });

  it("uses market rates instead of a hardcoded 2", () => {
    expect(
      scoreZoneAndPosition(
        tableWithTeamAt(PICK_FILLERS, BARCELONA_ID, 6),
        tableWithTeamAt(RESULT_FILLERS, BARCELONA_ID, 2),
        1.5,
        0.5,
        TOP_ZONE,
        BOT_ZONE,
      ),
    ).toBe(1.5);
    expect(
      scoreZoneAndPosition(
        tableWithTeamAt(PICK_FILLERS, BARCELONA_ID, 6),
        tableWithTeamAt(RESULT_FILLERS, BARCELONA_ID, 6),
        1.5,
        0.5,
        TOP_ZONE,
        BOT_ZONE,
      ),
    ).toBe(2);
  });
});

describe("classifyRankedPick", () => {
  const results = tableWithTeamAt(RESULT_FILLERS, BARCELONA_ID, 6);

  it("is pending before a result exists", () => {
    expect(
      classifyRankedPick(BARCELONA_ID, 6, [], TABLE_SIZE, TOP_ZONE, BOT_ZONE),
    ).toBe("pending");
  });

  it("labels miss, zone and exact after settlement", () => {
    expect(
      classifyRankedPick(
        BARCELONA_ID,
        6,
        tableWithTeamAt(RESULT_FILLERS, BARCELONA_ID, 13),
        TABLE_SIZE,
        TOP_ZONE,
        BOT_ZONE,
      ),
    ).toBe("miss");
    expect(
      classifyRankedPick(
        BARCELONA_ID,
        6,
        tableWithTeamAt(RESULT_FILLERS, BARCELONA_ID, 2),
        TABLE_SIZE,
        TOP_ZONE,
        BOT_ZONE,
      ),
    ).toBe("zone");
    expect(
      classifyRankedPick(
        BARCELONA_ID,
        6,
        results,
        TABLE_SIZE,
        TOP_ZONE,
        BOT_ZONE,
      ),
    ).toBe("exact");
  });

  it("labels a middle slot as a miss after settlement", () => {
    expect(
      classifyRankedPick(BARCELONA_ID, 9, results, TABLE_SIZE, TOP_ZONE, BOT_ZONE),
    ).toBe("miss");
  });
});
