import {
  barBox,
  chartScale,
  type ChartScale,
} from "@/components/charts/VerticalStatChart";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import { formatPropHistoryCount } from "@/lib/playerPropHistory";
import type { PlayerPropHistoryPoint } from "@/types/api";

interface PlayerPropHistoryStripProps {
  points: PlayerPropHistoryPoint[];
  thresholdLine: number;
  hits: number;
  played: number;
}

function barColor(value: number, thresholdLine: number): string {
  if (value > thresholdLine) {
    return CHART_COLOR_POSITIVE;
  }
  return CHART_COLOR_NEGATIVE;
}

function thresholdBottomPercent(thresholdLine: number, scale: ChartScale): number {
  if (!scale.signed) {
    return (thresholdLine / scale.max) * 100;
  }
  const span = scale.max - scale.min;
  return ((thresholdLine - scale.min) / span) * 100;
}

/** Narrow recent-match bars for one player prop line. */
export function PlayerPropHistoryStrip({
  points,
  thresholdLine,
  hits,
  played,
}: PlayerPropHistoryStripProps) {
  const countLabel = formatPropHistoryCount(hits, played);
  if (played === 0) {
    return <span className="text-muted">{countLabel}</span>;
  }

  const scale = chartScale(
    points.map((point) => point.value),
    thresholdLine,
  );
  const thresholdBottom = thresholdBottomPercent(thresholdLine, scale);

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-end gap-0.5" aria-hidden="true">
        {points.map((point, index) => {
          const box = barBox(point.value, scale);
          return (
            <div
              key={`${index}-${point.value}`}
              className="relative h-8 w-1.5 shrink-0 rounded-md bg-chart-track"
            >
              <div
                className="absolute inset-x-0 rounded-md"
                style={{
                  height: `${box.height}%`,
                  bottom: `${box.bottom}%`,
                  backgroundColor: barColor(point.value, thresholdLine),
                }}
              />
              <div
                className="pointer-events-none absolute inset-x-0 border-t border-dashed border-chart-axis"
                style={{ bottom: `${thresholdBottom}%` }}
              />
            </div>
          );
        })}
      </div>
      <span className="whitespace-nowrap text-text">{countLabel}</span>
    </div>
  );
}
