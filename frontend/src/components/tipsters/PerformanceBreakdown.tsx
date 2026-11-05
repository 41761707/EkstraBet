"use client";

import { useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { SignedLeagueProfitChart } from "@/components/stats/SignedLeagueProfitChart";
import type { SignedProfitPoint } from "@/components/stats/SignedLeagueProfitChart";
import { BetsPanel } from "@/components/tipsters/BetsPanel";
import { ChoiceTabs } from "@/components/tipsters/ChoiceTabs";
import { ResultCalendar } from "@/components/tipsters/ResultCalendar";
import {
  formatTipsterAmount,
  formatTipsterProfit,
  formatTipsterRoi,
  formatTipsterUnits,
  performanceItemLabel,
  signedAmountClassName,
  TIPSTER_EMPTY_VALUE,
  toPerformanceUnits,
  type PerformanceDimension,
} from "@/components/tipsters/tipsterModel";
import { formatOdds, formatPercent } from "@/lib/format";
import type {
  CurrencyCode,
  PerformanceBreakdown as TipsterPerformance,
  PerformanceItem,
} from "@/types/api";

export const PERFORMANCE_TITLE = "Analityka";
export const PERFORMANCE_INTRO =
  "Analiza w oparciu o wygrane kupony oraz odrębne, pojedyncze zdarzenia.";
export const PERFORMANCE_EMPTY_TITLE = "Brak rozliczonych kuponów";
export const PERFORMANCE_EMPTY_MESSAGE =
  "Statystyki pojawią się po pierwszym rozliczonym kuponie.";
export const PERFORMANCE_COUPON_TAB = "Per kupon";
export const PERFORMANCE_SINGLE_TAB = "Per zakład";
export const PERFORMANCE_UNIT_TAB = "Jednostka";
export const PERFORMANCE_COUPON_HINT =
  "Wygrana i wynik biorą cały kupon. Zdarzenie na przegranym kuponie jest " +
  "przegrane, nawet gdy samo weszło, bo cały kupon jest przegrany..";
export const PERFORMANCE_SINGLE_HINT =
  "Każde zdarzenie liczy się jak zdarzenie pojedyncze za stawkę kuponu, w którym zostało zagrane. Zdarzenie weszło - wynik " +
  "to kurs × stawka − stawka, także na przegranym kuponie.";
export const PERFORMANCE_WON_LABEL = "Wygrane";
export const PERFORMANCE_STAKE_LABEL = "Stawka";
export const PERFORMANCE_RESULT_LABEL = "Wynik";
export const PERFORMANCE_AVG_PROFIT_LABEL = "Śr. wynik";
export const PERFORMANCE_AVG_ODDS_LABEL = "Śr. kurs";
export const PERFORMANCE_SETTLED_LABEL = "Zysk kuponów";
export const PERFORMANCE_OPEN_LABEL = "W obiegu";
export const PERFORMANCE_SINGLES_LABEL = "Wynik singli";

const SETTLED_HINT =
  "Wynik rozliczonych kuponów. Ta sama liczba co Wynik w rankingu.";
const OPEN_HINT = "Stawki kuponów, które jeszcze nie są rozliczone.";
const SINGLES_TOTAL_HINT = "Gdyby każde zdarzenie było grane osobno.";
const COUPON_AVG_PROFIT_TITLE =
  "Zysk kuponów w wierszu podzielony przez ich liczbę.";
const SINGLE_AVG_PROFIT_TITLE =
  "Wynik zdarzeń w wierszu podzielony przez ich liczbę.";
const COUPON_AVG_ODDS_TITLE =
  "Średni kurs łączony kuponu.";
const SINGLE_AVG_ODDS_TITLE = "Średni kurs zdarzenia.";
const SINGLE_STAKE_TITLE = "Stawka kuponu liczona przy każdym zdarzeniu.";
const COUPON_COUNT_LABEL = "Kupony";
const SINGLE_COUNT_LABEL = "Zakłady";

type PerformanceLensId = "coupon" | "single";
type PerformanceMeasure = "currency" | "unit";

interface PerformanceAmounts {
  stake: (value: number | null) => string;
  profit: (value: number | null) => string;
}

interface PerformanceGroups {
  by_event_family: PerformanceItem[];
  by_league: PerformanceItem[];
  by_country: PerformanceItem[];
  best_event_family: PerformanceItem | null;
  worst_event_family: PerformanceItem | null;
  best_league: PerformanceItem | null;
  worst_league: PerformanceItem | null;
  best_country: PerformanceItem | null;
  worst_country: PerformanceItem | null;
}

interface PerformanceBreakdownProps {
  data: TipsterPerformance;
  currency: CurrencyCode;
  applyTax: boolean;
  username: string | null;
}

export function PerformanceBreakdown({
  data,
  currency,
  applyTax,
  username,
}: PerformanceBreakdownProps) {
  const [lens, setLens] = useState<PerformanceLensId>("coupon");
  const [measure, setMeasure] = useState<PerformanceMeasure>("currency");
  if (data.settled_count === 0) {
    return (
      <BetsPanel title={PERFORMANCE_TITLE} description={PERFORMANCE_INTRO}>
        <StatusMessage
          variant="empty"
          title={PERFORMANCE_EMPTY_TITLE}
          message={PERFORMANCE_EMPTY_MESSAGE}
        />
      </BetsPanel>
    );
  }

  const groups = groupsFor(data, lens);
  const unitSize = data.unit_size;
  const canUseUnits = unitSize !== null && unitSize > 0;
  const activeMeasure = canUseUnits ? measure : "currency";
  const amounts = amountsFor(activeMeasure, currency, unitSize);
  return (
    <BetsPanel title={PERFORMANCE_TITLE} description={PERFORMANCE_INTRO}>
      <PerformanceTotals data={data} amounts={amounts} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ChoiceTabs
          label="Sposób liczenia"
          tabs={[
            { id: "coupon", label: PERFORMANCE_COUPON_TAB },
            { id: "single", label: PERFORMANCE_SINGLE_TAB },
          ]}
          value={lens}
          onChange={setLens}
        />
        {canUseUnits ? (
          <ChoiceTabs
            label="Jednostka kwot"
            tabs={[
              { id: "currency", label: currency },
              { id: "unit", label: PERFORMANCE_UNIT_TAB },
            ]}
            value={activeMeasure}
            onChange={setMeasure}
          />
        ) : null}
      </div>
      {activeMeasure === "unit" && unitSize !== null ? (
        <p className="text-sm leading-relaxed text-muted">
          {unitMeasureHint(unitSize, currency)}
        </p>
      ) : null}
      <p className="text-sm leading-relaxed text-muted">
        {lens === "coupon" ? PERFORMANCE_COUPON_HINT : PERFORMANCE_SINGLE_HINT}
      </p>
      <PerformanceGroup
        title="Według typu zakładu"
        items={groups.by_event_family}
        best={groups.best_event_family}
        worst={groups.worst_event_family}
        dimension="family"
        lens={lens}
        amounts={amounts}
      />
      <PerformanceGroup
        title="Według ligi"
        items={groups.by_league}
        best={groups.best_league}
        worst={groups.worst_league}
        dimension="league"
        lens={lens}
        amounts={amounts}
      />
      <PerformanceGroup
        title="Według kraju"
        items={groups.by_country}
        best={groups.best_country}
        worst={groups.worst_country}
        dimension="country"
        lens={lens}
        amounts={amounts}
      />
      <ResultCalendar
        username={username}
        applyTax={applyTax}
        currency={currency}
      />
    </BetsPanel>
  );
}

function amountsFor(
  measure: PerformanceMeasure,
  currency: CurrencyCode,
  unitSize: number | null,
): PerformanceAmounts {
  if (measure === "unit" && unitSize !== null && unitSize > 0) {
    return {
      stake: (value) => formatTipsterUnits(scaleUnits(value, unitSize)),
      profit: (value) => formatTipsterUnits(scaleUnits(value, unitSize), true),
    };
  }
  return {
    stake: (value) => formatTipsterAmount(value, currency),
    profit: (value) => formatTipsterProfit(value, currency),
  };
}

function scaleUnits(value: number | null, unitSize: number): number | null {
  if (value === null) {
    return null;
  }
  return toPerformanceUnits(value, unitSize);
}

function unitMeasureHint(unitSize: number, currency: CurrencyCode): string {
  const unit = formatTipsterAmount(unitSize, currency);
  return (
    `Kwoty podzielone przez aktualną jednostkę (${unit}). ` +
    "Kurs, skuteczność i ROI bez zmian."
  );
}

function groupsFor(
  data: TipsterPerformance,
  lens: PerformanceLensId,
): PerformanceGroups {
  if (lens === "single") {
    return data.singles;
  }
  return data;
}

function PerformanceTotals({
  data,
  amounts,
}: {
  data: TipsterPerformance;
  amounts: PerformanceAmounts;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <PerformanceTotal
        label={PERFORMANCE_SETTLED_LABEL}
        value={amounts.profit(data.settled_profit)}
        hint={SETTLED_HINT}
        valueClassName={signedAmountClassName(data.settled_profit)}
      />
      <PerformanceTotal
        label={PERFORMANCE_OPEN_LABEL}
        value={amounts.stake(data.open_stake)}
        hint={OPEN_HINT}
        valueClassName="text-text"
      />
      <PerformanceTotal
        label={PERFORMANCE_SINGLES_LABEL}
        value={amounts.profit(data.singles.profit_total)}
        hint={SINGLES_TOTAL_HINT}
        valueClassName={signedAmountClassName(data.singles.profit_total)}
      />
    </div>
  );
}

function PerformanceTotal({
  label,
  value,
  hint,
  valueClassName,
}: {
  label: string;
  value: string;
  hint: string;
  valueClassName: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-raised px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${valueClassName}`}>{value}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{hint}</p>
    </div>
  );
}

interface PerformanceGroupProps {
  title: string;
  items: PerformanceItem[];
  best: PerformanceItem | null;
  worst: PerformanceItem | null;
  dimension: PerformanceDimension;
  lens: PerformanceLensId;
  amounts: PerformanceAmounts;
}

function PerformanceGroup({
  title,
  items,
  best,
  worst,
  dimension,
  lens,
  amounts,
}: PerformanceGroupProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 border-t border-border pt-5">
      <h3 className="text-base font-semibold text-text">{title}</h3>
      {best || worst ? (
        <p className="text-sm text-muted">
          Najlepszy: {formatHighlight(best, dimension, amounts)}. Najsłabszy:{" "}
          {formatHighlight(worst, dimension, amounts)}.
        </p>
      ) : null}
      {/* suma słupków dubluje kupony; właściwy wynik jest w kartach wyżej */}
      <SignedLeagueProfitChart
        title={lens === "coupon" ? "Wynik kuponów" : "Wynik zdarzeń"}
        points={performanceChartPoints(items, dimension)}
        totalProfit={0}
        showTotal={false}
        formatValue={(value) => amounts.profit(value)}
        countSuffix={lens === "coupon" ? "kup." : "zakł."}
      />
      <PerformanceTable
        items={items}
        dimension={dimension}
        lens={lens}
        amounts={amounts}
      />
    </div>
  );
}

interface PerformanceTableProps {
  items: PerformanceItem[];
  dimension: PerformanceDimension;
  lens: PerformanceLensId;
  amounts: PerformanceAmounts;
}

function PerformanceTable({
  items,
  dimension,
  lens,
  amounts,
}: PerformanceTableProps) {
  const isCoupon = lens === "coupon";
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted text-left text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Wymiar</th>
            <th className="px-3 py-2 text-right font-medium">
              {isCoupon ? COUPON_COUNT_LABEL : SINGLE_COUNT_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_WON_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">Skuteczność</th>
            <th
              className="px-3 py-2 text-right font-medium"
              title={isCoupon ? undefined : SINGLE_STAKE_TITLE}
            >
              {PERFORMANCE_STAKE_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">
              {PERFORMANCE_RESULT_LABEL}
            </th>
            <th
              className="px-3 py-2 text-right font-medium"
              title={isCoupon ? COUPON_AVG_PROFIT_TITLE : SINGLE_AVG_PROFIT_TITLE}
            >
              {PERFORMANCE_AVG_PROFIT_LABEL}
            </th>
            <th
              className="px-3 py-2 text-right font-medium"
              title={isCoupon ? COUPON_AVG_ODDS_TITLE : SINGLE_AVG_ODDS_TITLE}
            >
              {PERFORMANCE_AVG_ODDS_LABEL}
            </th>
            <th className="px-3 py-2 text-right font-medium">ROI</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <PerformanceRow
              key={performanceRowKey(item, dimension)}
              item={item}
              dimension={dimension}
              amounts={amounts}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PerformanceRow({
  item,
  dimension,
  amounts,
}: {
  item: PerformanceItem;
  dimension: PerformanceDimension;
  amounts: PerformanceAmounts;
}) {
  return (
    <tr className="border-t border-border text-text">
      <td className="px-3 py-2">{performanceItemLabel(item, dimension)}</td>
      <td className="px-3 py-2 text-right">{item.count}</td>
      <td className="px-3 py-2 text-right">{item.won}</td>
      <td className="px-3 py-2 text-right">{formatPercent(item.accuracy)}</td>
      <td className="px-3 py-2 text-right">
        {amounts.stake(item.stake_total)}
      </td>
      <td
        className={`px-3 py-2 text-right ${signedAmountClassName(
          item.profit_total,
        )}`}
      >
        {amounts.profit(item.profit_total)}
      </td>
      <td
        className={`px-3 py-2 text-right ${signedAmountClassName(
          item.avg_profit,
        )}`}
      >
        {amounts.profit(item.avg_profit)}
      </td>
      <td className="px-3 py-2 text-right">{formatAverageOdds(item.avg_odds)}</td>
      <td className="px-3 py-2 text-right">{formatTipsterRoi(item.roi_pct)}</td>
    </tr>
  );
}

function formatHighlight(
  item: PerformanceItem | null,
  dimension: PerformanceDimension,
  amounts: PerformanceAmounts,
): string {
  if (!item) {
    return "-";
  }
  return `${performanceItemLabel(item, dimension)} (${amounts.profit(
    item.profit_total,
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
