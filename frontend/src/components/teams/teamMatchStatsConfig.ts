import type { TeamSeasonMatchPoint } from "@/types/api";

export type TeamMatchStatLineKey =
  | "cards"
  | "offsides"
  | "corners"
  | "shots"
  | "shots_on_target"
  | "fouls";

export type TeamMatchStatPerspective = "team" | "opponent" | "total";

export interface TeamMatchStatThresholds {
  team: number;
  opponent: number;
  total: number;
}

export interface TeamMatchStatPerspectiveConfig {
  defaultLine: number;
  minLine: number;
  maxLine: number;
}

export interface TeamMatchStatChartDefinition {
  key: TeamMatchStatLineKey;
  configGroupTitle: string;
  expanderTitle: string;
  teamChartTitle: string;
  opponentChartTitle: string;
  totalChartTitle: string;
  lineStep: number;
  perspectiveConfig: Record<
    TeamMatchStatPerspective,
    TeamMatchStatPerspectiveConfig
  >;
  teamValue: (match: TeamSeasonMatchPoint) => number;
  opponentValue: (match: TeamSeasonMatchPoint) => number;
  totalValue: (match: TeamSeasonMatchPoint) => number;
}

export const TEAM_MATCH_STAT_PERSPECTIVES: TeamMatchStatPerspective[] = [
  "team",
  "opponent",
  "total",
];

function buildPerspectiveConfig(
  teamDefault: number,
  teamMax: number,
  totalDefault?: number,
  totalMax?: number,
): Record<TeamMatchStatPerspective, TeamMatchStatPerspectiveConfig> {
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

export const TEAM_MATCH_STAT_CHARTS: TeamMatchStatChartDefinition[] = [
  {
    key: "cards",
    configGroupTitle: "Kartki",
    expanderTitle: "Kartki w meczach",
    teamChartTitle: "Kartki w meczach",
    opponentChartTitle: "Kartki przeciwnika w meczach",
    totalChartTitle: "Kartki łącznie w meczach",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(2, 8, 4, 16),
    teamValue: (match) => match.team_cards,
    opponentValue: (match) => match.opponent_cards,
    totalValue: (match) => match.total_cards,
  },
  {
    key: "offsides",
    configGroupTitle: "Spalone",
    expanderTitle: "Liczba spalonych w meczach",
    teamChartTitle: "Spalone w meczach",
    opponentChartTitle: "Spalone przeciwnika w meczach",
    totalChartTitle: "Spalone łącznie w meczach",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(2.5, 6, 5, 12),
    teamValue: (match) => match.team_offsides,
    opponentValue: (match) => match.opponent_offsides,
    totalValue: (match) => match.total_offsides,
  },
  {
    key: "corners",
    configGroupTitle: "Rzuty rożne",
    expanderTitle: "Liczba rzutów rożnych w meczach",
    teamChartTitle: "Rzuty rożne w meczach",
    opponentChartTitle: "Rzuty rożne przeciwnika w meczach",
    totalChartTitle: "Rzuty rożne łącznie w meczach",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(5.5, 15, 11, 30),
    teamValue: (match) => match.team_corners,
    opponentValue: (match) => match.opponent_corners,
    totalValue: (match) => match.total_corners,
  },
  {
    key: "shots",
    configGroupTitle: "Strzały",
    expanderTitle: "Liczba strzałów w meczach",
    teamChartTitle: "Strzały w meczach",
    opponentChartTitle: "Strzały przeciwnika w meczach",
    totalChartTitle: "Strzały łącznie w meczach",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(13.5, 30, 27, 60),
    teamValue: (match) => match.team_shots,
    opponentValue: (match) => match.opponent_shots,
    totalValue: (match) => match.total_shots,
  },
  {
    key: "shots_on_target",
    configGroupTitle: "Strzały celne",
    expanderTitle: "Liczba strzałów celnych w meczach",
    teamChartTitle: "Strzały celne w meczach",
    opponentChartTitle: "Strzały celne przeciwnika w meczach",
    totalChartTitle: "Strzały celne łącznie w meczach",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(4.5, 15, 9, 30),
    teamValue: (match) => match.team_shots_on_target,
    opponentValue: (match) => match.opponent_shots_on_target,
    totalValue: (match) => match.total_shots_on_target,
  },
  {
    key: "fouls",
    configGroupTitle: "Faule",
    expanderTitle: "Liczba fauli w meczach",
    teamChartTitle: "Faule w meczach",
    opponentChartTitle: "Faule przeciwnika w meczach",
    totalChartTitle: "Faule łącznie w meczach",
    lineStep: 0.5,
    perspectiveConfig: buildPerspectiveConfig(11.5, 20, 23, 40),
    teamValue: (match) => match.team_fouls,
    opponentValue: (match) => match.opponent_fouls,
    totalValue: (match) => match.total_fouls,
  },
];

export function buildDefaultStatLines(): Record<
  TeamMatchStatLineKey,
  TeamMatchStatThresholds
> {
  return Object.fromEntries(
    TEAM_MATCH_STAT_CHARTS.map((definition) => [
      definition.key,
      {
        team: definition.perspectiveConfig.team.defaultLine,
        opponent: definition.perspectiveConfig.opponent.defaultLine,
        total: definition.perspectiveConfig.total.defaultLine,
      },
    ]),
  ) as Record<TeamMatchStatLineKey, TeamMatchStatThresholds>;
}

export function resolvePerspectiveSliderLabel(
  perspective: TeamMatchStatPerspective,
  teamName: string,
): string {
  if (perspective === "team") {
    return teamName;
  }
  if (perspective === "opponent") {
    return "Przeciwnik";
  }
  return "Razem";
}
