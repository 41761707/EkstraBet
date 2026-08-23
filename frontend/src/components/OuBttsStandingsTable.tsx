import Link from "next/link";
import { formatPercent } from "@/lib/format";
import type { OuBttsStandingRow } from "@/types/api";

interface OuBttsStandingsTableProps {
  standings: OuBttsStandingRow[];
  seasonId?: number;
  leagueId?: number;
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

export function OuBttsStandingsTable({
  standings,
  seasonId,
  leagueId,
}: OuBttsStandingsTableProps) {
  if (standings.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-3 py-3 font-medium">Drużyna</th>
            <th className="px-3 py-3 text-center font-medium">M</th>
            <th className="px-3 py-3 text-center font-medium">BTTS</th>
            <th className="px-3 py-3 text-center font-medium">BTTS %</th>
            <th className="px-3 py-3 text-center font-medium">O 1.5</th>
            <th className="px-3 py-3 text-center font-medium">O 1.5 %</th>
            <th className="px-3 py-3 text-center font-medium">O 2.5</th>
            <th className="px-3 py-3 text-center font-medium">O 2.5 %</th>
            <th className="px-3 py-3 text-center font-medium">O 3.5</th>
            <th className="px-3 py-3 text-center font-medium">O 3.5 %</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row) => (
            <tr
              key={row.team_id}
              className="border-t border-border hover:bg-surface-muted"
            >
              <td className="px-3 py-2 font-medium">
                <Link
                  href={teamHref(row.team_id, seasonId, leagueId)}
                  className="text-text transition hover:text-accent-text"
                >
                  {row.team_name}
                </Link>
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {row.played}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {row.btts_count}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {formatPercent(row.btts_percentage)}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {row.over_1_5_count}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {formatPercent(row.over_1_5_percentage)}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {row.over_2_5_count}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {formatPercent(row.over_2_5_percentage)}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {row.over_3_5_count}
              </td>
              <td className="px-3 py-2 text-center text-muted">
                {formatPercent(row.over_3_5_percentage)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
