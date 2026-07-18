import {
  ComparisonChart,
  DistributionChart,
} from "@/components/stats/AnalyticsCharts";
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
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-left text-slate-400">
          <tr>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 text-right font-medium">Total</th>
            <th className="px-4 py-3 text-right font-medium">Correct</th>
            <th className="px-4 py-3 text-right font-medium">Accuracy</th>
            <th className="px-4 py-3 text-right font-medium">Share</th>
            {showProfit ? (
              <th className="px-4 py-3 text-right font-medium">Profit</th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.key}
              className="border-t border-slate-800/80 hover:bg-slate-900/50"
            >
              <td className="px-4 py-3 text-white">{row.key}</td>
              <td className="px-4 py-3 text-right text-slate-200">
                {row.total}
              </td>
              <td className="px-4 py-3 text-right text-slate-200">
                {row.correct}
              </td>
              <td className="px-4 py-3 text-right text-slate-200">
                {formatPercent(row.accuracy_pct)}
              </td>
              <td className="px-4 py-3 text-right text-slate-200">
                {formatPercent(row.share_pct)}
              </td>
              {showProfit ? (
                <td className="px-4 py-3 text-right text-slate-200">
                  {formatProfit(row.profit)}
                </td>
              ) : null}
            </tr>
          ))}
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
      <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
        <p className="text-xs uppercase tracking-wide text-slate-400">
          {label} total
        </p>
        <p className="mt-1 text-2xl font-semibold text-white">{total}</p>
      </div>
      <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
        <p className="text-xs uppercase tracking-wide text-slate-400">
          {label} correct
        </p>
        <p className="mt-1 text-2xl font-semibold text-emerald-300">
          {correct}
        </p>
      </div>
      <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
        <p className="text-xs uppercase tracking-wide text-slate-400">
          {label} accuracy
        </p>
        <p className="mt-1 text-2xl font-semibold text-sky-300">
          {formatPercent(accuracyPct)}
        </p>
      </div>
      <div className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-4">
        <p className="text-xs uppercase tracking-wide text-slate-400">
          {label} profit
        </p>
        <p className="mt-1 text-2xl font-semibold text-amber-300">
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
      <h3 className="text-xl font-semibold text-white">{title}</h3>

      <div className="space-y-4">
        <h4 className="text-sm font-medium uppercase tracking-wide text-slate-400">
          Predictions
        </h4>
        <SummaryCards
          label="Predictions"
          total={category.predictions.total}
          correct={category.predictions.correct}
          accuracyPct={category.predictions.accuracy_pct}
          profitTotal={category.predictions.profit_total}
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <DistributionChart
            title="Prediction distribution"
            data={category.predictions.charts.distribution}
          />
          <ComparisonChart
            title="Prediction outcomes"
            data={category.predictions.charts.comparison}
          />
        </div>
        <BreakdownTable
          rows={category.predictions.by_type}
          showProfit={false}
        />
      </div>

      <div className="space-y-4">
        <h4 className="text-sm font-medium uppercase tracking-wide text-slate-400">
          Bets
        </h4>
        <SummaryCards
          label="Bets"
          total={category.bets.total}
          correct={category.bets.correct}
          accuracyPct={category.bets.accuracy_pct}
          profitTotal={category.bets.profit_total}
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <DistributionChart
            title="Bet distribution"
            data={category.bets.charts.distribution}
          />
          <ComparisonChart
            title="Bet outcomes"
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
