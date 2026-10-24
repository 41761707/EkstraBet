import type { MatchSummary } from "@/types/api";

export const FOOTBALL_H2H_OVER_LINE = 2.5;
export const HOCKEY_H2H_OVER_LINE = 6.5;

export interface DisplayedHeadToHeadStats {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsConceded: number;
  bttsPercentage: number;
  overPercentage: number;
}

/** Canonical H2H total-goals line: 2.5 in football, 6.5 in hockey. */
export function h2hOverLine(isHockey: boolean): number {
  return isHockey ? HOCKEY_H2H_OVER_LINE : FOOTBALL_H2H_OVER_LINE;
}

function percentage(count: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return (count * 100) / total;
}

/**
 * Aggregate the H2H meetings currently shown in the prematch window.
 * The API summary covers the full history; the slider only lists a slice.
 */
export function summarizeDisplayedHeadToHead(
  teamId: number,
  meetings: MatchSummary[],
  isHockey: boolean,
): DisplayedHeadToHeadStats {
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsConceded = 0;
  let bttsCount = 0;
  let overCount = 0;
  let played = 0;
  const overLine = h2hOverLine(isHockey);

  for (const meeting of meetings) {
    if (meeting.home_goals == null || meeting.away_goals == null) {
      continue;
    }
    const isHome = meeting.home_team.id === teamId;
    const teamGoals = isHome ? meeting.home_goals : meeting.away_goals;
    const opponentGoals = isHome ? meeting.away_goals : meeting.home_goals;

    played += 1;
    goalsFor += teamGoals;
    goalsConceded += opponentGoals;
    if (teamGoals > opponentGoals) {
      wins += 1;
    } else if (teamGoals === opponentGoals) {
      draws += 1;
    } else {
      losses += 1;
    }
    if (teamGoals > 0 && opponentGoals > 0) {
      bttsCount += 1;
    }
    if (meeting.home_goals + meeting.away_goals > overLine) {
      overCount += 1;
    }
  }

  return {
    played,
    wins,
    draws,
    losses,
    goalsFor,
    goalsConceded,
    bttsPercentage: percentage(bttsCount, played),
    overPercentage: percentage(overCount, played),
  };
}
