import type { ReactNode } from "react";
import Link from "next/link";

import { BetRecommendationsTable } from "@/components/bets/BetRecommendationsTable";
import { BetsFilters } from "@/components/bets/BetsFilters";
import { PlayerBetsBody } from "@/components/bets/PlayerBetsBody";
import { PaginationBar } from "@/components/PaginationBar";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getAllEventOptions,
  getBetRecommendations,
  getLeagues,
  getModels,
} from "@/lib/api";
import type { EventFilterOption } from "@/lib/betEventOptions";
import {
  areBetsDateFiltersValid,
  betsDateQueryParams,
  betsFilterPath,
  parseBetsFilterValues,
  type BetsFilterValues,
  type BetsSubject,
} from "@/lib/betsFilterParams";
import { PLAYER_PROP_EVENT_OPTIONS } from "@/lib/playerPropEvents";
import {
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type BetRecommendationsResponse,
  type FilterOption,
  type LeagueSummary,
  type ModelSummary,
} from "@/types/api";

const PAGE_SIZE = 50;

export const dynamic = "force-dynamic";

interface BetsPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

interface LoadedBetsFilters {
  leagues: FilterOption[];
  events: EventFilterOption[];
  models: FilterOption[];
}

export default async function BetsPage({ searchParams }: BetsPageProps) {
  const params = await searchParams;
  const parsedFilters = parseBetsFilterValues(params);
  const sportId = resolveBetsSportId(parsedFilters.sportId);
  const filterOptions = await loadBetsFilterOptions(
    sportId,
    parsedFilters.subject,
  );

  if (!filterOptions.ok) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować filtrów bukmacherskich"
        message={filterOptions.message}
      />
    );
  }

  const filters = sanitizeBetsFilters(parsedFilters, sportId, filterOptions);
  return (
    <BetsPageLayout
      filters={filters}
      filterOptions={filterOptions}
      searchParams={params}
    />
  );
}

function BetsPageLayout({
  filters,
  filterOptions,
  searchParams,
}: {
  filters: BetsFilterValues;
  filterOptions: LoadedBetsFilters;
  searchParams: Record<string, string | undefined>;
}) {
  const filtersSection = (
    <BetsFiltersSection
      filters={filters}
      leagues={filterOptions.leagues}
      events={filterOptions.events}
      models={filterOptions.models}
    />
  );

  if (!areBetsDateFiltersValid(filters)) {
    return (
      <div className="space-y-8">
        <BetsPageHeader />
        {filtersSection}
        <StatusMessage
          variant="error"
          title="Nieprawidłowy przedział dat"
          message="Data od nie może być późniejsza niż data do."
        />
      </div>
    );
  }

  if (isPlayerBetsView(filters)) {
    return (
      <div className="space-y-8">
        <BetsPageHeader />
        {filtersSection}
        <PlayerBetsBody
          filters={filters}
          leagues={filterOptions.leagues}
          pageSize={PAGE_SIZE}
          searchParams={searchParams}
        />
      </div>
    );
  }

  return (
    <TeamBetsLayout
      filters={filters}
      leagues={filterOptions.leagues}
      filtersSection={filtersSection}
      searchParams={searchParams}
    />
  );
}

async function TeamBetsLayout({
  filters,
  leagues,
  filtersSection,
  searchParams,
}: {
  filters: BetsFilterValues;
  leagues: FilterOption[];
  filtersSection: ReactNode;
  searchParams: Record<string, string | undefined>;
}) {
  try {
    const dateParams = betsDateQueryParams(filters);
    const response = await getBetRecommendations({
      leagueIds:
        filters.leagueIds.length > 0
          ? filters.leagueIds
          : leagues.map((league) => league.id),
      eventIds: filters.eventIds,
      modelIds: filters.modelIds,
      minOdds: filters.minOdds,
      positiveEvOnly: filters.positiveEvOnly,
      applyTax: filters.applyTax,
      settlementStatus: filters.settlementStatus || undefined,
      sortBy: filters.sortBy,
      sortOrder: filters.sortOrder,
      page: filters.page,
      pageSize: PAGE_SIZE,
      ...dateParams,
    });

    return (
      <div className="space-y-8">
        <BetsPageHeader />
        {filtersSection}
        <BetsRecommendationsSection
          response={response}
          filters={filters}
          searchParams={searchParams}
        />
      </div>
    );
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować rekomendacji bukmacherskich z API.";
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować rekomendacji bukmacherskich"
        message={message}
      />
    );
  }
}

async function loadBetsFilterOptions(
  sportId: number,
  subject: BetsSubject,
): Promise<({ ok: true } & LoadedBetsFilters) | { ok: false; message: string }> {
  try {
    if (isPlayerBetsView({ sportId, subject })) {
      return await loadPlayerFilterOptions(sportId);
    }
    return await loadTeamFilterOptions(sportId);
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować filtrów bukmacherskich z API.";
    return { ok: false, message };
  }
}

async function loadTeamFilterOptions(
  sportId: number,
): Promise<{ ok: true } & LoadedBetsFilters> {
  const [leaguesResponse, eventsResponse, modelsResponse] = await Promise.all([
    getLeagues({ active: true, sportId }),
    getAllEventOptions(sportId),
    getModels(),
  ]);
  return {
    ok: true,
    leagues: toLeagueOptions(leaguesResponse.leagues),
    events: eventsResponse,
    models: toModelOptions(modelsResponse.models, sportId),
  };
}

async function loadPlayerFilterOptions(
  sportId: number,
): Promise<{ ok: true } & LoadedBetsFilters> {
  const [leaguesResponse, modelsResponse] = await Promise.all([
    getLeagues({ active: true, sportId }),
    getModels(),
  ]);
  return {
    ok: true,
    leagues: toLeagueOptions(leaguesResponse.leagues),
    events: PLAYER_PROP_EVENT_OPTIONS.map((event) => ({
      id: event.id,
      label: event.label,
      familyName: "PLAYER_PROP",
    })),
    models: toModelOptions(modelsResponse.models, sportId),
  };
}

function sanitizeBetsFilters(
  parsedFilters: BetsFilterValues,
  sportId: number,
  options: LoadedBetsFilters,
): BetsFilterValues {
  return {
    ...parsedFilters,
    sportId,
    leagueIds: parsedFilters.leagueIds.filter((id) =>
      options.leagues.some((league) => league.id === id),
    ),
    eventIds: parsedFilters.eventIds.filter((id) =>
      options.events.some((event) => event.id === id),
    ),
    modelIds: parsedFilters.modelIds.filter((id) =>
      options.models.some((model) => model.id === id),
    ),
  };
}

function resolveBetsSportId(sportId: number): number {
  return sportId === HOCKEY_SPORT_ID ? HOCKEY_SPORT_ID : FOOTBALL_SPORT_ID;
}

function isPlayerBetsView(filters: {
  sportId: number;
  subject: BetsSubject;
}): boolean {
  return filters.subject === "players" && filters.sportId === HOCKEY_SPORT_ID;
}

function toLeagueOptions(leagues: LeagueSummary[]): FilterOption[] {
  return leagues.map((league) => ({
    id: league.id,
    label: league.name,
  }));
}

function toModelOptions(models: ModelSummary[], sportId: number): FilterOption[] {
  return models
    .filter((model) => model.active === 1 && model.sport_id === sportId)
    .map((model) => ({ id: model.id, label: model.name }))
    .sort((left, right) => left.label.localeCompare(right.label, "pl"));
}

function BetsPageHeader() {
  return (
    <section className="space-y-2">
      <Link
        href="/"
        className="text-sm text-accent-text transition hover:text-accent-text-hover"
      >
        ← Powrót do lig
      </Link>
      <h1 className="text-3xl font-bold text-text">Kącik Bukmacherski</h1>
      <p className="text-muted">
        Rekomendowane zakłady na dowolne ligi i zakłady
      </p>
    </section>
  );
}

function BetsFiltersSection({
  filters,
  leagues,
  events,
  models,
}: {
  filters: BetsFilterValues;
  leagues: FilterOption[];
  events: EventFilterOption[];
  models: FilterOption[];
}) {
  return (
    <section className="space-y-4 rounded-xl border border-border bg-surface p-5">
      <h2 className="text-lg font-semibold text-text">Filtry</h2>
      <BetsFilters
        key={betsFilterPath(filters)}
        leagues={leagues}
        events={events}
        models={models}
        values={filters}
      />
    </section>
  );
}

function BetsRecommendationsSection({
  response,
  filters,
  searchParams,
}: {
  response: BetRecommendationsResponse;
  filters: BetsFilterValues;
  searchParams: Record<string, string | undefined>;
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-text">Rekomendacje</h2>
        <span className="text-sm text-muted">
          {response.total_count} zakładów
        </span>
      </div>
      {response.recommendations.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Nie ma rekomendacji"
          message="Spróbuj dopasować filtry lub zmienić przedział dat."
        />
      ) : (
        <>
          <BetRecommendationsTable
            recommendations={response.recommendations}
            applyTax={filters.applyTax}
          />
          <PaginationBar
            basePath="/bets"
            currentPage={filters.page}
            totalCount={response.total_count}
            pageSize={PAGE_SIZE}
            searchParams={searchParams}
          />
        </>
      )}
    </section>
  );
}
