import type {
  ChatChartSpec,
  ChatDataSource,
  ChatTableSpec,
  FootballPlayerMatchStat,
  FootballPlayerMatchStatsResponse,
  FootballPlayersListResponse,
  HockeyPlayerMatchStat,
  HockeyPlayerMatchStatsResponse,
  TeamProfile,
} from "@/types/api";

import { enumArg, numberArg, stringArg } from "./args";
import { fetchReadOnly, getEndpoint } from "./http";
import { resolveSeasonIdByYears } from "./leagues";
import { average, fetchTeamProfileForLatestSeason, resolveTeamId } from "./teams";
import type {
  FootballPlayerLeaderStat,
  TeamPlayerStatLeadersResponse,
  ToolResult,
} from "./types";
import {
  FOOTBALL_PLAYER_STAT_LABELS,
  FOOTBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
} from "./types";

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

function isHockeyPlayerStatsResponse(
  response: FootballPlayerMatchStatsResponse | HockeyPlayerMatchStatsResponse,
): response is HockeyPlayerMatchStatsResponse {
  return "player_role" in response;
}

async function resolveSeasonIdForPlayers(
  args: Record<string, unknown>,
): Promise<{ seasonId: number; warning?: string }> {
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
  // Cast: match union nie ma wspólnego indeksu dla wszystkich kluczów stat
  const value = (match as unknown as Record<string, number | null | undefined>)[
    stat
  ];
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

function buildPlayerStatVisuals(params: {
  playerName: string;
  label: string;
  matches: Array<FootballPlayerMatchStat | HockeyPlayerMatchStat>;
  stat: PlayerStatSummaryKey;
}): { chart: ChatChartSpec; table: ChatTableSpec } {
  const { playerName, label, matches, stat } = params;
  return {
    chart: {
      type: "bar",
      title: `${label}: ${playerName}`,
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
    },
    table: {
      title: `${label}: ${playerName}`,
      columns: ["Mecz", "Data", label],
      rows: matches.map((match) => [
        `${match.home_team} - ${match.away_team}`,
        match.match_date,
        playerStatSummaryValue(match, stat),
      ]),
    },
  };
}

function aggregatePlayerStatValues(
  matches: Array<FootballPlayerMatchStat | HockeyPlayerMatchStat>,
  stat: PlayerStatSummaryKey,
) {
  const values = matches.map((match) => playerStatSummaryValue(match, stat));
  const total = values.reduce((sum, value) => sum + value, 0);
  const maximum = values.length > 0 ? Math.max(...values) : 0;
  return {
    total,
    maximum,
    maximumMatches: matches.filter(
      (match) => playerStatSummaryValue(match, stat) === maximum,
    ),
    averageRounded: Math.round(average(values) * 100) / 100,
  };
}

export async function getPlayerStatSummary(
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
    { season_id: season.seasonId, team_id: teamId, search: query },
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
  const playerRole = isHockey ? stats.player_role : null;
  const stat = resolvePlayerStat(args, sportId, playerRole);
  const label = getPlayerStatLabel(stat, sportId, playerRole);
  const matches = stats.matches.slice(0, limit);
  const agg = aggregatePlayerStatValues(matches, stat);
  const visuals = buildPlayerStatVisuals({
    playerName: player.common_name,
    label,
    matches,
    stat,
  });

  return {
    name: "get_player_stat_summary",
    summary: `${player.common_name}: ${label.toLocaleLowerCase("pl")} = ${agg.total} w ${matches.length} meczach, maksymalnie ${agg.maximum}, średnio ${agg.averageRounded}.`,
    data: {
      player,
      sport_id: sportId,
      season_id: season.seasonId,
      stat,
      total: agg.total,
      maximum: agg.maximum,
      maximum_matches: agg.maximumMatches,
      average: agg.averageRounded,
      matches,
    },
    chart: visuals.chart,
    table: visuals.table,
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
        ? [
            `Znaleziono kilku zawodników dla "${query}". Użyłem: ${player.common_name}.`,
          ]
        : []),
      ...(matches.length === 0
        ? ["Nie znaleziono logu meczowego dla wybranego zawodnika."]
        : []),
    ],
  };
}

type LeaderRow = {
  playerId: number;
  playerName: string;
  total: number;
  appearances: number;
  average: number;
};

function buildTeamPlayerLeaderResult(params: {
  team: TeamProfile["team"];
  teamId: number;
  seasonId: number;
  leagueId?: number;
  limit: number;
  stat: FootballPlayerLeaderStat;
  targetMatchIds: number[];
  lookbackMatches: number;
  topRows: LeaderRow[];
  leadersPath: string;
  resolvedDataSource?: ChatDataSource;
  warnings: string[];
}): ToolResult {
  const leader = params.topRows[0] ?? null;
  const statLabel =
    FOOTBALL_PLAYER_STAT_LABELS[params.stat].toLocaleLowerCase("pl");
  const statName = FOOTBALL_PLAYER_STAT_LABELS[params.stat];

  return {
    name: "get_team_player_stat_leader",
    summary: leader
      ? `${leader.playerName} prowadzi w ${statLabel}: ${leader.total} w ostatnich ${params.lookbackMatches} meczach drużyny ${params.team.name}.`
      : `Nie znaleziono zawodnika z danymi ${statLabel} dla drużyny ${params.team.name}.`,
    data: {
      team: params.team,
      season_id: params.seasonId,
      stat: params.stat,
      lookback_matches: params.lookbackMatches,
      target_match_ids: params.targetMatchIds,
      leader,
      players: params.topRows,
    },
    chart: {
      type: "bar",
      title: `${statName} w ostatnich ${params.lookbackMatches} meczach`,
      xLabel: "Zawodnik",
      yLabel: statName,
      seriesLabel: statName,
      points: params.topRows.map((row) => ({
        label: row.playerName,
        value: row.total,
        metadata: { appearances: row.appearances, average: row.average },
      })),
    },
    table: buildPlayerLeaderTable({
      title: `${statName}: ${params.team.name}`,
      stat: params.stat,
      rows: params.topRows,
    }),
    dataSources: [
      ...(params.resolvedDataSource ? [params.resolvedDataSource] : []),
      {
        label: "Profil drużyny",
        endpoint: getEndpoint(`/teams/${params.teamId}/profile`),
        params: {
          team_id: params.teamId,
          season_id: params.seasonId,
          league_id: params.leagueId ?? null,
          limit: params.limit,
        },
      },
      {
        label: "Liderzy statystyk zawodników",
        endpoint: getEndpoint(params.leadersPath),
        params: {
          team_id: params.teamId,
          season_id: params.seasonId,
          stat: params.stat,
          match_ids: params.targetMatchIds.join(","),
          top: 8,
        },
      },
    ],
    warnings: params.warnings,
  };
}

export async function getTeamPlayerStatLeader(
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
    [
      "goals",
      "assists",
      "shots",
      "shots_on_target",
      "fouls_conceded",
      "yellow_cards",
    ],
    "shots_on_target",
  );
  const seasonId =
    requestedSeasonId ??
    (seasonYears ? await resolveSeasonIdByYears(seasonYears) : undefined);
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
  const targetMatchIds = targetMatches.map((match) => match.match_id);
  const leadersPath = `/teams/${resolvedTeam.teamId}/player-stat-leaders`;
  const leadersResponse = await fetchReadOnly<TeamPlayerStatLeadersResponse>(
    leadersPath,
    {
      season_id: effectiveSeasonId,
      stat,
      match_ids: targetMatchIds.join(","),
      top: 8,
    },
  );
  const topRows: LeaderRow[] = leadersResponse.leaders.map((row) => ({
    playerId: row.player_id,
    playerName: row.player_name,
    total: row.total,
    appearances: row.appearances,
    average: row.average,
  }));

  return buildTeamPlayerLeaderResult({
    team: profile.team,
    teamId: resolvedTeam.teamId,
    seasonId: effectiveSeasonId,
    leagueId,
    limit,
    stat,
    targetMatchIds,
    lookbackMatches: targetMatches.length,
    topRows,
    leadersPath,
    resolvedDataSource: resolvedTeam.dataSource,
    warnings: [
      ...(resolvedTeam.warning ? [resolvedTeam.warning] : []),
      ...(seasonYears && !requestedSeasonId
        ? [`Sezon rozpoznany po latach: ${seasonYears}.`]
        : []),
      ...(inferred
        ? [`Użyłem najnowszego sezonu z meczów drużyny: ${effectiveSeasonId}.`]
        : []),
      ...(targetMatches.length < limit
        ? [
            `Znaleziono tylko ${targetMatches.length} meczów drużyny dla tego zakresu.`,
          ]
        : []),
      ...(topRows.length === 0
        ? ["Brak statystyk zawodników dla ostatnich meczów tej drużyny."]
        : []),
    ],
  });
}
