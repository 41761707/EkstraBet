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
    { label: "Ogółem", stats: overall },
    { label: "U siebie", stats: home },
    { label: "Na wyjeździe", stats: away },
  ];

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Zakres</th>
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
              className="border-t border-border hover:bg-surface-muted"
            >
              <td className="px-4 py-2 font-medium text-text">{row.label}</td>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-3 py-2 text-center text-muted ${
                    column.key === "points" ? "font-semibold text-accent-text" : ""
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
