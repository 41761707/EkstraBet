import type { ApiErrorBody, HeadToHeadSummary, MatchDetails } from "@/types/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type SearchParams = Record<
  string,
  string | number | boolean | undefined | null
>;

export function applySearchParams(url: URL, params?: SearchParams): void {
  if (!params) {
    return;
  }
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }
}

/**
 * Relative BFF path for browser calls. Never embeds the FastAPI host —
 * Client Components must use this (or `@/lib/apiClient`) instead of API_BASE_URL.
 */
export function buildClientProxyPath(
  path: string,
  params?: SearchParams,
): string {
  const normalized = path.startsWith("/") ? path.slice(1) : path;
  const url = new URL(`/api/backend/${normalized}`, "http://browser.local");
  applySearchParams(url, params);
  return `${url.pathname}${url.search}`;
}

export async function parseErrorMessage(response: Response): Promise<string> {
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

/** Fills missing fields from older API responses / Next.js cache. */
export function normalizeMatchDetails(payload: MatchDetails): MatchDetails {
  const homeTeamId = payload.home_team?.id ?? 0;
  const awayTeamId = payload.away_team?.id ?? 0;

  return {
    ...payload,
    final_predictions: payload.final_predictions ?? [],
    prediction_analysis: payload.prediction_analysis ?? null,
    odds: payload.odds ?? [],
    has_player_stats: payload.has_player_stats ?? false,
    head_to_head:
      payload.head_to_head ?? emptyHeadToHead(homeTeamId, awayTeamId),
    home_team_history: payload.home_team_history ?? [],
    away_team_history: payload.away_team_history ?? [],
    boxscore: payload.boxscore ?? null,
    model_assessments: payload.model_assessments ?? [],
  };
}
