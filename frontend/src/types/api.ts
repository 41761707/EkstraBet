/** TypeScript types mirroring FastAPI league and match schemas. */

export interface LeagueSummary {
  id: number;
  name: string;
  country_id: number | null;
  country_name: string | null;
  country_emoji: string | null;
  sport_id: number | null;
  sport_name: string | null;
  active: boolean;
  last_update: string | null;
  slug: string;
}

export interface LeaguesListResponse {
  leagues: LeagueSummary[];
  total_count: number;
}

export interface LeagueSeason {
  season_id: number;
  years: string;
  match_count: number;
}

export interface LeagueDetails extends LeagueSummary {
  current_season_id: number | null;
  tier: number | null;
  has_player_stats: boolean;
  match_count: number;
  seasons: LeagueSeason[];
}

export interface TeamInMatch {
  id: number;
  name: string;
  shortcut: string | null;
}

export interface MatchScoreResolution {
  has_extra_time: boolean;
  has_penalties: boolean;
  regulation_home_goals: number | null;
  regulation_away_goals: number | null;
  penalties_home_goals: number | null;
  penalties_away_goals: number | null;
  overtime_winner?: number | null;
  shootout_winner?: number | null;
}

export interface MatchSummary {
  id: number;
  league_id: number;
  season_id: number;
  round: number | null;
  round_label: string | null;
  game_date: string;
  home_team: TeamInMatch;
  away_team: TeamInMatch;
  home_goals: number | null;
  away_goals: number | null;
  result: string;
  is_played: boolean;
  score_resolution: MatchScoreResolution | null;
}

export interface LeagueMatchesListResponse {
  matches: MatchSummary[];
  total_count: number;
  league_id: number;
  season_id: number;
}

export type StandingScope = "overall" | "home" | "away" | "ou_btts";

export interface TraditionalStandingRow {
  position: number;
  team_id: number;
  team_name: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
}

export interface OuBttsStandingRow {
  position: number;
  team_id: number;
  team_name: string;
  played: number;
  btts_count: number;
  btts_percentage: number;
  over_1_5_count: number;
  over_1_5_percentage: number;
  over_2_5_count: number;
  over_2_5_percentage: number;
  over_3_5_count: number;
  over_3_5_percentage: number;
}

export interface LeagueRound {
  round_number: number;
  round_label: string;
  game_date: string;
}

export interface LeagueRoundsListResponse {
  rounds: LeagueRound[];
  total_count: number;
}

export interface LeagueStandingsResponse {
  league_id: number;
  season_id: number;
  scope: StandingScope;
  standings: TraditionalStandingRow[] | OuBttsStandingRow[];
  total_count: number;
}

export const HOCKEY_SPORT_ID = 2;
export const BASKETBALL_SPORT_ID = 3;
export const SPORT_REGULAR_SEASON_PHASE = 100;
export const SPORT_PLAYOFFS_PHASE = 200;

export interface SportTeamSummary {
  team_id: number;
  team_name: string;
  team_shortcut: string | null;
}

export interface SportTeamsListResponse {
  teams: SportTeamSummary[];
  total_count: number;
}

export interface SportMatchesListResponse {
  matches: MatchSummary[];
  total_count: number;
  league_id: number;
  season_id: number;
}

export interface HockeyStandingRow {
  position: number;
  team_id: number;
  team_name: string;
  played: number;
  wins: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  overtime_wins: number;
  overtime_losses: number;
}

export interface BasketballStandingRow {
  position: number;
  team_id: number;
  team_name: string;
  played: number;
  wins: number;
  losses: number;
  points_for: number;
  points_against: number;
  point_difference: number;
  win_percentage: number;
}

export type SportStandingScope = "overall" | "home" | "away";

export interface SportStandingsResponse {
  league_id: number;
  season_id: number;
  scope: SportStandingScope;
  sport_id: number;
  hockey_standings: HockeyStandingRow[] | null;
  basketball_standings: BasketballStandingRow[] | null;
  total_count: number;
}

export interface HockeyTeamHistoryPoint {
  match_id: number;
  match_date: string;
  opponent_shortcut: string;
  team_goals: number;
  opponent_goals: number;
  total_goals: number;
  first_period_goals?: number | null;
  team_shots_on_goal: number | null;
  opponent_shots_on_goal: number | null;
  result: string;
  home_team_name: string;
  away_team_name: string;
  home_goals: number;
  away_goals: number;
}

export interface BasketballTeamHistoryPoint {
  match_id: number;
  match_date: string;
  opponent_shortcut: string;
  team_points: number;
  opponent_points: number;
  total_points: number;
  result: string;
  home_team_name: string;
  away_team_name: string;
  home_points: number;
  away_points: number;
}

export interface SportTeamHistoryResponse {
  team_id: number;
  sport_id: number;
  hockey_history: HockeyTeamHistoryPoint[] | null;
  basketball_history: BasketballTeamHistoryPoint[] | null;
  total_count: number;
}

export interface SportLeagueStatRow {
  team_name: string;
  team_shortcut: string;
  matches_played?: number | null;
  avg_for?: number | null;
  avg_against?: number | null;
  field_goal_pct?: number | null;
  three_point_pct?: number | null;
  over_4_5_pct?: number | null;
  over_5_5_pct?: number | null;
  over_6_5_pct?: number | null;
  over_7_5_pct?: number | null;
  over_210_5_pct?: number | null;
  over_220_5_pct?: number | null;
  over_230_5_pct?: number | null;
}

export interface SportPointsDistributionSummary {
  average_total: number;
  median_total: number;
  min_total: number;
  max_total: number;
  average_home: number;
  average_away: number;
}

export interface SportLeagueStatsResponse {
  league_id: number;
  season_id: number;
  sport_id: number;
  category: string;
  rows: SportLeagueStatRow[];
  distribution: SportPointsDistributionSummary | null;
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[];
}

export type FormResult = "W" | "D" | "L";
export type HockeyFormResult = "W" | "D" | "L" | "WPD" | "PPD";
export type TeamFormResult = FormResult | HockeyFormResult;

export interface TeamSummary {
  id: number;
  name: string;
  shortcut: string | null;
  country_id: number | null;
  country_name: string | null;
  country_emoji: string | null;
  sport_id: number | null;
  sport_name: string | null;
}

export interface TeamSplitStats {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_conceded: number;
  goal_difference: number;
  points: number;
}

export interface HeadToHeadSummary {
  team_id: number;
  opponent_id: number;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_conceded: number;
  btts_count: number;
  btts_percentage: number;
  avg_goals_per_match: number;
  meetings: MatchSummary[];
}

export interface TeamSeasonMatchPoint {
  match_id: number;
  match_date: string;
  opponent_shortcut: string;
  opponent_name: string;
  total_goals: number;
  btts: boolean;
  result: TeamFormResult;
  home_team_name: string;
  away_team_name: string;
  home_goals: number;
  away_goals: number;
  is_home: boolean;
  team_cards: number;
  opponent_cards: number;
  total_cards: number;
  team_offsides: number;
  opponent_offsides: number;
  total_offsides: number;
  team_corners: number;
  opponent_corners: number;
  total_corners: number;
  team_shots: number;
  opponent_shots: number;
  total_shots: number;
  team_shots_on_target: number;
  opponent_shots_on_target: number;
  total_shots_on_target: number;
  team_fouls: number;
  opponent_fouls: number;
  total_fouls: number;
  team_penalty_minutes?: number;
  opponent_penalty_minutes?: number;
  total_penalty_minutes?: number;
  team_penalties?: number;
  opponent_penalties?: number;
  total_penalties?: number;
  first_period_goals?: number | null;
}

export interface TeamProfile {
  team: TeamSummary;
  season_id: number | null;
  league_id: number | null;
  form: FormResult[];
  recent_matches: MatchSummary[];
  overall_stats: TeamSplitStats;
  home_stats: TeamSplitStats;
  away_stats: TeamSplitStats;
  season_matches: TeamSeasonMatchPoint[];
  head_to_head: HeadToHeadSummary | null;
}

export interface EventFamilyRef {
  id: number;
  name: string;
}

export interface MatchPredictionItem {
  prediction_id: number;
  event_id: number;
  event_name: string;
  event_family: EventFamilyRef | null;
  model_id: number;
  model_name: string | null;
  value: number | null;
  outcome: number | null;
}

export interface OddsItem {
  id: number;
  match_id: number;
  bookmaker_id: number;
  bookmaker_name: string;
  event_id: number;
  event_name: string;
  event_family: EventFamilyRef | null;
  odds: number;
}

export interface HockeyMatchStats {
  home_goals: number | null;
  away_goals: number | null;
  home_shots_on_goal: number | null;
  away_shots_on_goal: number | null;
  home_penalty_minutes: number | null;
  away_penalty_minutes: number | null;
  home_penalties: number | null;
  away_penalties: number | null;
  home_pp_goals: number | null;
  away_pp_goals: number | null;
  home_sh_goals: number | null;
  away_sh_goals: number | null;
  home_shots_accuracy: number | null;
  away_shots_accuracy: number | null;
  home_saves: number | null;
  away_saves: number | null;
  home_saves_accuracy: number | null;
  away_saves_accuracy: number | null;
  home_pp_accuracy: number | null;
  away_pp_accuracy: number | null;
  home_pk_accuracy: number | null;
  away_pk_accuracy: number | null;
  home_faceoffs_won: number | null;
  away_faceoffs_won: number | null;
  home_faceoffs_accuracy: number | null;
  away_faceoffs_accuracy: number | null;
  home_hits: number | null;
  away_hits: number | null;
  home_turnovers: number | null;
  away_turnovers: number | null;
  home_empty_net_goals: number | null;
  away_empty_net_goals: number | null;
}

export interface MatchBasicStats {
  home_goals: number | null;
  away_goals: number | null;
  home_xg: number | null;
  away_xg: number | null;
  home_possession: number | null;
  away_possession: number | null;
  home_shots: number | null;
  away_shots: number | null;
  home_shots_on_goal: number | null;
  away_shots_on_goal: number | null;
  home_free_kicks: number | null;
  away_free_kicks: number | null;
  home_corners: number | null;
  away_corners: number | null;
  home_offsides: number | null;
  away_offsides: number | null;
  home_fouls: number | null;
  away_fouls: number | null;
  home_yellow_cards: number | null;
  away_yellow_cards: number | null;
  home_red_cards: number | null;
  away_red_cards: number | null;
}

export interface MatchPlayerStat {
  player_id: number;
  player_name: string;
  team_id: number;
  team_name: string;
  goals: number | null;
  assists: number | null;
  red_cards: number | null;
  yellow_cards: number | null;
  corners_won: number | null;
  shots: number | null;
  shots_on_target: number | null;
  blocked_shots: number | null;
  passes: number | null;
  crosses: number | null;
  tackles: number | null;
  offsides: number | null;
  fouls_conceded: number | null;
  fouls_won: number | null;
  saves: number | null;
}

export interface HockeyGoalieBoxscoreRow {
  player_id: number;
  player_name: string;
  team_id: number;
  team_name: string;
  points: number | null;
  penalty_minutes: number | null;
  time_on_ice: string | null;
  shots_against: number | null;
  shots_saved: number | null;
  saves_accuracy: number | null;
}

export interface HockeySkaterBoxscoreRow {
  player_id: number;
  player_name: string;
  team_id: number;
  team_name: string;
  goals: number | null;
  assists: number | null;
  points: number | null;
  plus_minus: number | null;
  penalty_minutes: number | null;
  shots_on_goal: number | null;
  time_on_ice: string | null;
}

export interface HockeyMatchBoxscore {
  goalies: HockeyGoalieBoxscoreRow[];
  skaters: HockeySkaterBoxscoreRow[];
}

export type PlayedBetterFinalAssessment =
  | "HOME_PLAYED_BETTER"
  | "DRAW"
  | "AWAY_PLAYED_BETTER";

export interface MatchModelAssessment {
  model_id: number;
  model_name: string;
  model_version: string;
  assessment_type: string;
  home_played_better_probability: number;
  draw_probability: number;
  away_played_better_probability: number;
  final_assessment: PlayedBetterFinalAssessment;
  confidence: number | null;
  dominance_score: number | null;
  feature_snapshot: Record<string, number> | null;
  updated_at: string | null;
}

export interface MatchDetails {
  id: number;
  league_id: number;
  season_id: number;
  sport_id: number | null;
  round: number | null;
  round_label: string | null;
  game_date: string;
  home_team: TeamInMatch;
  away_team: TeamInMatch;
  home_goals: number | null;
  away_goals: number | null;
  result: string;
  is_played: boolean;
  score_resolution: MatchScoreResolution | null;
  final_predictions: MatchPredictionItem[];
  odds: OddsItem[];
  stats: MatchBasicStats | null;
  hockey_stats: HockeyMatchStats | null;
  has_player_stats: boolean;
  head_to_head: HeadToHeadSummary;
  home_team_history: TeamSeasonMatchPoint[];
  away_team_history: TeamSeasonMatchPoint[];
  boxscore: MatchPlayerStat[] | null;
  hockey_boxscore: HockeyMatchBoxscore | null;
  model_assessments: MatchModelAssessment[];
}

export type SettlementStatus = "pending" | "won" | "lost";
export type BetSortBy = "ev" | "probability" | "game_date";
export type BetSortOrder = "asc" | "desc";

export interface BetRecommendation {
  bet_id: number;
  match_id: number;
  league_id: number;
  league_name: string;
  season_id: number;
  game_date: string;
  home_team: TeamInMatch;
  away_team: TeamInMatch;
  event_id: number;
  event_name: string;
  event_family: EventFamilyRef | null;
  odds: number;
  probability: number;
  probability_pct: number;
  ev: number;
  ev_after_tax: number | null;
  bookmaker_id: number | null;
  bookmaker_name: string | null;
  model_id: number;
  model_name: string;
  settlement_status: SettlementStatus;
  custom_bet: boolean;
}

export interface BetRecommendationsResponse {
  recommendations: BetRecommendation[];
  total_count: number;
  filters_applied: Record<string, unknown>;
}

export type AnalyticsStatType = "ou" | "btts" | "result" | "all";
export type AnalyticsGroupBy = "none" | "team" | "league";
export type AnalyticsAggregationMetric = "accuracy" | "profit";

export interface ChartDistribution {
  labels: string[];
  values: number[];
  percentages: number[];
}

export interface ChartComparison {
  labels: string[];
  correct: number[];
  incorrect: number[];
}

export interface ChartData {
  distribution: ChartDistribution;
  comparison: ChartComparison;
}

export interface TypeBreakdownRow {
  key: string;
  total: number;
  correct: number;
  accuracy_pct: number | null;
  share_pct: number | null;
  profit: number | null;
}

export interface PredictionBetBreakdown {
  total: number;
  correct: number;
  accuracy_pct: number | null;
  profit_total: number | null;
  by_type: TypeBreakdownRow[];
  charts: ChartData;
}

export interface CategoryStatistics {
  predictions: PredictionBetBreakdown;
  bets: PredictionBetBreakdown;
}

export interface DistributionBucket {
  count: number;
  percentage: number;
}

export interface LeagueCharacteristics {
  played_matches: number;
  avg_goals_per_match: number;
  ou: Record<string, DistributionBucket>;
  btts: Record<string, DistributionBucket>;
  result: Record<string, DistributionBucket>;
}

export interface EntityAggregationRow {
  entity_id: number | null;
  entity_name: string;
  total_predictions: number | null;
  correct_predictions: number | null;
  accuracy_pct: number | null;
  profit: number | null;
}

export interface AccuracyAggregation {
  metric: "accuracy";
  ou: EntityAggregationRow[] | null;
  btts: EntityAggregationRow[] | null;
  result: EntityAggregationRow[] | null;
}

export interface ProfitAggregation {
  metric: "profit";
  ou: EntityAggregationRow[] | null;
  btts: EntityAggregationRow[] | null;
  result: EntityAggregationRow[] | null;
}

export interface AnalyticsAggregations {
  by_team: AccuracyAggregation | null;
  by_league: AccuracyAggregation | ProfitAggregation | null;
}

export interface ModelAnalyticsResponse {
  categories: Record<string, CategoryStatistics>;
  aggregations: AnalyticsAggregations;
  league_characteristics: LeagueCharacteristics | null;
  filters_applied: Record<string, unknown>;
}

export interface ModelSummary {
  id: number;
  name: string;
  active: number;
  sport_id: number;
  sport_name: string | null;
}

export interface ModelListResponse {
  models: ModelSummary[];
  total_models: number;
}

export interface ModelEventFamily {
  id: number;
  sport_id: number;
  name: string;
}

export interface ModelDetailsResponse {
  id: number;
  name: string;
  active: number;
  sport_id: number;
  sport_name: string | null;
  event_families: ModelEventFamily[];
  total_events: number;
}

export interface EventFamilySummary {
  id: number;
  sport_id: number;
  name: string;
  sport_name: string | null;
  description: string | null;
}

export interface EventFamilyListResponse {
  event_families: EventFamilySummary[];
  total_families: number;
}

export interface EventFamilyMappingItem {
  id: number;
  event_id: number;
  event_family_id: number;
  event_name: string | null;
  family_name: string | null;
}

export interface EventFamilyEventsResponse {
  family_events: EventFamilyMappingItem[];
  total_events: number;
}

export interface FilterOption {
  id: number;
  label: string;
}

export interface PlayerSport {
  sport_id: number;
  label: string;
  emoji: string;
  available: boolean;
}

export interface PlayerSportsListResponse {
  sports: PlayerSport[];
  total_count: number;
}

export interface PlayerCountryOption {
  id: number;
  name: string;
  emoji: string | null;
}

export interface PlayerCountriesResponse {
  countries: PlayerCountryOption[];
  total_count: number;
}

export interface PlayerTeamOption {
  id: number;
  name: string;
  country_id: number | null;
}

export interface PlayerTeamsResponse {
  teams: PlayerTeamOption[];
  total_count: number;
}

export interface PlayerSeasonOption {
  season_id: number;
  years: string;
}

export interface PlayerSeasonsResponse {
  seasons: PlayerSeasonOption[];
  total_count: number;
}

export interface FootballPlayerSummary {
  id: number;
  common_name: string;
  current_team_id: number;
  position: string | null;
}

export interface FootballPlayersListResponse {
  players: FootballPlayerSummary[];
  total_count: number;
  season_id: number;
}

export interface FootballPlayerStatsSummary {
  goals: number;
  assists: number;
  shots: number;
  shots_on_target: number;
  fouls_conceded: number;
  yellow_cards: number;
}

export interface FootballPlayerMatchStat {
  match_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  opponent_shortcut: string;
  goals: number;
  assists: number;
  shots: number;
  shots_on_target: number;
  fouls_conceded: number;
  yellow_cards: number;
}

export interface FootballPlayerMatchStatsResponse {
  player_id: number;
  season_id: number;
  match_count: number;
  summary: FootballPlayerStatsSummary;
  matches: FootballPlayerMatchStat[];
}

export interface HockeyPlayerStatsSummary {
  is_goalie: boolean;
  points: number | null;
  goals: number | null;
  assists: number | null;
  plus_minus: number | null;
  penalty_minutes: number | null;
  average_penalty_minutes: number | null;
  average_sog: number | null;
  average_toi: string | null;
  shots_against: number | null;
  shots_saved: number | null;
  saves_acc: number | null;
}

export interface HockeyPlayerMatchStat {
  match_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  opponent_shortcut: string;
  toi: string;
  toi_minutes: number;
  points: number | null;
  goals: number | null;
  assists: number | null;
  plus_minus: number | null;
  penalty_minutes: number | null;
  sog: number | null;
  shots_against: number | null;
  shots_saved: number | null;
  saves_acc: number | null;
}

export interface HockeyPlayerMatchStatsResponse {
  player_id: number;
  season_id: number;
  match_count: number;
  player_role: "skater" | "goalie";
  summary: HockeyPlayerStatsSummary;
  matches: HockeyPlayerMatchStat[];
}

export type PlayerMatchStatsResponse =
  | FootballPlayerMatchStatsResponse
  | HockeyPlayerMatchStatsResponse;

export type FootballPlayerStatKey =
  | "goals"
  | "assists"
  | "shots"
  | "shots_on_target"
  | "fouls_conceded"
  | "yellow_cards";

export type HockeySkaterStatKey =
  | "points"
  | "goals"
  | "assists"
  | "sog"
  | "plus_minus"
  | "penalty_minutes"
  | "toi_minutes";

export type HockeyGoalieStatKey =
  | "shots_against"
  | "shots_saved"
  | "saves_acc"
  | "toi_minutes";

export type PlayerStatKey =
  | FootballPlayerStatKey
  | HockeySkaterStatKey
  | HockeyGoalieStatKey;

export type ChatMessageRole = "user" | "assistant";

export interface ChatSportContext {
  sport_id: number;
  label: string;
}

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  answer?: ChatAnswer;
}

export type ChatChartType = "bar" | "line";

export interface ChatChartPoint {
  label: string;
  value: number;
  secondaryValue?: number | null;
  metadata?: Record<string, string | number | boolean | null>;
}

export interface ChatChartSpec {
  type: ChatChartType;
  title: string;
  xLabel?: string;
  yLabel?: string;
  seriesLabel?: string;
  secondarySeriesLabel?: string;
  points: ChatChartPoint[];
}

export interface ChatTableSpec {
  title: string;
  columns: string[];
  rows: (string | number | null)[][];
}

export interface ChatDataSource {
  label: string;
  endpoint: string;
  params?: Record<string, string | number | boolean | null>;
}

export interface ChatAnswer {
  answerText: string;
  chart?: ChatChartSpec | null;
  table?: ChatTableSpec | null;
  dataSources: ChatDataSource[];
  warnings: string[];
}

export interface ChatRequest {
  messages: Pick<ChatMessage, "role" | "content">[];
  sport: ChatSportContext;
}

export interface ChatResponse {
  answer: ChatAnswer;
}
