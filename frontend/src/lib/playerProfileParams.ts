import { PLAYER_PROFILE_SPORT_IDS } from "@/lib/playerProfileSports";
import { parsePositiveInt } from "@/lib/searchParams";

export const PROFILE_MATCH_WINDOWS = [5, 10, 15] as const;

export interface PlayerProfileQuery {
  seasonId: number | null;
  opponentTeamId: number | null;
  teammateId: number | null;
  matchLimit: number | null;
}

export interface PlayerProfileParams extends PlayerProfileQuery {
  teammateLabel: string | null;
}

/** Reads profile filters from the page query. A garbage number becomes null. */
export function parsePlayerProfileParams(
  searchParams: Record<string, string | undefined>,
): PlayerProfileParams {
  const label = searchParams.teammate_label?.trim() ?? "";
  return {
    seasonId: parsePositiveInt(searchParams.season_id),
    opponentTeamId: parsePositiveInt(searchParams.opponent_team_id),
    teammateId: parsePositiveInt(searchParams.teammate_id),
    matchLimit: parseProfileMatchLimit(searchParams.match_limit),
    teammateLabel: label || null,
  };
}

/** Query string for `/players/{playerId}`. Empty filters are omitted. */
export function buildPlayerProfileQuery(params: PlayerProfileParams): string {
  const search = new URLSearchParams();
  appendId(search, "season_id", params.seasonId);
  appendId(search, "opponent_team_id", params.opponentTeamId);
  appendId(search, "teammate_id", params.teammateId);
  appendId(search, "match_limit", params.matchLimit);
  const label = params.teammateLabel?.trim();
  if (label) {
    search.set("teammate_label", label);
  }
  return search.toString();
}

/** Profile URL with the season copied from the players list. */
export function buildPlayerProfileHref(
  playerId: number,
  seasonId: number | null,
): string {
  const query = buildPlayerProfileQuery({
    seasonId,
    opponentTeamId: null,
    teammateId: null,
    matchLimit: null,
    teammateLabel: null,
  });
  if (!query) {
    return `/players/${playerId}`;
  }
  return `/players/${playerId}?${query}`;
}

/** Expander link for a sport that has a profile. Other sports return null. */
export function playerProfilePanelHref(
  sportId: number,
  playerId: number,
  seasonId: number,
): string | null {
  if (!PLAYER_PROFILE_SPORT_IDS.has(sportId)) {
    return null;
  }
  return buildPlayerProfileHref(playerId, seasonId);
}

/** A teammate must be a different player than the profile subject. */
export function canSelectTeammate(
  playerId: number,
  teammateId: number,
): boolean {
  return teammateId !== playerId;
}

function parseProfileMatchLimit(value: string | undefined): number | null {
  const parsed = parsePositiveInt(value);
  for (const windowLimit of PROFILE_MATCH_WINDOWS) {
    if (parsed === windowLimit) {
      return windowLimit;
    }
  }
  return null;
}

function appendId(
  search: URLSearchParams,
  key: string,
  value: number | null,
): void {
  if (value == null) {
    return;
  }
  search.set(key, String(value));
}
