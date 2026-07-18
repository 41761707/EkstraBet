import {
  FootballPlayersSection,
  PlayersSportTabs,
} from "@/components/players/FootballPlayersSection";
import { getMatchLimitOptions } from "@/components/players/playerStatsConfig";
import {
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  parsePlayerStatKeys,
  type PlayersFilterValues,
} from "@/lib/playerFilterParams";
import { StatusMessage } from "@/components/StatusMessage";
import {
  ApiError,
  getPlayerCountries,
  getPlayerSeasons,
  getPlayerSports,
  getPlayerTeams,
  getPlayers,
} from "@/lib/api";
import { parsePositiveInt } from "@/lib/searchParams";

interface PlayersPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

function parseMatchLimit(value: string | undefined, sportId: number): number {
  const parsed = parsePositiveInt(value);
  const options = getMatchLimitOptions(sportId).map((option) => option.value);
  if (parsed && options.includes(parsed as (typeof options)[number])) {
    return parsed;
  }
  return sportId === HOCKEY_SPORT_ID ? 200 : 50;
}

function pickSportId(
  sports: { sport_id: number }[],
  requestedId?: string,
): number | null {
  if (requestedId) {
    const parsed = Number(requestedId);
    if (
      Number.isInteger(parsed) &&
      parsed > 0 &&
      sports.some((sport) => sport.sport_id === parsed)
    ) {
      return parsed;
    }
  }
  return (
    sports.find((sport) => sport.sport_id === FOOTBALL_SPORT_ID)?.sport_id ??
    sports[0]?.sport_id ??
    null
  );
}

function pickCountryId(
  countries: { id: number }[],
  requestedId?: string,
): number | null {
  if (requestedId) {
    const parsed = Number(requestedId);
    if (
      Number.isInteger(parsed) &&
      parsed > 0 &&
      countries.some((country) => country.id === parsed)
    ) {
      return parsed;
    }
  }
  return countries[0]?.id ?? null;
}

function pickTeamId(
  teams: { id: number }[],
  requestedId?: string,
): number | null {
  if (requestedId) {
    const parsed = Number(requestedId);
    if (
      Number.isInteger(parsed) &&
      parsed > 0 &&
      teams.some((team) => team.id === parsed)
    ) {
      return parsed;
    }
  }
  return teams[0]?.id ?? null;
}

function pickSeasonId(
  seasons: { season_id: number }[],
  requestedId?: string,
): number | null {
  if (requestedId) {
    const parsed = Number(requestedId);
    if (
      Number.isInteger(parsed) &&
      parsed > 0 &&
      seasons.some((season) => season.season_id === parsed)
    ) {
      return parsed;
    }
  }
  return seasons[0]?.season_id ?? null;
}

export default async function PlayersPage({ searchParams }: PlayersPageProps) {
  const params = await searchParams;

  let sportsResponse;
  let loadError: string | null = null;

  try {
    sportsResponse = await getPlayerSports();
  } catch (error) {
    loadError =
      error instanceof ApiError
        ? error.message
        : "Nie udało się pobrać listy sportów.";
    sportsResponse = { sports: [], total_count: 0 };
  }

  const sportId = pickSportId(sportsResponse.sports, params.sport_id);
  const selectedStats = parsePlayerStatKeys(
    params.stats,
    sportId ?? FOOTBALL_SPORT_ID,
  );
  const currentSport =
    sportsResponse.sports.find((item) => item.sport_id === sportId) ?? null;

  if (!currentSport?.available) {
    return (
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold text-white">Zawodnicy</h1>
          <p className="text-sm text-slate-400">
            Szczegółowe statystyki i analizy zawodników z różnych dyscyplin.
          </p>
        </header>

        {loadError ? (
          <StatusMessage
            variant="error"
            title="Błąd ładowania"
            message={loadError}
          />
        ) : null}

        <PlayersSportTabs
          sports={sportsResponse.sports}
          currentSportId={sportId ?? FOOTBALL_SPORT_ID}
        />

        <StatusMessage
          variant="info"
          title="Wkrótce"
          message={
            currentSport
              ? `${currentSport.emoji} ${currentSport.label} — wkrótce w nowej wersji.`
              : "Wybrany sport nie jest jeszcze dostępny."
          }
        />
      </main>
    );
  }

  let countries: Awaited<ReturnType<typeof getPlayerCountries>>["countries"] =
    [];
  let seasons: Awaited<ReturnType<typeof getPlayerSeasons>>["seasons"] = [];
  let teams: Awaited<ReturnType<typeof getPlayerTeams>>["teams"] = [];
  let players: Awaited<ReturnType<typeof getPlayers>>["players"] = [];

  try {
    const [countriesResponse, seasonsResponse] = await Promise.all([
      getPlayerCountries(sportId!),
      getPlayerSeasons(sportId!),
    ]);
    countries = countriesResponse.countries;
    seasons = seasonsResponse.seasons;

    const countryId = pickCountryId(countries, params.country_id);
    const seasonId = pickSeasonId(seasons, params.season_id);
    const matchLimit = parseMatchLimit(params.match_limit, sportId!);
    const search = params.search?.trim() ?? "";

    if (sportId === HOCKEY_SPORT_ID || countryId) {
      const teamsResponse = await getPlayerTeams(
        sportId!,
        countryId ?? undefined,
      );
      teams = teamsResponse.teams;
    }

    const teamId = search ? null : pickTeamId(teams, params.team_id);

    const filters: PlayersFilterValues = {
      sportId: sportId!,
      countryId,
      teamId,
      seasonId,
      matchLimit,
      search,
    };

    if (seasonId && (teamId || search)) {
      const playersResponse = await getPlayers({
        sportId: sportId!,
        seasonId,
        teamId: teamId ?? undefined,
        search: search || undefined,
      });
      players = playersResponse.players;
    }

    return (
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold text-white">Zawodnicy</h1>
          <p className="text-sm text-slate-400">
            Szczegółowe statystyki i analizy zawodników z różnych dyscyplin.
          </p>
        </header>

        <PlayersSportTabs
          sports={sportsResponse.sports}
          currentSportId={sportId!}
        />

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-sky-300">
            {currentSport.emoji} {currentSport.label} — Zawodnicy
          </h2>
          <FootballPlayersSection
            countries={countries}
            teams={teams}
            seasons={seasons}
            players={players}
            filters={filters}
            initialSelectedStats={selectedStats}
          />
        </section>
      </main>
    );
  } catch (error) {
    return (
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold text-white">Zawodnicy</h1>
        </header>
        <PlayersSportTabs
          sports={sportsResponse.sports}
          currentSportId={sportId ?? FOOTBALL_SPORT_ID}
        />
        <StatusMessage
          variant="error"
          title="Błąd ładowania"
          message={
            error instanceof ApiError
              ? error.message
              : "Nie udało się załadować danych zawodników."
          }
        />
      </main>
    );
  }
}

