import type { TeamSeasonMatchPoint } from "@/types/api";
import type {
  TeamMatchStatChartDefinition,
  TeamMatchStatLineKey,
  TeamMatchStatThresholds,
} from "@/components/teams/teamMatchStatsConfig";

export type HockeyMatchStatLineKey =
  | "shots_on_goal"
  | "penalty_minutes"
  | "penalties";

function buildPerspectiveConfig(
  teamDefault: number,
  teamMax: number,
  totalDefault?: number,
  totalMax?: number,
) {
  return {
    team: { defaultLine: teamDefault, minLine: 0.5, maxLine: teamMax },
    opponent: { defaultLine: teamDefault, minLine: 0.5, maxLine: teamMax },
    total: {
      defaultLine: totalDefault ?? teamDefault * 2,
      minLine: 0.5,
      maxLine: totalMax ?? teamMax * 2,
    },
  };
}

export const HOCKEY_TEAM_MATCH_STAT_CHARTS: TeamMatchStatChartDefinition[] = [
  {
    key: "shots_on_target" as TeamMatchStatLineKey,
    configGroupTitle: "Strzały na bramkę",
    expanderTitle: "Strzały na bramkę w meczach",
    teamChartTitle: "Strzały na bramkę drużyny",
    opponentChartTitle: "Strzały na bramkę przeciwnika",
    totalChartTitle: "Strzały na bramkę łącznie",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(28, 45, 56, 90),
    teamValue: (match) => match.team_shots_on_target,
    opponentValue: (match) => match.opponent_shots_on_target,
    totalValue: (match) => match.total_shots_on_target,
  },
  {
    key: "shots" as TeamMatchStatLineKey,
    configGroupTitle: "Strzały",
    expanderTitle: "Liczba strzałów w meczach",
    teamChartTitle: "Strzały drużyny",
    opponentChartTitle: "Strzały przeciwnika",
    totalChartTitle: "Strzały łącznie",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(28, 45, 56, 90),
    teamValue: (match) => match.team_shots,
    opponentValue: (match) => match.opponent_shots,
    totalValue: (match) => match.total_shots,
  },
  {
    key: "cards" as TeamMatchStatLineKey,
    configGroupTitle: "Minuty kar",
    expanderTitle: "Minuty kar w meczach",
    teamChartTitle: "Minuty kar drużyny",
    opponentChartTitle: "Minuty kar przeciwnika",
    totalChartTitle: "Minuty kar łącznie",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(8, 20, 16, 40),
    teamValue: (match) => match.team_penalty_minutes ?? 0,
    opponentValue: (match) => match.opponent_penalty_minutes ?? 0,
    totalValue: (match) => match.total_penalty_minutes ?? 0,
  },
  {
    key: "offsides" as TeamMatchStatLineKey,
    configGroupTitle: "Liczba kar",
    expanderTitle: "Liczba kar w meczach",
    teamChartTitle: "Kary drużyny",
    opponentChartTitle: "Kary przeciwnika",
    totalChartTitle: "Kary łącznie",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(4, 10, 8, 20),
    teamValue: (match) => match.team_penalties ?? 0,
    opponentValue: (match) => match.opponent_penalties ?? 0,
    totalValue: (match) => match.total_penalties ?? 0,
  },
];

export function buildHockeyDefaultStatLines(): Record<
  TeamMatchStatLineKey,
  TeamMatchStatThresholds
> {
  return Object.fromEntries(
    HOCKEY_TEAM_MATCH_STAT_CHARTS.map((definition) => [
      definition.key,
      {
        team: definition.perspectiveConfig.team.defaultLine,
        opponent: definition.perspectiveConfig.opponent.defaultLine,
        total: definition.perspectiveConfig.total.defaultLine,
      },
    ]),
  ) as Record<TeamMatchStatLineKey, TeamMatchStatThresholds>;
}
