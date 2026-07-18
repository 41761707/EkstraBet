import type { TeamSeasonMatchPoint, TeamSplitStats } from "@/types/api";

function emptySplitStats(): TeamSplitStats {
  return {
    played: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goals_for: 0,
    goals_conceded: 0,
    goal_difference: 0,
    points: 0,
  };
}

function applyMatchToSplitStats(
  stats: TeamSplitStats,
  match: TeamSeasonMatchPoint,
): void {
  const goalsFor = match.is_home ? match.home_goals : match.away_goals;
  const goalsConceded = match.is_home ? match.away_goals : match.home_goals;

  stats.played += 1;
  stats.goals_for += goalsFor;
  stats.goals_conceded += goalsConceded;

  if (match.result === "W") {
    stats.wins += 1;
    stats.points += 3;
  } else if (match.result === "D") {
    stats.draws += 1;
    stats.points += 1;
  } else {
    stats.losses += 1;
  }

  stats.goal_difference = stats.goals_for - stats.goals_conceded;
}

export function computeSplitStatsFromHistory(history: TeamSeasonMatchPoint[]): {
  overall: TeamSplitStats;
  home: TeamSplitStats;
  away: TeamSplitStats;
} {
  const overall = emptySplitStats();
  const home = emptySplitStats();
  const away = emptySplitStats();

  for (const match of history) {
    applyMatchToSplitStats(overall, match);
    applyMatchToSplitStats(match.is_home ? home : away, match);
  }

  return { overall, home, away };
}
