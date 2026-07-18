import type { ChatChartSpec } from "@/types/api";

interface ChatChartRendererProps {
  chart: ChatChartSpec;
}

export function ChatChartRenderer({ chart }: ChatChartRendererProps) {
  if (chart.points.length === 0) {
    return null;
  }

  const values = chart.points.flatMap((point) =>
    point.secondaryValue === undefined || point.secondaryValue === null
      ? [point.value]
      : [point.value, point.secondaryValue],
  );
  const maxValue = Math.max(...values, 1);

  return (
    <section className="space-y-4 rounded-xl border border-slate-700/80 bg-slate-950/70 p-4">
      <div>
        <h3 className="text-sm font-semibold text-white">{chart.title}</h3>
        {chart.yLabel ? (
          <p className="mt-1 text-xs text-slate-400">{chart.yLabel}</p>
        ) : null}
      </div>

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
    </section>
  );
}
