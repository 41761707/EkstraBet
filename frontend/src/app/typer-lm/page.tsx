import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { StatusMessage } from "@/components/StatusMessage";
import { TyperLmAdminSection } from "@/components/typer-lm/TyperLmAdminPanel";
import { TyperLmDashboard } from "@/components/typer-lm/TyperLmDashboard";
import { TyperLmRules } from "@/components/typer-lm/TyperLmRules";
import {
  ApiError,
  getCurrentUser,
  getLeagueRounds,
  getTyperAdminCandidates,
  getTyperDashboard,
  getTyperLeaderboard,
  getTyperLongTermAutoResult,
  getTyperLongTermDashboard,
} from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import {
  CHAMPIONS_LEAGUE_LEAGUE_ID,
  GROUP_STAGE_MATCH_COUNT,
  resolveGroupMatchCount,
  selectKnockoutRounds,
} from "@/lib/typerLmAdmin";
import type {
  LeagueRound,
  LongTermAutoResultResponse,
  LongTermDashboardResponse,
  LongTermMarketCard,
  TyperAdminCandidate,
  TyperLeaderboardRow,
} from "@/types/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Typer LM | EkstraBet",
  description:
    "Typuj wyniki Ligi Mistrzów 1X2, śledź własną historię zmian i ranking.",
};

export default async function TyperLmPage() {
  if (!isAuthEnabled()) {
    redirect("/");
  }

  const page = await loadTyperLmPage();
  if (page.kind === "unauthenticated") {
    redirect("/login");
  }
  if (page.kind === "error") {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować Typera LM"
        message={page.message}
      />
    );
  }

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold text-text">Typer LM</h1>
        <p className="text-muted">
          Typuj wyniki spotkań w ramach Ligi Mistrzów w sezonie 2026/2027.
        </p>
      </section>
      <TyperLmRules />
      <TyperLmAdminSection
        isAdmin={page.isAdmin}
        seasonId={page.dashboard.season_id}
        initialCandidates={page.adminCandidates}
        initialGroupMatchCount={page.groupMatchCount}
        knockoutRounds={page.knockoutRounds}
        knockoutRoundsError={page.knockoutRoundsError}
        longTermMarkets={page.longTermDashboard?.markets ?? []}
        longTermAutoResults={page.longTermAutoResults}
      />
      <TyperLmDashboard
        dashboard={page.dashboard}
        leaderboard={page.leaderboard}
        leaderboardError={page.leaderboardError}
        currentUserUuid={page.userUuid}
        currentUserDisplayName={page.displayName}
        longTermDashboard={page.longTermDashboard}
        longTermError={page.longTermError}
      />
    </div>
  );
}

type TyperLmPageResult =
  | {
      kind: "ok";
      dashboard: Awaited<ReturnType<typeof getTyperDashboard>>;
      leaderboard: TyperLeaderboardRow[];
      leaderboardError?: string;
      userUuid: string;
      displayName: string;
      isAdmin: boolean;
      adminCandidates: TyperAdminCandidate[] | null;
      groupMatchCount: number;
      knockoutRounds: LeagueRound[];
      knockoutRoundsError?: string;
      longTermDashboard: LongTermDashboardResponse | null;
      longTermError?: string;
      longTermAutoResults: Record<number, LongTermAutoResultResponse | null>;
    }
  | { kind: "unauthenticated" }
  | { kind: "error"; message: string };

async function loadTyperLmPage(): Promise<TyperLmPageResult> {
  try {
    const user = await getCurrentUser();
    const dashboard = await getTyperDashboard();
    const [leaderboardResult, adminBootstrap, longTermResult] =
      await Promise.all([
        loadLeaderboard(dashboard.season_id),
        user.is_admin
          ? loadAdminBootstrap(dashboard.season_id)
          : Promise.resolve(emptyAdminBootstrap()),
        loadLongTermDashboard(dashboard.season_id),
      ]);
    const longTermAutoResults = user.is_admin
      ? await loadLongTermAutoResults(longTermResult.dashboard?.markets ?? [])
      : {};
    return {
      kind: "ok",
      dashboard,
      leaderboard: leaderboardResult.rows,
      leaderboardError: leaderboardResult.error,
      userUuid: user.uuid,
      displayName: user.display_name?.trim() || user.username,
      isAdmin: user.is_admin,
      adminCandidates: adminBootstrap.candidates,
      groupMatchCount: adminBootstrap.groupMatchCount,
      knockoutRounds: adminBootstrap.knockoutRounds,
      knockoutRoundsError: adminBootstrap.knockoutRoundsError,
      longTermDashboard: longTermResult.dashboard,
      longTermError: longTermResult.error,
      longTermAutoResults,
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthenticated" };
    }
    const message =
      error instanceof ApiError
        ? error.message
        : "Spróbuj odświeżyć stronę. Jeśli problem wraca, zaloguj się ponownie.";
    return { kind: "error", message };
  }
}

function emptyAdminBootstrap(): {
  candidates: TyperAdminCandidate[] | null;
  groupMatchCount: number;
  knockoutRounds: LeagueRound[];
  knockoutRoundsError?: string;
} {
  return {
    candidates: null,
    groupMatchCount: GROUP_STAGE_MATCH_COUNT,
    knockoutRounds: [],
    knockoutRoundsError: undefined,
  };
}

async function loadAdminBootstrap(seasonId: number): Promise<{
  candidates: TyperAdminCandidate[] | null;
  groupMatchCount: number;
  knockoutRounds: LeagueRound[];
  knockoutRoundsError?: string;
}> {
  const [candidateResult, knockoutResult] = await Promise.all([
    loadAdminCandidates(seasonId),
    loadKnockoutRounds(seasonId),
  ]);
  return {
    candidates: candidateResult.candidates,
    groupMatchCount: candidateResult.groupMatchCount,
    knockoutRounds: knockoutResult.rounds,
    knockoutRoundsError: knockoutResult.error,
  };
}

async function loadAdminCandidates(
  seasonId: number,
): Promise<{
  candidates: TyperAdminCandidate[] | null;
  groupMatchCount: number;
}> {
  try {
    const payload = await getTyperAdminCandidates(seasonId, 1);
    return {
      candidates: payload.candidates,
      groupMatchCount: resolveGroupMatchCount(payload.group_match_count),
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { candidates: [], groupMatchCount: GROUP_STAGE_MATCH_COUNT };
    }
    // błąd panelu nie może zablokować widoku uczestnika
    return { candidates: null, groupMatchCount: GROUP_STAGE_MATCH_COUNT };
  }
}

async function loadKnockoutRounds(
  seasonId: number,
): Promise<{ rounds: LeagueRound[]; error?: string }> {
  try {
    const payload = await getLeagueRounds(CHAMPIONS_LEAGUE_LEAGUE_ID, seasonId);
    return { rounds: selectKnockoutRounds(payload.rounds) };
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się wczytać rund pucharowych. Wpisz numer rundy.";
    return { rounds: [], error: message };
  }
}

async function loadLeaderboard(
  seasonId: number,
): Promise<{ rows: TyperLeaderboardRow[]; error?: string }> {
  try {
    const rows = await getTyperLeaderboard(seasonId);
    return { rows };
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować rankingu z API.";
    return { rows: [], error: message };
  }
}

async function loadLongTermDashboard(
  seasonId: number,
): Promise<{
  dashboard: LongTermDashboardResponse | null;
  error?: string;
}> {
  try {
    const dashboard = await getTyperLongTermDashboard(seasonId);
    return { dashboard };
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować rynków długoterminowych.";
    return { dashboard: null, error: message };
  }
}

async function loadLongTermAutoResults(
  markets: readonly LongTermMarketCard[],
): Promise<Record<number, LongTermAutoResultResponse | null>> {
  const entries = await Promise.all(
    markets.map(async (market) => {
      try {
        const payload = await getTyperLongTermAutoResult(market.market_id);
        return [market.market_id, payload] as const;
      } catch {
        // błąd propozycji nie może zablokować panelu administratora
        return [market.market_id, null] as const;
      }
    }),
  );
  return Object.fromEntries(entries);
}
