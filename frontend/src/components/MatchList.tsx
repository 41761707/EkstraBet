import Link from "next/link";
import { MatchScoreDisplay } from "@/components/MatchScoreDisplay";
import { formatMatchDateTime } from "@/lib/format";
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
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="min-w-full table-fixed text-sm">
        <thead className="bg-surface-muted text-center text-muted">
          <tr>
            <th className="w-[16%] px-4 py-3 font-medium">Data</th>
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
              className="border-t border-border hover:bg-surface-muted"
            >
              <td className="px-4 py-3 text-center text-muted">
                <Link
                  href={`/matches/${match.id}`}
                  className="transition hover:text-accent-text"
                >
                  {formatMatchDateTime(match.game_date)}
                </Link>
              </td>
              {hideRoundColumn ? null : (
                <td className="px-4 py-3 text-center text-subtle">
                  {match.round_label ?? "—"}
                </td>
              )}
              <td className="px-4 py-3 text-center font-medium">
                <Link
                  href={teamHref(match.home_team.id, seasonId, leagueId)}
                  className="text-text transition hover:text-accent-text"
                >
                  {match.home_team.name}
                </Link>
              </td>
              <td className="px-4 py-3 text-center font-semibold">
                <Link
                  href={`/matches/${match.id}`}
                  className="inline-flex justify-center transition hover:text-accent-text"
                >
                  <MatchScoreDisplay match={match} size="sm" />
                </Link>
              </td>
              <td className="px-4 py-3 text-center font-medium">
                <Link
                  href={teamHref(match.away_team.id, seasonId, leagueId)}
                  className="text-text transition hover:text-accent-text"
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
