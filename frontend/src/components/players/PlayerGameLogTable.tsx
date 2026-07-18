import type {
  FootballPlayerMatchStat,
  HockeyPlayerMatchStat,
  PlayerStatKey,
} from "@/types/api";
import { getStatDefinition } from "@/components/players/playerStatsConfig";

interface PlayerGameLogTableProps {
  sportId: number;
  playerRole?: "skater" | "goalie";
  matches: (FootballPlayerMatchStat | HockeyPlayerMatchStat)[];
  selectedStats: PlayerStatKey[];
}

export function PlayerGameLogTable({
  sportId,
  playerRole,
  matches,
  selectedStats,
}: PlayerGameLogTableProps) {
  if (selectedStats.length === 0) {
    return (
      <p className="text-sm text-slate-400">
        Wybierz statystyki do wyświetlenia w tabeli.
      </p>
    );
  }

  if (matches.length === 0) {
    return null;
  }

  const statColumns = selectedStats.map((key) =>
    getStatDefinition(key, sportId, playerRole),
  );

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
          <tr>
            <th className="px-3 py-3 font-medium">L.P.</th>
            <th className="px-3 py-3 font-medium">Gospodarz</th>
            <th className="px-3 py-3 font-medium">Gość</th>
            <th className="px-3 py-3 font-medium">Data</th>
            {statColumns.map((column) => (
              <th
                key={column.key}
                className="px-3 py-3 text-center font-medium"
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matches.map((match, index) => (
            <tr
              key={match.match_id}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-3 py-2 text-slate-400">{index + 1}</td>
              <td className="px-3 py-2 text-white">{match.home_team}</td>
              <td className="px-3 py-2 text-white">{match.away_team}</td>
              <td className="px-3 py-2 text-slate-300">{match.match_date}</td>
              {statColumns.map((column) => (
                <td
                  key={column.key}
                  className="px-3 py-2 text-center text-slate-200"
                >
                  {formatTableValue(getMatchStatValue(match, column.key))}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatTableValue(value: string | number | null | undefined) {
  return value ?? "-";
}

function getMatchStatValue(
  match: FootballPlayerMatchStat | HockeyPlayerMatchStat,
  statKey: PlayerStatKey,
) {
  return (
    match as unknown as Record<
      PlayerStatKey,
      string | number | null | undefined
    >
  )[statKey];
}
