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

const MIN_BAR_PERCENT = 4;

export interface VerticalStatChartPoint {
  label: string;
  value: number;
}

export interface ChartScale {
  min: number;
  max: number;
  signed: boolean;
}

/** Zero stays the baseline once any value or the threshold drops below it. */
export function chartScale(
  values: readonly number[],
  thresholdLine: number,
): ChartScale {
  const lowest = Math.min(...values, thresholdLine);
  if (lowest >= 0) {
    return {
      min: 0,
      max: Math.max(...values, thresholdLine, 1),
      signed: false,
    };
  }
  return {
    min: Math.min(lowest, 0),
    max: Math.max(...values, thresholdLine, 0),
    signed: true,
  };
}

/** Bar box as percentages of the track. Signed bars grow away from zero. */
export function barBox(
  value: number,
  scale: ChartScale,
): { bottom: number; height: number } {
  if (!scale.signed) {
    return {
      bottom: 0,
      height: Math.max((value / scale.max) * 100, MIN_BAR_PERCENT),
    };
  }
  const span = scale.max - scale.min;
  const zero = ((0 - scale.min) / span) * 100;
  if (value === 0) {
    return { bottom: zero, height: 0 };
  }
  const raw = (Math.abs(value) / span) * 100;
  const room = value > 0 ? 100 - zero : zero;
  const height = Math.min(Math.max(raw, MIN_BAR_PERCENT), room);
  return {
    bottom: value > 0 ? zero : zero - height,
    height,
  };
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
  scale,
  size,
}: {
  points: VerticalStatChartPoint[];
  thresholdLine: number;
  scale: ChartScale;
  size: ChartSize;
}) {
  const density = getChartBarDensityClasses(points.length, size);
  const span = scale.max - scale.min;
  const thresholdBottom = scale.signed
    ? ((thresholdLine - scale.min) / span) * 100
    : (thresholdLine / scale.max) * 100;

  return (
    <div className={density.containerClass}>
      {points.map((point) => {
        const box = barBox(point.value, scale);
        return (
          <div key={point.label} className={density.columnClass}>
            <span className={density.valueClass}>{point.value}</span>
            <div
              className={[
                "relative rounded-md bg-chart-track",
                density.barHeightClass,
                density.barWidthClass,
                scale.signed ? "" : "flex items-end",
              ]
                .filter((part) => part !== "")
                .join(" ")}
            >
              <div
                className={`${scale.signed ? "absolute inset-x-0" : "w-full"} rounded-md`}
                style={{
                  height: `${box.height}%`,
                  bottom: scale.signed ? `${box.bottom}%` : undefined,
                  backgroundColor: barColor(point.value, thresholdLine),
                }}
              />
              <div
                className="pointer-events-none absolute inset-x-0 border-t border-dashed border-chart-axis"
                style={{ bottom: `${thresholdBottom}%` }}
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
  const scale = chartScale(values, thresholdLine);
  const average = values.reduce((sum, value) => sum + value, 0) / values.length;
  const hits = values.filter((value) => value > thresholdLine).length;
  const hitRate = (hits / values.length) * 100;
  const chartTitle = `${title}: ${playerName}`;

  return (
    <div className="min-w-0 space-y-3 overflow-hidden rounded-xl border border-border bg-surface p-4">
      <div className="min-w-0">
        <h4 className="break-words text-sm font-semibold text-text">
          {chartTitle}
        </h4>
        <p className="mt-1 text-xs text-muted">
          Średnia: {average.toFixed(1)} · Skuteczność O{" "}
          {thresholdLine.toFixed(1)}:{" "}
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
            scale={scale}
            size="expanded"
          />
        }
      >
        <VerticalStatBars
          points={points}
          thresholdLine={thresholdLine}
          scale={scale}
          size="compact"
        />
      </ChartScrollArea>
    </div>
  );
}
