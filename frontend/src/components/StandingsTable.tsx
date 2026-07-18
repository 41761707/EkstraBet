import Link from "next/link";
import type { TraditionalStandingRow } from "@/types/api";

interface StandingsTableProps {
  standings: TraditionalStandingRow[];
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

export function StandingsTable({
  standings,
  seasonId,
  leagueId,
}: StandingsTableProps) {
  if (standings.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
          <tr>
            <th className="px-3 py-3 font-medium">#</th>
            <th className="px-3 py-3 font-medium">Team</th>
            <th className="px-3 py-3 text-center font-medium">MP</th>
            <th className="px-3 py-3 text-center font-medium">W</th>
            <th className="px-3 py-3 text-center font-medium">D</th>
            <th className="px-3 py-3 text-center font-medium">L</th>
            <th className="px-3 py-3 text-center font-medium">GF</th>
            <th className="px-3 py-3 text-center font-medium">GA</th>
            <th className="px-3 py-3 text-center font-medium">GD</th>
            <th className="px-3 py-3 text-center font-medium">Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((row) => (
            <tr
              key={row.team_id}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-3 py-2 text-slate-400">{row.position}</td>
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
                {row.wins}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.draws}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.losses}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.goals_for}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.goals_against}
              </td>
              <td className="px-3 py-2 text-center text-slate-300">
                {row.goal_difference}
              </td>
              <td className="px-3 py-2 text-center font-semibold text-sky-200">
                {row.points}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
