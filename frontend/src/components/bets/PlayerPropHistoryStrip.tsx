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
  side?: "over" | "under";
  compact?: boolean;
  scale?: ChartScale;
}

function barColor(
  value: number,
  thresholdLine: number,
  side: "over" | "under",
): string {
  const hit = side === "under" ? value < thresholdLine : value > thresholdLine;
  if (hit) {
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

/** Narrow recent-match bars. Compact rows share one scale across teams. */
export function PlayerPropHistoryStrip({
  points,
  thresholdLine,
  hits,
  played,
  side = "over",
  compact = false,
  scale: scaleOverride,
}: PlayerPropHistoryStripProps) {
  const countLabel = formatPropHistoryCount(hits, played);
  if (played === 0) {
    return <span className="text-muted">{countLabel}</span>;
  }

  const scale =
    scaleOverride ??
    chartScale(
      points.map((point) => point.value),
      thresholdLine,
    );
  const thresholdBottom = thresholdBottomPercent(thresholdLine, scale);
  const trackClassName = compact
    ? "relative h-4 w-1.5 shrink-0 rounded-md bg-chart-track"
    : "relative h-8 w-1.5 shrink-0 rounded-md bg-chart-track";
  const countClassName = compact
    ? "whitespace-nowrap text-xs text-text"
    : "whitespace-nowrap text-text";

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-end gap-0.5" aria-hidden="true">
        {points.map((point, index) => {
          const box = barBox(point.value, scale);
          return (
            <div
              key={`${index}-${point.value}`}
              className={trackClassName}
            >
              <div
                className="absolute inset-x-0 rounded-md"
                style={{
                  height: `${box.height}%`,
                  bottom: `${box.bottom}%`,
                  backgroundColor: barColor(point.value, thresholdLine, side),
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
      <span className={countClassName}>{countLabel}</span>
    </div>
  );
}
