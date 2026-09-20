import { StatusMessage } from "@/components/StatusMessage";
import {
  formatTipsterAmount,
  formatTipsterProfit,
  formatTipsterRoi,
  performanceItemLabel,
  signedAmountClassName,
  TIPSTER_EMPTY_VALUE,
  type PerformanceDimension,
} from "@/components/tipsters/tipsterModel";
import { formatOdds, formatPercent } from "@/lib/format";
import type {
  CurrencyCode,
  PerformanceBreakdown as TipsterPerformance,
  PerformanceItem,
} from "@/types/api";

export const PERFORMANCE_TITLE = "Analityka";
export const PERFORMANCE_EMPTY_TITLE = "Brak rozliczonych kuponów";
export const PERFORMANCE_EMPTY_MESSAGE =
  "Statystyki pojawią się po pierwszym rozliczonym kuponie.";
export const PERFORMANCE_WON_LABEL = "Wygrane";
export const PERFORMANCE_STAKE_LABEL = "Stawka";
export const PERFORMANCE_AVG_PROFIT_LABEL = "Śr. profit";
export const PERFORMANCE_AVG_ODDS_LABEL = "Śr. kurs";

interface PerformanceBreakdownProps {
  data: TipsterPerformance;
  currency: CurrencyCode;
}

export function PerformanceBreakdown({
  data,
  currency,
}: PerformanceBreakdownProps) {
  const isEmpty =
    data.by_event_family.length === 0 &&
    data.by_league.length === 0 &&
    data.by_league_tier.length === 0;

  if (isEmpty) {
    return (
      <StatusMessage
        variant="empty"
        title={PERFORMANCE_EMPTY_TITLE}
        message={PERFORMANCE_EMPTY_MESSAGE}
      />
    );
  }

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold text-text">{PERFORMANCE_TITLE}</h3>
      <PerformanceGroup
        title="Według typu zakładu"
        items={data.by_event_family}
        best={data.best_event_family}
        worst={data.worst_event_family}
        dimension="family"
        currency={currency}
      />
      <PerformanceGroup
        title="Według ligi"
        items={data.by_league}
        best={data.best_league}
        worst={data.worst_league}
        dimension="league"
        currency={currency}
      />
      <PerformanceGroup
        title="Według poziomu ligi"
        items={data.by_league_tier}
        best={data.best_league_tier}
        worst={data.worst_league_tier}
        dimension="tier"
        currency={currency}
      />
    </div>
  );
}

interface PerformanceGroupProps {
  title: string;
  items: PerformanceItem[];
  best: PerformanceItem | null;
  worst: PerformanceItem | null;
  dimension: PerformanceDimension;
  currency: CurrencyCode;
}

function PerformanceGroup({
  title,
  items,
  best,
  worst,
  dimension,
  currency,
}: PerformanceGroupProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-text">{title}</p>
      {best || worst ? (
        <p className="text-sm text-muted">
          Najlepszy: {formatHighlight(best, dimension, currency)}. Najsłabszy:{" "}
          {formatHighlight(worst, dimension, currency)}.
        </p>
      ) : null}
      <PerformanceTable items={items} dimension={dimension} currency={currency} />
    </div>
  );
}

interface PerformanceTableProps {
  items: PerformanceItem[];
  dimension: PerformanceDimension;
  currency: CurrencyCode;
}

function PerformanceTable({
  items,
  dimension,
  currency,
}: PerformanceTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Wymiar</th>
            <th className="px-3 py-2 text-right font-medium">Kupony</th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_WON_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">Trafność</th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_STAKE_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">Profit</th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_AVG_PROFIT_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_AVG_ODDS_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">ROI</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={performanceRowKey(item, dimension)}
              className="border-t border-border text-text"
            >
              <td className="px-3 py-2">{performanceItemLabel(item, dimension)}</td>
              <td className="px-3 py-2 text-right">{item.count}</td>
              <td className="px-3 py-2 text-right">{item.won}</td>
              <td className="px-3 py-2 text-right">
                {formatPercent(item.accuracy)}
              </td>
              <td className="px-3 py-2 text-right">
                {formatTipsterAmount(item.stake_total, currency)}
              </td>
              <td
                className={`px-3 py-2 text-right ${signedAmountClassName(
                  item.profit_total,
                )}`}
              >
                {formatTipsterProfit(item.profit_total, currency)}
              </td>
              <td
                className={`px-3 py-2 text-right ${signedAmountClassName(
                  item.avg_profit,
                )}`}
              >
                {formatTipsterProfit(item.avg_profit, currency)}
              </td>
              <td className="px-3 py-2 text-right">
                {formatAverageOdds(item.avg_odds)}
              </td>
              <td className="px-3 py-2 text-right">
                {formatTipsterRoi(item.roi_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatHighlight(
  item: PerformanceItem | null,
  dimension: PerformanceDimension,
  currency: CurrencyCode,
): string {
  if (!item) {
    return "—";
  }
  return `${performanceItemLabel(item, dimension)} (${formatTipsterProfit(
    item.profit_total,
    currency,
  )})`;
}

function formatAverageOdds(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return TIPSTER_EMPTY_VALUE;
  }
  return formatOdds(value);
}

function performanceRowKey(
  item: PerformanceItem,
  dimension: PerformanceDimension,
): string {
  if (dimension === "family") {
    return `family-${item.event_family_id ?? "other"}`;
  }
  if (dimension === "league") {
    return `league-${item.league_id ?? "none"}`;
  }
  return `tier-${item.league_tier ?? "none"}`;
}
