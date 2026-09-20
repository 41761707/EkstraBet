import Link from "next/link";

import { PaginationBar } from "@/components/PaginationBar";
import { StatusMessage } from "@/components/StatusMessage";
import {
  couponHistoryStatusLabel,
  couponStatusClassName,
  formatCouponCombinedOdds,
  formatTipsterAmount,
  formatTipsterProfit,
  historyEventLabel,
  historyMatchLabel,
  isCombinedLeg,
  legOutcomeClassName,
  legOutcomeLabel,
  signedAmountClassName,
} from "@/components/tipsters/tipsterModel";
import { formatMatchDateTime, formatOdds } from "@/lib/format";
import type {
  CouponLegSummary,
  CouponPage,
  CouponSummary,
  CurrencyCode,
} from "@/types/api";

export const COUPON_HISTORY_TITLE = "Historia kuponów";
export const COUPON_HISTORY_EMPTY_TITLE = "Brak kuponów";
export const COUPON_HISTORY_EMPTY_MESSAGE =
  "Tu pojawi się historia po dodaniu pierwszego kuponu.";
export const COUPON_HISTORY_PUBLIC_EMPTY_MESSAGE =
  "Historia pojawi się po kuponach tego użytkownika.";
export const COUPON_HISTORY_SYSTEM_EMPTY_MESSAGE =
  "Historia pojawi się po kuponach tego konta systemowego.";

interface CouponHistoryTableProps {
  coupons: CouponPage;
  currency: CurrencyCode;
  profilePath: string;
  searchParams: Record<string, string | undefined>;
  isOwnProfile?: boolean;
  isSystemProfile?: boolean;
}

export function CouponHistoryTable({
  coupons,
  currency,
  profilePath,
  searchParams,
  isOwnProfile = true,
  isSystemProfile = false,
}: CouponHistoryTableProps) {
  if (coupons.total === 0) {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-text">{COUPON_HISTORY_TITLE}</h3>
        <StatusMessage
          variant="empty"
          title={COUPON_HISTORY_EMPTY_TITLE}
          message={couponHistoryEmptyMessage(isOwnProfile, isSystemProfile)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-text">{COUPON_HISTORY_TITLE}</h3>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-muted text-left text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Data</th>
              <th className="px-3 py-2 font-medium">Nogi</th>
              <th className="px-3 py-2 text-right font-medium">Kurs</th>
              <th className="px-3 py-2 text-right font-medium">Stawka</th>
              <th className="px-3 py-2 text-right font-medium">Profit</th>
              <th className="px-3 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {coupons.items.map((coupon) => (
              <CouponHistoryRow
                key={coupon.id}
                coupon={coupon}
                currency={currency}
              />
            ))}
          </tbody>
        </table>
      </div>
      <PaginationBar
        basePath={profilePath}
        currentPage={coupons.page}
        totalCount={coupons.total}
        pageSize={coupons.page_size}
        searchParams={searchParams}
      />
    </div>
  );
}

interface CouponHistoryRowProps {
  coupon: CouponSummary;
  currency: CurrencyCode;
}

function CouponHistoryRow({ coupon, currency }: CouponHistoryRowProps) {
  const created = coupon.created_at
    ? formatMatchDateTime(coupon.created_at)
    : "—";
  const statusLabel = couponHistoryStatusLabel(
    coupon.settled,
    coupon.outcome,
    coupon.legs,
  );
  return (
    <tr className="border-t border-border align-top text-text">
      <td className="px-3 py-2 text-muted">{created}</td>
      <td className="px-3 py-2">
        <ul className="space-y-1">
          {coupon.legs.map((leg) => (
            <HistoryLegLine key={leg.id} leg={leg} />
          ))}
        </ul>
      </td>
      <td className="px-3 py-2 text-right">
        {formatCouponCombinedOdds(coupon)}
      </td>
      <td className="px-3 py-2 text-right">
        {formatTipsterAmount(coupon.stake_amount, currency)}
      </td>
      <td
        className={`px-3 py-2 text-right ${signedAmountClassName(coupon.profit)}`}
      >
        {formatTipsterProfit(coupon.profit, currency)}
      </td>
      <td
        className={`px-3 py-2 ${couponStatusClassName(
          coupon.settled,
          coupon.outcome,
          coupon.legs,
        )}`}
      >
        {statusLabel}
      </td>
    </tr>
  );
}

function HistoryLegLine({ leg }: { leg: CouponLegSummary }) {
  return (
    <li>
      <Link
        href={`/matches/${leg.match_id}`}
        className="transition hover:text-accent-text-hover"
      >
        {historyMatchLabel(leg)}
      </Link>
      {isCombinedLeg(leg.event_ids) ? " · Combined" : null}
      {`: ${historyEventLabel(leg)} · ${formatOdds(leg.odds)} · `}
      <span className={legOutcomeClassName(leg.outcome)}>
        {legOutcomeLabel(leg.outcome)}
      </span>
    </li>
  );
}

function couponHistoryEmptyMessage(
  isOwnProfile: boolean,
  isSystemProfile: boolean,
): string {
  if (isOwnProfile) {
    return COUPON_HISTORY_EMPTY_MESSAGE;
  }
  if (isSystemProfile) {
    return COUPON_HISTORY_SYSTEM_EMPTY_MESSAGE;
  }
  return COUPON_HISTORY_PUBLIC_EMPTY_MESSAGE;
}
