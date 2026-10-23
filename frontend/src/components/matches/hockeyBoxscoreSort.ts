import type {
  HockeyGoalieBoxscoreRow,
  HockeySkaterBoxscoreRow,
} from "@/types/api";

export type BoxscoreSortDirection = "asc" | "desc";

export type GoalieSortKey =
  | "team_name"
  | "player_name"
  | "points"
  | "penalty_minutes"
  | "time_on_ice"
  | "shots_against"
  | "shots_saved"
  | "saves_accuracy"
  | "rating";

export type SkaterSortKey =
  | "team_name"
  | "player_name"
  | "goals"
  | "assists"
  | "points"
  | "plus_minus"
  | "penalty_minutes"
  | "shots_on_goal"
  | "time_on_ice"
  | "rating";

export interface BoxscoreSortState<Key extends string> {
  key: Key;
  direction: BoxscoreSortDirection;
}

export type BoxscoreSortValue = string | number | null;

const TEXT_SORT_KEYS = new Set<string>(["team_name", "player_name"]);

/**
 * First click on a stat column sorts highest-first so TOI and counts
 * surface the leaders. Names and teams start A-Z. The next click flips.
 */
export function nextBoxscoreSort<Key extends string>(
  current: BoxscoreSortState<Key> | null,
  key: Key,
): BoxscoreSortState<Key> {
  if (current === null || current.key !== key) {
    return {
      key,
      direction: TEXT_SORT_KEYS.has(key) ? "asc" : "desc",
    };
  }
  return {
    key,
    direction: current.direction === "asc" ? "desc" : "asc",
  };
}

/** Return a new list. Missing values stay at the bottom in both directions. */
export function sortBoxscoreRows<Row extends { player_id: number }, Key extends string>(
  rows: readonly Row[],
  sort: BoxscoreSortState<Key>,
  valueOf: (row: Row, key: Key) => BoxscoreSortValue,
): Row[] {
  return [...rows].sort((left, right) => {
    const compared = compareSortValues(
      valueOf(left, sort.key),
      valueOf(right, sort.key),
      sort.direction,
    );
    if (compared !== 0) {
      return compared;
    }
    return left.player_id - right.player_id;
  });
}

/** Parse `minutes:seconds` ice time. Unparseable values sort as missing. */
export function timeOnIceSeconds(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }
  const match = /^(\d+):(\d{2})$/.exec(value.trim());
  if (!match) {
    return null;
  }
  return Number(match[1]) * 60 + Number(match[2]);
}

export function goalieSortValue(
  row: HockeyGoalieBoxscoreRow & { rating?: number | null },
  key: GoalieSortKey,
): BoxscoreSortValue {
  if (key === "time_on_ice") {
    return timeOnIceSeconds(row.time_on_ice);
  }
  if (key === "rating") {
    return row.rating ?? null;
  }
  return row[key];
}

export function skaterSortValue(
  row: HockeySkaterBoxscoreRow & { rating?: number | null },
  key: SkaterSortKey,
): BoxscoreSortValue {
  if (key === "time_on_ice") {
    return timeOnIceSeconds(row.time_on_ice);
  }
  if (key === "rating") {
    return row.rating ?? null;
  }
  return row[key];
}

function compareSortValues(
  left: BoxscoreSortValue,
  right: BoxscoreSortValue,
  direction: BoxscoreSortDirection,
): number {
  if (typeof left === "string" || typeof right === "string") {
    return compareText(asText(left), asText(right), direction);
  }
  return compareNumbers(left, right, direction);
}

function asText(value: BoxscoreSortValue): string {
  return typeof value === "string" ? value : "";
}

function compareText(
  left: string,
  right: string,
  direction: BoxscoreSortDirection,
): number {
  if (!left && !right) {
    return 0;
  }
  if (!left) {
    return 1;
  }
  if (!right) {
    return -1;
  }
  const compared = left.localeCompare(right, "pl", { sensitivity: "base" });
  return direction === "asc" ? compared : -compared;
}

function compareNumbers(
  left: number | null,
  right: number | null,
  direction: BoxscoreSortDirection,
): number {
  if (left === null && right === null) {
    return 0;
  }
  if (left === null) {
    return 1;
  }
  if (right === null) {
    return -1;
  }
  return direction === "asc" ? left - right : right - left;
}
