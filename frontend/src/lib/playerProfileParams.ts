import { parsePositiveInt } from "@/lib/searchParams";

export interface PlayerProfileQuery {
  seasonId: number | null;
  opponentTeamId: number | null;
  ownTeamId: number | null;
  teammateId: number | null;
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
    ownTeamId: parsePositiveInt(searchParams.own_team_id),
    teammateId: parsePositiveInt(searchParams.teammate_id),
    teammateLabel: label || null,
  };
}

/** Query string for `/players/{playerId}`. Empty filters are omitted. */
export function buildPlayerProfileQuery(params: PlayerProfileParams): string {
  const search = new URLSearchParams();
  appendId(search, "season_id", params.seasonId);
  appendId(search, "opponent_team_id", params.opponentTeamId);
  appendId(search, "own_team_id", params.ownTeamId);
  appendId(search, "teammate_id", params.teammateId);
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
    ownTeamId: null,
    teammateId: null,
    teammateLabel: null,
  });
  if (!query) {
    return `/players/${playerId}`;
  }
  return `/players/${playerId}?${query}`;
}

/** A teammate must be a different player than the profile subject. */
export function canSelectTeammate(
  playerId: number,
  teammateId: number,
): boolean {
  return teammateId !== playerId;
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
