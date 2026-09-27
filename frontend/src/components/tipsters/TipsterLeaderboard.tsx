import Link from "next/link";

import { PaginationBar } from "@/components/PaginationBar";
import { StatusMessage } from "@/components/StatusMessage";
import {
  formatPerformanceLegHits,
  formatTipsterAmount,
  formatTipsterProfit,
  formatTipsterRoi,
  signedAmountClassName,
  TIPSTER_EMPTY_VALUE,
  TYPERS_PATH,
} from "@/components/tipsters/tipsterModel";
import { formatOdds, formatPercent } from "@/lib/format";
import { profilePath } from "@/lib/profilePaths";
import type { LeaderboardRow } from "@/types/api";

export const TIPSTER_LEADERBOARD_TITLE = "Ranking";
export const TIPSTER_LEADERBOARD_EMPTY_TITLE = "Ranking jest pusty";
export const TIPSTER_LEADERBOARD_EMPTY_MESSAGE =
  "Pojawi się, gdy ktoś skonfiguruje kapitał. Spróbuj też poluzować filtry.";
export const SYSTEM_ACCOUNT_LABEL = "Agent";
export const TIPSTER_LEADERBOARD_EVENTS_LABEL = "Zdarzenia";

interface TipsterLeaderboardProps {
  rows: LeaderboardRow[];
  total: number;
  page: number;
  pageSize: number;
  searchParams: Record<string, string | undefined>;
}

export function TipsterLeaderboard({
  rows,
  total,
  page,
  pageSize,
  searchParams,
}: TipsterLeaderboardProps) {
  if (rows.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title={TIPSTER_LEADERBOARD_EMPTY_TITLE}
        message={TIPSTER_LEADERBOARD_EMPTY_MESSAGE}
      />
    );
  }

  const placeOffset = (page - 1) * pageSize;

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-text">
          {TIPSTER_LEADERBOARD_TITLE}
        </h2>
        <span className="text-sm text-muted">{total} typerów</span>
      </div>
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-surface-muted text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">#</th>
              <th className="px-3 py-2 font-medium">Typer</th>
              <th className="px-3 py-2 text-right font-medium">Kupony</th>
              <th className="px-3 py-2 text-right font-medium">Skuteczność</th>
              <th className="px-3 py-2 text-right font-medium">
                {TIPSTER_LEADERBOARD_EVENTS_LABEL}
              </th>
              <th className="px-3 py-2 text-right font-medium">Wynik</th>
              <th className="px-3 py-2 text-right font-medium">Śr. wynik</th>
              <th className="px-3 py-2 text-right font-medium">ROI</th>
              <th className="px-3 py-2 text-right font-medium">Śr. kurs</th>
              <th className="px-3 py-2 text-right font-medium">Saldo</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <LeaderboardTableRow
                key={row.user_id}
                row={row}
                place={placeOffset + index + 1}
                applyTax={searchParams.apply_tax === "true"}
              />
            ))}
          </tbody>
        </table>
      </div>
      <PaginationBar
        basePath={TYPERS_PATH}
        currentPage={page}
        totalCount={total}
        pageSize={pageSize}
        searchParams={searchParams}
      />
    </section>
  );
}

function LeaderboardTableRow({
  row,
  place,
  applyTax,
}: {
  row: LeaderboardRow;
  place: number;
  applyTax: boolean;
}) {
  const displayName = row.display_name?.trim() || row.username;
  const href = applyTax
    ? `${profilePath(row.username)}?apply_tax=true`
    : profilePath(row.username);
  return (
    <tr className="bg-surface text-text even:bg-surface-muted">
      <td className="px-3 py-2 text-muted">{place}</td>
      <td className="px-3 py-2">
        <Link
          href={href}
          className="font-medium text-accent-text transition hover:text-accent-text-hover"
        >
          {displayName}
        </Link>
        <span className="mt-0.5 block text-xs text-muted">
          @{row.username}
          {row.is_system ? ` · ${SYSTEM_ACCOUNT_LABEL}` : null}
        </span>
      </td>
      <td className="px-3 py-2 text-right">{row.bets_count}</td>
      <td className="px-3 py-2 text-right">
        {formatPercent(row.accuracy_pct)}
      </td>
      <LeaderboardLegHits row={row} />
      <td
        className={`px-3 py-2 text-right ${signedAmountClassName(row.profit_total)}`}
      >
        {formatTipsterProfit(row.profit_total, row.currency)}
      </td>
      <td
        className={`px-3 py-2 text-right ${signedAmountClassName(row.avg_profit)}`}
      >
        {formatTipsterProfit(row.avg_profit, row.currency)}
      </td>
      <td className="px-3 py-2 text-right">{formatTipsterRoi(row.roi_pct)}</td>
      <td className="px-3 py-2 text-right">
        {formatNullableOdds(row.avg_odds)}
      </td>
      <td className="px-3 py-2 text-right">
        {formatTipsterAmount(row.current_balance, row.currency)}
      </td>
    </tr>
  );
}

interface LeaderboardLegHitsProps {
  row: LeaderboardRow;
}

function LeaderboardLegHits({ row }: LeaderboardLegHitsProps) {
  const hitOnLostCoupon = row.legs_won_on_lost_coupons > 0;
  return (
    <td
      className={`px-3 py-2 text-right ${
        hitOnLostCoupon ? "text-success" : ""
      }`}
    >
      {formatPerformanceLegHits(row.legs_won, row.legs_count)}
    </td>
  );
}

function formatNullableOdds(value: number | null): string {
  if (value === null || Number.isNaN(value)) {
    return TIPSTER_EMPTY_VALUE;
  }
  return formatOdds(value);
}
