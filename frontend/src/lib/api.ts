import { decodeRouteParam } from "@/lib/leaguePaths";
import type {
  ApiErrorBody,
  AnalyticsAggregationMetric,
  AnalyticsGroupBy,
  AnalyticsStatType,
  BetRecommendationsResponse,
  BetSortBy,
  BetSortOrder,
  EventFamilyEventsResponse,
  EventFamilyListResponse,
  HeadToHeadSummary,
  LeagueDetails,
  LeagueCharacteristics,
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
} from "@/types/api";

import { getServerAuthHeaders } from "@/lib/auth";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getApiBaseUrl(): string {
  return (
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    DEFAULT_API_BASE_URL
  );
}

function applySearchParams(
  url: URL,
  params?: Record<string, string | number | boolean | undefined | null>,
): void {
  if (!params) {
    return;
  }
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }
}

function buildUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
): string {
  const url = new URL(path, getApiBaseUrl());
  applySearchParams(url, params);
  return url.toString();
}

/** Browser calls go through Next proxy so HttpOnly cookie can attach Bearer. */
function buildClientProxyUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
): string {
  const normalized = path.startsWith("/") ? path.slice(1) : path;
  const url = new URL(`/api/backend/${normalized}`, window.location.origin);
  applySearchParams(url, params);
  return url.toString();
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      return body.detail.map((item) => item.msg).join(", ");
    }
  } catch {
    // odpowiedź bez JSON — zostaw domyślny komunikat
  }
  return `Request failed with status ${response.status}`;
}

async function fetchApi<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
  init?: RequestInit,
): Promise<T> {
  const isBrowser = typeof window !== "undefined";
  const url = isBrowser
    ? buildClientProxyUrl(path, params)
    : buildUrl(path, params);
  const authHeaders = isBrowser ? {} : await getServerAuthHeaders();

  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: "application/json",
      ...authHeaders,
      ...init?.headers,
    },
    ...(isBrowser ? { cache: "no-store" as const } : { next: { revalidate: 60 } }),
  });

  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
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

function emptyHeadToHead(
  homeTeamId: number,
  awayTeamId: number,
): HeadToHeadSummary {
  return {
    team_id: homeTeamId,
    opponent_id: awayTeamId,
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goals_for: 0,
    goals_conceded: 0,
    btts_count: 0,
    btts_percentage: 0,
    avg_goals_per_match: 0,
    meetings: [],
  };
}

/** Uzupełnia brakujące pola z starszych odpowiedzi API / cache Next.js. */
export function normalizeMatchDetails(payload: MatchDetails): MatchDetails {
  const homeTeamId = payload.home_team?.id ?? 0;
  const awayTeamId = payload.away_team?.id ?? 0;

  return {
    ...payload,
    final_predictions: payload.final_predictions ?? [],
    odds: payload.odds ?? [],
    has_player_stats: payload.has_player_stats ?? false,
    head_to_head:
      payload.head_to_head ?? emptyHeadToHead(homeTeamId, awayTeamId),
    home_team_history: payload.home_team_history ?? [],
    away_team_history: payload.away_team_history ?? [],
    boxscore: payload.boxscore ?? null,
  };
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
  includeLeagueCharacteristics?: boolean;
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
    include_league_characteristics: options?.includeLeagueCharacteristics,
  });
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

export async function getSeasonOptions(): Promise<FilterOption[]> {
  const { leagues } = await getLeagues({ active: true });
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
