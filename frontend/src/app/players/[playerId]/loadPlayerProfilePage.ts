import {
  getPlayerProfile,
  getPlayerSeasons,
  getPlayerTeams,
} from "@/lib/api";
import type { PlayerProfileQuery } from "@/lib/playerProfileParams";
import { ApiError } from "@/lib/apiShared";
import type {
  PlayerProfileResponse,
  PlayerSeasonOption,
  PlayerTeamOption,
} from "@/types/api";

const PROFILE_LOAD_ERROR = "Nie udało się załadować profilu zawodnika.";
const DICTIONARY_LOAD_ERROR = "Nie udało się pobrać sezonów i drużyn.";

export type PlayerProfilePageResult =
  | { kind: "notFound" }
  | {
      kind: "error";
      sliceError: string;
    }
  | {
      kind: "ready";
      profile: PlayerProfileResponse;
      seasons: PlayerSeasonOption[];
      teams: PlayerTeamOption[];
      dictionariesError: string | null;
    };

/** Loads the profile envelope, then seasons and teams for its sport. */
export async function loadPlayerProfilePage(
  playerId: number,
  params: PlayerProfileQuery,
): Promise<PlayerProfilePageResult> {
  let profile: PlayerProfileResponse;
  try {
    profile = await getPlayerProfile(playerId, params);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { kind: "notFound" };
    }
    return {
      kind: "error",
      sliceError: messageFrom(error, PROFILE_LOAD_ERROR),
    };
  }

  const dictionaries = await loadDictionaries(profile.sport_id);
  return {
    kind: "ready",
    profile,
    seasons: dictionaries.seasons,
    teams: dictionaries.teams,
    dictionariesError: dictionaries.dictionariesError,
  };
}

async function loadDictionaries(sportId: number): Promise<{
  seasons: PlayerSeasonOption[];
  teams: PlayerTeamOption[];
  dictionariesError: string | null;
}> {
  const [seasons, teams] = await Promise.all([
    loadSeasons(sportId),
    loadTeams(sportId),
  ]);
  return {
    seasons: seasons.items,
    teams: teams.items,
    dictionariesError: seasons.error ?? teams.error,
  };
}

async function loadSeasons(
  sportId: number,
): Promise<{ items: PlayerSeasonOption[]; error: string | null }> {
  try {
    const response = await getPlayerSeasons(sportId);
    return { items: response.seasons, error: null };
  } catch (error) {
    return {
      items: [],
      error: messageFrom(error, DICTIONARY_LOAD_ERROR),
    };
  }
}

async function loadTeams(
  sportId: number,
): Promise<{ items: PlayerTeamOption[]; error: string | null }> {
  try {
    const response = await getPlayerTeams(sportId);
    return { items: response.teams, error: null };
  } catch (error) {
    return {
      items: [],
      error: messageFrom(error, DICTIONARY_LOAD_ERROR),
    };
  }
}

function messageFrom(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return fallback;
}
