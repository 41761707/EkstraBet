import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { StatusMessage } from "@/components/StatusMessage";
import { TyperLmDashboard } from "@/components/typer-lm/TyperLmDashboard";
import {
  ApiError,
  getCurrentUser,
  getTyperDashboard,
  getTyperLeaderboard,
} from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import type { TyperLeaderboardRow } from "@/types/api";

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
          Typuj regulaminowe 1 / X / 2 w opublikowanych meczach Ligi Mistrzów.
          Kurs Superbet może pojawić się później — to nie blokuje zapisu typu.
        </p>
      </section>
      <TyperLmDashboard
        dashboard={page.dashboard}
        leaderboard={page.leaderboard}
        leaderboardError={page.leaderboardError}
        currentUserUuid={page.userUuid}
        currentUserDisplayName={page.displayName}
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
    }
  | { kind: "unauthenticated" }
  | { kind: "error"; message: string };

async function loadTyperLmPage(): Promise<TyperLmPageResult> {
  try {
    const user = await getCurrentUser();
    const dashboard = await getTyperDashboard();
    const leaderboardResult = await loadLeaderboard(dashboard.season_id);
    return {
      kind: "ok",
      dashboard,
      leaderboard: leaderboardResult.rows,
      leaderboardError: leaderboardResult.error,
      userUuid: user.uuid,
      displayName: user.display_name?.trim() || user.username,
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
