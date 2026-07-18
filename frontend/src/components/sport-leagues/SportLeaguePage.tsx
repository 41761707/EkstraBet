import Link from "next/link";
import { ExpandableSection } from "@/components/ExpandableSection";
import { LeagueHeader } from "@/components/leagues/LeagueHeader";
import { MatchList } from "@/components/MatchList";
import { SportLeagueDateFilter } from "@/components/sport-leagues/SportLeagueDateFilter";
import { SportLeaguePhaseSelector } from "@/components/sport-leagues/SportLeaguePhaseSelector";
import { SportLeagueStatsSection } from "@/components/sport-leagues/SportLeagueStatsSection";
import { SportStandingsSection } from "@/components/sport-leagues/SportStandingsSection";
import { StatusMessage } from "@/components/StatusMessage";
import {
  getSportLeagueMatches,
  getSportLeagueStandings,
  getSportLeagueStats,
} from "@/lib/api";
import {
  parseSportLeagueFilters,
  phaseLabel,
  sportLeaguePath,
} from "@/lib/sportLeagueParams";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type LeagueDetails,
  type SportLeagueStatsResponse,
} from "@/types/api";

interface SportLeaguePageProps {
  league: LeagueDetails;
  searchParams: Record<string, string | undefined>;
}

export async function SportLeaguePage({
  league,
  searchParams,
}: SportLeaguePageProps) {
  const sportId = league.sport_id;
  if (sportId !== HOCKEY_SPORT_ID && sportId !== BASKETBALL_SPORT_ID) {
    return null;
  }

  const filters = parseSportLeagueFilters(
    league.seasons,
    league.current_season_id,
    searchParams,
  );

  if (!filters.seasonId) {
    return (
      <div className="space-y-6">
        <LeagueHeader
          name={league.name}
          countryEmoji={league.country_emoji}
          countryName={league.country_name}
          sportName={league.sport_name}
          lastUpdate={league.last_update}
        />
        <StatusMessage
          variant="empty"
          title="Brak sezonów"
          message="Ta liga nie ma jeszcze sezonów z meczami."
        />
      </div>
    );
  }

  const matchOptions = {
    phase: filters.phase,
    dateFrom: filters.dateFilter ? filters.dateFrom : undefined,
    dateTo: filters.dateFilter ? filters.dateTo : undefined,
  };

  const hockeyCategories = ["shots", "goals", "over_under"] as const;
  const basketballCategories = ["shooting", "points", "over_under"] as const;
  const statCategories =
    sportId === HOCKEY_SPORT_ID ? hockeyCategories : basketballCategories;

  const [
    matchesResponse,
    overallStandings,
    homeStandings,
    awayStandings,
    ...statsResponses
  ] = await Promise.all([
    getSportLeagueMatches(league.id, filters.seasonId, matchOptions),
    getSportLeagueStandings(league.id, filters.seasonId, "overall"),
    getSportLeagueStandings(league.id, filters.seasonId, "home"),
    getSportLeagueStandings(league.id, filters.seasonId, "away"),
    ...statCategories.map((category) =>
      getSportLeagueStats(
        league.id,
        filters.seasonId,
        category,
        filters.phase,
      ).catch(() => null),
    ),
  ]);

  const statsMap = statCategories.reduce<
    Record<string, SportLeagueStatsResponse | null>
  >((accumulator, category, index) => {
    accumulator[category] = statsResponses[index] ?? null;
    return accumulator;
  }, {});

  const currentPhaseLabel = phaseLabel(filters.phase);

  return (
    <div className="space-y-8">
      <LeagueHeader
        name={league.name}
        countryEmoji={league.country_emoji}
        countryName={league.country_name}
        sportName={league.sport_name}
        lastUpdate={league.last_update}
      />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-white">Sezon</h2>
        <div className="flex flex-wrap gap-2">
          {league.seasons.map((season) => {
            const isActive = season.season_id === filters.seasonId;
            return (
              <Link
                key={season.season_id}
                href={sportLeaguePath(league.slug, {
                  seasonId: season.season_id,
                  phase: filters.phase,
                  dateFilter: filters.dateFilter,
                  dateFrom: filters.dateFrom,
                  dateTo: filters.dateTo,
                })}
                className={`rounded-full px-3 py-1.5 text-sm transition ${
                  isActive
                    ? "bg-sky-600 text-white"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {season.years}
                <span className="ml-1 text-xs opacity-75">
                  ({season.match_count})
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      <SportLeaguePhaseSelector
        leagueSlug={league.slug}
        seasonId={filters.seasonId}
        selectedPhase={filters.phase}
        dateFilter={filters.dateFilter}
        dateFrom={filters.dateFrom}
        dateTo={filters.dateTo}
      />

      <SportLeagueDateFilter leagueSlug={league.slug} filters={filters} />

      <div className="space-y-4">
        <ExpandableSection
          title={`Terminarz — ${currentPhaseLabel}`}
          defaultOpen
        >
          <div className="space-y-4">
            <p className="text-sm text-slate-400">
              {matchesResponse.total_count} mecz
              {matchesResponse.total_count === 1 ? "" : "ów"}
            </p>
            {matchesResponse.matches.length === 0 ? (
              <StatusMessage
                variant="empty"
                title="Brak meczów"
                message="Brak meczów dla wprowadzonej konfiguracji."
              />
            ) : (
              <MatchList
                matches={matchesResponse.matches}
                seasonId={filters.seasonId}
                leagueId={league.id}
                hideRoundColumn
              />
            )}
          </div>
        </ExpandableSection>

        <ExpandableSection title="Tabele ligowe">
          <SportStandingsSection
            sportId={sportId}
            overallHockey={overallStandings.hockey_standings ?? undefined}
            homeHockey={homeStandings.hockey_standings ?? undefined}
            awayHockey={awayStandings.hockey_standings ?? undefined}
            overallBasketball={
              overallStandings.basketball_standings ?? undefined
            }
            homeBasketball={homeStandings.basketball_standings ?? undefined}
            awayBasketball={awayStandings.basketball_standings ?? undefined}
          />
        </ExpandableSection>

        <ExpandableSection title="Statystyki ligowe">
          <SportLeagueStatsSection sportId={sportId} stats={statsMap} />
        </ExpandableSection>
      </div>
    </div>
  );
}
