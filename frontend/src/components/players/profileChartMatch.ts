import type {
  HockeyPlayerMatchStat,
  HockeyPlayerSliceMatch,
} from "@/types/api";

/** Map a profile row onto the match shape used by the players charts. */
export function toProfileChartMatch(
  match: HockeyPlayerSliceMatch,
): HockeyPlayerMatchStat {
  const homeTeam =
    match.venue === "home" ? match.own_team_name : match.opponent_name;
  const awayTeam =
    match.venue === "home" ? match.opponent_name : match.own_team_name;
  return {
    match_id: match.match_id,
    home_team: homeTeam,
    away_team: awayTeam,
    match_date: shortDayMonth(match.game_date),
    opponent_shortcut: match.opponent_shortcut,
    opponent_name: match.opponent_name,
    toi: match.toi,
    toi_minutes: match.toi_minutes,
    points: match.points,
    goals: match.goals,
    assists: match.assists,
    plus_minus: match.plus_minus,
    penalty_minutes: match.penalty_minutes,
    sog: match.sog,
    shots_against: match.shots_against,
    shots_saved: match.shots_saved,
    saves_acc: match.saves_acc,
    rating: match.rating,
  };
}

/** Chart axis uses day.month, the same label as the players list. */
function shortDayMonth(gameDate: string): string {
  const parts = gameDate.split("-");
  if (parts.length !== 3) {
    return gameDate;
  }
  return `${parts[2]}.${parts[1]}`;
}
