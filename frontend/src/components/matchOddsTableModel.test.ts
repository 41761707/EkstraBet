import { describe, expect, it } from "vitest";

import {
  buildUstaloneMarketPredictions,
  isMissingOddsValue,
  nextOddsSortState,
  ODDS_MARKET_EVENT_IDS,
  ODDS_SORT_BOOKMAKER_KEY,
  resolveOddsSortValue,
  sortOddsRows,
  type OddsColumn,
} from "@/components/matchOddsTableModel";
import type {
  MatchPredictionItem,
  PredictionPreviewResponse,
} from "@/types/api";

const HOME_COLUMN: OddsColumn = {
  key: "home",
  label: "Gospodarz",
  eventId: 1,
};

const COLUMNS: readonly OddsColumn[] = [HOME_COLUMN];

function makePrediction(
  eventId: number,
  value: number | null,
): MatchPredictionItem {
  return {
    prediction_id: 1,
    event_id: eventId,
    event_name: "1",
    event_family: null,
    model_id: 1,
    model_name: null,
    value,
    outcome: null,
  };
}

function makeAnalysis(
  overrides: Partial<{
    p_home: number;
    p_draw: number;
    p_away: number;
    p_yes: number;
    p_no: number;
    over_25: number;
    under_25: number;
  }> = {},
): PredictionPreviewResponse {
  return {
    result: {
      p_home: overrides.p_home ?? 0.3,
      p_draw: overrides.p_draw ?? 0.3,
      p_away: overrides.p_away ?? 0.4,
    },
    btts: {
      p_yes: overrides.p_yes ?? 0.45,
      p_no: overrides.p_no ?? 0.55,
    },
    goals: {
      lambda_home: 0,
      lambda_away: 0,
      total_buckets: {},
      over_25: overrides.over_25 ?? 0.35,
      under_25: overrides.under_25 ?? 0.65,
      top_exact_scores: [],
    },
  };
}

describe("buildUstaloneMarketPredictions", () => {
  it("maps all market outcomes from prediction_analysis", () => {
    const analysis = makeAnalysis({
      p_home: 0.25,
      p_draw: 0.35,
      p_away: 0.4,
      p_yes: 0.48,
      p_no: 0.52,
      over_25: 0.41,
      under_25: 0.59,
    });

    expect(buildUstaloneMarketPredictions(analysis)).toEqual([
      { event_id: ODDS_MARKET_EVENT_IDS.home, value: 0.25 },
      { event_id: ODDS_MARKET_EVENT_IDS.draw, value: 0.35 },
      { event_id: ODDS_MARKET_EVENT_IDS.away, value: 0.4 },
      { event_id: ODDS_MARKET_EVENT_IDS.bttsYes, value: 0.48 },
      { event_id: ODDS_MARKET_EVENT_IDS.bttsNo, value: 0.52 },
      { event_id: ODDS_MARKET_EVENT_IDS.over, value: 0.41 },
      { event_id: ODDS_MARKET_EVENT_IDS.under, value: 0.59 },
    ]);
  });

  it("falls back to final predictions when analysis is null", () => {
    const fallback = [makePrediction(3, 0.4), makePrediction(12, 0.62)];
    expect(buildUstaloneMarketPredictions(null, fallback)).toEqual([
      { event_id: 3, value: 0.4 },
      { event_id: 12, value: 0.62 },
    ]);
  });

  it("prefers analysis over favorite-only final predictions", () => {
    const analysis = makeAnalysis({ p_away: 0.4, under_25: 0.62 });
    const favoritesOnly = [makePrediction(3, 0.4)];
    const result = buildUstaloneMarketPredictions(analysis, favoritesOnly);

    expect(result).toHaveLength(7);
    expect(
      resolveOddsSortValue("USTALONE", ODDS_MARKET_EVENT_IDS.home, new Map(), result),
    ).toBe(Number((1 / 0.3).toFixed(2)));
    expect(
      resolveOddsSortValue("USTALONE", ODDS_MARKET_EVENT_IDS.away, new Map(), result),
    ).toBe(2.5);
    expect(
      resolveOddsSortValue("USTALONE", ODDS_MARKET_EVENT_IDS.over, new Map(), result),
    ).toBe(Number((1 / 0.35).toFixed(2)));
  });
});

describe("nextOddsSortState", () => {
  it("starts odds column with desc when current is null", () => {
    expect(nextOddsSortState(null, "home")).toEqual({
      key: "home",
      direction: "desc",
    });
  });

  it("starts bookmaker column with asc when current is null", () => {
    expect(nextOddsSortState(null, ODDS_SORT_BOOKMAKER_KEY)).toEqual({
      key: ODDS_SORT_BOOKMAKER_KEY,
      direction: "asc",
    });
  });

  it("toggles direction on the same column", () => {
    const afterDesc = nextOddsSortState(
      { key: "home", direction: "desc" },
      "home",
    );
    expect(afterDesc).toEqual({ key: "home", direction: "asc" });

    const afterAsc = nextOddsSortState(afterDesc, "home");
    expect(afterAsc).toEqual({ key: "home", direction: "desc" });
  });

  it("uses default direction when switching column", () => {
    expect(
      nextOddsSortState({ key: "home", direction: "asc" }, "draw"),
    ).toEqual({ key: "draw", direction: "desc" });

    expect(
      nextOddsSortState(
        { key: "home", direction: "desc" },
        ODDS_SORT_BOOKMAKER_KEY,
      ),
    ).toEqual({ key: ODDS_SORT_BOOKMAKER_KEY, direction: "asc" });
  });

  it("does not mutate current state", () => {
    const current = { key: "home", direction: "desc" as const };
    const snapshot = { ...current };
    nextOddsSortState(current, "home");
    expect(current).toEqual(snapshot);
  });
});

describe("isMissingOddsValue", () => {
  it("treats null, undefined and non-positive as missing", () => {
    expect(isMissingOddsValue(null)).toBe(true);
    expect(isMissingOddsValue(undefined)).toBe(true);
    expect(isMissingOddsValue(0)).toBe(true);
    expect(isMissingOddsValue(-1)).toBe(true);
    expect(isMissingOddsValue(1.5)).toBe(false);
  });
});

describe("resolveOddsSortValue", () => {
  it("reads bookmaker odds from lookup", () => {
    const lookup = new Map<string, number>([["Superbet:1", 2.4]]);
    expect(resolveOddsSortValue("Superbet", 1, lookup, [])).toBe(2.4);
  });

  it("returns null for missing lookup key or non-positive odds", () => {
    const lookup = new Map<string, number>([
      ["Superbet:1", 0],
      ["Fortuna:1", -0.5],
    ]);
    expect(resolveOddsSortValue("Betclic", 1, lookup, [])).toBeNull();
    expect(resolveOddsSortValue("Superbet", 1, lookup, [])).toBeNull();
    expect(resolveOddsSortValue("Fortuna", 1, lookup, [])).toBeNull();
  });

  it("computes USTALONE odds as 1 / value rounded to 2 decimals", () => {
    const predictions = [makePrediction(1, 0.5)];
    expect(resolveOddsSortValue("USTALONE", 1, new Map(), predictions)).toBe(
      2,
    );

    const rounded = [makePrediction(1, 0.333)];
    expect(resolveOddsSortValue("USTALONE", 1, new Map(), rounded)).toBe(
      Number((1 / 0.333).toFixed(2)),
    );
  });

  it("returns null for USTALONE without prediction or non-positive value", () => {
    expect(resolveOddsSortValue("USTALONE", 1, new Map(), [])).toBeNull();
    expect(
      resolveOddsSortValue("USTALONE", 1, new Map(), [makePrediction(1, null)]),
    ).toBeNull();
    expect(
      resolveOddsSortValue("USTALONE", 1, new Map(), [makePrediction(1, 0)]),
    ).toBeNull();
    expect(
      resolveOddsSortValue("USTALONE", 1, new Map(), [makePrediction(1, -0.2)]),
    ).toBeNull();
  });
});

describe("sortOddsRows", () => {
  const rows = ["USTALONE", "Superbet", "Betclic", "Fortuna"] as const;

  it("sorts by bookmaker name with pl localeCompare asc and desc", () => {
    const asc = sortOddsRows(
      rows,
      { key: ODDS_SORT_BOOKMAKER_KEY, direction: "asc" },
      COLUMNS,
      new Map(),
      [],
    );
    expect(asc).toEqual(
      [...rows].sort((left, right) => left.localeCompare(right, "pl")),
    );

    const desc = sortOddsRows(
      rows,
      { key: ODDS_SORT_BOOKMAKER_KEY, direction: "desc" },
      COLUMNS,
      new Map(),
      [],
    );
    expect(desc).toEqual(
      [...rows].sort((left, right) => right.localeCompare(left, "pl")),
    );
  });

  it("sorts odds descending with highest first and USTALONE by computed odds", () => {
    const lookup = new Map<string, number>([
      ["Superbet:1", 3.1],
      ["Betclic:1", 2.5],
      ["Fortuna:1", 1.8],
    ]);
    const predictions = [makePrediction(1, 0.5)]; // USTALONE -> 2.00

    const sorted = sortOddsRows(
      rows,
      { key: "home", direction: "desc" },
      COLUMNS,
      lookup,
      predictions,
    );
    expect(sorted).toEqual(["Superbet", "Betclic", "USTALONE", "Fortuna"]);
  });

  it("sorts odds ascending with lowest first", () => {
    const lookup = new Map<string, number>([
      ["Superbet:1", 3.1],
      ["Betclic:1", 2.5],
      ["Fortuna:1", 1.8],
    ]);
    const predictions = [makePrediction(1, 0.5)]; // USTALONE -> 2.00

    const sorted = sortOddsRows(
      rows,
      { key: "home", direction: "asc" },
      COLUMNS,
      lookup,
      predictions,
    );
    expect(sorted).toEqual(["Fortuna", "USTALONE", "Betclic", "Superbet"]);
  });

  it("keeps missing, zero and non-positive odds at the end for both directions", () => {
    const lookup = new Map<string, number>([
      ["Superbet:1", 2.2],
      ["Betclic:1", 0],
      ["Fortuna:1", -1],
    ]);
    // USTALONE bez predykcji = missing

    const desc = sortOddsRows(
      rows,
      { key: "home", direction: "desc" },
      COLUMNS,
      lookup,
      [],
    );
    expect(desc[0]).toBe("Superbet");
    expect(desc.slice(1)).toEqual(["USTALONE", "Betclic", "Fortuna"]);

    const asc = sortOddsRows(
      rows,
      { key: "home", direction: "asc" },
      COLUMNS,
      lookup,
      [],
    );
    expect(asc[0]).toBe("Superbet");
    expect(asc.slice(1)).toEqual(["USTALONE", "Betclic", "Fortuna"]);
  });

  it("places USTALONE at the end when prediction is missing", () => {
    const lookup = new Map<string, number>([
      ["Superbet:1", 2.2],
      ["Betclic:1", 1.9],
      ["Fortuna:1", 1.7],
    ]);

    const sorted = sortOddsRows(
      rows,
      { key: "home", direction: "desc" },
      COLUMNS,
      lookup,
      [],
    );
    expect(sorted[sorted.length - 1]).toBe("USTALONE");
  });

  it("keeps input order when every odds value is missing", () => {
    const input = ["USTALONE", "Superbet", "Betclic", "Fortuna"];
    const lookup = new Map<string, number>([
      ["Superbet:1", 0],
      ["Betclic:1", -2],
    ]);

    const desc = sortOddsRows(
      input,
      { key: "home", direction: "desc" },
      COLUMNS,
      lookup,
      [],
    );
    const asc = sortOddsRows(
      input,
      { key: "home", direction: "asc" },
      COLUMNS,
      lookup,
      [],
    );
    expect(desc).toEqual(input);
    expect(asc).toEqual(input);
  });

  it("keeps input order on equal bookmaker names", () => {
    const input = ["Alpha", "Alpha", "Beta"];
    const sorted = sortOddsRows(
      input,
      { key: ODDS_SORT_BOOKMAKER_KEY, direction: "asc" },
      COLUMNS,
      new Map(),
      [],
    );
    expect(sorted).toEqual(input);
  });

  it("keeps input order on equal odds (stable tie-break)", () => {
    const lookup = new Map<string, number>([
      ["Superbet:1", 2.0],
      ["Betclic:1", 2.0],
      ["Fortuna:1", 2.0],
    ]);
    const predictions = [makePrediction(1, 0.5)]; // USTALONE -> 2.00
    const input = ["USTALONE", "Superbet", "Betclic", "Fortuna"];

    const sorted = sortOddsRows(
      input,
      { key: "home", direction: "desc" },
      COLUMNS,
      lookup,
      predictions,
    );
    expect(sorted).toEqual(input);
  });

  it("returns a copy of rows when sort key is unknown", () => {
    const input = ["USTALONE", "Superbet", "Betclic"];
    const sorted = sortOddsRows(
      input,
      { key: "unknown", direction: "desc" },
      COLUMNS,
      new Map(),
      [],
    );
    expect(sorted).toEqual(input);
    expect(sorted).not.toBe(input);
  });

  it("returns empty array for empty rows", () => {
    expect(
      sortOddsRows(
        [],
        { key: "home", direction: "desc" },
        COLUMNS,
        new Map(),
        [],
      ),
    ).toEqual([]);
  });

  it("does not mutate input rows", () => {
    const input = ["USTALONE", "Superbet", "Betclic", "Fortuna"];
    const snapshot = [...input];
    const lookup = new Map<string, number>([
      ["Superbet:1", 3.1],
      ["Betclic:1", 2.5],
      ["Fortuna:1", 1.8],
    ]);

    sortOddsRows(
      input,
      { key: "home", direction: "desc" },
      COLUMNS,
      lookup,
      [makePrediction(1, 0.5)],
    );
    expect(input).toEqual(snapshot);

    sortOddsRows(
      input,
      { key: ODDS_SORT_BOOKMAKER_KEY, direction: "asc" },
      COLUMNS,
      lookup,
      [],
    );
    expect(input).toEqual(snapshot);
  });
});
