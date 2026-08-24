import { formatProbability } from "@/lib/format";
import type { ProbabilityBarPoint } from "@/components/predictions/predictionChartModel";

interface HorizontalProbabilityBarsProps {
  title: string;
  points: ProbabilityBarPoint[];
  emptyMessage?: string;
}

export function HorizontalProbabilityBars({
  title,
  points,
  emptyMessage = "Brak danych.",
}: HorizontalProbabilityBarsProps) {
  if (points.length === 0) {
    return (
      <article className="rounded-xl border border-border bg-surface p-4">
        <h3 className="mb-3 font-semibold text-accent-text">{title}</h3>
        <p className="text-sm text-muted">{emptyMessage}</p>
      </article>
    );
  }

  return (
    <article className="rounded-xl border border-border bg-surface p-4">
      <h3 className="mb-3 font-semibold text-accent-text">{title}</h3>
      <div className="space-y-3">
        {points.map((point) => {
          const width = Math.max(point.barPercent, point.probability > 0 ? 8 : 0);
          return (
            <div key={point.id} className="space-y-1">
              <div className="flex items-center justify-between gap-3 text-xs text-muted">
                <span
                  className={`truncate ${
                    point.isFavorite ? "font-semibold text-accent-text" : ""
                  }`}
                  title={point.label}
                >
                  {point.label}
                  {point.isFavorite ? (
                    <span className="ml-1 text-[10px] uppercase tracking-wide">
                      faworyt
                    </span>
                  ) : null}
                </span>
                <span className="shrink-0 tabular-nums font-semibold text-text">
                  {formatProbability(point.probability)}
                </span>
              </div>
              <div className="h-7 rounded-md bg-chart-track">
                <div
                  className={`flex h-7 items-center rounded-md px-2 text-xs font-semibold ${
                    point.isFavorite ? "ring-1 ring-inset ring-accent/60" : ""
                  }`}
                  style={{
                    width: `${width}%`,
                    backgroundColor: point.color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}
