import "server-only";

/**
 * Server-only FastAPI client for RSC / route handlers.
 * Browser code must use `@/lib/apiClient` (BFF paths only).
 */

import { cache } from "react";
import { redirect } from "next/navigation";

import { decodeRouteParam } from "@/lib/leaguePaths";
import {
  ApiError,
  applySearchParams,
  normalizeMatchDetails,
  parseErrorMessage,
  type SearchParams,
} from "@/lib/apiShared";
import { getServerAuthHeaders } from "@/lib/auth";
import { FIRST_LOGIN_PATH, isFirstLoginRequiredError } from "@/lib/firstLogin";
import { getApiBaseUrl } from "@/lib/runtimeConfig";
import type {
  AnalyticsAggregationMetric,
  AnalyticsGroupBy,
  AnalyticsStatType,
  BetRecommendationsResponse,
  BetSortBy,
  BetSortOrder,
  DailyMatchesResponse,
  EventFamilyEventsResponse,
  EventFamilyListResponse,
  FavoriteLeagueIdsResponse,
  LeagueDetails,
  LeagueCharacteristics,
  LeagueComparisonsResponse,
  LeagueMatchesListResponse,
  LeagueRoundsListResponse,
  LeaguesListResponse,
  LeagueStandingsResponse,
  MatchDetails,
  ModelAnalyticsResponse,
  ModelDetailsResponse,
  ModelListResponse,
  SettlementStatus,
  SportLeagueStatsResponse,
  SportMatchesListResponse,
  SportStandingScope,
  SportStandingsResponse,
  SportTeamHistoryResponse,
  SportTeamsListResponse,
  StandingScope,
  TeamProfile,
  FilterOption,
  PlayerSportsListResponse,
  PlayerCountriesResponse,
  PlayerTeamsResponse,
  PlayerSeasonsResponse,
  FootballPlayersListResponse,
  PlayerMatchStatsResponse,
  PredictionPreviewRequest,
  PredictionPreviewResponse,
  RatingMetric,
  RatingProgressResponse,
  TeamsListResponse,
  UserPublic,
} from "@/types/api";

export { ApiError, normalizeMatchDetails } from "@/lib/apiShared";

function buildUrl(path: string, params?: SearchParams): string {
  const url = new URL(path, getApiBaseUrl());
  applySearchParams(url, params);
  return url.toString();
}

async function fetchApi<T>(
  path: string,
  params?: SearchParams,
  init?: RequestInit,
): Promise<T> {
  const authHeaders = await getServerAuthHeaders();
  const response = await fetch(buildUrl(path, params), {
    ...init,
    headers: {
      Accept: "application/json",
      ...authHeaders,
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    if (isFirstLoginRequiredError(response.status, message)) {
      redirect(FIRST_LOGIN_PATH);
    }
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
}

/** Current authenticated user; never cached across requests so first_login stays fresh. */
export const getCurrentUser = cache(async (): Promise<UserPublic> => {
  const authHeaders = await getServerAuthHeaders();
  const response = await fetch(buildUrl("/auth/me"), {
    headers: {
      Accept: "application/json",
      ...authHeaders,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<UserPublic>;
});

/** Favorite league IDs for the current user; never cached across requests. */
export async function getFavoriteLeagueIds(): Promise<FavoriteLeagueIdsResponse> {
  return fetchApi<FavoriteLeagueIdsResponse>("/users/me/favorite-leagues");
}

export async function getLeagues(options?: {
  active?: boolean;
  sportId?: number;
}): Promise<LeaguesListResponse> {
  return fetchApi<LeaguesListResponse>("/leagues", {
    active: options?.active ?? true,
    sport_id: options?.sportId,
  });
}

export async function getLeagueDetails(
  leagueId: number,
): Promise<LeagueDetails> {
  return fetchApi<LeagueDetails>(`/leagues/${leagueId}`);
}

export async function resolveLeagueId(
  leagueIdOrSlug: string,
): Promise<number | null> {
  const normalizedSlug = decodeRouteParam(leagueIdOrSlug);
  const numericId = Number(normalizedSlug);
  if (
    Number.isInteger(numericId) &&
    numericId > 0 &&
    String(numericId) === normalizedSlug
  ) {
    return numericId;
  }

  const { leagues } = await getLeagues({ active: undefined });
  const match = leagues.find((league) => league.slug === normalizedSlug);
  return match?.id ?? null;
}

export async function getLeagueMatches(
  leagueId: number,
  seasonId: number,
  round?: number,
): Promise<LeagueMatchesListResponse> {
  return fetchApi<LeagueMatchesListResponse>(`/leagues/${leagueId}/matches`, {
    season_id: seasonId,
    round,
  });
}

export async function getLeagueRounds(
  leagueId: number,
  seasonId: number,
): Promise<LeagueRoundsListResponse> {
  return fetchApi<LeagueRoundsListResponse>(
    `/leagues/${leagueId}/rounds/${seasonId}`,
  );
}

export async function getLeagueCharacteristics(
  leagueId: number,
  seasonId: number,
): Promise<LeagueCharacteristics> {
  return fetchApi<LeagueCharacteristics>(
    `/leagues/${leagueId}/characteristics`,
    { season_id: seasonId },
  );
}

export async function getLeagueRatingProgress(
  leagueId: number,
  seasonId: number,
  metric: RatingMetric = "elo",
): Promise<RatingProgressResponse> {
  return fetchApi<RatingProgressResponse>(
    `/leagues/${leagueId}/rating-progress`,
    { season_id: seasonId, metric },
  );
}

export async function getLeagueStandings(
  leagueId: number,
  seasonId: number,
  scope: StandingScope = "overall",
): Promise<LeagueStandingsResponse> {
  return fetchApi<LeagueStandingsResponse>(
    `/leagues/${leagueId}/standings`,
    {
      season_id: seasonId,
      scope,
    },
  );
}

export async function getSportLeagueMatches(
  leagueId: number,
  seasonId: number,
  options?: {
    phase?: number;
    dateFrom?: string;
    dateTo?: string;
  },
): Promise<SportMatchesListResponse> {
  return fetchApi<SportMatchesListResponse>(
    `/leagues/${leagueId}/sport/matches`,
    {
      season_id: seasonId,
      phase: options?.phase,
      date_from: options?.dateFrom,
      date_to: options?.dateTo,
    },
  );
}

export async function getSportLeagueTeams(
  leagueId: number,
  seasonId: number,
): Promise<SportTeamsListResponse> {
  return fetchApi<SportTeamsListResponse>(`/leagues/${leagueId}/sport/teams`, {
    season_id: seasonId,
  });
}

export async function getSportLeagueStandings(
  leagueId: number,
  seasonId: number,
  scope: SportStandingScope = "overall",
): Promise<SportStandingsResponse> {
  return fetchApi<SportStandingsResponse>(
    `/leagues/${leagueId}/sport/standings`,
    {
      season_id: seasonId,
      scope,
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
  return fetchApi<SportTeamHistoryResponse>(
    `/leagues/${leagueId}/sport/teams/${teamId}/history`,
    {
      season_id: seasonId,
      phase: options?.phase,
      lookback: options?.lookback,
    },
  );
}

export async function getSportLeagueStats(
  leagueId: number,
  seasonId: number,
  category: string,
  phase?: number,
): Promise<SportLeagueStatsResponse> {
  return fetchApi<SportLeagueStatsResponse>(
    `/leagues/${leagueId}/sport/stats/${category}`,
    {
      season_id: seasonId,
      phase,
    },
  );
}

export async function getTeamProfile(
  teamId: number,
  options: {
    seasonId: number;
    leagueId?: number;
    limit?: number;
    opponentId?: number;
  },
): Promise<TeamProfile> {
  return fetchApi<TeamProfile>(`/teams/${teamId}/profile`, {
    season_id: options.seasonId,
    league_id: options.leagueId,
    limit: options.limit,
    opponent_id: options.opponentId,
  });
}

export async function getFootballTeams(): Promise<TeamsListResponse> {
  const pageSize = 500;
  const firstPage = await fetchApi<TeamsListResponse>("/teams/search", {
    sport_id: 1,
    page: 1,
    page_size: pageSize,
  });
  const pageCount = Math.ceil(firstPage.total_count / pageSize);
  if (pageCount <= 1) {
    return firstPage;
  }

  const remainingPages = await Promise.all(
    Array.from({ length: pageCount - 1 }, (_, index) =>
      fetchApi<TeamsListResponse>("/teams/search", {
        sport_id: 1,
        page: index + 2,
        page_size: pageSize,
      }),
    ),
  );
  return {
    ...firstPage,
    teams: [
      ...firstPage.teams,
      ...remainingPages.flatMap((page) => page.teams),
    ],
  };
}

export async function previewPrediction(
  request: PredictionPreviewRequest,
): Promise<PredictionPreviewResponse> {
  return fetchApi<PredictionPreviewResponse>(
    "/predictions/preview",
    undefined,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      cache: "no-store",
    },
  );
}

export async function getMatchDetails(
  matchId: number,
  modelIds?: number[],
): Promise<MatchDetails> {
  const modelIdsParam =
    modelIds && modelIds.length > 0 ? modelIds.join(",") : undefined;
  const payload = await fetchApi<MatchDetails>(`/matches/${matchId}/details`, {
    model_ids: modelIdsParam,
  });
  return normalizeMatchDetails(payload);
}

/** Daily matches from all active leagues for a calendar date (YYYY-MM-DD). */
export async function getDailyMatches(
  matchDate: string,
): Promise<DailyMatchesResponse> {
  return fetchApi<DailyMatchesResponse>("/matches/daily", {
    match_date: matchDate,
  });
}

export async function getBetRecommendations(options?: {
  leagueIds?: number[];
  seasonId?: number;
  eventIds?: number[];
  modelIds?: number[];
  bookmakerIds?: number[];
  matchDate?: string;
  dateFrom?: string;
  dateTo?: string;
  fromNow?: boolean;
  minOdds?: number;
  positiveEvOnly?: boolean;
  applyTax?: boolean;
  settlementStatus?: SettlementStatus;
  sortBy?: BetSortBy;
  sortOrder?: BetSortOrder;
  page?: number;
  pageSize?: number;
}): Promise<BetRecommendationsResponse> {
  return fetchApi<BetRecommendationsResponse>("/bets/recommendations", {
    league_ids:
      options?.leagueIds && options.leagueIds.length > 0
        ? options.leagueIds.join(",")
        : undefined,
    season_id: options?.seasonId,
    event_ids:
      options?.eventIds && options.eventIds.length > 0
        ? options.eventIds.join(",")
        : undefined,
    model_ids:
      options?.modelIds && options.modelIds.length > 0
        ? options.modelIds.join(",")
        : undefined,
    bookmaker_ids:
      options?.bookmakerIds && options.bookmakerIds.length > 0
        ? options.bookmakerIds.join(",")
        : undefined,
    match_date: options?.matchDate,
    date_from: options?.dateFrom,
    date_to: options?.dateTo,
    from_now: options?.fromNow,
    min_odds: options?.minOdds,
    positive_ev_only: options?.positiveEvOnly,
    apply_tax: options?.applyTax,
    settlement_status: options?.settlementStatus,
    sort_by: options?.sortBy,
    sort_order: options?.sortOrder,
    page: options?.page,
    page_size: options?.pageSize,
  });
}

export async function getModelAnalytics(options?: {
  statType?: AnalyticsStatType;
  modelResultIds?: number[];
  modelOuIds?: number[];
  modelBttsIds?: number[];
  leagueIds?: number[];
  seasonId?: number;
  dateFrom?: string;
  dateTo?: string;
  roundFrom?: number;
  roundTo?: number;
  teamId?: number;
  settledOnly?: boolean;
  positiveEvOnly?: boolean;
  applyTax?: boolean;
  groupBy?: AnalyticsGroupBy;
  aggregationMetric?: AnalyticsAggregationMetric;
}): Promise<ModelAnalyticsResponse> {
  return fetchApi<ModelAnalyticsResponse>("/analytics/models", {
    stat_type: options?.statType,
    model_result_ids:
      options?.modelResultIds && options.modelResultIds.length > 0
        ? options.modelResultIds.join(",")
        : undefined,
    model_ou_ids:
      options?.modelOuIds && options.modelOuIds.length > 0
        ? options.modelOuIds.join(",")
        : undefined,
    model_btts_ids:
      options?.modelBttsIds && options.modelBttsIds.length > 0
        ? options.modelBttsIds.join(",")
        : undefined,
    league_ids:
      options?.leagueIds && options.leagueIds.length > 0
        ? options.leagueIds.join(",")
        : undefined,
    season_id: options?.seasonId,
    date_from: options?.dateFrom,
    date_to: options?.dateTo,
    round_from: options?.roundFrom,
    round_to: options?.roundTo,
    team_id: options?.teamId,
    settled_only: options?.settledOnly,
    positive_ev_only: options?.positiveEvOnly,
    apply_tax: options?.applyTax,
    group_by: options?.groupBy,
    aggregation_metric: options?.aggregationMetric,
  });
}

export async function getLeagueComparisons(options?: {
  leagueIds?: number[];
  seasonId?: number;
}): Promise<LeagueComparisonsResponse> {
  return fetchApi<LeagueComparisonsResponse>(
    "/analytics/league-comparisons",
    {
      league_ids:
        options?.leagueIds && options.leagueIds.length > 0
          ? options.leagueIds.join(",")
          : undefined,
      season_id: options?.seasonId,
    },
  );
}

export async function getModels(): Promise<ModelListResponse> {
  return fetchApi<ModelListResponse>("/models/models");
}

export async function getModelDetails(
  modelId: number,
): Promise<ModelDetailsResponse> {
  return fetchApi<ModelDetailsResponse>(`/models/models/${modelId}/details`);
}

export interface ModelsByFamily {
  result: FilterOption[];
  ou: FilterOption[];
  btts: FilterOption[];
}

export async function getModelsGroupedByFamily(
  sportId = 1,
): Promise<ModelsByFamily> {
  const { models } = await getModels();
  const activeModels = models.filter(
    (model) => model.active === 1 && model.sport_id === sportId,
  );

  const grouped: ModelsByFamily = {
    result: [],
    ou: [],
    btts: [],
  };

  const detailsList = await Promise.all(
    activeModels.map(async (model) => {
      try {
        return await getModelDetails(model.id);
      } catch {
        return null;
      }
    }),
  );

  for (const details of detailsList) {
    if (!details) {
      continue;
    }
    const option = { id: details.id, label: details.name };
    const familyNames = new Set(
      details.event_families.map((family) => family.name.toUpperCase()),
    );
    if (familyNames.has("REZULTAT")) {
      grouped.result.push(option);
    }
    if (familyNames.has("OU")) {
      grouped.ou.push(option);
    }
    if (familyNames.has("BTTS")) {
      grouped.btts.push(option);
    }
  }

  for (const key of Object.keys(grouped) as (keyof ModelsByFamily)[]) {
    grouped[key].sort((left, right) =>
      left.label.localeCompare(right.label, "pl"),
    );
  }

  return grouped;
}

export async function getSeasonOptions(
  sportId?: number,
): Promise<FilterOption[]> {
  const { leagues } = await getLeagues({
    active: true,
    sportId,
  });
  const seasons = new Map<number, string>();

  await Promise.all(
    leagues.slice(0, 12).map(async (league) => {
      try {
        const details = await getLeagueDetails(league.id);
        for (const season of details.seasons) {
          seasons.set(season.season_id, season.years);
        }
      } catch {
        // pomijamy ligi bez dostępnych sezonów
      }
    }),
  );

  return Array.from(seasons.entries())
    .map(([id, label]) => ({ id, label }))
    .sort((left, right) => right.id - left.id);
}

export async function getEventFamilies(
  sportId?: number,
): Promise<EventFamilyListResponse> {
  return fetchApi<EventFamilyListResponse>("/models/event-families", {
    sport_id: sportId,
  });
}

export async function getFamilyEvents(
  familyId: number,
): Promise<EventFamilyEventsResponse> {
  return fetchApi<EventFamilyEventsResponse>(
    `/models/event-family-mappings/${familyId}`,
  );
}

export async function getAllEventOptions(
  sportId = 1,
): Promise<{ id: number; label: string }[]> {
  const families = await getEventFamilies(sportId);
  const eventsById = new Map<number, string>();

  await Promise.all(
    families.event_families.map(async (family) => {
      const response = await getFamilyEvents(family.id);
      for (const mapping of response.family_events) {
        if (mapping.event_name) {
          eventsById.set(mapping.event_id, mapping.event_name);
        }
      }
    }),
  );

  return Array.from(eventsById.entries())
    .map(([id, label]) => ({ id, label }))
    .sort((left, right) => left.label.localeCompare(right.label, "pl"));
}

export async function getPlayerSports(): Promise<PlayerSportsListResponse> {
  return fetchApi<PlayerSportsListResponse>("/players/sports");
}

export async function getPlayerCountries(
  sportId: number,
): Promise<PlayerCountriesResponse> {
  return fetchApi<PlayerCountriesResponse>(
    `/players/${sportId}/filters/countries`,
  );
}

export async function getPlayerTeams(
  sportId: number,
  countryId?: number,
): Promise<PlayerTeamsResponse> {
  return fetchApi<PlayerTeamsResponse>(
    `/players/${sportId}/filters/teams`,
    { country_id: countryId },
  );
}

export async function getPlayerSeasons(
  sportId: number,
): Promise<PlayerSeasonsResponse> {
  return fetchApi<PlayerSeasonsResponse>(
    `/players/${sportId}/filters/seasons`,
  );
}

export async function getPlayers(options: {
  sportId: number;
  seasonId: number;
  teamId?: number;
  search?: string;
}): Promise<FootballPlayersListResponse> {
  return fetchApi<FootballPlayersListResponse>(
    `/players/${options.sportId}`,
    {
      season_id: options.seasonId,
      team_id: options.teamId,
      search: options.search,
    },
  );
}

export async function getPlayerMatchStats(
  sportId: number,
  playerId: number,
  options: { seasonId: number; limit?: number },
): Promise<PlayerMatchStatsResponse> {
  return fetchApi<PlayerMatchStatsResponse>(
    `/players/${sportId}/${playerId}/match-stats`,
    {
      season_id: options.seasonId,
      limit: options.limit ?? 50,
    },
  );
}
