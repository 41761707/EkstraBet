import type {
  ChatChartPoint,
  ChatChartSpec,
  ChatDataSource,
  ChatSportContext,
  ChatTableSpec,
  FootballPlayerMatchStat,
  FootballPlayerMatchStatsResponse,
  FootballPlayersListResponse,
  HockeyPlayerMatchStat,
  HockeyPlayerMatchStatsResponse,
  LeagueDetails,
  LeagueStandingsResponse,
  LeaguesListResponse,
  TeamProfile,
  TeamSeasonMatchPoint,
} from "@/types/api";
import { getApiBaseUrl, getServerAuthHeaders } from "@/lib/auth";

type PrimitiveParam = string | number | boolean | null | undefined;

interface ToolResult {
  name: string;
  summary: string;
  data: unknown;
  chart?: ChatChartSpec | null;
  table?: ChatTableSpec | null;
  dataSources: ChatDataSource[];
  warnings: string[];
}

export type ChatToolName =
  | "list_leagues"
  | "search_teams"
  | "get_team_profile"
  | "get_team_overview"
  | "get_team_stat_series"
  | "get_team_player_stat_leader"
  | "get_player_stat_summary"
  | "get_matchup_projection"
  | "get_league_table"
  | "get_league_standings";

export interface PlannedToolCall {
  tool: ChatToolName;
  args: Record<string, unknown>;
}

export const CHAT_TOOL_DESCRIPTIONS = [
  {
    tool: "list_leagues",
    description:
      "Lists leagues, optionally filtered by active status and sport_id.",
    args: {
      active: "boolean optional",
      sport_id: "number optional, e.g. 1 football, 2 hockey, 3 basketball",
    },
  },
  {
    tool: "search_teams",
    description:
      "Searches teams by natural team name, country, sport, or shortcut.",
    args: {
      query: "string required",
      sport_id: "number optional",
      page_size: "number optional, max 10",
    },
  },
  {
    tool: "get_team_profile",
    description:
      "Gets a team profile after team id is known",
    args: {
      team_id: "number required",
      season_id: "number optional; omit for latest/all played matches across seasons",
      league_id: "number optional",
      limit: "number optional, max 20",
    },
  },
  {
    tool: "get_player_stat_summary",
    description:
      "Finds a player by name in the selected sport and returns supported match-log stat totals, averages, a table, and a chart.",
    args: {
      query: "string required player search phrase, e.g. Connor McDavid",
      season_id: "number optional",
      season_years: "string optional, e.g. 2024/2025",
      team_id: "number optional",
      sport_id: "number required from GUI context",
      stat:
        "football: goals, assists, shots, shots_on_target, fouls_conceded, yellow_cards; hockey skater: points, goals, assists, sog, plus_minus, penalty_minutes, toi_minutes; hockey goalie: shots_against, shots_saved, saves_acc, toi_minutes",
      limit: "number optional recent matches, max 200; use 200 for full-season player questions",
    },
  },
  {
    tool: "get_team_overview",
    description:
      "Builds a team profile by team name or id, including recent form, split stats, and an optional chart chosen by the assistant.",
    args: {
      team_id: "number optional when query is provided",
      query: "string optional team search phrase",
      season_id: "number optional",
      season_years: "string optional, e.g. 2024/2025",
      league_id: "number optional",
      limit: "number optional, max 20",
    },
  },
  {
    tool: "get_team_stat_series",
    description:
      "Builds chart-ready recent-match series for one team and one statistic.",
    args: {
      team_id: "number optional when query is provided",
      query: "string optional team search phrase",
      season_id: "number optional; omit for latest/all played matches across seasons",
      league_id: "number optional",
      stat:
        "one of goals, total_goals, shots, shots_on_target, corners, cards, offsides, fouls, penalty_minutes, penalties",
      perspective: "one of team, opponent, total",
      limit: "number optional, max 20",
    },
  },
  {
    tool: "get_team_player_stat_leader",
    description:
      "Finds which football player on a team leads a selected stat across the team's recent matches.",
    args: {
      team_id: "number optional when query is provided",
      query: "string optional team search phrase",
      season_id: "number optional",
      season_years: "string optional, e.g. 2024/2025",
      stat: "one of goals, assists, shots, shots_on_target, fouls_conceded, yellow_cards",
      limit: "number optional recent team matches, max 10",
    },
  },
  {
    tool: "get_matchup_projection",
    description:
      "Projects a hypothetical match between team A and team B using recent team statistics. Use for questions about predicted score, cards, corners, fouls, shots, or any supported match statistic.",
    args: {
      team_a_query: "string required; treated as home/team A",
      team_b_query: "string required; treated as away/team B",
      target:
        "one of result, goals, cards, corners, shots, shots_on_target, offsides, fouls, penalty_minutes, penalties",
      season_id: "number optional",
      season_years: "string optional, e.g. 2024/2025",
      league_id: "number optional",
      limit: "number optional recent matches per team, max 20",
    },
  },
  {
    tool: "get_league_standings",
    description: "Gets league standings for one season.",
    args: {
      league_id: "number required",
      season_id: "number required",
      scope: "overall, home, away, or ou_btts",
    },
  },
  {
    tool: "get_league_table",
    description:
      "Finds a league by name, resolves season years, and returns the league table.",
    args: {
      query: "string required league search phrase",
      season_years: "string required, e.g. 2024/2025",
      scope: "overall, home, away, or ou_btts",
    },
  },
] as const;

const MAX_TOOL_CALLS = 4;

const STAT_LABELS = {
  goals: "Bramki",
  total_goals: "Suma bramek",
  shots: "Strzały",
  shots_on_target: "Strzały celne",
  corners: "Rzuty rożne",
  cards: "Kartki",
  offsides: "Spalone",
  fouls: "Faule",
  penalty_minutes: "Minuty kar",
  penalties: "Kary",
} as const;

type StatKey = keyof typeof STAT_LABELS;
type StatPerspective = "team" | "opponent" | "total";
type MatchupTarget = StatKey | "result";
type FootballPlayerLeaderStat = keyof Pick<
  FootballPlayerMatchStat,
  | "goals"
  | "assists"
  | "shots"
  | "shots_on_target"
  | "fouls_conceded"
  | "yellow_cards"
>;

const FOOTBALL_SPORT_ID = 1;
const HOCKEY_SPORT_ID = 2;
const FOOTBALL_PLAYER_STAT_LABELS: Record<FootballPlayerLeaderStat, string> = {
  goals: "Bramki",
  assists: "Asysty",
  shots: "Strzały",
  shots_on_target: "Strzały celne",
  fouls_conceded: "Faule",
  yellow_cards: "Żółte kartki",
};

type HockeySkaterPlayerStat = keyof Pick<
  HockeyPlayerMatchStat,
  | "points"
  | "goals"
  | "assists"
  | "sog"
  | "plus_minus"
  | "penalty_minutes"
  | "toi_minutes"
>;
type HockeyGoaliePlayerStat = keyof Pick<
  HockeyPlayerMatchStat,
  "shots_against" | "shots_saved" | "saves_acc" | "toi_minutes"
>;
type PlayerStatSummaryKey =
  | FootballPlayerLeaderStat
  | HockeySkaterPlayerStat
  | HockeyGoaliePlayerStat;

const HOCKEY_SKATER_STAT_LABELS: Record<HockeySkaterPlayerStat, string> = {
  points: "Punkty",
  goals: "Bramki",
  assists: "Asysty",
  sog: "Strzały na bramkę",
  plus_minus: "Plus/minus",
  penalty_minutes: "Minuty kar",
  toi_minutes: "Czas na lodzie (min)",
};

const HOCKEY_GOALIE_STAT_LABELS: Record<HockeyGoaliePlayerStat, string> = {
  shots_against: "Strzały przeciwko",
  shots_saved: "Obrony",
  saves_acc: "Skuteczność obron (%)",
  toi_minutes: "Czas na lodzie (min)",
};

function buildUrl(
  path: string,
  params?: Record<string, PrimitiveParam>,
): string {
  const url = new URL(path, getApiBaseUrl());
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function fetchReadOnly<T>(
  path: string,
  params?: Record<string, PrimitiveParam>,
): Promise<T> {
  const authHeaders = await getServerAuthHeaders();
  const response = await fetch(buildUrl(path, params), {
    headers: {
      Accept: "application/json",
      ...authHeaders,
    },
    cache: "no-store",
    signal: AbortSignal.timeout(12_000),
  });

  if (!response.ok) {
    throw new Error(`Read-only API request failed: GET ${path}`);
  }

  return response.json() as Promise<T>;
}

function getEndpoint(path: string): string {
  return `GET ${path}`;
}

function numberArg(
  args: Record<string, unknown>,
  key: string,
  options?: { required?: boolean; min?: number; max?: number },
): number | undefined {
  const value = args[key];
  if (value === undefined || value === null || value === "") {
    if (options?.required) {
      throw new Error(`Missing required argument: ${key}`);
    }
    return undefined;
  }

  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(parsed)) {
    throw new Error(`Argument ${key} must be an integer`);
  }
  if (options?.min !== undefined && parsed < options.min) {
    throw new Error(`Argument ${key} must be at least ${options.min}`);
  }
  if (options?.max !== undefined && parsed > options.max) {
    throw new Error(`Argument ${key} must be at most ${options.max}`);
  }
  return parsed;
}

function stringArg(
  args: Record<string, unknown>,
  key: string,
  options?: { required?: boolean; maxLength?: number },
): string | undefined {
  const value = args[key];
  if (value === undefined || value === null || value === "") {
    if (options?.required) {
      throw new Error(`Missing required argument: ${key}`);
    }
    return undefined;
  }
  if (typeof value !== "string") {
    throw new Error(`Argument ${key} must be a string`);
  }
  return value.slice(0, options?.maxLength ?? 120);
}

function booleanArg(
  args: Record<string, unknown>,
  key: string,
): boolean | undefined {
  const value = args[key];
  return typeof value === "boolean" ? value : undefined;
}

function enumArg<T extends string>(
  args: Record<string, unknown>,
  key: string,
  allowed: readonly T[],
  fallback: T,
): T {
  const value = args[key];
  return typeof value === "string" && allowed.includes(value as T)
    ? (value as T)
    : fallback;
}

function normalizeSearchText(value: string): string {
  return value
    .toLocaleLowerCase("pl")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function normalizeSeasonYears(value: string): string | null {
  const years = value.match(/\d{2,4}/g);
  if (!years || years.length < 2) {
    return null;
  }

  const firstYear = Number(years[0].length === 2 ? `20${years[0]}` : years[0]);
  const secondYear =
    years[1].length === 2
      ? Math.floor(firstYear / 100) * 100 + Number(years[1])
      : Number(years[1]);
  if (!Number.isInteger(firstYear) || !Number.isInteger(secondYear)) {
    return null;
  }

  return `${firstYear}/${secondYear}`;
}

function isSeasonYearsMatch(actual: string, expected: string): boolean {
  const normalizedActual = normalizeSearchText(actual);
  const normalizedExpected = normalizeSearchText(expected);
  const actualSeason = normalizeSeasonYears(actual);
  const expectedSeason = normalizeSeasonYears(expected);
  return (
    Boolean(actualSeason && expectedSeason && actualSeason === expectedSeason) ||
    normalizedActual === normalizedExpected ||
    normalizedActual.replace(/\s/g, "") === normalizedExpected.replace(/\s/g, "")
  );
}

async function resolveLeagueByQuery(
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
  const first = matches[0] ?? response.leagues.find(
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

function resolveSeasonIdFromLeague(
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

async function resolveSeasonIdByYears(seasonYears: string): Promise<number> {
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

async function resolveTeamId(args: Record<string, unknown>): Promise<{
  teamId: number;
  teamName?: string;
  warning?: string;
  dataSource?: ChatDataSource;
}> {
  const directTeamId = numberArg(args, "team_id", { min: 1 });
  if (directTeamId) {
    return { teamId: directTeamId };
  }

  const query = stringArg(args, "query", { required: true, maxLength: 80 })!;
  const sportId = numberArg(args, "sport_id", { min: 1 });
  const response = await fetchReadOnly<{
    teams: { id: number; name: string; sport_name?: string | null }[];
  }>("/teams/search", {
    team_name: query,
    sport_id: sportId,
    page_size: 5,
  });

  const first = response.teams[0];
  if (!first) {
    throw new Error(`No team found for query: ${query}`);
  }

  const warning =
    response.teams.length > 1
      ? `Znaleziono kilka drużyn dla "${query}". Użyłem pierwszego wyniku: ${first.name}.`
      : undefined;

  return {
    teamId: first.id,
    teamName: first.name,
    warning,
    dataSource: {
      label: "Wyszukiwanie drużyn",
      endpoint: getEndpoint("/teams/search"),
      params: { team_name: query, sport_id: sportId ?? null, page_size: 5 },
    },
  };
}

function valueForMatch(
  match: TeamSeasonMatchPoint,
  stat: StatKey,
  perspective: StatPerspective,
): number {
  if (stat === "goals") {
    if (perspective === "opponent") {
      return match.is_home ? match.away_goals : match.home_goals;
    }
    if (perspective === "total") {
      return match.total_goals;
    }
    return match.is_home ? match.home_goals : match.away_goals;
  }

  const key = `${perspective}_${stat}` as keyof TeamSeasonMatchPoint;
  const value = match[key];
  return typeof value === "number" ? value : 0;
}

function average(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function averageStat(
  matches: TeamSeasonMatchPoint[],
  stat: StatKey,
  perspective: StatPerspective,
): number {
  return average(matches.map((match) => valueForMatch(match, stat, perspective)));
}

function roundProjection(value: number): number {
  return Math.round(value * 10) / 10;
}

function buildStatSeriesChart(params: {
  teamName: string;
  stat: StatKey;
  perspective: StatPerspective;
  matches: TeamSeasonMatchPoint[];
}): ChatChartSpec {
  const points: ChatChartPoint[] = params.matches.map((match) => ({
    label: `${match.opponent_shortcut} ${String(match.match_date).slice(0, 10)}`,
    value: valueForMatch(match, params.stat, params.perspective),
    metadata: {
      match_id: match.match_id,
      opponent: match.opponent_name,
      result: match.result,
      home_team: match.home_team_name,
      away_team: match.away_team_name,
    },
  }));

  const perspectiveLabel =
    params.perspective === "team"
      ? params.teamName
      : params.perspective === "opponent"
        ? "Rywal"
        : "Łącznie";

  return {
    type: "bar",
    title: `${STAT_LABELS[params.stat]}: ${perspectiveLabel}`,
    xLabel: "Mecz",
    yLabel: STAT_LABELS[params.stat],
    seriesLabel: perspectiveLabel,
    points,
  };
}

async function fetchTeamProfileForLatestSeason(params: {
  teamId: number;
  seasonId?: number;
  leagueId?: number;
  limit: number;
}): Promise<{ profile: TeamProfile; seasonId: number | null; inferred: boolean }> {
  const initialProfile = await fetchReadOnly<TeamProfile>(
    `/teams/${params.teamId}/profile`,
    {
      season_id: params.seasonId,
      league_id: params.leagueId,
      limit: params.limit,
    },
  );
  if (params.seasonId || initialProfile.season_id) {
    return {
      profile: initialProfile,
      seasonId: initialProfile.season_id ?? params.seasonId ?? null,
      inferred: false,
    };
  }

  const latestSeasonId = initialProfile.recent_matches[0]?.season_id ?? null;
  if (!latestSeasonId) {
    return { profile: initialProfile, seasonId: null, inferred: false };
  }

  const profile = await fetchReadOnly<TeamProfile>(
    `/teams/${params.teamId}/profile`,
    {
      season_id: latestSeasonId,
      league_id: params.leagueId,
      limit: params.limit,
    },
  );
  return { profile, seasonId: latestSeasonId, inferred: true };
}

function playerStatValue(
  match: FootballPlayerMatchStat,
  stat: FootballPlayerLeaderStat,
): number {
  const value = match[stat];
  return typeof value === "number" ? value : 0;
}

function buildPlayerLeaderTable(params: {
  title: string;
  stat: FootballPlayerLeaderStat;
  rows: {
    playerName: string;
    total: number;
    appearances: number;
    average: number;
  }[];
}): ChatTableSpec {
  return {
    title: params.title,
    columns: [
      "Zawodnik",
      FOOTBALL_PLAYER_STAT_LABELS[params.stat],
      "Mecze",
      "Śr./mecz",
    ],
    rows: params.rows.map((row) => [
      row.playerName,
      row.total,
      row.appearances,
      row.average,
    ]),
  };
}

function isHockeyPlayerStatsResponse(
  response: FootballPlayerMatchStatsResponse | HockeyPlayerMatchStatsResponse,
): response is HockeyPlayerMatchStatsResponse {
  return "player_role" in response;
}

async function resolveSeasonIdForPlayers(args: Record<string, unknown>): Promise<{
  seasonId: number;
  warning?: string;
}> {
  const requestedSeasonId = numberArg(args, "season_id", { min: 1 });
  if (requestedSeasonId) {
    return { seasonId: requestedSeasonId };
  }

  const seasonYears = stringArg(args, "season_years", { maxLength: 20 });
  if (seasonYears) {
    return { seasonId: await resolveSeasonIdByYears(seasonYears) };
  }

  const sportId = numberArg(args, "sport_id", { required: true, min: 1 })!;
  const response = await fetchReadOnly<{
    seasons: { season_id: number; years: string }[];
  }>(`/players/${sportId}/filters/seasons`);
  const latestSeason = response.seasons[0];
  if (!latestSeason) {
    throw new Error(`No player stat seasons found for sport ${sportId}`);
  }

  return {
    seasonId: latestSeason.season_id,
    warning: `Nie podano sezonu, więc użyłem najnowszego sezonu zawodników: ${latestSeason.years}.`,
  };
}

async function getPlayerStatSummary(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const sportId = numberArg(args, "sport_id", { required: true, min: 1 })!;
  const query = stringArg(args, "query", { required: true, maxLength: 80 })!;
  const teamId = numberArg(args, "team_id", { min: 1 });
  const hasSeasonFilter = Boolean(
    numberArg(args, "season_id", { min: 1 }) ||
      stringArg(args, "season_years", { maxLength: 20 }),
  );
  const limit =
    numberArg(args, "limit", { min: 1, max: 200 }) ??
    (hasSeasonFilter ? 200 : 10);
  const season = await resolveSeasonIdForPlayers(args);
  const playersResponse = await fetchReadOnly<FootballPlayersListResponse>(
    `/players/${sportId}`,
    {
      season_id: season.seasonId,
      team_id: teamId,
      search: query,
    },
  );
  const player = playersResponse.players[0];
  if (!player) {
    throw new Error(`No player found for query: ${query}`);
  }

  const stats = await fetchReadOnly<
    FootballPlayerMatchStatsResponse | HockeyPlayerMatchStatsResponse
  >(`/players/${sportId}/${player.id}/match-stats`, {
    season_id: season.seasonId,
    limit,
  });
  const isHockey = isHockeyPlayerStatsResponse(stats);
  const stat = resolvePlayerStat(args, sportId, isHockey ? stats.player_role : null);
  const label = getPlayerStatLabel(stat, sportId, isHockey ? stats.player_role : null);
  const matches = stats.matches.slice(0, limit);
  const values = matches.map((match) => playerStatSummaryValue(match, stat));
  const total = values.reduce((sum, value) => sum + value, 0);
  const maximum = values.length > 0 ? Math.max(...values) : 0;
  const maximumMatches = matches.filter(
    (match) => playerStatSummaryValue(match, stat) === maximum,
  );
  const averageValue = average(values);
  const averageRounded = Math.round(averageValue * 100) / 100;
  const chart: ChatChartSpec = {
    type: "bar",
    title: `${label}: ${player.common_name}`,
    xLabel: "Mecz",
    yLabel: label,
    seriesLabel: label,
    points: [...matches].reverse().map((match) => ({
      label: `${match.opponent_shortcut} ${match.match_date}`,
      value: playerStatSummaryValue(match, stat),
      metadata: {
        match_id: match.match_id,
        home_team: match.home_team,
        away_team: match.away_team,
      },
    })),
  };
  const table: ChatTableSpec = {
    title: `${label}: ${player.common_name}`,
    columns: ["Mecz", "Data", label],
    rows: matches.map((match) => [
      `${match.home_team} - ${match.away_team}`,
      match.match_date,
      playerStatSummaryValue(match, stat),
    ]),
  };

  return {
    name: "get_player_stat_summary",
    summary: `${player.common_name}: ${label.toLocaleLowerCase("pl")} = ${total} w ${matches.length} meczach, maksymalnie ${maximum}, średnio ${averageRounded}.`,
    data: {
      player,
      sport_id: sportId,
      season_id: season.seasonId,
      stat,
      total,
      maximum,
      maximum_matches: maximumMatches,
      average: averageRounded,
      matches,
    },
    chart,
    table,
    dataSources: [
      {
        label: "Wyszukiwanie zawodnika",
        endpoint: getEndpoint(`/players/${sportId}`),
        params: {
          sport_id: sportId,
          season_id: season.seasonId,
          team_id: teamId ?? null,
          search: query,
        },
      },
      {
        label: "Statystyki meczowe zawodnika",
        endpoint: getEndpoint(`/players/${sportId}/${player.id}/match-stats`),
        params: {
          sport_id: sportId,
          player_id: player.id,
          season_id: season.seasonId,
          limit,
        },
      },
    ],
    warnings: [
      ...(season.warning ? [season.warning] : []),
      ...(playersResponse.players.length > 1
        ? [`Znaleziono kilku zawodników dla "${query}". Użyłem: ${player.common_name}.`]
        : []),
      ...(matches.length === 0
        ? ["Nie znaleziono logu meczowego dla wybranego zawodnika."]
        : []),
    ],
  };
}

function resolvePlayerStat(
  args: Record<string, unknown>,
  sportId: number,
  playerRole: "skater" | "goalie" | null,
): PlayerStatSummaryKey {
  const requested = stringArg(args, "stat", { maxLength: 40 });
  if (sportId === HOCKEY_SPORT_ID && playerRole === "goalie") {
    const allowed = Object.keys(HOCKEY_GOALIE_STAT_LABELS);
    return allowed.includes(requested ?? "")
      ? (requested as HockeyGoaliePlayerStat)
      : "saves_acc";
  }
  if (sportId === HOCKEY_SPORT_ID) {
    const allowed = Object.keys(HOCKEY_SKATER_STAT_LABELS);
    return allowed.includes(requested ?? "")
      ? (requested as HockeySkaterPlayerStat)
      : "points";
  }

  const allowed = Object.keys(FOOTBALL_PLAYER_STAT_LABELS);
  return allowed.includes(requested ?? "")
    ? (requested as FootballPlayerLeaderStat)
    : "goals";
}

function getPlayerStatLabel(
  stat: PlayerStatSummaryKey,
  sportId: number,
  playerRole: "skater" | "goalie" | null,
): string {
  if (sportId === HOCKEY_SPORT_ID && playerRole === "goalie") {
    return HOCKEY_GOALIE_STAT_LABELS[stat as HockeyGoaliePlayerStat];
  }
  if (sportId === HOCKEY_SPORT_ID) {
    return HOCKEY_SKATER_STAT_LABELS[stat as HockeySkaterPlayerStat];
  }
  return FOOTBALL_PLAYER_STAT_LABELS[stat as FootballPlayerLeaderStat];
}

function playerStatSummaryValue(
  match: FootballPlayerMatchStat | HockeyPlayerMatchStat,
  stat: PlayerStatSummaryKey,
): number {
  const value = (match as unknown as Record<string, number | null | undefined>)[
    stat
  ];
  return typeof value === "number" ? value : 0;
}

async function listLeagues(args: Record<string, unknown>): Promise<ToolResult> {
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

async function searchTeams(args: Record<string, unknown>): Promise<ToolResult> {
  const query = stringArg(args, "query", { required: true, maxLength: 80 })!;
  const sportId = numberArg(args, "sport_id", { min: 1 });
  const pageSize = numberArg(args, "page_size", { min: 1, max: 10 }) ?? 5;
  const response = await fetchReadOnly("/teams/search", {
    team_name: query,
    sport_id: sportId,
    page_size: pageSize,
  });

  return {
    name: "search_teams",
    summary: `Wyniki wyszukiwania drużyny dla "${query}".`,
    data: response,
    dataSources: [
      {
        label: "Wyszukiwanie drużyn",
        endpoint: getEndpoint("/teams/search"),
        params: { team_name: query, sport_id: sportId ?? null, page_size: pageSize },
      },
    ],
    warnings: [],
  };
}

async function getTeamProfile(args: Record<string, unknown>): Promise<ToolResult> {
  const teamId = numberArg(args, "team_id", { required: true, min: 1 })!;
  const seasonId = numberArg(args, "season_id", { min: 1 });
  const leagueId = numberArg(args, "league_id", { min: 1 });
  const limit = numberArg(args, "limit", { min: 1, max: 20 }) ?? 10;
  const response = await fetchReadOnly<TeamProfile>(`/teams/${teamId}/profile`, {
    season_id: seasonId,
    league_id: leagueId,
    limit,
  });

  return {
    name: "get_team_profile",
    summary: seasonId
      ? `Profil drużyny ${response.team.name} dla sezonu ${seasonId}.`
      : `Profil drużyny ${response.team.name} bez filtra sezonu.`,
    data: {
      team: response.team,
      season_id: response.season_id,
      league_id: response.league_id,
      form: response.form,
      overall_stats: response.overall_stats,
      recent_matches: response.recent_matches.slice(0, limit),
    },
    dataSources: [
      {
        label: "Profil drużyny",
        endpoint: getEndpoint(`/teams/${teamId}/profile`),
        params: {
          team_id: teamId,
          season_id: seasonId ?? null,
          league_id: leagueId ?? null,
          limit,
        },
      },
    ],
    warnings: seasonId
      ? []
      : ["Nie podano sezonu, więc pobrałem mecze bez filtra sezonu."],
  };
}

function buildTeamOverviewTable(profile: TeamProfile): ChatTableSpec {
  return {
    title: `Profil: ${profile.team.name}`,
    columns: ["Zakres", "M", "W", "R", "P", "Bramki", "Pkt"],
    rows: [
      [
        "Ogółem",
        profile.overall_stats.played,
        profile.overall_stats.wins,
        profile.overall_stats.draws,
        profile.overall_stats.losses,
        `${profile.overall_stats.goals_for}:${profile.overall_stats.goals_conceded}`,
        profile.overall_stats.points,
      ],
      [
        "Dom",
        profile.home_stats.played,
        profile.home_stats.wins,
        profile.home_stats.draws,
        profile.home_stats.losses,
        `${profile.home_stats.goals_for}:${profile.home_stats.goals_conceded}`,
        profile.home_stats.points,
      ],
      [
        "Wyjazd",
        profile.away_stats.played,
        profile.away_stats.wins,
        profile.away_stats.draws,
        profile.away_stats.losses,
        `${profile.away_stats.goals_for}:${profile.away_stats.goals_conceded}`,
        profile.away_stats.points,
      ],
    ],
  };
}

function pickTeamOverviewChart(profile: TeamProfile): ChatChartSpec | null {
  const matches = profile.season_matches.slice(0, 10).reverse();
  if (matches.length === 0) {
    return null;
  }

  const hasShotsOnTarget = matches.some(
    (match) => match.team_shots_on_target > 0,
  );
  const stat: StatKey = hasShotsOnTarget ? "shots_on_target" : "goals";
  return buildStatSeriesChart({
    teamName: profile.team.name,
    stat,
    perspective: "team",
    matches,
  });
}

async function getTeamOverview(args: Record<string, unknown>): Promise<ToolResult> {
  const resolvedTeam = await resolveTeamId(args);
  const requestedSeasonId = numberArg(args, "season_id", { min: 1 });
  const seasonYears = stringArg(args, "season_years", { maxLength: 20 });
  const leagueId = numberArg(args, "league_id", { min: 1 });
  const limit = numberArg(args, "limit", { min: 1, max: 20 }) ?? 10;
  const seasonId = requestedSeasonId ?? (
    seasonYears ? await resolveSeasonIdByYears(seasonYears) : undefined
  );

  const initialProfile = await fetchReadOnly<TeamProfile>(
    `/teams/${resolvedTeam.teamId}/profile`,
    {
      season_id: seasonId,
      league_id: leagueId,
      limit,
    },
  );
  const latestSeasonId =
    initialProfile.season_id ??
    initialProfile.recent_matches[0]?.season_id ??
    null;
  const profile =
    seasonId || !latestSeasonId
      ? initialProfile
      : await fetchReadOnly<TeamProfile>(
          `/teams/${resolvedTeam.teamId}/profile`,
          {
            season_id: latestSeasonId,
            league_id: leagueId,
            limit,
          },
        );
  const effectiveSeasonId = profile.season_id ?? latestSeasonId;

  return {
    name: "get_team_overview",
    summary: effectiveSeasonId
      ? `Profil drużyny ${profile.team.name} dla sezonu ${effectiveSeasonId}.`
      : `Profil drużyny ${profile.team.name} bez filtra sezonu.`,
    data: {
      team: profile.team,
      season_id: effectiveSeasonId,
      league_id: profile.league_id,
      form: profile.form,
      overall_stats: profile.overall_stats,
      home_stats: profile.home_stats,
      away_stats: profile.away_stats,
      recent_matches: profile.recent_matches.slice(0, limit),
      season_matches: profile.season_matches.slice(0, limit),
    },
    chart: pickTeamOverviewChart(profile),
    table: buildTeamOverviewTable(profile),
    dataSources: [
      ...(resolvedTeam.dataSource ? [resolvedTeam.dataSource] : []),
      {
        label: "Profil drużyny",
        endpoint: getEndpoint(`/teams/${resolvedTeam.teamId}/profile`),
        params: {
          team_id: resolvedTeam.teamId,
          season_id: effectiveSeasonId,
          league_id: leagueId ?? null,
          limit,
        },
      },
    ],
    warnings: [
      ...(resolvedTeam.warning ? [resolvedTeam.warning] : []),
      ...(seasonYears && !requestedSeasonId
        ? [`Sezon rozpoznany po latach: ${seasonYears}.`]
        : []),
      ...(!seasonId && effectiveSeasonId
        ? [`Użyłem najnowszego sezonu z meczów drużyny: ${effectiveSeasonId}.`]
        : []),
    ],
  };
}

async function getTeamStatSeries(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const resolvedTeam = await resolveTeamId(args);
  const seasonId = numberArg(args, "season_id", { min: 1 });
  const leagueId = numberArg(args, "league_id", { min: 1 });
  const limit = numberArg(args, "limit", { min: 1, max: 20 }) ?? 10;
  const stat = enumArg(
    args,
    "stat",
    [
      "goals",
      "total_goals",
      "shots",
      "shots_on_target",
      "corners",
      "cards",
      "offsides",
      "fouls",
      "penalty_minutes",
      "penalties",
    ],
    "shots_on_target",
  );
  const perspective = enumArg(
    args,
    "perspective",
    ["team", "opponent", "total"],
    "team",
  );

  const profile = await fetchReadOnly<TeamProfile>(
    `/teams/${resolvedTeam.teamId}/profile`,
    {
      season_id: seasonId,
      league_id: leagueId,
      limit,
    },
  );
  const matches = profile.season_matches.slice(0, limit).reverse();
  const chart = buildStatSeriesChart({
    teamName: profile.team.name,
    stat,
    perspective,
    matches,
  });

  const warnings = [
    ...(resolvedTeam.warning ? [resolvedTeam.warning] : []),
    ...(seasonId
      ? []
      : ["Nie podano sezonu, więc seria obejmuje najnowsze mecze bez filtra sezonu."]),
    ...(matches.length === 0
      ? ["Nie znaleziono meczów z danymi dla wybranych parametrów."]
      : []),
  ];

  return {
    name: "get_team_stat_series",
    summary: `${STAT_LABELS[stat]} dla ${profile.team.name}: ostatnie ${matches.length} meczów.`,
    data: {
      team: profile.team,
      season_id: profile.season_id,
      league_id: profile.league_id,
      stat,
      perspective,
      matches: chart.points,
    },
    chart,
    dataSources: [
      ...(resolvedTeam.dataSource ? [resolvedTeam.dataSource] : []),
      {
        label: "Seria statystyk drużyny",
        endpoint: getEndpoint(`/teams/${resolvedTeam.teamId}/profile`),
        params: {
          team_id: resolvedTeam.teamId,
          season_id: seasonId ?? null,
          league_id: leagueId ?? null,
          limit,
        },
      },
    ],
    warnings,
  };
}

async function getTeamPlayerStatLeader(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const sportId = numberArg(args, "sport_id", { min: 1 }) ?? FOOTBALL_SPORT_ID;
  if (sportId !== FOOTBALL_SPORT_ID) {
    throw new Error(
      "get_team_player_stat_leader supports football only. Use get_player_stat_summary for hockey player questions.",
    );
  }

  const resolvedTeam = await resolveTeamId({
    ...args,
    sport_id: FOOTBALL_SPORT_ID,
  });
  const requestedSeasonId = numberArg(args, "season_id", { min: 1 });
  const seasonYears = stringArg(args, "season_years", { maxLength: 20 });
  const leagueId = numberArg(args, "league_id", { min: 1 });
  const limit = numberArg(args, "limit", { min: 1, max: 10 }) ?? 5;
  const stat = enumArg(
    args,
    "stat",
    ["goals", "assists", "shots", "shots_on_target", "fouls_conceded", "yellow_cards"],
    "shots_on_target",
  );
  const seasonId = requestedSeasonId ?? (
    seasonYears ? await resolveSeasonIdByYears(seasonYears) : undefined
  );
  const { profile, seasonId: effectiveSeasonId, inferred } =
    await fetchTeamProfileForLatestSeason({
      teamId: resolvedTeam.teamId,
      seasonId,
      leagueId,
      limit,
    });

  if (!effectiveSeasonId) {
    throw new Error(`No season found for team ${profile.team.name}`);
  }

  const targetMatches = profile.season_matches.slice(0, limit);
  const targetMatchIds = new Set(targetMatches.map((match) => match.match_id));
  const playersResponse = await fetchReadOnly<FootballPlayersListResponse>(
    `/players/${FOOTBALL_SPORT_ID}`,
    {
      season_id: effectiveSeasonId,
      team_id: resolvedTeam.teamId,
    },
  );
  const playerStats = await Promise.all(
    playersResponse.players.map(async (player) => {
      try {
        const stats = await fetchReadOnly<FootballPlayerMatchStatsResponse>(
          `/players/${FOOTBALL_SPORT_ID}/${player.id}/match-stats`,
          {
            season_id: effectiveSeasonId,
            limit: 50,
          },
        );
        const matches = stats.matches.filter((match) =>
          targetMatchIds.has(match.match_id),
        );
        const total = matches.reduce(
          (sum, match) => sum + playerStatValue(match, stat),
          0,
        );
        return {
          playerId: player.id,
          playerName: player.common_name,
          total,
          appearances: matches.length,
          average: matches.length > 0
            ? Math.round((total / matches.length) * 100) / 100
            : 0,
        };
      } catch {
        return {
          playerId: player.id,
          playerName: player.common_name,
          total: 0,
          appearances: 0,
          average: 0,
        };
      }
    }),
  );
  const leaders = playerStats
    .filter((player) => player.appearances > 0 || player.total > 0)
    .sort((left, right) =>
      right.total - left.total ||
      right.appearances - left.appearances ||
      left.playerName.localeCompare(right.playerName, "pl"),
    );
  const topRows = leaders.slice(0, 8);
  const leader = leaders[0] ?? null;
  const statLabel = FOOTBALL_PLAYER_STAT_LABELS[stat].toLocaleLowerCase("pl");
  const table = buildPlayerLeaderTable({
    title: `${FOOTBALL_PLAYER_STAT_LABELS[stat]}: ${profile.team.name}`,
    stat,
    rows: topRows,
  });
  const chart: ChatChartSpec = {
    type: "bar",
    title: `${FOOTBALL_PLAYER_STAT_LABELS[stat]} w ostatnich ${targetMatches.length} meczach`,
    xLabel: "Zawodnik",
    yLabel: FOOTBALL_PLAYER_STAT_LABELS[stat],
    seriesLabel: FOOTBALL_PLAYER_STAT_LABELS[stat],
    points: topRows.map((row) => ({
      label: row.playerName,
      value: row.total,
      metadata: {
        appearances: row.appearances,
        average: row.average,
      },
    })),
  };

  return {
    name: "get_team_player_stat_leader",
    summary: leader
      ? `${leader.playerName} prowadzi w ${statLabel}: ${leader.total} w ostatnich ${targetMatches.length} meczach drużyny ${profile.team.name}.`
      : `Nie znaleziono zawodnika z danymi ${statLabel} dla drużyny ${profile.team.name}.`,
    data: {
      team: profile.team,
      season_id: effectiveSeasonId,
      stat,
      lookback_matches: targetMatches.length,
      target_match_ids: [...targetMatchIds],
      leader,
      players: topRows,
    },
    chart,
    table,
    dataSources: [
      ...(resolvedTeam.dataSource ? [resolvedTeam.dataSource] : []),
      {
        label: "Profil drużyny",
        endpoint: getEndpoint(`/teams/${resolvedTeam.teamId}/profile`),
        params: {
          team_id: resolvedTeam.teamId,
          season_id: effectiveSeasonId,
          league_id: leagueId ?? null,
          limit,
        },
      },
      {
        label: "Lista zawodników drużyny",
        endpoint: getEndpoint(`/players/${FOOTBALL_SPORT_ID}`),
        params: {
          sport_id: FOOTBALL_SPORT_ID,
          season_id: effectiveSeasonId,
          team_id: resolvedTeam.teamId,
        },
      },
      {
        label: "Statystyki meczowe zawodników",
        endpoint: getEndpoint(`/players/${FOOTBALL_SPORT_ID}/{player_id}/match-stats`),
        params: {
          sport_id: FOOTBALL_SPORT_ID,
          season_id: effectiveSeasonId,
          limit: 50,
        },
      },
    ],
    warnings: [
      ...(resolvedTeam.warning ? [resolvedTeam.warning] : []),
      ...(seasonYears && !requestedSeasonId
        ? [`Sezon rozpoznany po latach: ${seasonYears}.`]
        : []),
      ...(inferred
        ? [`Użyłem najnowszego sezonu z meczów drużyny: ${effectiveSeasonId}.`]
        : []),
      ...(targetMatches.length < limit
        ? [`Znaleziono tylko ${targetMatches.length} meczów drużyny dla tego zakresu.`]
        : []),
      ...(leaders.length === 0
        ? ["Brak statystyk zawodników dla ostatnich meczów tej drużyny."]
        : []),
    ],
  };
}

function buildMatchupChart(params: {
  teamAName: string;
  teamBName: string;
  target: MatchupTarget;
  teamAProjection: number;
  teamBProjection: number;
}): ChatChartSpec {
  const title =
    params.target === "result"
      ? "Projekcja bramek"
      : `Projekcja: ${STAT_LABELS[params.target]}`;

  return {
    type: "bar",
    title,
    xLabel: "Drużyna",
    yLabel: params.target === "result" ? "Bramki" : STAT_LABELS[params.target],
    seriesLabel: "Projekcja",
    points: [
      {
        label: params.teamAName,
        value: params.teamAProjection,
      },
      {
        label: params.teamBName,
        value: params.teamBProjection,
      },
    ],
  };
}

function buildMatchupTable(params: {
  teamAName: string;
  teamBName: string;
  target: MatchupTarget;
  teamAForAverage: number;
  teamAAgainstAverage: number;
  teamBForAverage: number;
  teamBAgainstAverage: number;
  teamAProjection: number;
  teamBProjection: number;
}): ChatTableSpec {
  const label =
    params.target === "result" ? "Bramki" : STAT_LABELS[params.target];

  return {
    title: `Projekcja: ${params.teamAName} vs ${params.teamBName}`,
    columns: ["Drużyna", `Śr. ${label}`, `Śr. rywali`, "Projekcja"],
    rows: [
      [
        params.teamAName,
        params.teamAForAverage,
        params.teamBAgainstAverage,
        params.teamAProjection,
      ],
      [
        params.teamBName,
        params.teamBForAverage,
        params.teamAAgainstAverage,
        params.teamBProjection,
      ],
      [
        "Suma meczu",
        null,
        null,
        roundProjection(params.teamAProjection + params.teamBProjection),
      ],
    ],
  };
}

function matchupResultLabel(teamAProjection: number, teamBProjection: number): string {
  const roundedA = Math.max(0, Math.round(teamAProjection));
  const roundedB = Math.max(0, Math.round(teamBProjection));
  if (Math.abs(teamAProjection - teamBProjection) < 0.25) {
    return `najbliżej remisu, około ${roundedA}:${roundedB}`;
  }
  return teamAProjection > teamBProjection
    ? `lekka przewaga gospodarza, około ${roundedA}:${roundedB}`
    : `lekka przewaga gościa, około ${roundedA}:${roundedB}`;
}

async function getMatchupProjection(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const teamAQuery = stringArg(args, "team_a_query", {
    required: true,
    maxLength: 80,
  })!;
  const teamBQuery = stringArg(args, "team_b_query", {
    required: true,
    maxLength: 80,
  })!;
  const target = enumArg(
    args,
    "target",
    [
      "result",
      "goals",
      "total_goals",
      "shots",
      "shots_on_target",
      "corners",
      "cards",
      "offsides",
      "fouls",
      "penalty_minutes",
      "penalties",
    ],
    "result",
  );
  const requestedSeasonId = numberArg(args, "season_id", { min: 1 });
  const seasonYears = stringArg(args, "season_years", { maxLength: 20 });
  const leagueId = numberArg(args, "league_id", { min: 1 });
  const limit = numberArg(args, "limit", { min: 1, max: 20 }) ?? 10;
  const seasonId = requestedSeasonId ?? (
    seasonYears ? await resolveSeasonIdByYears(seasonYears) : undefined
  );
  const sportId = numberArg(args, "sport_id", { min: 1 });
  const teamA = await resolveTeamId({ query: teamAQuery, sport_id: sportId });
  const teamB = await resolveTeamId({ query: teamBQuery, sport_id: sportId });
  const [profileA, profileB] = await Promise.all([
    fetchReadOnly<TeamProfile>(`/teams/${teamA.teamId}/profile`, {
      season_id: seasonId,
      league_id: leagueId,
      limit,
    }),
    fetchReadOnly<TeamProfile>(`/teams/${teamB.teamId}/profile`, {
      season_id: seasonId,
      league_id: leagueId,
      limit,
    }),
  ]);
  const matchesA = profileA.season_matches.slice(0, limit);
  const matchesB = profileB.season_matches.slice(0, limit);
  const stat: StatKey = target === "result" ? "goals" : target;
  const teamAForAverage = roundProjection(averageStat(matchesA, stat, "team"));
  const teamAAgainstAverage = roundProjection(
    averageStat(matchesA, stat, "opponent"),
  );
  const teamBForAverage = roundProjection(averageStat(matchesB, stat, "team"));
  const teamBAgainstAverage = roundProjection(
    averageStat(matchesB, stat, "opponent"),
  );
  const teamAProjection = roundProjection(
    (teamAForAverage + teamBAgainstAverage) / 2,
  );
  const teamBProjection = roundProjection(
    (teamBForAverage + teamAAgainstAverage) / 2,
  );
  const table = buildMatchupTable({
    teamAName: profileA.team.name,
    teamBName: profileB.team.name,
    target,
    teamAForAverage,
    teamAAgainstAverage,
    teamBForAverage,
    teamBAgainstAverage,
    teamAProjection,
    teamBProjection,
  });
  const chart = buildMatchupChart({
    teamAName: profileA.team.name,
    teamBName: profileB.team.name,
    target,
    teamAProjection,
    teamBProjection,
  });
  const resultSummary =
    target === "result"
      ? matchupResultLabel(teamAProjection, teamBProjection)
      : `oczekiwana suma: ${roundProjection(teamAProjection + teamBProjection)}`;

  return {
    name: "get_matchup_projection",
    summary: `Hipotetyczna projekcja ${profileA.team.name} vs ${profileB.team.name}: ${resultSummary}.`,
    data: {
      team_a: profileA.team,
      team_b: profileB.team,
      season_id: seasonId ?? null,
      target,
      lookback_matches: limit,
      team_a_for_average: teamAForAverage,
      team_a_against_average: teamAAgainstAverage,
      team_b_for_average: teamBForAverage,
      team_b_against_average: teamBAgainstAverage,
      team_a_projection: teamAProjection,
      team_b_projection: teamBProjection,
      total_projection: roundProjection(teamAProjection + teamBProjection),
      result_hint: resultSummary,
    },
    chart,
    table,
    dataSources: [
      ...(teamA.dataSource ? [teamA.dataSource] : []),
      ...(teamB.dataSource ? [teamB.dataSource] : []),
      {
        label: "Profil drużyny A",
        endpoint: getEndpoint(`/teams/${teamA.teamId}/profile`),
        params: {
          team_id: teamA.teamId,
          season_id: seasonId ?? null,
          league_id: leagueId ?? null,
          limit,
        },
      },
      {
        label: "Profil drużyny B",
        endpoint: getEndpoint(`/teams/${teamB.teamId}/profile`),
        params: {
          team_id: teamB.teamId,
          season_id: seasonId ?? null,
          league_id: leagueId ?? null,
          limit,
        },
      },
    ],
    warnings: [
      ...(teamA.warning ? [teamA.warning] : []),
      ...(teamB.warning ? [teamB.warning] : []),
      "To jest projekcja statystyczna z ostatnich meczów, a nie pewna predykcja wyniku.",
      ...(matchesA.length === 0 || matchesB.length === 0
        ? ["Jedna z drużyn ma za mało meczów dla stabilnej projekcji."]
        : []),
    ],
  };
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

async function getLeagueTable(args: Record<string, unknown>): Promise<ToolResult> {
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
        endpoint: getEndpoint(`/leagues/${resolvedLeague.league.id}/standings`),
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

async function getLeagueStandings(
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

const TOOL_RUNNERS: Record<
  ChatToolName,
  (args: Record<string, unknown>) => Promise<ToolResult>
> = {
  list_leagues: listLeagues,
  search_teams: searchTeams,
  get_team_profile: getTeamProfile,
  get_team_overview: getTeamOverview,
  get_team_stat_series: getTeamStatSeries,
  get_team_player_stat_leader: getTeamPlayerStatLeader,
  get_player_stat_summary: getPlayerStatSummary,
  get_matchup_projection: getMatchupProjection,
  get_league_table: getLeagueTable,
  get_league_standings: getLeagueStandings,
};

export async function runPlannedTools(
  plannedCalls: PlannedToolCall[],
  sport: ChatSportContext,
): Promise<ToolResult[]> {
  const results: ToolResult[] = [];
  for (const call of plannedCalls.slice(0, MAX_TOOL_CALLS)) {
    const runner = TOOL_RUNNERS[call.tool];
    if (!runner) {
      results.push({
        name: call.tool,
        summary: `Narzędzie ${call.tool} nie jest dozwolone.`,
        data: null,
        dataSources: [],
        warnings: [`Pominięto niedozwolone narzędzie: ${call.tool}.`],
      });
      continue;
    }

    try {
      results.push(
        await runner({
          ...(call.args ?? {}),
          sport_id: sport.sport_id,
        }),
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Unknown tool execution error.";
      results.push({
        name: call.tool,
        summary: `Narzędzie ${call.tool} nie zwróciło danych.`,
        data: null,
        dataSources: [],
        warnings: [message],
      });
    }
  }
  return results;
}
