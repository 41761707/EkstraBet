import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import type { TeamFormResult } from "@/types/api";

interface TeamResultsChartProps {
  teamName: string;
  results: TeamFormResult[];
}

const RESULT_ROWS: {
  key: TeamFormResult;
  label: string;
  color: string;
}[] = [
  { key: "W", label: "Wygrane", color: CHART_COLOR_POSITIVE },
  { key: "D", label: "Remisy", color: CHART_COLOR_DRAW },
  { key: "L", label: "Porażki", color: CHART_COLOR_NEGATIVE },
];

export function TeamResultsChart({
  teamName,
  results,
}: TeamResultsChartProps) {
  if (results.length === 0) {
    return null;
  }

  const counts = {
    W: results.filter((result) => result === "W").length,
    D: results.filter((result) => result === "D").length,
    L: results.filter((result) => result === "L").length,
    WPD: results.filter((result) => result === "WPD").length,
    PPD: results.filter((result) => result === "PPD").length,
  };
  const footballRows = RESULT_ROWS.filter((row) =>
    ["W", "D", "L"].includes(row.key),
  );
  const maxCount = Math.max(
    ...footballRows.map((row) => counts[row.key]),
    1,
  );

  return (
    <div className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <div>
        <h4 className="text-sm font-semibold text-white">
          Rezultaty meczów: {teamName}
        </h4>
        <p className="mt-1 text-xs text-slate-400">
          Analizowane mecze: {results.length}
        </p>
      </div>

      <div className="space-y-3">
        {footballRows.map((row) => {
          const value = counts[row.key];
          const width = (value / maxCount) * 100;
          return (
            <div key={row.key} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-300">
                <span>{row.label}</span>
                <span className="font-semibold text-white">{value}</span>
              </div>
              <div className="h-8 rounded-md bg-slate-800/80">
                <div
                  className="flex h-8 items-center rounded-md px-2 text-xs font-semibold text-white"
                  style={{
                    width: `${Math.max(width, value > 0 ? 12 : 0)}%`,
                    backgroundColor: row.color,
                  }}
                >
                  {value > 0 ? value : ""}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
