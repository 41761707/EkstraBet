import { FavoriteBadge } from "@/components/charts/FavoriteBadge";

import type { ExpectedValueBarPoint } from "@/components/matches/hockeyPlayerPredictionsModel";

interface HorizontalExpectedValueBarsProps {
  title: string;
  points: ExpectedValueBarPoint[];
  emptyMessage?: string;
  formatValue?: (value: number) => string;
}

export function HorizontalExpectedValueBars({
  title,
  points,
  emptyMessage = "Brak danych.",
  formatValue = formatTwoDecimals,
}: HorizontalExpectedValueBarsProps) {
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
        {points.map((point) => (
          <ExpectedValueRow
            key={point.id}
            point={point}
            label={formatValue(point.value)}
          />
        ))}
      </div>
    </article>
  );
}

function ExpectedValueRow({
  point,
  label,
}: {
  point: ExpectedValueBarPoint;
  label: string;
}) {
  const width = Math.max(point.barPercent, point.value > 0 ? 8 : 0);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-3 text-xs text-muted">
        <span className="flex min-w-0 items-center gap-1.5" title={point.label}>
          <span
            className={`truncate ${
              point.isFavorite ? "font-semibold text-accent-text" : ""
            }`}
          >
            {point.label}
          </span>
          {point.isFavorite ? <FavoriteBadge /> : null}
        </span>
        <span className="shrink-0 tabular-nums font-semibold text-text">
          {label}
        </span>
      </div>
      <div className="relative h-5">
        <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-chart-track" />
        <div
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full"
          style={{ width: `${width}%`, backgroundColor: point.color }}
        />
        <div
          className={`absolute top-1/2 h-3.5 w-3.5 rounded-full ${
            point.isFavorite ? "ring-2 ring-accent/70 ring-offset-1 ring-offset-surface" : ""
          }`}
          style={{
            left: `clamp(0px, calc(${width}% - 7px), calc(100% - 14px))`,
            backgroundColor: point.color,
            transform: "translateY(-50%)",
          }}
          title={`${point.label}: ${label}`}
        />
      </div>
    </div>
  );
}

function formatTwoDecimals(value: number): string {
  return value.toFixed(2);
}
