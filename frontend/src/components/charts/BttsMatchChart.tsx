import {
  getBttsBarLabel,
  getChartBarDensityClasses,
} from "@/components/charts/chartBarDensity";
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

interface BttsMatchChartPoint {
  label: string;
  btts: boolean;
}

interface BttsMatchChartProps {
  title: string;
  teamName: string;
  points: BttsMatchChartPoint[];
  compactScrollAlign?: CompactScrollAlign;
}

type ChartSize = "compact" | "expanded";

const BTTS_BAR_HEIGHT = 72;

function BttsBars({
  points,
  size,
}: {
  points: BttsMatchChartPoint[];
  size: ChartSize;
}) {
  const density = getChartBarDensityClasses(points.length, size);

  return (
    <div className={density.containerClass}>
      {points.map((point) => {
        const isPositive = point.btts;
        return (
          <div key={point.label} className={density.columnClass}>
            <div
              className={`flex ${density.barHeightClass} ${density.barWidthClass} items-end rounded-md bg-slate-800/80`}
            >
              <div
                className={`flex w-full items-center justify-center rounded-md ${density.barLabelClass}`}
                style={{
                  height: `${BTTS_BAR_HEIGHT}%`,
                  backgroundColor: isPositive
                    ? CHART_COLOR_POSITIVE
                    : CHART_COLOR_NEGATIVE,
                }}
              >
                {getBttsBarLabel(isPositive, points.length)}
              </div>
            </div>
            <span className={density.labelClass}>{point.label}</span>
          </div>
        );
      })}
    </div>
  );
}

export function BttsMatchChart({
  title,
  teamName,
  points,
  compactScrollAlign,
}: BttsMatchChartProps) {
  if (points.length === 0) {
    return null;
  }

  const bttsCount = points.filter((point) => point.btts).length;
  const hitRate = (bttsCount / points.length) * 100;
  const chartTitle = `${title}: ${teamName}`;

  return (
    <div className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
      <div>
        <h4 className="text-sm font-semibold text-white">{chartTitle}</h4>
        <p className="mt-1 text-xs text-slate-400">
          Liczba BTTS: {bttsCount} · Hitrate BTTS: {formatPercent(hitRate)}
        </p>
      </div>

      <ChartScrollArea
        chartTitle={chartTitle}
        compactScrollAlign={compactScrollAlign}
        scrollKey={getChartPointsScrollKey(points)}
        expandedChildren={<BttsBars points={points} size="expanded" />}
      >
        <BttsBars points={points} size="compact" />
      </ChartScrollArea>
    </div>
  );
}
