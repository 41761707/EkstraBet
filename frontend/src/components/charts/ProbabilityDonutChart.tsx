import { buildPieSlicesFromSegments } from "@/lib/pieSlices";
import { CHART_COLOR_NEUTRAL } from "@/lib/chartColors";
import { formatProbability } from "@/lib/format";
import type { ProbabilitySegmentView } from "@/components/predictions/predictionChartModel";

interface ProbabilityDonutChartProps {
  title: string;
  segments: ProbabilitySegmentView[];
  ariaLabel: string;
}

export function ProbabilityDonutChart({
  title,
  segments,
  ariaLabel,
}: ProbabilityDonutChartProps) {
  const slices = buildPieSlicesFromSegments(
    segments.map((segment) => ({ id: segment.id, percent: segment.percent })),
  );
  const colorById = new Map(segments.map((segment) => [segment.id, segment.color]));

  return (
    <article className="rounded-xl border border-border bg-surface p-4">
      <h3 className="mb-3 font-semibold text-accent-text">{title}</h3>
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-5">
        <svg
          viewBox="0 0 100 100"
          className="h-36 w-36 shrink-0 drop-shadow-sm"
          role="img"
          aria-label={ariaLabel}
        >
          {slices.map((slice) => {
            const fill = colorById.get(slice.id) ?? CHART_COLOR_NEUTRAL;
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
          <circle cx="50" cy="50" r="22" className="fill-surface" />
        </svg>

        <ul className="w-full min-w-0 space-y-2 text-sm">
          {segments.map((segment) => (
            <li
              key={segment.id}
              className={`flex items-center justify-between gap-3 rounded-md px-1.5 py-1 ${
                segment.isFavorite
                  ? "bg-surface-muted ring-1 ring-accent/50"
                  : ""
              }`}
            >
              <span className="flex min-w-0 items-center gap-2 text-muted">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: segment.color }}
                  aria-hidden
                />
                <span className="truncate" title={segment.label}>
                  {segment.label}
                  {segment.isFavorite ? (
                    <span className="ml-1 text-[10px] uppercase tracking-wide text-accent-text">
                      faworyt
                    </span>
                  ) : null}
                </span>
              </span>
              <span className="shrink-0 tabular-nums font-medium text-text">
                {formatProbability(segment.probability)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  );
}
