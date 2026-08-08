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
import type {
  PlayerMatchStatsResponse,
  PredictionPreviewRequest,
  PredictionPreviewResponse,
  SeasonProjectionMode,
  SeasonProjectionResponse,
  SportTeamHistoryResponse,
} from "@/types/api";

export { ApiError, buildClientProxyPath } from "@/lib/apiShared";

async function fetchViaBff<T>(
  path: string,
  params?: SearchParams,
  init?: RequestInit,
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
    throw new ApiError(response.status, message);
  }

  return response.json() as Promise<T>;
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
