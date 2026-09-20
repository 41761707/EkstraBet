import type { Metadata } from "next";
import type { ReactNode } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { TipsterFilters } from "@/components/tipsters/TipsterFilters";
import { TipsterLeaderboard } from "@/components/tipsters/TipsterLeaderboard";
import {
  areTipsterDateFiltersValid,
  parseTipsterLeaderboardFilters,
  tipsterFilterCatalogMessage,
  TIPSTER_FILTER_CATALOG_ERROR_TITLE,
  tipsterLeaderboardPath,
  toTipsterLeaderboardQuery,
  type TipsterLeaderboardFilters,
} from "@/components/tipsters/tipsterModel";
import {
  ApiError,
  getEventFamilies,
  getLeagues,
  getTipsterLeaderboard,
} from "@/lib/api";
import {
  FOOTBALL_SPORT_ID,
  type FilterOption,
  type LeaderboardResponse,
} from "@/types/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Ranking typerów | EkstraBet",
  description:
    "Porównaj ludzi i konta systemowe po proficie, ROI i skuteczności.",
};

interface TypersPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

export default async function TypersPage({ searchParams }: TypersPageProps) {
  const params = await searchParams;
  const filters = parseTipsterLeaderboardFilters(params);
  const filterOptionsPromise = loadTypersFilterOptions();

  if (!areTipsterDateFiltersValid(filters)) {
    const filterOptions = await filterOptionsPromise;
    return (
      <TypersPageLayout filters={filters} filterOptions={filterOptions}>
        <StatusMessage
          variant="error"
          title="Nieprawidłowy przedział dat"
          message="Data od nie może być późniejsza niż data do."
        />
      </TypersPageLayout>
    );
  }

  const [filterOptions, ranking] = await Promise.all([
    filterOptionsPromise,
    loadLeaderboard(filters),
  ]);

  return (
    <TypersPageLayout filters={filters} filterOptions={filterOptions}>
      {ranking.ok ? (
        <TipsterLeaderboard
          rows={ranking.response.items}
          total={ranking.response.total}
          page={filters.page}
          pageSize={filters.pageSize}
          searchParams={params}
        />
      ) : (
        <StatusMessage
          variant="error"
          title="Nie udało się załadować rankingu typerów"
          message={ranking.message}
        />
      )}
    </TypersPageLayout>
  );
}

interface TypersFilterOptions {
  leagues: FilterOption[];
  eventFamilies: FilterOption[];
  leaguesFailed: boolean;
  familiesFailed: boolean;
}

function TypersPageLayout({
  filters,
  filterOptions,
  children,
}: {
  filters: TipsterLeaderboardFilters;
  filterOptions: TypersFilterOptions;
  children: ReactNode;
}) {
  const filterWarning = tipsterFilterCatalogMessage(
    filterOptions.leaguesFailed,
    filterOptions.familiesFailed,
  );
  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold text-text">Ranking typerów</h1>
        <p className="text-muted">
          Agregaty ludzi i kont systemowych. Wiersz otwiera publiczny profil.
        </p>
      </section>
      <section className="space-y-4 rounded-xl border border-border bg-surface p-5">
        <h2 className="text-lg font-semibold text-text">Filtry</h2>
        {filterWarning ? (
          <StatusMessage
            variant="info"
            title={TIPSTER_FILTER_CATALOG_ERROR_TITLE}
            message={filterWarning}
          />
        ) : null}
        <TipsterFilters
          key={tipsterLeaderboardPath(filters)}
          values={filters}
          leagues={filterOptions.leagues}
          eventFamilies={filterOptions.eventFamilies}
        />
      </section>
      {children}
    </div>
  );
}

async function loadTypersFilterOptions(): Promise<TypersFilterOptions> {
  const [leaguesResult, familiesResult] = await Promise.allSettled([
    getLeagues({ active: true, sportId: FOOTBALL_SPORT_ID }),
    getEventFamilies(FOOTBALL_SPORT_ID),
  ]);

  return {
    leagues:
      leaguesResult.status === "fulfilled"
        ? leaguesResult.value.leagues.map((league) => ({
            id: league.id,
            label: league.name,
          }))
        : [],
    eventFamilies:
      familiesResult.status === "fulfilled"
        ? familiesResult.value.event_families.map((family) => ({
            id: family.id,
            label: family.name,
          }))
        : [],
    leaguesFailed: leaguesResult.status === "rejected",
    familiesFailed: familiesResult.status === "rejected",
  };
}

async function loadLeaderboard(
  filters: TipsterLeaderboardFilters,
): Promise<
  | { ok: true; response: LeaderboardResponse }
  | { ok: false; message: string }
> {
  try {
    const response = await getTipsterLeaderboard(
      toTipsterLeaderboardQuery(filters),
    );
    return { ok: true, response };
  } catch (error) {
    return {
      ok: false,
      message:
        error instanceof ApiError
          ? error.message
          : "Nie udało się załadować rankingu typerów z API.",
    };
  }
}
