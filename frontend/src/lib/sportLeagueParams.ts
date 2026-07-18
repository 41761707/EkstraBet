import {
  SPORT_PLAYOFFS_PHASE,
  SPORT_REGULAR_SEASON_PHASE,
} from "@/types/api";

export {
  SPORT_PLAYOFFS_PHASE,
  SPORT_REGULAR_SEASON_PHASE,
};

export interface SportLeagueFilters {
  seasonId: number;
  phase: number;
  dateFilter: boolean;
  dateFrom: string;
  dateTo: string;
}

function formatIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function defaultSportDateRange(): { from: string; to: string } {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const nextWeek = new Date(today);
  nextWeek.setDate(today.getDate() + 7);
  return {
    from: formatIsoDate(yesterday),
    to: formatIsoDate(nextWeek),
  };
}

export function parseSportLeagueFilters(
  seasons: { season_id: number }[],
  currentSeasonId: number | null,
  searchParams: Record<string, string | undefined>,
): SportLeagueFilters {
  const defaultDates = defaultSportDateRange();

  const requestedSeason = Number(searchParams.season_id);
  const seasonId =
    Number.isInteger(requestedSeason) &&
    seasons.some((season) => season.season_id === requestedSeason)
      ? requestedSeason
      : currentSeasonId ?? seasons[0]?.season_id ?? 0;

  const requestedPhase = Number(searchParams.phase);
  const phase =
    requestedPhase === SPORT_PLAYOFFS_PHASE
      ? SPORT_PLAYOFFS_PHASE
      : SPORT_REGULAR_SEASON_PHASE;

  return {
    seasonId,
    phase,
    dateFilter: searchParams.date_filter !== "false",
    dateFrom: searchParams.date_from ?? defaultDates.from,
    dateTo: searchParams.date_to ?? defaultDates.to,
  };
}

export function sportLeaguePath(
  slug: string,
  filters: Partial<SportLeagueFilters> & { season_id?: number },
): string {
  const params = new URLSearchParams();
  const seasonId = filters.seasonId ?? filters.season_id;
  if (seasonId) {
    params.set("season_id", String(seasonId));
  }
  const phase = filters.phase ?? SPORT_REGULAR_SEASON_PHASE;
  if (phase !== SPORT_REGULAR_SEASON_PHASE) {
    params.set("phase", String(phase));
  }
  if (filters.dateFilter === false) {
    params.set("date_filter", "false");
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  const search = params.toString();
  return search
    ? `/leagues/${encodeURIComponent(slug)}?${search}`
    : `/leagues/${encodeURIComponent(slug)}`;
}

export function phaseLabel(phase: number): string {
  return phase === SPORT_PLAYOFFS_PHASE ? "Playoffy" : "Sezon zasadniczy";
}
