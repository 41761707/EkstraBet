import {
  ComparisonChart,
  DistributionChart,
} from "@/components/stats/AnalyticsCharts";
import { formatAnalyticsTypeLabel } from "@/lib/analyticsLabels";
import { getSemanticBarColor } from "@/lib/chartColors";
import { formatPercent, formatProfit } from "@/lib/format";
import type { CategoryStatistics } from "@/types/api";

interface AnalyticsCategoryPanelProps {
  title: string;
  category: CategoryStatistics;
}

function BreakdownTable({
  rows,
  showProfit,
}: {
  rows: CategoryStatistics["predictions"]["by_type"];
  showProfit: boolean;
}) {
  if (rows.length === 0) {
    return null;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-left text-muted">
          <tr>
            <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide">
              Typ
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide">
              Łącznie
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide">
              Trafione
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide">
              Skuteczność
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide">
              Udział
            </th>
            {showProfit ? (
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide">
                Zysk
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const label = formatAnalyticsTypeLabel(row.key);
            return (
              <tr
                key={row.key}
                className="border-t border-border hover:bg-surface-muted/50"
              >
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-2.5 font-medium text-text">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: getSemanticBarColor(label) }}
                      aria-hidden
                    />
                    {label}
                  </span>
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-text">
                  {row.total}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-text">
                  {row.correct}
                </td>
                <td className="px-4 py-3 text-right tabular-nums font-medium text-accent-text-hover">
                  {formatPercent(row.accuracy_pct)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-muted">
                  {formatPercent(row.share_pct)}
                </td>
                {showProfit ? (
                  <td className="px-4 py-3 text-right tabular-nums font-medium text-warning-text">
                    {formatProfit(row.profit)}
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SummaryCards({
  label,
  total,
  correct,
  accuracyPct,
  profitTotal,
}: {
  label: string;
  total: number;
  correct: number;
  accuracyPct: number | null;
  profitTotal: number | null;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {label} łącznie
        </p>
        <p className="mt-1.5 text-2xl font-semibold tabular-nums text-text">
          {total}
        </p>
      </div>
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {label} trafione
        </p>
        <p className="mt-1.5 text-2xl font-semibold tabular-nums text-success">
          {correct}
        </p>
      </div>
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {label} skuteczność
        </p>
        <p className="mt-1.5 text-2xl font-semibold tabular-nums text-accent-text">
          {formatPercent(accuracyPct)}
        </p>
      </div>
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
          {label} zysk
        </p>
        <p className="mt-1.5 text-2xl font-semibold tabular-nums text-warning">
          {formatProfit(profitTotal)}
        </p>
      </div>
    </div>
  );
}

export function AnalyticsCategoryPanel({
  title,
  category,
}: AnalyticsCategoryPanelProps) {
  return (
    <section className="space-y-6">
      <h3 className="text-xl font-semibold tracking-tight text-text">
        {title}
      </h3>

      <div className="space-y-4">
        <h4 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
          Predykcje
        </h4>
        <SummaryCards
          label="Predykcje"
          total={category.predictions.total}
          correct={category.predictions.correct}
          accuracyPct={category.predictions.accuracy_pct}
          profitTotal={category.predictions.profit_total}
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <DistributionChart
            title="Rozkład predykcji"
            data={category.predictions.charts.distribution}
          />
          <ComparisonChart
            title="Wyniki predykcji"
            data={category.predictions.charts.comparison}
          />
        </div>
        <BreakdownTable
          rows={category.predictions.by_type}
          showProfit={false}
        />
      </div>

      <div className="space-y-4">
        <h4 className="text-xs font-semibold uppercase tracking-[0.16em] text-muted">
          Zakłady
        </h4>
        <SummaryCards
          label="Zakłady"
          total={category.bets.total}
          correct={category.bets.correct}
          accuracyPct={category.bets.accuracy_pct}
          profitTotal={category.bets.profit_total}
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <DistributionChart
            title="Rozkład zakładów"
            data={category.bets.charts.distribution}
          />
          <ComparisonChart
            title="Wyniki zakładów"
            data={category.bets.charts.comparison}
          />
        </div>
        <BreakdownTable
          rows={category.bets.by_type}
          showProfit
        />
      </div>
    </section>
  );
}
