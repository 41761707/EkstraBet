import type { DailyMatchSummary } from "@/types/api";

export { getWarsawDateIso } from "@/lib/date";

export interface DailyMatchLeagueGroup {
  leagueId: number;
  leagueName: string;
  matches: DailyMatchSummary[];
}

export interface DailyMatchGroup {
  sportId: number;
  sportName: string;
  leagues: DailyMatchLeagueGroup[];
}

/**
 * Group daily matches as sport -> league -> matches without mutating input.
 * Sorting is deterministic: sport name, league name, then kick-off time.
 */
export function groupDailyMatches(
  matches: DailyMatchSummary[],
): DailyMatchGroup[] {
  const sportMap = new Map<
    number,
    {
      sportId: number;
      sportName: string;
      leagues: Map<
        number,
        {
          leagueId: number;
          leagueName: string;
          matches: DailyMatchSummary[];
        }
      >;
    }
  >();

  for (const match of matches) {
    let sportGroup = sportMap.get(match.sport_id);
    if (!sportGroup) {
      sportGroup = {
        sportId: match.sport_id,
        sportName: match.sport_name,
        leagues: new Map(),
      };
      sportMap.set(match.sport_id, sportGroup);
    }

    let leagueGroup = sportGroup.leagues.get(match.league_id);
    if (!leagueGroup) {
      leagueGroup = {
        leagueId: match.league_id,
        leagueName: match.league_name,
        matches: [],
      };
      sportGroup.leagues.set(match.league_id, leagueGroup);
    }

    leagueGroup.matches.push(match);
  }

  return [...sportMap.values()]
    .map((sportGroup) => ({
      sportId: sportGroup.sportId,
      sportName: sportGroup.sportName,
      leagues: [...sportGroup.leagues.values()]
        .map((leagueGroup) => ({
          leagueId: leagueGroup.leagueId,
          leagueName: leagueGroup.leagueName,
          matches: [...leagueGroup.matches].sort((left, right) =>
            left.game_date.localeCompare(right.game_date),
          ),
        }))
        .sort((left, right) =>
          left.leagueName.localeCompare(right.leagueName, "pl"),
        ),
    }))
    .sort((left, right) =>
      left.sportName.localeCompare(right.sportName, "pl"),
    );
}
