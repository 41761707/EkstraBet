import type { ChartComparison, ChartDistribution } from "@/types/api";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
  getSemanticBarColor,
} from "@/lib/chartColors";

interface DistributionChartProps {
  data: ChartDistribution;
  title: string;
}

interface ComparisonChartProps {
  data: ChartComparison;
  title: string;
}

export function DistributionChart({ data, title }: DistributionChartProps) {
  const maxValue = Math.max(...data.values, 1);

  return (
    <div className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <h4 className="text-sm font-semibold text-white">{title}</h4>
      <div className="space-y-2">
        {data.labels.map((label, index) => {
          const width = (data.values[index] / maxValue) * 100;
          return (
            <div key={label} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-300">
                <span>{label}</span>
                <span>
                  {data.values[index]} ({data.percentages[index]?.toFixed(1)}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${width}%`,
                    backgroundColor: getSemanticBarColor(label),
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ComparisonChart({ data, title }: ComparisonChartProps) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <h4 className="text-sm font-semibold text-white">{title}</h4>
      <div className="space-y-3">
        {data.labels.map((label, index) => {
          const correct = data.correct[index] ?? 0;
          const incorrect = data.incorrect[index] ?? 0;
          const total = correct + incorrect;
          const correctWidth = total > 0 ? (correct / total) * 100 : 0;
          const incorrectWidth = total > 0 ? (incorrect / total) * 100 : 0;

          return (
            <div key={label} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-300">
                <span>{label}</span>
                <span>
                  {correct} / {incorrect} (trafione/chybione)
                </span>
              </div>
              <div className="flex h-3 overflow-hidden rounded-full bg-slate-800">
                <div
                  style={{
                    width: `${correctWidth}%`,
                    backgroundColor: CHART_COLOR_POSITIVE,
                  }}
                  title={`Trafione: ${correct}`}
                />
                <div
                  style={{
                    width: `${incorrectWidth}%`,
                    backgroundColor: CHART_COLOR_NEGATIVE,
                  }}
                  title={`Chybione: ${incorrect}`}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-4 text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_POSITIVE }}
          />
          Trafione
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_NEGATIVE }}
          />
          Chybione
        </span>
      </div>
    </div>
  );
}
