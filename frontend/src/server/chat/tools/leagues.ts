import type {
  ChatDataSource,
  ChatTableSpec,
  LeagueDetails,
  LeagueStandingsResponse,
  LeaguesListResponse,
} from "@/types/api";

import { booleanArg, enumArg, numberArg, stringArg } from "./args";
import { fetchReadOnly, getEndpoint } from "./http";
import { isSeasonYearsMatch, normalizeSearchText } from "./text";
import type { ToolResult } from "./types";

export async function resolveLeagueByQuery(
  query: string,
  sportId?: number,
): Promise<{
  league: LeagueDetails;
  warning?: string;
  dataSource: ChatDataSource;
}> {
  const response = await fetchReadOnly<LeaguesListResponse>("/leagues", {
    active: undefined,
    sport_id: sportId,
  });
  const normalizedQuery = normalizeSearchText(query);
  const matches = response.leagues.filter((league) => {
    const normalizedName = normalizeSearchText(league.name);
    const normalizedSlug = normalizeSearchText(league.slug);
    return (
      normalizedName.includes(normalizedQuery) ||
      normalizedQuery.includes(normalizedName) ||
      normalizedSlug.includes(normalizedQuery)
    );
  });
  const first =
    matches[0] ??
    response.leagues.find(
      (league) => normalizeSearchText(league.name) === normalizedQuery,
    );

  if (!first) {
    throw new Error(`No league found for query: ${query}`);
  }

  const league = await fetchReadOnly<LeagueDetails>(`/leagues/${first.id}`);
  return {
    league,
    warning:
      matches.length > 1
        ? `Znaleziono kilka lig dla "${query}". Użyłem pierwszego wyniku: ${first.name}.`
        : undefined,
    dataSource: {
      label: "Wyszukiwanie ligi",
      endpoint: getEndpoint("/leagues"),
      params: { active: null, sport_id: sportId ?? null, query },
    },
  };
}

export function resolveSeasonIdFromLeague(
  league: LeagueDetails,
  seasonYears?: string,
): { seasonId: number; warning?: string } {
  if (seasonYears) {
    const season = league.seasons.find((item) =>
      isSeasonYearsMatch(item.years, seasonYears),
    );
    if (season) {
      return { seasonId: season.season_id };
    }
    throw new Error(
      `Season ${seasonYears} not found for league ${league.name}`,
    );
  }

  const currentSeason = league.current_season_id;
  if (currentSeason) {
    return { seasonId: currentSeason };
  }

  const latestSeason = [...league.seasons].sort(
    (left, right) => right.season_id - left.season_id,
  )[0];
  if (!latestSeason) {
    throw new Error(`No seasons found for league ${league.name}`);
  }
  return {
    seasonId: latestSeason.season_id,
    warning: `Liga nie ma current_season_id, użyłem season_id=${latestSeason.season_id}.`,
  };
}

export async function resolveSeasonIdByYears(
  seasonYears: string,
): Promise<number> {
  const response = await fetchReadOnly<{
    seasons: { id?: number; season_id?: number; years?: string }[];
  }>("/helper/seasons");
  const season = response.seasons.find(
    (item) => item.years && isSeasonYearsMatch(item.years, seasonYears),
  );
  const seasonId = season?.season_id ?? season?.id;
  if (!seasonId) {
    throw new Error(`Season ${seasonYears} not found`);
  }
  return seasonId;
}

function buildStandingsTable(
  title: string,
  standings: LeagueStandingsResponse,
): ChatTableSpec {
  const rows = standings.standings.slice(0, 12);
  return {
    title,
    columns:
      standings.scope === "ou_btts"
        ? ["#", "Drużyna", "M", "BTTS %", "Over 2.5 %"]
        : ["#", "Drużyna", "M", "W", "R", "P", "Bramki", "Pkt"],
    rows: rows.map((row) =>
      "points" in row
        ? [
            row.position,
            row.team_name,
            row.played,
            row.wins,
            row.draws,
            row.losses,
            `${row.goals_for}:${row.goals_against}`,
            row.points,
          ]
        : [
            row.position,
            row.team_name,
            row.played,
            row.btts_percentage,
            row.over_2_5_percentage,
          ],
    ),
  };
}

export async function listLeagues(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const active = booleanArg(args, "active");
  const sportId = numberArg(args, "sport_id", { min: 1 });
  const response = await fetchReadOnly<LeaguesListResponse>("/leagues", {
    active: active ?? true,
    sport_id: sportId,
  });

  const leagues = response.leagues.slice(0, 20);
  return {
    name: "list_leagues",
    summary: `Znaleziono ${response.total_count} lig, zwracam pierwsze ${leagues.length}.`,
    data: leagues,
    dataSources: [
      {
        label: "Lista lig",
        endpoint: getEndpoint("/leagues"),
        params: { active: active ?? true, sport_id: sportId ?? null },
      },
    ],
    warnings:
      response.total_count > leagues.length
        ? ["Wynik został skrócony do 20 lig."]
        : [],
  };
}

export async function getLeagueTable(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const query = stringArg(args, "query", { required: true, maxLength: 80 })!;
  const seasonYears = stringArg(args, "season_years", {
    required: true,
    maxLength: 20,
  })!;
  const scope = enumArg(
    args,
    "scope",
    ["overall", "home", "away", "ou_btts"],
    "overall",
  );
  const sportId = numberArg(args, "sport_id", { min: 1 });
  const resolvedLeague = await resolveLeagueByQuery(query, sportId);
  const season = resolveSeasonIdFromLeague(resolvedLeague.league, seasonYears);
  const standings = await fetchReadOnly<LeagueStandingsResponse>(
    `/leagues/${resolvedLeague.league.id}/standings`,
    {
      season_id: season.seasonId,
      scope,
    },
  );
  const table = buildStandingsTable(
    `Tabela: ${resolvedLeague.league.name} ${seasonYears}`,
    standings,
  );

  return {
    name: "get_league_table",
    summary: `Tabela ligi ${resolvedLeague.league.name} za sezon ${seasonYears}.`,
    data: {
      league: resolvedLeague.league,
      season_id: season.seasonId,
      season_years: seasonYears,
      standings: standings.standings.slice(0, 12),
    },
    table,
    dataSources: [
      resolvedLeague.dataSource,
      {
        label: "Szczegóły ligi i sezony",
        endpoint: getEndpoint(`/leagues/${resolvedLeague.league.id}`),
        params: { league_id: resolvedLeague.league.id },
      },
      {
        label: "Tabela ligowa",
        endpoint: getEndpoint(
          `/leagues/${resolvedLeague.league.id}/standings`,
        ),
        params: {
          league_id: resolvedLeague.league.id,
          season_id: season.seasonId,
          scope,
        },
      },
    ],
    warnings: [
      ...(resolvedLeague.warning ? [resolvedLeague.warning] : []),
      ...(season.warning ? [season.warning] : []),
      ...(standings.total_count > 12
        ? ["Tabela została skrócona do pierwszych 12 pozycji."]
        : []),
    ],
  };
}

export async function getLeagueStandings(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const leagueId = numberArg(args, "league_id", { required: true, min: 1 })!;
  const seasonId = numberArg(args, "season_id", { required: true, min: 1 })!;
  const scope = enumArg(
    args,
    "scope",
    ["overall", "home", "away", "ou_btts"],
    "overall",
  );
  const [details, standings] = await Promise.all([
    fetchReadOnly<LeagueDetails>(`/leagues/${leagueId}`),
    fetchReadOnly<LeagueStandingsResponse>(`/leagues/${leagueId}/standings`, {
      season_id: seasonId,
      scope,
    }),
  ]);
  const rows = standings.standings.slice(0, 12);
  const table = buildStandingsTable(`Tabela: ${details.name}`, standings);

  return {
    name: "get_league_standings",
    summary: `Tabela ligi ${details.name}, sezon ${seasonId}, zakres ${scope}.`,
    data: { league: details, standings: rows },
    table,
    dataSources: [
      {
        label: "Tabela ligowa",
        endpoint: getEndpoint(`/leagues/${leagueId}/standings`),
        params: { league_id: leagueId, season_id: seasonId, scope },
      },
    ],
    warnings:
      standings.total_count > rows.length
        ? ["Tabela została skrócona do pierwszych 12 pozycji."]
        : [],
  };
}
