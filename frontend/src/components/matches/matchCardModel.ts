import {
  FOOTBALL_H2H_OVER_LINE,
  summarizeDisplayedHeadToHead,
} from "@/components/matches/prematchHeadToHeadSummary";
import {
  formatMatchDateTime,
  formatProbability,
  formatRoundLabel,
} from "@/lib/format";
import {
  FOOTBALL_SPORT_ID,
  type MatchSummary,
  type PredictionPreviewResponse,
  type TeamFormResult,
  type TeamInMatch,
  type TeamSeasonMatchPoint,
} from "@/types/api";

/** Ile spotkań mieści się w pionowej karcie przy czcionce czytelnej na telefonie. */
export const MATCH_CARD_MEETING_LIMIT = 5;

const HEADER_NAME_LIMIT = 34;
const LEAGUE_NAME_LIMIT = 36;
const H2H_NAME_LIMIT = 14;
const FORM_SIDE_LIMIT = 19;

export interface MatchCardSegment {
  label: string;
  share: number;
  percentLabel: string;
  tone: "home" | "draw" | "away";
}

export interface MatchCardShare {
  leftLabel: string;
  rightLabel: string;
  leftShare: number;
  rightShare: number;
  leftPercentLabel: string;
  rightPercentLabel: string;
}

export interface MatchCardScoreChip {
  score: string;
  percentLabel: string;
}

export interface MatchCardMeetingRow {
  dateLabel: string;
  homeName: string;
  awayName: string;
  score: string;
  bothTeamsScored: boolean;
  overTwoAndHalf: boolean;
}

export interface MatchCardFormRow {
  dateLabel: string;
  result: TeamFormResult;
  homeName: string;
  awayName: string;
  score: string;
  bothTeamsScored: boolean;
  overTwoAndHalf: boolean;
}

export interface MatchCardForm {
  teamName: string;
  rows: MatchCardFormRow[];
}

export interface MatchCardHeadToHeadRate {
  label: string;
  percentLabel: string;
}

export interface MatchCardHeadToHead {
  statsLabel: string | null;
  btts: MatchCardHeadToHeadRate | null;
  over: MatchCardHeadToHeadRate | null;
  rows: MatchCardMeetingRow[];
}

export interface FootballMatchCard {
  leagueName: string;
  metaLabel: string;
  homeTeamName: string;
  awayTeamName: string;
  fileName: string;
  result: MatchCardSegment[] | null;
  btts: MatchCardShare | null;
  overUnder: MatchCardShare | null;
  topScores: MatchCardScoreChip[];
  headToHead: MatchCardHeadToHead;
  homeForm: MatchCardForm;
  awayForm: MatchCardForm;
}

export interface FootballMatchCardInput {
  sportId: number | null;
  leagueName: string;
  gameDate: string;
  roundLabel: string | null;
  homeTeam: TeamInMatch;
  awayTeam: TeamInMatch;
  prediction: PredictionPreviewResponse | null;
  headToHeadMeetings: MatchSummary[];
  homeHistory: TeamSeasonMatchPoint[];
  awayHistory: TeamSeasonMatchPoint[];
}

export function buildFootballMatchCard(
  input: FootballMatchCardInput,
): FootballMatchCard | null {
  if (input.sportId !== FOOTBALL_SPORT_ID) {
    return null;
  }
  const homeTeamName = truncateLabel(input.homeTeam.name, HEADER_NAME_LIMIT);
  const awayTeamName = truncateLabel(input.awayTeam.name, HEADER_NAME_LIMIT);
  return {
    leagueName: truncateLabel(input.leagueName, LEAGUE_NAME_LIMIT).toLocaleUpperCase(
      "pl-PL",
    ),
    metaLabel: buildMetaLabel(input.gameDate, input.roundLabel),
    homeTeamName,
    awayTeamName,
    fileName: shareFileName(input.homeTeam.name, input.awayTeam.name),
    result: buildResult(input),
    btts: buildShare(
      input.prediction?.btts.p_yes,
      input.prediction?.btts.p_no,
      "Tak",
      "Nie",
    ),
    overUnder: buildShare(
      input.prediction?.goals.over_25,
      input.prediction?.goals.under_25,
      "Powyżej",
      "Poniżej",
    ),
    topScores: buildTopScores(input.prediction),
    headToHead: buildHeadToHead(input.homeTeam.id, input.headToHeadMeetings),
    homeForm: buildForm(homeTeamName, input.homeHistory),
    awayForm: buildForm(awayTeamName, input.awayHistory),
  };
}

export function matchCardHasProbabilities(card: FootballMatchCard): boolean {
  return (
    card.result !== null
    || card.btts !== null
    || card.overUnder !== null
    || card.topScores.length > 0
  );
}

export function formatMatchCardDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = String(date.getFullYear()).slice(-2);
  return `${day}.${month}.${year}`;
}

function buildMetaLabel(gameDate: string, roundLabel: string | null): string {
  const kickoff = formatMatchDateTime(gameDate);
  const round = formatRoundLabel(roundLabel?.trim() ? roundLabel : null);
  if (round === null) {
    return kickoff;
  }
  return `${kickoff} · ${round}`;
}

function buildResult(input: FootballMatchCardInput): MatchCardSegment[] | null {
  const prediction = input.prediction;
  if (prediction === null) {
    return null;
  }
  const values = [
    prediction.result.p_home,
    prediction.result.p_draw,
    prediction.result.p_away,
  ];
  if (values.some((value) => !Number.isFinite(value)) || sumOf(values) <= 0) {
    return null;
  }
  const shares = normalizeShares(values);
  const labels = [
    sideLabel(input.homeTeam),
    "Remis",
    sideLabel(input.awayTeam),
  ];
  const tones: MatchCardSegment["tone"][] = ["home", "draw", "away"];
  return values.map((value, index) => ({
    label: labels[index] ?? "",
    share: shares[index] ?? 0,
    percentLabel: formatProbability(value),
    tone: tones[index] ?? "draw",
  }));
}

function buildShare(
  left: number | undefined,
  right: number | undefined,
  leftLabel: string,
  rightLabel: string,
): MatchCardShare | null {
  if (left === undefined || right === undefined) {
    return null;
  }
  if (!Number.isFinite(left) || !Number.isFinite(right) || left + right <= 0) {
    return null;
  }
  const [leftShare, rightShare] = normalizeShares([
    Math.max(left, 0),
    Math.max(right, 0),
  ]);
  return {
    leftLabel,
    rightLabel,
    leftShare: leftShare ?? 0,
    rightShare: rightShare ?? 0,
    leftPercentLabel: formatProbability(left),
    rightPercentLabel: formatProbability(right),
  };
}

function buildTopScores(
  prediction: PredictionPreviewResponse | null,
): MatchCardScoreChip[] {
  if (prediction === null) {
    return [];
  }
  return [...prediction.goals.top_exact_scores]
    .filter((item) => Number.isFinite(item.probability) && item.probability > 0)
    .sort((left, right) => right.probability - left.probability)
    .slice(0, 3)
    .map((item) => ({
      score: item.score,
      percentLabel: formatProbability(item.probability),
    }));
}

function buildHeadToHead(
  homeTeamId: number,
  meetings: MatchSummary[],
): MatchCardHeadToHead {
  const played = meetings.filter(hasScore).slice(0, MATCH_CARD_MEETING_LIMIT);
  if (played.length === 0) {
    return { statsLabel: null, btts: null, over: null, rows: [] };
  }
  const stats = summarizeDisplayedHeadToHead(homeTeamId, played, false);
  return {
    statsLabel: recentMeetingsLabel(stats.played),
    btts: { label: "BTTS", percentLabel: wholePercent(stats.bttsPercentage) },
    over: { label: "Over 2.5", percentLabel: wholePercent(stats.overPercentage) },
    rows: played.map((meeting) => {
      const homeGoals = meeting.home_goals ?? 0;
      const awayGoals = meeting.away_goals ?? 0;
      return {
        dateLabel: formatMatchCardDate(meeting.game_date),
        homeName: truncateLabel(meeting.home_team.name, H2H_NAME_LIMIT),
        awayName: truncateLabel(meeting.away_team.name, H2H_NAME_LIMIT),
        score: `${homeGoals}:${awayGoals}`,
        bothTeamsScored: homeGoals > 0 && awayGoals > 0,
        overTwoAndHalf: homeGoals + awayGoals > FOOTBALL_H2H_OVER_LINE,
      };
    }),
  };
}

function buildForm(
  teamName: string,
  history: TeamSeasonMatchPoint[],
): MatchCardForm {
  const rows = history.slice(0, MATCH_CARD_MEETING_LIMIT).map((point) => {
    return {
      dateLabel: formatMatchCardDate(point.match_date),
      result: point.result,
      homeName: truncateLabel(point.home_team_name, FORM_SIDE_LIMIT),
      awayName: truncateLabel(point.away_team_name, FORM_SIDE_LIMIT),
      score: `${point.home_goals}:${point.away_goals}`,
      bothTeamsScored: point.btts,
      overTwoAndHalf: point.total_goals > FOOTBALL_H2H_OVER_LINE,
    };
  });
  return { teamName, rows };
}

function sideLabel(team: TeamInMatch): string {
  const shortcut = team.shortcut?.trim();
  if (shortcut) {
    return truncateLabel(shortcut, 10);
  }
  return truncateLabel(team.name, 14);
}

function recentMeetingsLabel(count: number): string {
  if (count === 1) {
    return "Statystyki ostatniego spotkania";
  }
  return `Statystyki ostatnich ${count} spotkań`;
}

function wholePercent(value: number): string {
  return `${Math.round(value)}%`;
}

function hasScore(meeting: MatchSummary): boolean {
  return meeting.home_goals !== null && meeting.away_goals !== null;
}

function normalizeShares(values: number[]): number[] {
  const total = sumOf(values);
  if (total <= 0) {
    return values.map(() => 0);
  }
  return values.map((value) => value / total);
}

function sumOf(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0);
}

function truncateLabel(value: string, maxLength: number): string {
  const trimmed = value.trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength - 1).trimEnd()}…`;
}

function shareFileName(homeName: string, awayName: string): string {
  const slug = [homeName, awayName].map(slugPart).filter(Boolean).join("-");
  return `${slug || "mecz"}.png`;
}

function slugPart(value: string): string {
  return value
    .toLowerCase()
    .replace(/ł/g, "l")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
