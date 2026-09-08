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
import {
  loadModelsGroupedByFamily,
  type ModelsByFamily,
} from "@/lib/modelsByFamily";
import {
  FOOTBALL_SPORT_ID,
  type AdminLeague,
  type AdminUser,
  type AnalyticsStatType,
  type CreateLeagueRequest,
  type CreateUserRequest,
  type FavoriteLeagueMutationResponse,
  type ModelAnalyticsResponse,
  type ModelDetailsResponse,
  type ModelListResponse,
  type PlayerMatchStatsResponse,
  type PredictionPreviewRequest,
  type PredictionPreviewResponse,
  type PublishTyperMatchesResponse,
  type RatingMetric,
  type RatingProgressResponse,
  type SeasonProjectionMode,
  type SeasonProjectionModeFlags,
  type SeasonProjectionResponse,
  type SportTeamHistoryResponse,
  type LongTermPicksPayload,
  type SaveLongTermPicksResponse,
  type SaveTyperPredictionResponse,
  type SettleLongTermResponse,
  type LongTermAutoResultResponse,
  type LongTermPickChange,
  type TyperAdminCandidatesResponse,
  type TyperOutcome,
  type TyperPredictionChange,
  type TyperRevealedPredictionsResponse,
  type UserPreferencesResponse,
  type UserPreferencesUpdate,
} from "@/types/api";

export { ApiError, buildClientProxyPath } from "@/lib/apiShared";
export type { ModelsByFamily };

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

export interface GetModelAnalyticsOptions {
  statType?: AnalyticsStatType;
  modelResultIds?: number[];
  modelOuIds?: number[];
  modelBttsIds?: number[];
  leagueIds?: number[];
  seasonId?: number;
  dateFrom?: string;
  dateTo?: string;
  teamId?: number;
  settledOnly?: boolean;
  applyTax?: boolean;
}

function joinIdList(ids: number[] | undefined): string | undefined {
  if (!ids || ids.length === 0) {
    return undefined;
  }
  return ids.join(",");
}

export async function getModelAnalytics(
  options: GetModelAnalyticsOptions,
): Promise<ModelAnalyticsResponse> {
  return fetchViaBff<ModelAnalyticsResponse>("/analytics/models", {
    stat_type: options.statType,
    model_result_ids: joinIdList(options.modelResultIds),
    model_ou_ids: joinIdList(options.modelOuIds),
    model_btts_ids: joinIdList(options.modelBttsIds),
    league_ids: joinIdList(options.leagueIds),
    season_id: options.seasonId,
    date_from: options.dateFrom,
    date_to: options.dateTo,
    team_id: options.teamId,
    settled_only: options.settledOnly,
    apply_tax: options.applyTax,
  });
}

export async function getModels(): Promise<ModelListResponse> {
  return fetchViaBff<ModelListResponse>("/models/models");
}

export async function getModelDetails(
  modelId: number,
): Promise<ModelDetailsResponse> {
  return fetchViaBff<ModelDetailsResponse>(`/models/models/${modelId}/details`);
}

export async function getModelsGroupedByFamily(
  sportId = FOOTBALL_SPORT_ID,
): Promise<ModelsByFamily> {
  return loadModelsGroupedByFamily(sportId, {
    getModels,
    getModelDetails,
  });
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

export async function getTyperRevealedPredictions(
  seasonId: number,
  roundNumber: number,
): Promise<TyperRevealedPredictionsResponse> {
  return fetchViaBff<TyperRevealedPredictionsResponse>(
    "/typer-lm/revealed-predictions",
    {
      season_id: seasonId,
      round_number: roundNumber,
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

export async function saveTyperLongTermPicks(
  marketId: number,
  payload: LongTermPicksPayload,
): Promise<SaveLongTermPicksResponse> {
  return fetchViaBff<SaveLongTermPicksResponse>(
    `/typer-lm/long-term/markets/${marketId}/picks`,
    undefined,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(longTermPicksRequestBody(payload)),
    },
  );
}

export async function getTyperLongTermHistory(
  marketId: number,
): Promise<LongTermPickChange[]> {
  return fetchViaBff<LongTermPickChange[]>(
    `/typer-lm/long-term/markets/${marketId}/history`,
  );
}

export async function getTyperLongTermAdminHistory(options: {
  userUuid: string;
  marketId?: number;
  seasonId?: number;
}): Promise<LongTermPickChange[]> {
  return fetchViaBff<LongTermPickChange[]>(
    "/typer-lm/long-term/admin/prediction-history",
    {
      user_uuid: options.userUuid,
      market_id: options.marketId,
      season_id: options.seasonId,
    },
  );
}

export async function getTyperLongTermAutoResult(
  marketId: number,
): Promise<LongTermAutoResultResponse> {
  return fetchViaBff<LongTermAutoResultResponse>(
    `/typer-lm/long-term/admin/markets/${marketId}/auto-result`,
  );
}

export async function settleTyperLongTermMarket(
  marketId: number,
  payload: LongTermPicksPayload,
): Promise<SettleLongTermResponse> {
  return fetchViaBff<SettleLongTermResponse>(
    `/typer-lm/long-term/admin/markets/${marketId}/settle`,
    undefined,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(longTermPicksRequestBody(payload)),
    },
  );
}

type LongTermPicksRequestBody = {
  team_ids?: number[];
  subject_texts?: string[];
  is_text_correct?: boolean;
};

function longTermPicksRequestBody(
  payload: LongTermPicksPayload,
): LongTermPicksRequestBody {
  // xor egzekwuje serwis; tabela ma wysyłać wyłącznie team_ids
  const body: LongTermPicksRequestBody = {};
  if (payload.teamIds !== undefined) {
    body.team_ids = payload.teamIds;
  }
  if (payload.subjectTexts !== undefined) {
    body.subject_texts = payload.subjectTexts;
  }
  if (payload.isTextCorrect !== undefined) {
    body.is_text_correct = payload.isTextCorrect;
  }
  return body;
}

export async function createAdminUser(
  request: CreateUserRequest,
): Promise<AdminUser> {
  return fetchViaBff<AdminUser>("/admin/users", undefined, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export async function setAdminUserActive(
  uuid: string,
  isActive: boolean,
): Promise<AdminUser> {
  return fetchViaBff<AdminUser>(
    `/admin/users/${uuid}/active`,
    undefined,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: isActive }),
    },
  );
}

export async function setAdminUserAdmin(
  uuid: string,
  isAdmin: boolean,
): Promise<AdminUser> {
  return fetchViaBff<AdminUser>(
    `/admin/users/${uuid}/admin`,
    undefined,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_admin: isAdmin }),
    },
  );
}

export async function createAdminLeague(
  request: CreateLeagueRequest,
): Promise<AdminLeague> {
  return fetchViaBff<AdminLeague>("/admin/leagues", undefined, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export async function setAdminLeagueActive(
  leagueId: number,
  active: boolean,
): Promise<AdminLeague> {
  return fetchViaBff<AdminLeague>(
    `/admin/leagues/${leagueId}/active`,
    undefined,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    },
  );
}
