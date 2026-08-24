import type { ChartComparison, ChartDistribution } from "@/types/api";
import { formatAnalyticsTypeLabel } from "@/lib/analyticsLabels";
import {
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_NEUTRAL,
  CHART_COLOR_POSITIVE,
  getSemanticBarColor,
} from "@/lib/chartColors";
import {
  buildPieSlicesFromSegments,
  normalizeProbabilitiesToPercents,
} from "@/lib/pieSlices";

interface DistributionChartProps {
  data: ChartDistribution;
  title: string;
}

interface ComparisonChartProps {
  data: ChartComparison;
  title: string;
}

export function DistributionChart({ data, title }: DistributionChartProps) {
  const total = data.values.reduce((sum, value) => sum + value, 0);
  const percents =
    total > 0
      ? normalizeProbabilitiesToPercents(
          data.values.map((value) => value / total),
        )
      : data.values.map(() => 0);

  const segments = data.labels.map((rawLabel, index) => {
    const label = formatAnalyticsTypeLabel(rawLabel);
    return {
      id: rawLabel,
      label,
      value: data.values[index] ?? 0,
      percent: percents[index] ?? 0,
      color: getSemanticBarColor(label),
    };
  });

  const slices = buildPieSlicesFromSegments(
    segments.map((segment) => ({
      id: segment.id,
      percent: segment.percent,
    })),
  );

  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <h4 className="text-sm font-semibold tracking-tight text-text">
        {title}
      </h4>
      {total === 0 ? (
        <p className="text-sm text-muted">Brak danych do wykresu.</p>
      ) : (
        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-center sm:gap-6">
          <svg
            viewBox="0 0 100 100"
            className="h-40 w-40 shrink-0"
            role="img"
            aria-label={title}
          >
            {slices.map((slice) => {
              const fill =
                segments.find((segment) => segment.id === slice.id)?.color ??
                CHART_COLOR_NEUTRAL;
              if (slice.isFullCircle) {
                return (
                  <circle key={slice.id} cx="50" cy="50" r="42" fill={fill} />
                );
              }
              if (!slice.path) {
                return null;
              }
              return <path key={slice.id} d={slice.path} fill={fill} />;
            })}
          </svg>

          <ul className="w-full min-w-0 space-y-2.5">
            {segments.map((segment) => (
              <li
                key={segment.id}
                className="flex items-center justify-between gap-3 rounded-lg bg-surface-muted px-2.5 py-2"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <span
                    className="h-3 w-3 shrink-0 rounded-full"
                    style={{ backgroundColor: segment.color }}
                    aria-hidden
                  />
                  <span
                    className="truncate text-sm font-medium text-text"
                    title={segment.label}
                  >
                    {segment.label}
                  </span>
                </span>
                <span className="shrink-0 text-right">
                  <span className="block text-sm font-semibold tabular-nums text-text">
                    {segment.percent}%
                  </span>
                  <span className="block text-xs tabular-nums text-muted">
                    {segment.value} szt.
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function ComparisonChart({ data, title }: ComparisonChartProps) {
  return (
    <div className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <h4 className="text-sm font-semibold tracking-tight text-text">
        {title}
      </h4>
      <div className="space-y-4">
        {data.labels.map((rawLabel, index) => {
          const label = formatAnalyticsTypeLabel(rawLabel);
          const correct = data.correct[index] ?? 0;
          const incorrect = data.incorrect[index] ?? 0;
          const total = correct + incorrect;
          const correctWidth = total > 0 ? (correct / total) * 100 : 0;
          const incorrectWidth = total > 0 ? (incorrect / total) * 100 : 0;

          return (
            <div key={rawLabel} className="space-y-2">
              <div className="flex items-end justify-between gap-3">
                <span className="text-sm font-medium text-text">
                  {label}
                </span>
                <span className="text-xs tabular-nums text-muted">
                  <span className="font-medium text-success">{correct}</span>
                  {" / "}
                  <span className="font-medium text-danger">{incorrect}</span>
                  <span className="ml-1 text-subtle">popr./błęd.</span>
                </span>
              </div>
              <div className="flex h-3.5 overflow-hidden rounded-full bg-chart-track">
                <div
                  style={{
                    width: `${correctWidth}%`,
                    backgroundColor: CHART_COLOR_POSITIVE,
                  }}
                  title={`Poprawne: ${correct}`}
                />
                <div
                  style={{
                    width: `${incorrectWidth}%`,
                    backgroundColor: CHART_COLOR_NEGATIVE,
                  }}
                  title={`Błędne: ${incorrect}`}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-4 border-t border-border pt-3 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: CHART_COLOR_POSITIVE }}
          />
          Poprawne
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: CHART_COLOR_NEGATIVE }}
          />
          Błędne
        </span>
      </div>
    </div>
  );
}
