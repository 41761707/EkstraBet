import type { TeamSplitStats } from "@/types/api";

interface TeamSplitStatsTableProps {
  overall: TeamSplitStats;
  home: TeamSplitStats;
  away: TeamSplitStats;
}

const columns = [
  { key: "played", label: "MP" },
  { key: "wins", label: "W" },
  { key: "draws", label: "D" },
  { key: "losses", label: "L" },
  { key: "goals_for", label: "GF" },
  { key: "goals_conceded", label: "GA" },
  { key: "goal_difference", label: "GD" },
  { key: "points", label: "Pts" },
] as const;

export function TeamSplitStatsTable({
  overall,
  home,
  away,
}: TeamSplitStatsTableProps) {
  const rows = [
    { label: "Overall", stats: overall },
    { label: "Home", stats: home },
    { label: "Away", stats: away },
  ];

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
          <tr>
            <th className="px-4 py-3 font-medium">Scope</th>
            {columns.map((column) => (
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
          {rows.map((row) => (
            <tr
              key={row.label}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-4 py-2 font-medium text-white">{row.label}</td>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-3 py-2 text-center text-slate-300 ${
                    column.key === "points" ? "font-semibold text-sky-200" : ""
                  }`}
                >
                  {row.stats[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
