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
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
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
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-3 py-2 font-medium">
                <Link
                  href={teamHref(row.team_id, seasonId, leagueId)}
                  className="text-white transition hover:text-sky-200"
                >
                  {row.team_name}
                </Link>
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.played}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.btts_count}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {formatPercent(row.btts_percentage)}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.over_1_5_count}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {formatPercent(row.over_1_5_percentage)}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.over_2_5_count}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {formatPercent(row.over_2_5_percentage)}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.over_3_5_count}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {formatPercent(row.over_3_5_percentage)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
