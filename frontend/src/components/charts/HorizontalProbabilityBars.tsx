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
      <article className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
        <h3 className="mb-3 font-semibold text-sky-300">{title}</h3>
        <p className="text-sm text-slate-400">{emptyMessage}</p>
      </article>
    );
  }

  return (
    <article className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
      <h3 className="mb-3 font-semibold text-sky-300">{title}</h3>
      <div className="space-y-3">
        {points.map((point) => {
          const width = Math.max(point.barPercent, point.probability > 0 ? 8 : 0);
          return (
            <div key={point.id} className="space-y-1">
              <div className="flex items-center justify-between gap-3 text-xs text-slate-300">
                <span
                  className={`truncate ${
                    point.isFavorite ? "font-semibold text-sky-300" : ""
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
                <span className="shrink-0 tabular-nums font-semibold text-white">
                  {formatProbability(point.probability)}
                </span>
              </div>
              <div className="h-7 rounded-md bg-slate-800/80">
                <div
                  className={`flex h-7 items-center rounded-md px-2 text-xs font-semibold text-white ${
                    point.isFavorite ? "ring-1 ring-inset ring-sky-300/60" : ""
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
