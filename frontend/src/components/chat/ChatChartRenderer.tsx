import type { ChatChartPoint, ChatChartSpec } from "@/types/api";

interface ChatChartRendererProps {
  chart: ChatChartSpec;
}

function maxPointValue(points: ChatChartPoint[]): number {
  const values = points.flatMap((point) =>
    point.secondaryValue === undefined || point.secondaryValue === null
      ? [point.value]
      : [point.value, point.secondaryValue],
  );
  return Math.max(...values, 1);
}

function BarChartBody({ chart, maxValue }: { chart: ChatChartSpec; maxValue: number }) {
  return (
    <div className="flex items-end gap-3 overflow-x-auto pb-2">
      {chart.points.map((point) => {
        const height = Math.max((point.value / maxValue) * 100, 4);
        const secondaryHeight =
          point.secondaryValue === undefined || point.secondaryValue === null
            ? null
            : Math.max((point.secondaryValue / maxValue) * 100, 4);

        return (
          <div
            key={`${point.label}-${point.value}`}
            className="flex min-w-[4.5rem] flex-col items-center gap-2"
          >
            <div className="flex h-44 items-end gap-1 rounded-md bg-slate-900/80 px-2 py-2">
              <div className="flex h-full flex-col justify-end gap-1">
                <span className="text-center text-xs font-semibold text-white">
                  {point.value}
                </span>
                <div
                  className="w-7 rounded-t-md bg-sky-400"
                  style={{ height: `${height}%` }}
                  title={`${chart.seriesLabel ?? "Wartość"}: ${point.value}`}
                />
              </div>
              {secondaryHeight !== null ? (
                <div className="flex h-full flex-col justify-end gap-1">
                  <span className="text-center text-xs font-semibold text-amber-100">
                    {point.secondaryValue}
                  </span>
                  <div
                    className="w-7 rounded-t-md bg-amber-400"
                    style={{ height: `${secondaryHeight}%` }}
                    title={`${chart.secondarySeriesLabel ?? "Wartość 2"}: ${
                      point.secondaryValue
                    }`}
                  />
                </div>
              ) : null}
            </div>
            <span className="max-w-[5rem] text-center text-[10px] leading-tight text-slate-400">
              {point.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function LineChartBody({ chart, maxValue }: { chart: ChatChartSpec; maxValue: number }) {
  const width = Math.max(chart.points.length * 56, 240);
  const height = 180;
  const padX = 16;
  const padY = 16;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;

  function xAt(index: number): number {
    if (chart.points.length <= 1) {
      return padX + innerW / 2;
    }
    return padX + (index / (chart.points.length - 1)) * innerW;
  }

  function yAt(value: number): number {
    return padY + innerH - (value / maxValue) * innerH;
  }

  const primaryPath = chart.points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${xAt(index)} ${yAt(point.value)}`)
    .join(" ");
  const hasSecondary = chart.points.some(
    (point) => point.secondaryValue !== undefined && point.secondaryValue !== null,
  );
  const secondaryPath = hasSecondary
    ? chart.points
        .map((point, index) => {
          const value = point.secondaryValue ?? point.value;
          return `${index === 0 ? "M" : "L"} ${xAt(index)} ${yAt(value)}`;
        })
        .join(" ")
    : null;

  return (
    <div className="overflow-x-auto pb-2">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="min-w-full text-sky-400"
        role="img"
        aria-label={chart.title}
      >
        <path d={primaryPath} fill="none" stroke="currentColor" strokeWidth="2.5" />
        {secondaryPath ? (
          <path
            d={secondaryPath}
            fill="none"
            stroke="#fbbf24"
            strokeWidth="2.5"
          />
        ) : null}
        {chart.points.map((point, index) => (
          <g key={`${point.label}-${index}`}>
            <circle cx={xAt(index)} cy={yAt(point.value)} r="3.5" fill="#38bdf8" />
            <text
              x={xAt(index)}
              y={height - 2}
              textAnchor="middle"
              className="fill-slate-400"
              fontSize="9"
            >
              {point.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export function ChatChartRenderer({ chart }: ChatChartRendererProps) {
  if (chart.points.length === 0) {
    return null;
  }

  const maxValue = maxPointValue(chart.points);

  return (
    <section className="space-y-4 rounded-xl border border-slate-700/80 bg-slate-950/70 p-4">
      <div>
        <h3 className="text-sm font-semibold text-white">{chart.title}</h3>
        {chart.yLabel ? (
          <p className="mt-1 text-xs text-slate-400">{chart.yLabel}</p>
        ) : null}
      </div>

      {chart.type === "line" ? (
        <LineChartBody chart={chart} maxValue={maxValue} />
      ) : (
        <BarChartBody chart={chart} maxValue={maxValue} />
      )}
    </section>
  );
}
