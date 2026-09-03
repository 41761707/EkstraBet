import Link from "next/link";

import { BetRecommendationsTable } from "@/components/bets/BetRecommendationsTable";
import { BetsFilters } from "@/components/bets/BetsFilters";
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
} from "@/lib/betsFilterParams";
import type { BetRecommendationsResponse, FilterOption } from "@/types/api";

const PAGE_SIZE = 50;

export const dynamic = "force-dynamic";

interface BetsPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

export default async function BetsPage({ searchParams }: BetsPageProps) {
  const params = await searchParams;
  const filters = parseBetsFilterValues(params);
  const filterOptions = await loadBetsFilterOptions();

  if (!filterOptions.ok) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować filtrów bukmacherskich"
        message={filterOptions.message}
      />
    );
  }

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

  try {
    const dateParams = betsDateQueryParams(filters);
    const response = await getBetRecommendations({
      leagueIds: filters.leagueIds,
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
          searchParams={params}
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

async function loadBetsFilterOptions(): Promise<
  | {
      ok: true;
      leagues: FilterOption[];
      events: EventFilterOption[];
      models: FilterOption[];
    }
  | { ok: false; message: string }
> {
  try {
    const [leaguesResponse, eventsResponse, modelsResponse] = await Promise.all([
      getLeagues({ active: true }),
      getAllEventOptions(),
      getModels(),
    ]);
    return {
      ok: true,
      leagues: leaguesResponse.leagues.map((league) => ({
        id: league.id,
        label: league.name,
      })),
      events: eventsResponse,
      models: modelsResponse.models
        .filter((model) => model.active === 1)
        .map((model) => ({ id: model.id, label: model.name }))
        .sort((left, right) => left.label.localeCompare(right.label, "pl")),
    };
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować filtrów bukmacherskich z API.";
    return { ok: false, message };
  }
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
