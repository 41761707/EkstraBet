/**
 * Browser-facing API client. Talks only to the Next.js BFF (`/api/backend/...`).
 * Must not import `@/lib/runtimeConfig` or any `server-only` module.
 */

import {
  ApiError,
  buildClientProxyPath,
  parseErrorMessage,
  type SearchParams,
} from "@/lib/apiShared";
import { FIRST_LOGIN_PATH, isFirstLoginRequiredError } from "@/lib/firstLogin";
import type {
  FavoriteLeagueMutationResponse,
  PlayerMatchStatsResponse,
  PredictionPreviewRequest,
  PredictionPreviewResponse,
  PublishTyperMatchesResponse,
  RatingMetric,
  RatingProgressResponse,
  SeasonProjectionMode,
  SeasonProjectionModeFlags,
  SeasonProjectionResponse,
  SportTeamHistoryResponse,
  SaveTyperPredictionResponse,
  TyperAdminCandidatesResponse,
  TyperOutcome,
  TyperPredictionChange,
  UserPreferencesResponse,
  UserPreferencesUpdate,
} from "@/types/api";

export { ApiError, buildClientProxyPath } from "@/lib/apiShared";

interface FetchViaBffOptions {
  skipFirstLoginRedirect?: boolean;
}

async function fetchViaBff<T>(
  path: string,
  params?: SearchParams,
  init?: RequestInit,
  options?: FetchViaBffOptions,
): Promise<T> {
  const url = new URL(
    buildClientProxyPath(path, params),
    window.location.origin,
  ).toString();

  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    const skipRedirect = options?.skipFirstLoginRedirect === true;
    // preferencje na /first-login zostają lokalne — 403 nie może robić pętli redirectu
    if (!skipRedirect && isFirstLoginRequiredError(response.status, message)) {
      window.location.replace(FIRST_LOGIN_PATH);
    }
    throw new ApiError(response.status, message);
  }

  // DELETE publikacji Typera zwraca 204 bez ciała
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function addFavoriteLeague(
  leagueId: number,
): Promise<FavoriteLeagueMutationResponse> {
  return fetchViaBff<FavoriteLeagueMutationResponse>(
    `/users/me/favorite-leagues/${leagueId}`,
    undefined,
    { method: "PUT" },
  );
}

export async function removeFavoriteLeague(
  leagueId: number,
): Promise<FavoriteLeagueMutationResponse> {
  return fetchViaBff<FavoriteLeagueMutationResponse>(
    `/users/me/favorite-leagues/${leagueId}`,
    undefined,
    { method: "DELETE" },
  );
}

export async function getUserPreferences(): Promise<UserPreferencesResponse> {
  return fetchViaBff<UserPreferencesResponse>(
    "/users/me/preferences",
    undefined,
    undefined,
    { skipFirstLoginRedirect: true },
  );
}

export async function putUserPreferences(
  update: UserPreferencesUpdate,
): Promise<UserPreferencesResponse> {
  return fetchViaBff<UserPreferencesResponse>(
    "/users/me/preferences",
    undefined,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    },
    { skipFirstLoginRedirect: true },
  );
}

export async function previewPrediction(
  request: PredictionPreviewRequest,
): Promise<PredictionPreviewResponse> {
  return fetchViaBff<PredictionPreviewResponse>(
    "/predictions/preview",
    undefined,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );
}

export async function getPlayerMatchStats(
  sportId: number,
  playerId: number,
  options: { seasonId: number; limit?: number },
): Promise<PlayerMatchStatsResponse> {
  return fetchViaBff<PlayerMatchStatsResponse>(
    `/players/${sportId}/${playerId}/match-stats`,
    {
      season_id: options.seasonId,
      limit: options.limit ?? 50,
    },
  );
}

export async function getSportTeamHistory(
  leagueId: number,
  teamId: number,
  seasonId: number,
  options?: {
    phase?: number;
    lookback?: number;
  },
): Promise<SportTeamHistoryResponse> {
  return fetchViaBff<SportTeamHistoryResponse>(
    `/leagues/${leagueId}/sport/teams/${teamId}/history`,
    {
      season_id: seasonId,
      phase: options?.phase,
      lookback: options?.lookback,
    },
  );
}

export async function getLeagueRatingProgress(
  leagueId: number,
  seasonId: number,
  metric: RatingMetric = "elo",
): Promise<RatingProgressResponse> {
  return fetchViaBff<RatingProgressResponse>(
    `/leagues/${leagueId}/rating-progress`,
    {
      season_id: seasonId,
      metric,
    },
  );
}

export async function getSeasonProjectionModes(
  leagueId: number,
  seasonId: number,
): Promise<SeasonProjectionModeFlags> {
  return fetchViaBff<SeasonProjectionModeFlags>(
    `/leagues/${leagueId}/season-projection/modes`,
    {
      season_id: seasonId,
    },
  );
}

export async function getSeasonProjection(
  leagueId: number,
  seasonId: number,
  mode: SeasonProjectionMode = "from_now",
): Promise<SeasonProjectionResponse> {
  return fetchViaBff<SeasonProjectionResponse>(
    `/leagues/${leagueId}/season-projection`,
    {
      season_id: seasonId,
      mode,
    },
  );
}

export async function saveTyperPrediction(
  matchId: number,
  outcome: TyperOutcome,
): Promise<SaveTyperPredictionResponse> {
  return fetchViaBff<SaveTyperPredictionResponse>(
    `/typer-lm/predictions/${matchId}`,
    undefined,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outcome }),
    },
  );
}

export async function getTyperAdminCandidates(
  seasonId: number,
  roundNumber: number,
): Promise<TyperAdminCandidatesResponse> {
  return fetchViaBff<TyperAdminCandidatesResponse>(
    "/typer-lm/admin/candidates",
    {
      season_id: seasonId,
      round_number: roundNumber,
    },
  );
}

export async function publishTyperMatches(
  seasonId: number,
  roundNumber: number,
  matchIds: number[],
): Promise<PublishTyperMatchesResponse> {
  return fetchViaBff<PublishTyperMatchesResponse>(
    "/typer-lm/admin/publications",
    undefined,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        season_id: seasonId,
        round_number: roundNumber,
        match_ids: matchIds,
      }),
    },
  );
}

export async function deleteTyperPublication(matchId: number): Promise<void> {
  await fetchViaBff<undefined>(
    `/typer-lm/admin/publications/${matchId}`,
    undefined,
    { method: "DELETE" },
  );
}

export async function getTyperAdminPredictionHistory(options: {
  userUuid: string;
  matchId?: number;
  seasonId?: number;
}): Promise<TyperPredictionChange[]> {
  return fetchViaBff<TyperPredictionChange[]>(
    "/typer-lm/admin/prediction-history",
    {
      user_uuid: options.userUuid,
      match_id: options.matchId,
      season_id: options.seasonId,
    },
  );
}
