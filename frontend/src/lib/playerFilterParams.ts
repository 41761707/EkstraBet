import type { PlayerStatKey, PlayerTeamOption } from "@/types/api";

export const FOOTBALL_SPORT_ID = 1;
export const HOCKEY_SPORT_ID = 2;

export interface PlayersFilterValues {
  sportId: number;
  countryId: number | null;
  teamId: number | null;
  seasonId: number | null;
  matchLimit: number;
  search: string;
}

/** Teams shown in the dropdown for the currently selected country. */
export function teamsForCountry(
  teams: PlayerTeamOption[],
  countryId: number | null,
): PlayerTeamOption[] {
  if (countryId == null) {
    return teams;
  }
  return teams.filter((team) => team.country_id === countryId);
}

/** Keep country and team filters in sync when the country changes. */
export function selectCountryFilter(
  current: PlayersFilterValues,
  countryId: number | null,
  teams: PlayerTeamOption[],
): PlayersFilterValues {
  return {
    ...current,
    countryId,
    teamId: teamsForCountry(teams, countryId)[0]?.id ?? null,
  };
}

const FOOTBALL_PLAYER_STAT_KEYS: PlayerStatKey[] = [
  "goals",
  "assists",
  "shots",
  "shots_on_target",
  "fouls_conceded",
  "yellow_cards",
];

const HOCKEY_SKATER_STAT_KEYS: PlayerStatKey[] = [
  "points",
  "goals",
  "assists",
  "sog",
  "plus_minus",
  "penalty_minutes",
  "toi_minutes",
];

export function parsePlayerStatKeys(
  value: string | undefined,
  sportId = FOOTBALL_SPORT_ID,
): PlayerStatKey[] {
  const defaults =
    sportId === HOCKEY_SPORT_ID
      ? ["points", "goals", "assists", "sog", "penalty_minutes"]
      : ["goals", "assists"];
  const allowedKeys = new Set(
    sportId === HOCKEY_SPORT_ID
      ? HOCKEY_SKATER_STAT_KEYS
      : FOOTBALL_PLAYER_STAT_KEYS,
  );

  if (!value?.trim()) {
    return defaults as PlayerStatKey[];
  }

  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item): item is PlayerStatKey =>
      allowedKeys.has(item as PlayerStatKey),
    );
}

export function serializePlayerStatKeys(
  stats: PlayerStatKey[],
): string | undefined {
  if (stats.length === 0) {
    return undefined;
  }
  return stats.join(",");
}
