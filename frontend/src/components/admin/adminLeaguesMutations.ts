import {
  ADMIN_LEAGUE_CREATE_ERROR_TITLE,
  ADMIN_LEAGUE_TOGGLE_ERROR_TITLE,
  mapAdminLeagueError,
} from "@/components/admin/adminLeaguesModel";
import {
  createAdminLeague,
  setAdminLeagueActive,
} from "@/lib/apiClient";
import type { AdminLeague, CreateLeagueRequest } from "@/types/api";

export type AdminLeaguesMutationFailure = {
  ok: false;
  errorTitle: string;
  errorMessage: string;
};

export type AdminLeaguesMutationResult =
  | { ok: true; league: AdminLeague }
  | AdminLeaguesMutationFailure;

export async function submitCreateAdminLeague(
  request: CreateLeagueRequest,
): Promise<AdminLeaguesMutationResult> {
  try {
    const league = await createAdminLeague(request);
    return { ok: true, league };
  } catch (error) {
    return {
      ok: false,
      errorTitle: ADMIN_LEAGUE_CREATE_ERROR_TITLE,
      errorMessage: mapAdminLeagueError(error),
    };
  }
}

export async function submitToggleLeagueActive(
  league: AdminLeague,
): Promise<AdminLeaguesMutationResult> {
  try {
    const updated = await setAdminLeagueActive(league.id, !league.active);
    return { ok: true, league: updated };
  } catch (error) {
    return {
      ok: false,
      errorTitle: ADMIN_LEAGUE_TOGGLE_ERROR_TITLE,
      errorMessage: mapAdminLeagueError(error),
    };
  }
}
