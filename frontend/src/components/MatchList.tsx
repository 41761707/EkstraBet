import Link from "next/link";
import { MatchScoreDisplay } from "@/components/MatchScoreDisplay";
import { formatMatchDate } from "@/lib/format";
import type { MatchSummary } from "@/types/api";

interface MatchListProps {
  matches: MatchSummary[];
  seasonId?: number;
  leagueId?: number;
  hideRoundColumn?: boolean;
}

function teamHref(
  teamId: number,
  seasonId?: number,
  leagueId?: number,
): string {
  const params = new URLSearchParams();
  if (seasonId) {
    params.set("season_id", String(seasonId));
  }
  if (leagueId) {
    params.set("league_id", String(leagueId));
  }
  const query = params.toString();
  return query ? `/teams/${teamId}?${query}` : `/teams/${teamId}`;
}

export function MatchList({
  matches,
  seasonId,
  leagueId,
  hideRoundColumn = false,
}: MatchListProps) {
  if (matches.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full table-fixed text-sm">
        <thead className="bg-slate-900/80 text-center text-slate-400">
          <tr>
            <th className="w-[12%] px-4 py-3 font-medium">Data</th>
            {hideRoundColumn ? null : (
              <th className="w-[10%] px-4 py-3 font-medium">Kolejka</th>
            )}
            <th className="px-4 py-3 font-medium">Gospodarz</th>
            <th className="w-[18%] px-4 py-3 font-medium">Wynik</th>
            <th className="px-4 py-3 font-medium">Gość</th>
          </tr>
        </thead>
        <tbody>
          {matches.map((match) => (
            <tr
              key={match.id}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-4 py-3 text-center text-slate-300">
                <Link
                  href={`/matches/${match.id}`}
                  className="transition hover:text-sky-200"
                >
                  {formatMatchDate(match.game_date)}
                </Link>
              </td>
              {hideRoundColumn ? null : (
                <td className="px-4 py-3 text-center text-slate-400">
                  {match.round_label ?? "—"}
                </td>
              )}
              <td className="px-4 py-3 text-center font-medium">
                <Link
                  href={teamHref(match.home_team.id, seasonId, leagueId)}
                  className="text-white transition hover:text-sky-200"
                >
                  {match.home_team.name}
                </Link>
              </td>
              <td className="px-4 py-3 text-center font-semibold">
                <Link
                  href={`/matches/${match.id}`}
                  className="inline-flex justify-center transition hover:text-sky-100"
                >
                  <MatchScoreDisplay match={match} size="sm" />
                </Link>
              </td>
              <td className="px-4 py-3 text-center font-medium">
                <Link
                  href={teamHref(match.away_team.id, seasonId, leagueId)}
                  className="text-white transition hover:text-sky-200"
                >
                  {match.away_team.name}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
