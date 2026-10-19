import type {
  HockeyPlayerCountingStats,
  HockeyRosterPlayer,
} from "@/types/api";

export const ROSTER_STAT_WINDOWS = [
  {
    id: "season",
    label: "Sezon",
    title: "Statystyki sezonu zasadniczego",
  },
  {
    id: "last_5",
    label: "Ostatnie 5",
    title: "Ostatnie 5 meczów zawodnika",
  },
  {
    id: "last_10",
    label: "Ostatnie 10",
    title: "Ostatnie 10 meczów zawodnika",
  },
] as const;

export type RosterStatWindow = (typeof ROSTER_STAT_WINDOWS)[number]["id"];

export type RosterStatKey =
  | "games_played"
  | "goals"
  | "assists"
  | "points"
  | "shots_on_goal"
  | "shots_per_game"
  | "average_toi"
  | "save_percentage"
  | "goals_against_average";

const GOALIE_POSITION = "G";
const GOALIE_STAT_KEYS = new Set<RosterStatKey>([
  "save_percentage",
  "goals_against_average",
]);
const TEXT_SORT_KEYS = new Set<RosterSortKey>(["name", "position"]);

export type RosterSortKey = "name" | "position" | "number" | RosterStatKey;
export type RosterSortDirection = "asc" | "desc";

export interface RosterSortState {
  key: RosterSortKey;
  direction: RosterSortDirection;
}

/** Counting stats for the selected season or recent-game window. */
export function countingFor(
  player: HockeyRosterPlayer,
  windowId: RosterStatWindow,
): HockeyPlayerCountingStats {
  return player.stat_windows[windowId];
}

/** One table or goalie-card cell for a counting stat. */
export function formatRosterStat(
  player: HockeyRosterPlayer,
  counting: HockeyPlayerCountingStats,
  key: RosterStatKey,
): string {
  if (GOALIE_STAT_KEYS.has(key) && !isGoalie(player)) {
    return "—";
  }
  if (key === "average_toi") {
    return counting.average_toi ?? "—";
  }
  if (key === "shots_per_game") {
    return counting.shots_per_game === null
      ? "—"
      : counting.shots_per_game.toFixed(2);
  }
  if (key === "save_percentage") {
    return counting.save_percentage === null
      ? "—"
      : `${counting.save_percentage.toFixed(2)}%`;
  }
  if (key === "goals_against_average") {
    return counting.goals_against_average === null
      ? "—"
      : counting.goals_against_average.toFixed(2);
  }
  return String(counting[key]);
}

/** Display name used in the roster table and in name sorting. */
export function rosterPlayerLabel(player: HockeyRosterPlayer): string {
  if (player.common_name) {
    return player.common_name;
  }
  return `${player.first_name} ${player.last_name}`.trim();
}

/**
 * First click on a number column sorts highest-first.
 * Name and position start at A-Z. The next click flips direction.
 */
export function nextRosterSortState(
  current: RosterSortState | null,
  key: RosterSortKey,
): RosterSortState {
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
export function sortRosterPlayers(
  players: readonly HockeyRosterPlayer[],
  windowId: RosterStatWindow,
  sort: RosterSortState,
): HockeyRosterPlayer[] {
  return [...players].sort((left, right) => {
    const compared = comparePlayers(left, right, windowId, sort);
    if (compared !== 0) {
      return compared;
    }
    return left.player_id - right.player_id;
  });
}

function comparePlayers(
  left: HockeyRosterPlayer,
  right: HockeyRosterPlayer,
  windowId: RosterStatWindow,
  sort: RosterSortState,
): number {
  if (sort.key === "name" || sort.key === "position") {
    return compareText(
      textValue(left, sort.key),
      textValue(right, sort.key),
      sort.direction,
    );
  }
  return compareNumbers(
    numberValue(left, windowId, sort.key),
    numberValue(right, windowId, sort.key),
    sort.direction,
  );
}

function textValue(player: HockeyRosterPlayer, key: "name" | "position"): string {
  if (key === "name") {
    return rosterPlayerLabel(player);
  }
  return player.position.trim();
}

function numberValue(
  player: HockeyRosterPlayer,
  windowId: RosterStatWindow,
  key: Exclude<RosterSortKey, "name" | "position">,
): number | null {
  if (key === "number") {
    return player.number;
  }
  if (GOALIE_STAT_KEYS.has(key) && !isGoalie(player)) {
    return null;
  }
  const counting = countingFor(player, windowId);
  if (key === "average_toi") {
    return toiSeconds(counting.average_toi);
  }
  return counting[key];
}

function toiSeconds(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const match = /^(\d+):(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }
  return Number(match[1]) * 60 + Number(match[2]);
}

function compareText(
  left: string,
  right: string,
  direction: RosterSortDirection,
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
  direction: RosterSortDirection,
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

function isGoalie(player: HockeyRosterPlayer): boolean {
  return player.position.trim().toUpperCase() === GOALIE_POSITION;
}
