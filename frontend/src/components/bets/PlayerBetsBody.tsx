import { PlayerBetRecommendationsTable } from "@/components/bets/PlayerBetRecommendationsTable";
import { PaginationBar } from "@/components/PaginationBar";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getPlayerBetRecommendations } from "@/lib/api";
import {
  betsDateQueryParams,
  type BetsFilterValues,
} from "@/lib/betsFilterParams";
import type {
  FilterOption,
  PlayerPropRecommendationsResponse,
} from "@/types/api";

interface PlayerBetsBodyProps {
  filters: BetsFilterValues;
  leagues: FilterOption[];
  pageSize: number;
  searchParams: Record<string, string | undefined>;
}

/** Server read of hockey player recommendations for the bookmaking corner. */
export async function PlayerBetsBody({
  filters,
  leagues,
  pageSize,
  searchParams,
}: PlayerBetsBodyProps) {
  try {
    const dateParams = betsDateQueryParams(filters);
    const response = await getPlayerBetRecommendations({
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
      historyWindow: filters.historyWindow,
      page: filters.page,
      pageSize,
      ...dateParams,
    });
    return (
      <PlayerRecommendationsSection
        response={response}
        filters={filters}
        pageSize={pageSize}
        searchParams={searchParams}
      />
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

function PlayerRecommendationsSection({
  response,
  filters,
  pageSize,
  searchParams,
}: {
  response: PlayerPropRecommendationsResponse;
  filters: BetsFilterValues;
  pageSize: number;
  searchParams: Record<string, string | undefined>;
}) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-text">Rekomendacje</h2>
        <span className="text-sm text-muted">{response.total_count} zakładów</span>
      </div>
      {response.recommendations.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Nie ma rekomendacji"
          message="Spróbuj dopasować filtry lub zmienić przedział dat."
        />
      ) : (
        <>
          <PlayerBetRecommendationsTable
            recommendations={response.recommendations}
            applyTax={filters.applyTax}
          />
          <PaginationBar
            basePath="/bets"
            currentPage={filters.page}
            totalCount={response.total_count}
            pageSize={pageSize}
            searchParams={searchParams}
          />
        </>
      )}
    </section>
  );
}
