import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import { formatProfit } from "@/lib/format";

export interface SignedProfitPoint {
  leagueName: string;
  profit: number;
  totalBets: number;
}

interface SignedLeagueProfitChartProps {
  title: string;
  points: SignedProfitPoint[];
  totalProfit: number;
  labelWidthClassName?: string;
}

const ZERO_THRESHOLD = 0.005;

function profitBarColor(profit: number): string {
  if (Math.abs(profit) < ZERO_THRESHOLD) {
    return CHART_COLOR_DRAW;
  }
  return profit > 0 ? CHART_COLOR_POSITIVE : CHART_COLOR_NEGATIVE;
}

function SignedProfitRow({
  point,
  maxAbs,
  labelColumn,
}: {
  point: SignedProfitPoint;
  maxAbs: number;
  labelColumn: string;
}) {
  const widthPct = (Math.abs(point.profit) / maxAbs) * 50;
  const isNegative = point.profit < 0;
  const hasBar = Math.abs(point.profit) >= ZERO_THRESHOLD;

  return (
    <div
      className="grid items-center gap-3"
      style={{
        gridTemplateColumns: `${labelColumn} 1fr minmax(7.5rem,auto)`,
      }}
    >
      <span className="truncate text-xs text-muted" title={point.leagueName}>
        {point.leagueName}
      </span>
      <div className="relative h-6 rounded-md bg-chart-track">
        <div
          className="pointer-events-none absolute bottom-0 top-0 border-l border-dashed"
          style={{
            left: "50%",
            borderColor: `${CHART_COLOR_DRAW}cc`,
          }}
          title="Zero"
        />
        {hasBar ? (
          <div
            className="absolute top-0 h-6 rounded-md"
            style={{
              left: isNegative ? `${50 - widthPct}%` : "50%",
              width: `${Math.max(widthPct, 1.5)}%`,
              backgroundColor: profitBarColor(point.profit),
            }}
          />
        ) : null}
      </div>
      <span className="whitespace-nowrap text-xs tabular-nums text-text">
        {formatProfit(point.profit)} · {point.totalBets} zakł.
      </span>
    </div>
  );
}

export function SignedLeagueProfitChart({
  title,
  points,
  totalProfit,
  labelWidthClassName = "10rem",
}: SignedLeagueProfitChartProps) {
  if (points.length === 0) {
    return null;
  }

  const sorted = [...points].sort((left, right) => left.profit - right.profit);
  const maxAbs = Math.max(
    ...sorted.map((point) => Math.abs(point.profit)),
    1,
  );
  const labelColumn = `minmax(0,${labelWidthClassName})`;

  return (
    <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-text">{title}</h4>
        <span className="text-xs text-muted">
          Suma: {formatProfit(totalProfit)}
        </span>
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-muted">
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_POSITIVE }}
          />
          Dodatni
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_NEGATIVE }}
          />
          Ujemny
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: CHART_COLOR_DRAW }}
          />
          Zero
        </span>
      </div>

      <div className="relative max-h-96 overflow-y-auto pr-1">
        <div className="space-y-2">
          {sorted.map((point) => (
            <SignedProfitRow
              key={point.leagueName}
              point={point}
              maxAbs={maxAbs}
              labelColumn={labelColumn}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
