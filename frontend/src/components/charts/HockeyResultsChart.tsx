import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import type { HockeyFormResult } from "@/types/api";

interface HockeyResultsChartProps {
  teamName: string;
  results: HockeyFormResult[];
}

const RESULT_ROWS: {
  key: HockeyFormResult;
  label: string;
  color: string;
}[] = [
  { key: "W", label: "Wygrane", color: CHART_COLOR_POSITIVE },
  { key: "WPD", label: "Wygrane po dogrywce", color: "#22c55e" },
  { key: "PPD", label: "Przegrane po dogrywce", color: "#f97316" },
  { key: "D", label: "Remisy", color: CHART_COLOR_DRAW },
  { key: "L", label: "Przegrane", color: CHART_COLOR_NEGATIVE },
];

export function HockeyResultsChart({
  teamName,
  results,
}: HockeyResultsChartProps) {
  if (results.length === 0) {
    return null;
  }

  const counts = RESULT_ROWS.reduce(
    (accumulator, row) => ({
      ...accumulator,
      [row.key]: results.filter((result) => result === row.key).length,
    }),
    {} as Record<HockeyFormResult, number>,
  );
  const maxCount = Math.max(...Object.values(counts), 1);

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
        {RESULT_ROWS.map((row) => {
          const value = counts[row.key];
          if (value === 0) {
            return null;
          }
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
                    width: `${Math.max(width, 12)}%`,
                    backgroundColor: row.color,
                  }}
                >
                  {value}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
