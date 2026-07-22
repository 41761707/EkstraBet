import { formatProbability } from "@/lib/format";
import type { ProbabilityBarPoint } from "@/components/predictions/predictionChartModel";

interface VerticalProbabilityBarsProps {
  title: string;
  points: ProbabilityBarPoint[];
  emptyMessage?: string;
}

export function VerticalProbabilityBars({
  title,
  points,
  emptyMessage = "Brak danych.",
}: VerticalProbabilityBarsProps) {
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
      <div className="flex items-end justify-between gap-2 overflow-x-auto pb-1">
        {points.map((point) => {
          const height = Math.max(point.barPercent, point.probability > 0 ? 6 : 0);
          return (
            <div
              key={point.id}
              className="flex min-w-[2.75rem] flex-1 flex-col items-center gap-2"
            >
              <span className="text-xs font-semibold tabular-nums text-white">
                {formatProbability(point.probability)}
              </span>
              <div className="flex h-36 w-full max-w-[2.5rem] items-end rounded-md bg-slate-800/80 p-1">
                <div
                  className={`w-full rounded-md transition-[height] ${
                    point.isFavorite ? "ring-2 ring-sky-400/70 ring-offset-1 ring-offset-slate-900" : ""
                  }`}
                  style={{
                    height: `${height}%`,
                    backgroundColor: point.color,
                  }}
                  title={`${point.label}: ${formatProbability(point.probability)}`}
                />
              </div>
              <span
                className={`text-xs ${
                  point.isFavorite ? "font-semibold text-sky-300" : "text-slate-400"
                }`}
              >
                {point.label}
              </span>
            </div>
          );
        })}
      </div>
    </article>
  );
}
