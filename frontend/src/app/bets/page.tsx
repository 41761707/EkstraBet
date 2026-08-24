import Link from "next/link";
import { BetRecommendationsTable } from "@/components/bets/BetRecommendationsTable";
import { BetsFilters } from "@/components/bets/BetsFilters";
import {
  betsFilterPath,
  type BetsFilterValues,
} from "@/lib/betsFilterParams";
import { PaginationBar } from "@/components/PaginationBar";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getAllEventOptions,
  getBetRecommendations,
  getLeagues,
  getModels,
} from "@/lib/api";
import {
  parseBoolean,
  parseIdList,
  parsePositiveInt,
  todayIsoDate,
} from "@/lib/searchParams";
import type {
  BetSortBy,
  BetSortOrder,
  FilterOption,
  SettlementStatus,
} from "@/types/api";

const PAGE_SIZE = 50;

export const dynamic = "force-dynamic";

interface BetsPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

function parseFilters(
  params: Record<string, string | undefined>,
): BetsFilterValues {
  return {
    leagueIds: parseIdList(params.league_ids),
    eventIds: parseIdList(params.event_ids),
    modelIds: parseIdList(params.model_ids),
    matchDate: params.match_date ?? todayIsoDate(),
    fromNow: parseBoolean(params.from_now),
    minOdds: params.min_odds ? Number(params.min_odds) : 1.5,
    positiveEvOnly: parseBoolean(params.positive_ev_only),
    applyTax: parseBoolean(params.apply_tax),
    settlementStatus: (params.settlement_status ?? "") as
      | SettlementStatus
      | "",
    sortBy: (params.sort_by as BetSortBy | undefined) ?? "ev",
    sortOrder: (params.sort_order as BetSortOrder | undefined) ?? "desc",
    page: parsePositiveInt(params.page) ?? 1,
  };
}

export default async function BetsPage({ searchParams }: BetsPageProps) {
  const params = await searchParams;
  const filters = parseFilters(params);

  let leagues: FilterOption[] = [];
  let events: FilterOption[] = [];
  let models: FilterOption[] = [];

  try {
    const [leaguesResponse, eventsResponse, modelsResponse] = await Promise.all([
      getLeagues({ active: true }),
      getAllEventOptions(),
      getModels(),
    ]);

    leagues = leaguesResponse.leagues.map((league) => ({
      id: league.id,
      label: league.name,
    }));
    events = eventsResponse;
    models = modelsResponse.models
      .filter((model) => model.active === 1)
      .map((model) => ({
        id: model.id,
        label: model.name,
      }))
      .sort((left, right) => left.label.localeCompare(right.label, "pl"));
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować filtrów bukmacherskich z API.";

    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować filtrów bukmacherskich"
        message={message}
      />
    );
  }

  try {
    const response = await getBetRecommendations({
      leagueIds: filters.leagueIds,
      eventIds: filters.eventIds,
      modelIds: filters.modelIds,
      matchDate: filters.fromNow ? undefined : filters.matchDate,
      fromNow: filters.fromNow,
      minOdds: filters.minOdds,
      positiveEvOnly: filters.positiveEvOnly,
      applyTax: filters.applyTax,
      settlementStatus: filters.settlementStatus || undefined,
      sortBy: filters.sortBy,
      sortOrder: filters.sortOrder,
      page: filters.page,
      pageSize: PAGE_SIZE,
    });

    return (
      <div className="space-y-8">
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

        <section className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-lg font-semibold text-text">
              Rekomendacje
            </h2>
            <span className="text-sm text-muted">
              {response.total_count} zakładów
            </span>
          </div>

          {response.recommendations.length === 0 ? (
            <StatusMessage
              variant="empty"
              title="Nie ma rekomendacji"
              message="Spróbuj dopasować filtry lub wybrać inną datę meczu."
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
                searchParams={params}
              />
            </>
          )}
        </section>
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
