import Link from "next/link";
import { notFound } from "next/navigation";
import { ExpandableSection } from "@/components/ExpandableSection";
import { LeagueCharacteristicsSection } from "@/components/leagues/LeagueCharacteristicsSection";
import { LeagueHeader } from "@/components/leagues/LeagueHeader";
import { LeagueRoundSelector } from "@/components/leagues/LeagueRoundSelector";
import { LeagueStandingsSection } from "@/components/leagues/LeagueStandingsSection";
import { LeagueTeamComparisonsSection } from "@/components/leagues/LeagueTeamComparisonsSection";
import { MatchList } from "@/components/MatchList";
import { SportLeaguePage } from "@/components/sport-leagues/SportLeaguePage";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getLeagueCharacteristics,
  getLeagueDetails,
  getLeagueMatches,
  getLeagueRounds,
  getLeagueStandings,
  resolveLeagueId,
} from "@/lib/api";
import { leaguePath } from "@/lib/leaguePaths";
import type {
  LeagueRound,
  OuBttsStandingRow,
  TraditionalStandingRow,
} from "@/types/api";
import { BASKETBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/types/api";

interface LeaguePageProps {
  params: Promise<{ leagueId: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}

function pickSeasonId(
  seasons: { season_id: number }[],
  currentSeasonId: number | null,
  requestedSeasonId?: string,
): number | null {
  if (requestedSeasonId) {
    const parsed = Number(requestedSeasonId);
    if (
      Number.isInteger(parsed) &&
      parsed > 0 &&
      seasons.some((season) => season.season_id === parsed)
    ) {
      return parsed;
    }
  }

  if (
    currentSeasonId &&
    seasons.some((season) => season.season_id === currentSeasonId)
  ) {
    return currentSeasonId;
  }

  return seasons[0]?.season_id ?? null;
}

function pickRoundNumber(
  rounds: LeagueRound[],
  requestedRound?: string,
): number | null {
  if (rounds.length === 0) {
    return null;
  }

  if (requestedRound) {
    const parsed = Number(requestedRound);
    if (
      Number.isInteger(parsed) &&
      rounds.some((round) => round.round_number === parsed)
    ) {
      return parsed;
    }
  }

  return rounds[0]?.round_number ?? null;
}

function selectedRoundLabel(
  rounds: LeagueRound[],
  roundNumber: number | null,
): string {
  if (roundNumber === null) {
    return "";
  }
  return (
    rounds.find((round) => round.round_number === roundNumber)?.round_label ??
    String(roundNumber)
  );
}

export default async function LeaguePage({
  params,
  searchParams,
}: LeaguePageProps) {
  const { leagueId } = await params;
  const resolvedSearchParams = await searchParams;
  const { season_id: seasonIdParam, round: roundParam } = resolvedSearchParams;

  let resolvedId: number | null;
  try {
    resolvedId = await resolveLeagueId(leagueId);
  } catch (error) {
    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się rozpoznać identyfikatora ligi.";

    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować ligi"
        message={message}
      />
    );
  }

  if (!resolvedId) {
    notFound();
  }

  try {
    const league = await getLeagueDetails(resolvedId);

    if (
      league.sport_id === HOCKEY_SPORT_ID
      || league.sport_id === BASKETBALL_SPORT_ID
    ) {
      return (
        <SportLeaguePage
          league={league}
          searchParams={resolvedSearchParams}
        />
      );
    }

    const selectedSeasonId = pickSeasonId(
      league.seasons,
      league.current_season_id,
      seasonIdParam,
    );

    if (!selectedSeasonId) {
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

    const roundsResponse = await getLeagueRounds(league.id, selectedSeasonId);
    const selectedRound = pickRoundNumber(roundsResponse.rounds, roundParam);

    const [
      matchesResponse,
      overallStandings,
      homeStandings,
      awayStandings,
      ouBttsStandings,
      characteristicsResult,
    ] = await Promise.all([
      selectedRound !== null
        ? getLeagueMatches(league.id, selectedSeasonId, selectedRound)
        : Promise.resolve({
            matches: [],
            total_count: 0,
            league_id: league.id,
            season_id: selectedSeasonId,
          }),
      getLeagueStandings(league.id, selectedSeasonId, "overall"),
      getLeagueStandings(league.id, selectedSeasonId, "home"),
      getLeagueStandings(league.id, selectedSeasonId, "away"),
      getLeagueStandings(league.id, selectedSeasonId, "ou_btts"),
      getLeagueCharacteristics(league.id, selectedSeasonId).catch(() => null),
    ]);

    const overall = overallStandings.standings as TraditionalStandingRow[];
    const home = homeStandings.standings as TraditionalStandingRow[];
    const away = awayStandings.standings as TraditionalStandingRow[];
    const ouBtts = ouBttsStandings.standings as OuBttsStandingRow[];
    const roundLabel = selectedRoundLabel(
      roundsResponse.rounds,
      selectedRound,
    );

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
              const isActive = season.season_id === selectedSeasonId;
              return (
                <Link
                  key={season.season_id}
                  href={leaguePath(league.slug, {
                    season_id: season.season_id,
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

        <LeagueRoundSelector
          leagueSlug={league.slug}
          seasonId={selectedSeasonId}
          rounds={roundsResponse.rounds}
          selectedRound={selectedRound ?? -1}
        />

        <div className="space-y-4">
          <ExpandableSection
            title={
              selectedRound !== null
                ? `Terminarz — kolejka ${roundLabel}`
                : "Terminarz"
            }
            defaultOpen
          >
            <div className="space-y-4">
              <p className="text-sm text-slate-400">
                {matchesResponse.total_count} mecz
                {matchesResponse.total_count === 1 ? "" : "ów"}
              </p>
              {selectedRound === null ? (
                <StatusMessage
                  variant="empty"
                  title="Brak kolejek"
                  message="Nie znaleziono kolejek dla wybranego sezonu."
                />
              ) : matchesResponse.matches.length === 0 ? (
                <StatusMessage
                  variant="empty"
                  title="Brak meczów"
                  message="W wybranej kolejce nie ma zaplanowanych meczów."
                />
              ) : (
                <MatchList
                  matches={matchesResponse.matches}
                  seasonId={selectedSeasonId}
                  leagueId={league.id}
                  hideRoundColumn
                />
              )}
            </div>
          </ExpandableSection>

          <ExpandableSection title="Tabele ligowe">
            <LeagueStandingsSection
              overall={overall}
              home={home}
              away={away}
              ouBtts={ouBtts}
              seasonId={selectedSeasonId}
              leagueId={league.id}
              embedded
            />
          </ExpandableSection>

          {characteristicsResult ? (
            <>
              <LeagueCharacteristicsSection
                characteristics={characteristicsResult}
                leagueName={league.name}
              />
              <LeagueTeamComparisonsSection
                characteristics={characteristicsResult}
                ouBtts={ouBtts}
                homeStandings={home}
                awayStandings={away}
              />
            </>
          ) : (
            <ExpandableSection title="Statystyki ligowe">
              <StatusMessage
                variant="empty"
                title="Brak statystyk ligowych"
                message="Statystyki pojawią się po rozegraniu pierwszych meczów sezonu."
              />
            </ExpandableSection>
          )}
        </div>
      </div>
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    const message =
      error instanceof ApiError
        ? error.message
        : "Nie udało się załadować danych ligi z API.";

    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować ligi"
        message={message}
      />
    );
  }
}
