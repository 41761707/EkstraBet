import { getChartBarDensityClasses } from "@/components/charts/chartBarDensity";
import { ChartScrollArea } from "@/components/charts/ChartScrollArea";
import {
  getChartPointsScrollKey,
  type CompactScrollAlign,
} from "@/components/charts/chartScrollUtils";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import { formatPercent } from "@/lib/format";

interface VerticalStatChartPoint {
  label: string;
  value: number;
}

interface VerticalStatChartProps {
  title: string;
  playerName: string;
  points: VerticalStatChartPoint[];
  thresholdLine: number;
  compactScrollAlign?: CompactScrollAlign;
}

type ChartSize = "compact" | "expanded";

function barColor(value: number, threshold: number): string {
  return value > threshold ? CHART_COLOR_POSITIVE : CHART_COLOR_NEGATIVE;
}

function VerticalStatBars({
  points,
  thresholdLine,
  maxValue,
  size,
}: {
  points: VerticalStatChartPoint[];
  thresholdLine: number;
  maxValue: number;
  size: ChartSize;
}) {
  const density = getChartBarDensityClasses(points.length, size);

  return (
    <div className={density.containerClass}>
      {points.map((point) => {
        const height = Math.max((point.value / maxValue) * 100, 4);
        return (
          <div key={point.label} className={density.columnClass}>
            <span className={density.valueClass}>{point.value}</span>
            <div
              className={`relative flex ${density.barHeightClass} ${density.barWidthClass} items-end rounded-md bg-slate-800/80`}
            >
              <div
                className="w-full rounded-md"
                style={{
                  height: `${height}%`,
                  backgroundColor: barColor(point.value, thresholdLine),
                }}
              />
              <div
                className="pointer-events-none absolute left-0 right-0 border-t border-dashed border-white/70"
                style={{
                  bottom: `${(thresholdLine / maxValue) * 100}%`,
                }}
              />
            </div>
            <span className={density.labelClass}>{point.label}</span>
          </div>
        );
      })}
    </div>
  );
}

export function VerticalStatChart({
  title,
  playerName,
  points,
  thresholdLine,
  compactScrollAlign,
}: VerticalStatChartProps) {
  if (points.length === 0) {
    return null;
  }

  const values = points.map((point) => point.value);
  const maxValue = Math.max(...values, thresholdLine, 1);
  const average = values.reduce((sum, value) => sum + value, 0) / values.length;
  const hits = values.filter((value) => value > thresholdLine).length;
  const hitRate = (hits / values.length) * 100;
  const chartTitle = `${title}: ${playerName}`;

  return (
    <div className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <div>
        <h4 className="text-sm font-semibold text-white">{chartTitle}</h4>
        <p className="mt-1 text-xs text-slate-400">
          Średnia: {average.toFixed(1)} · Hitrate O {thresholdLine.toFixed(1)}:{" "}
          {formatPercent(hitRate)}
        </p>
      </div>

      <ChartScrollArea
        chartTitle={chartTitle}
        compactScrollAlign={compactScrollAlign}
        scrollKey={getChartPointsScrollKey(points)}
        expandedChildren={
          <VerticalStatBars
            points={points}
            thresholdLine={thresholdLine}
            maxValue={maxValue}
            size="expanded"
          />
        }
      >
        <VerticalStatBars
          points={points}
          thresholdLine={thresholdLine}
          maxValue={maxValue}
          size="compact"
        />
      </ChartScrollArea>
    </div>
  );
}
