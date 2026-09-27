import { StatusMessage } from "@/components/StatusMessage";
import { SignedLeagueProfitChart } from "@/components/stats/SignedLeagueProfitChart";
import type { SignedProfitPoint } from "@/components/stats/SignedLeagueProfitChart";
import { BetsPanel } from "@/components/tipsters/BetsPanel";
import {
  formatPerformanceLegHits,
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
export const PERFORMANCE_EVENTS_LABEL = "Zdarzenia";
export const PERFORMANCE_READING_HINT =
  "Wygrane i wynik liczą cały kupon. Zdarzenia pokazują, czy zdarzenie " +
  "z tej ligi, tego kraju albo tego typu zakładu weszło, nawet wtedy, gdy " +
  "kupon przegrał. Śr. kurs to średni kurs tych zdarzeń, a nie kurs łączny " +
  "kuponu.";
export const PERFORMANCE_STAKE_LABEL = "Stawka";
export const PERFORMANCE_RESULT_LABEL = "Wynik";
export const PERFORMANCE_AVG_PROFIT_LABEL = "Śr. wynik";
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
    data.by_country.length === 0;

  return (
    <BetsPanel
      title={PERFORMANCE_TITLE}
      description={PERFORMANCE_READING_HINT}
    >
      {isEmpty ? (
        <StatusMessage
          variant="empty"
          title={PERFORMANCE_EMPTY_TITLE}
          message={PERFORMANCE_EMPTY_MESSAGE}
        />
      ) : (
        <>
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
            title="Według kraju"
            items={data.by_country}
            best={data.best_country}
            worst={data.worst_country}
            dimension="country"
            currency={currency}
          />
        </>
      )}
    </BetsPanel>
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
    <div className="space-y-2 border-t border-border pt-5 first:border-t-0 first:pt-0">
      <h3 className="text-base font-semibold text-text">{title}</h3>
      {best || worst ? (
        <p className="text-sm text-muted">
          Najlepszy: {formatHighlight(best, dimension, currency)}. Najsłabszy:{" "}
          {formatHighlight(worst, dimension, currency)}.
        </p>
      ) : null}
      <SignedLeagueProfitChart
        title="Wynik"
        points={performanceChartPoints(items, dimension)}
        totalProfit={performanceChartTotal(items)}
        formatValue={(value) => formatTipsterProfit(value, currency)}
        countSuffix="kup."
      />
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
              {PERFORMANCE_EVENTS_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_STAKE_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_RESULT_LABEL}
            </th>
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
              <PerformanceLegHits item={item} />
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

interface PerformanceLegHitsProps {
  item: PerformanceItem;
}

function PerformanceLegHits({ item }: PerformanceLegHitsProps) {
  const hitOnLostCoupon = item.legs_won_on_lost_coupons > 0;
  return (
    <td
      className={`px-3 py-2 text-right ${
        hitOnLostCoupon ? "text-success" : ""
      }`}
    >
      {formatPerformanceLegHits(item.legs_won, item.legs_count)}
    </td>
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
  return `country-${item.country_id ?? "none"}`;
}

function performanceChartPoints(
  items: PerformanceItem[],
  dimension: PerformanceDimension,
): SignedProfitPoint[] {
  return items.map((item) => ({
    leagueName: performanceItemLabel(item, dimension),
    profit: item.profit_total,
    totalBets: item.count,
  }));
}

function performanceChartTotal(items: PerformanceItem[]): number {
  return items.reduce((sum, item) => sum + item.profit_total, 0);
}
