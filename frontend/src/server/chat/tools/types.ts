import type {
  ChatChartSpec,
  ChatDataSource,
  ChatTableSpec,
  FootballPlayerMatchStat,
} from "@/types/api";

export interface ToolResult {
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
  | "get_match_details"
  | "get_league_table"
  | "get_league_standings";

export interface PlannedToolCall {
  tool: ChatToolName;
  args: Record<string, unknown>;
}

export const MAX_TOOL_CALLS = 4;

export const FOOTBALL_SPORT_ID = 1;
export const HOCKEY_SPORT_ID = 2;

export const STAT_LABELS = {
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

export type StatKey = keyof typeof STAT_LABELS;
export type StatPerspective = "team" | "opponent" | "total";
export type MatchupTarget = StatKey | "result";

export type FootballPlayerLeaderStat = keyof Pick<
  FootballPlayerMatchStat,
  | "goals"
  | "assists"
  | "shots"
  | "shots_on_target"
  | "fouls_conceded"
  | "yellow_cards"
>;

export const FOOTBALL_PLAYER_STAT_LABELS: Record<
  FootballPlayerLeaderStat,
  string
> = {
  goals: "Bramki",
  assists: "Asysty",
  shots: "Strzały",
  shots_on_target: "Strzały celne",
  fouls_conceded: "Faule",
  yellow_cards: "Żółte kartki",
};

export interface TeamPlayerStatLeadersResponse {
  team_id: number;
  season_id: number;
  stat: string;
  match_ids: number[];
  leaders: Array<{
    player_id: number;
    player_name: string;
    total: number;
    appearances: number;
    average: number;
  }>;
}
