import type {
  MatchPredictionItem,
  PredictionPreviewResponse,
} from "@/types/api";

export type OddsSortDirection = "asc" | "desc";

export interface OddsSortState {
  key: string;
  direction: OddsSortDirection;
}

export interface OddsColumn {
  key: string;
  label: string;
  eventId: number;
}

/** Unit probability for a market event (enough for USTALONE odds). */
export interface MarketEventProbability {
  event_id: number;
  value: number | null;
}

export const ODDS_SORT_BOOKMAKER_KEY = "bookmaker" as const;

export const ODDS_MARKET_EVENT_IDS = {
  home: 1,
  draw: 2,
  away: 3,
  over: 8,
  under: 12,
  bttsYes: 6,
  bttsNo: 172,
} as const;

const USTALONE_ROW_NAME = "USTALONE";

/**
 * Build USTALONE probabilities for all odds-table markets.
 * Prefers full prediction_analysis (all outcomes); falls back to final
 * predictions (favorites only) when analysis is unavailable.
 */
export function buildUstaloneMarketPredictions(
  analysis: PredictionPreviewResponse | null,
  fallbackPredictions: readonly MatchPredictionItem[] = [],
): MarketEventProbability[] {
  if (analysis !== null) {
    return [
      { event_id: ODDS_MARKET_EVENT_IDS.home, value: analysis.result.p_home },
      { event_id: ODDS_MARKET_EVENT_IDS.draw, value: analysis.result.p_draw },
      { event_id: ODDS_MARKET_EVENT_IDS.away, value: analysis.result.p_away },
      { event_id: ODDS_MARKET_EVENT_IDS.bttsYes, value: analysis.btts.p_yes },
      { event_id: ODDS_MARKET_EVENT_IDS.bttsNo, value: analysis.btts.p_no },
      { event_id: ODDS_MARKET_EVENT_IDS.over, value: analysis.goals.over_25 },
      { event_id: ODDS_MARKET_EVENT_IDS.under, value: analysis.goals.under_25 },
    ];
  }

  return fallbackPredictions.map((item) => ({
    event_id: item.event_id,
    value: item.value,
  }));
}

/** Cycle sort direction for a column click. */
export function nextOddsSortState(
  current: OddsSortState | null,
  key: string,
): OddsSortState {
  if (current === null || current.key !== key) {
    return {
      key,
      direction: key === ODDS_SORT_BOOKMAKER_KEY ? "asc" : "desc",
    };
  }

  return {
    key,
    direction: current.direction === "asc" ? "desc" : "asc",
  };
}

/** True when value is a usable positive odds number. */
function hasPresentOddsValue(
  value: number | null | undefined,
): value is number {
  return value !== null && value !== undefined && value > 0;
}

/** True when value is absent or non-positive (sort to end). */
export function isMissingOddsValue(
  value: number | null | undefined,
): boolean {
  return !hasPresentOddsValue(value);
}

/**
 * Resolve numeric odds for a row/column; null means missing for sort.
 * USTALONE uses 1 / prediction.value (same rule as table display).
 */
export function resolveOddsSortValue(
  rowName: string,
  eventId: number,
  lookup: ReadonlyMap<string, number>,
  predictions: readonly MarketEventProbability[],
): number | null {
  if (rowName === USTALONE_ROW_NAME) {
    const prediction = predictions.find((item) => item.event_id === eventId);
    if (!prediction || prediction.value === null || prediction.value <= 0) {
      return null;
    }
    return Number((1 / prediction.value).toFixed(2));
  }

  const odds = lookup.get(`${rowName}:${eventId}`);
  if (odds === undefined || odds <= 0) {
    return null;
  }
  return odds;
}

function compareOddsValues(
  left: number | null,
  right: number | null,
  direction: OddsSortDirection,
): number {
  if (!hasPresentOddsValue(left) && !hasPresentOddsValue(right)) {
    return 0;
  }
  if (!hasPresentOddsValue(left)) {
    return 1;
  }
  if (!hasPresentOddsValue(right)) {
    return -1;
  }

  return direction === "asc" ? left - right : right - left;
}

/** Return a new sorted row list; never mutates `rows`. */
export function sortOddsRows(
  rows: readonly string[],
  sort: OddsSortState,
  columns: readonly OddsColumn[],
  lookup: ReadonlyMap<string, number>,
  predictions: readonly MarketEventProbability[],
): string[] {
  if (rows.length === 0) {
    return [];
  }

  const indexed = rows.map((row, index) => ({ row, index }));

  if (sort.key === ODDS_SORT_BOOKMAKER_KEY) {
    indexed.sort((left, right) => {
      const nameCompare = left.row.localeCompare(right.row, "pl");
      const signed =
        sort.direction === "asc" ? nameCompare : -nameCompare;
      return signed !== 0 ? signed : left.index - right.index;
    });
    return indexed.map((item) => item.row);
  }

  const column = columns.find((item) => item.key === sort.key);
  if (!column) {
    return [...rows];
  }

  indexed.sort((left, right) => {
    const leftValue = resolveOddsSortValue(
      left.row,
      column.eventId,
      lookup,
      predictions,
    );
    const rightValue = resolveOddsSortValue(
      right.row,
      column.eventId,
      lookup,
      predictions,
    );
    const valueCompare = compareOddsValues(
      leftValue,
      rightValue,
      sort.direction,
    );
    return valueCompare !== 0 ? valueCompare : left.index - right.index;
  });

  return indexed.map((item) => item.row);
}
