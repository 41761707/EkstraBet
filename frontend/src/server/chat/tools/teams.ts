import type {
  ChatChartPoint,
  ChatChartSpec,
  ChatDataSource,
  ChatTableSpec,
  TeamProfile,
  TeamSeasonMatchPoint,
} from "@/types/api";

import { enumArg, numberArg, stringArg } from "./args";
import { fetchReadOnly, getEndpoint } from "./http";
import { resolveSeasonIdByYears } from "./leagues";
import type { MatchupTarget, StatKey, StatPerspective, ToolResult } from "./types";
import { STAT_LABELS } from "./types";

export async function resolveTeamId(args: Record<string, unknown>): Promise<{
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

export function average(values: number[]): number {
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
  return average(
    matches.map((match) => valueForMatch(match, stat, perspective)),
  );
}

function roundProjection(value: number): number {
  return Math.round(value * 10) / 10;
}

export function buildStatSeriesChart(params: {
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

export async function fetchTeamProfileForLatestSeason(params: {
  teamId: number;
  seasonId?: number;
  leagueId?: number;
  limit: number;
}): Promise<{
  profile: TeamProfile;
  seasonId: number | null;
  inferred: boolean;
}> {
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

export async function searchTeams(
  args: Record<string, unknown>,
): Promise<ToolResult> {
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
        params: {
          team_name: query,
          sport_id: sportId ?? null,
          page_size: pageSize,
        },
      },
    ],
    warnings: [],
  };
}

export async function getTeamProfile(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const teamId = numberArg(args, "team_id", { required: true, min: 1 })!;
  const seasonId = numberArg(args, "season_id", { min: 1 });
  const leagueId = numberArg(args, "league_id", { min: 1 });
  const limit = numberArg(args, "limit", { min: 1, max: 20 }) ?? 10;
  const response = await fetchReadOnly<TeamProfile>(
    `/teams/${teamId}/profile`,
    {
      season_id: seasonId,
      league_id: leagueId,
      limit,
    },
  );

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

export async function getTeamOverview(
  args: Record<string, unknown>,
): Promise<ToolResult> {
  const resolvedTeam = await resolveTeamId(args);
  const requestedSeasonId = numberArg(args, "season_id", { min: 1 });
  const seasonYears = stringArg(args, "season_years", { maxLength: 20 });
  const leagueId = numberArg(args, "league_id", { min: 1 });
  const limit = numberArg(args, "limit", { min: 1, max: 20 }) ?? 10;
  const seasonId =
    requestedSeasonId ??
    (seasonYears ? await resolveSeasonIdByYears(seasonYears) : undefined);

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

export async function getTeamStatSeries(
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
    warnings: [
      ...(resolvedTeam.warning ? [resolvedTeam.warning] : []),
      ...(seasonId
        ? []
        : [
            "Nie podano sezonu, więc seria obejmuje najnowsze mecze bez filtra sezonu.",
          ]),
      ...(matches.length === 0
        ? ["Nie znaleziono meczów z danymi dla wybranych parametrów."]
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
      { label: params.teamAName, value: params.teamAProjection },
      { label: params.teamBName, value: params.teamBProjection },
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

function matchupResultLabel(
  teamAProjection: number,
  teamBProjection: number,
): string {
  const roundedA = Math.max(0, Math.round(teamAProjection));
  const roundedB = Math.max(0, Math.round(teamBProjection));
  if (Math.abs(teamAProjection - teamBProjection) < 0.25) {
    return `najbliżej remisu, około ${roundedA}:${roundedB}`;
  }
  return teamAProjection > teamBProjection
    ? `lekka przewaga gospodarza, około ${roundedA}:${roundedB}`
    : `lekka przewaga gościa, około ${roundedA}:${roundedB}`;
}

function computeMatchupProjections(
  matchesA: TeamSeasonMatchPoint[],
  matchesB: TeamSeasonMatchPoint[],
  target: MatchupTarget,
) {
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
  return {
    teamAForAverage,
    teamAAgainstAverage,
    teamBForAverage,
    teamBAgainstAverage,
    teamAProjection,
    teamBProjection,
  };
}

function buildMatchupResult(params: {
  profileA: TeamProfile;
  profileB: TeamProfile;
  teamA: Awaited<ReturnType<typeof resolveTeamId>>;
  teamB: Awaited<ReturnType<typeof resolveTeamId>>;
  seasonId?: number;
  leagueId?: number;
  limit: number;
  target: MatchupTarget;
  projections: ReturnType<typeof computeMatchupProjections>;
  resultSummary: string;
  matchesAEmpty: boolean;
  matchesBEmpty: boolean;
}): ToolResult {
  const { projections } = params;
  return {
    name: "get_matchup_projection",
    summary: `Hipotetyczna projekcja ${params.profileA.team.name} vs ${params.profileB.team.name}: ${params.resultSummary}.`,
    data: {
      team_a: params.profileA.team,
      team_b: params.profileB.team,
      season_id: params.seasonId ?? null,
      target: params.target,
      lookback_matches: params.limit,
      team_a_for_average: projections.teamAForAverage,
      team_a_against_average: projections.teamAAgainstAverage,
      team_b_for_average: projections.teamBForAverage,
      team_b_against_average: projections.teamBAgainstAverage,
      team_a_projection: projections.teamAProjection,
      team_b_projection: projections.teamBProjection,
      total_projection: roundProjection(
        projections.teamAProjection + projections.teamBProjection,
      ),
      result_hint: params.resultSummary,
    },
    chart: buildMatchupChart({
      teamAName: params.profileA.team.name,
      teamBName: params.profileB.team.name,
      target: params.target,
      teamAProjection: projections.teamAProjection,
      teamBProjection: projections.teamBProjection,
    }),
    table: buildMatchupTable({
      teamAName: params.profileA.team.name,
      teamBName: params.profileB.team.name,
      target: params.target,
      ...projections,
    }),
    dataSources: [
      ...(params.teamA.dataSource ? [params.teamA.dataSource] : []),
      ...(params.teamB.dataSource ? [params.teamB.dataSource] : []),
      {
        label: "Profil drużyny A",
        endpoint: getEndpoint(`/teams/${params.teamA.teamId}/profile`),
        params: {
          team_id: params.teamA.teamId,
          season_id: params.seasonId ?? null,
          league_id: params.leagueId ?? null,
          limit: params.limit,
        },
      },
      {
        label: "Profil drużyny B",
        endpoint: getEndpoint(`/teams/${params.teamB.teamId}/profile`),
        params: {
          team_id: params.teamB.teamId,
          season_id: params.seasonId ?? null,
          league_id: params.leagueId ?? null,
          limit: params.limit,
        },
      },
    ],
    warnings: [
      ...(params.teamA.warning ? [params.teamA.warning] : []),
      ...(params.teamB.warning ? [params.teamB.warning] : []),
      "To jest projekcja statystyczna z ostatnich meczów, a nie pewna predykcja wyniku.",
      ...(params.matchesAEmpty || params.matchesBEmpty
        ? ["Jedna z drużyn ma za mało meczów dla stabilnej projekcji."]
        : []),
    ],
  };
}

export async function getMatchupProjection(
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
  const seasonId =
    requestedSeasonId ??
    (seasonYears ? await resolveSeasonIdByYears(seasonYears) : undefined);
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
  const projections = computeMatchupProjections(matchesA, matchesB, target);
  const resultSummary =
    target === "result"
      ? matchupResultLabel(
          projections.teamAProjection,
          projections.teamBProjection,
        )
      : `oczekiwana suma: ${roundProjection(projections.teamAProjection + projections.teamBProjection)}`;

  return buildMatchupResult({
    profileA,
    profileB,
    teamA,
    teamB,
    seasonId,
    leagueId,
    limit,
    target,
    projections,
    resultSummary,
    matchesAEmpty: matchesA.length === 0,
    matchesBEmpty: matchesB.length === 0,
  });
}
