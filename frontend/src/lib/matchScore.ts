import type { MatchScoreResolution } from "@/types/api";

export interface MatchScoreInput {
  home_goals: number | null;
  away_goals: number | null;
  is_played: boolean;
  score_resolution?: MatchScoreResolution | null;
}

export interface ResolvedMatchScore {
  main: string;
  note: string | null;
}

function scorePair(home: number, away: number): string {
  return `${home} : ${away}`;
}

export function resolveMatchScore(match: MatchScoreInput): ResolvedMatchScore {
  if (!match.is_played) {
    return { main: "– : –", note: null };
  }

  const home = match.home_goals ?? 0;
  const away = match.away_goals ?? 0;
  const resolution = match.score_resolution;

  if (
    !resolution
    || (!resolution.has_extra_time && !resolution.has_penalties)
  ) {
    return { main: scorePair(home, away), note: null };
  }

  if (resolution.has_penalties) {
    const postOtHome = resolution.post_ot_home_goals ?? home;
    const postOtAway = resolution.post_ot_away_goals ?? away;
    const penaltiesHome = resolution.penalties_home_goals;
    const penaltiesAway = resolution.penalties_away_goals;
    const penaltyNote =
      penaltiesHome !== null
      && penaltiesHome !== undefined
      && penaltiesAway !== null
      && penaltiesAway !== undefined
        ? `(po karnych ${penaltiesHome} : ${penaltiesAway})`
        : "po rzutach karnych";

    return {
      main: scorePair(postOtHome, postOtAway),
      note: penaltyNote,
    };
  }

  const postOtHome = resolution.post_ot_home_goals ?? home;
  const postOtAway = resolution.post_ot_away_goals ?? away;
  return {
    main: scorePair(postOtHome, postOtAway),
    note: "po dogrywce",
  };
}

export function formatMatchScore(match: MatchScoreInput): string {
  const { main, note } = resolveMatchScore(match);
  if (!note) {
    return main;
  }
  if (note.startsWith("(")) {
    return `${main} ${note}`;
  }
  return `${main} ${note}`;
}
