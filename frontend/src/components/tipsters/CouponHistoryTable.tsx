import Link from "next/link";

import { PaginationBar } from "@/components/PaginationBar";
import { StatusMessage } from "@/components/StatusMessage";
import { BetsPanel } from "@/components/tipsters/BetsPanel";
import {
  COMBINED_SELECTION_LABEL,
  couponHistoryStatusLabel,
  couponShapeLabel,
  couponStatusPillClassName,
  formatCouponCombinedOdds,
  formatTipsterAmount,
  formatTipsterProfit,
  historyEventLabel,
  historyMatchLine,
  isCombinedLeg,
  legOutcomeDotClassName,
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
      <BetsPanel title={COUPON_HISTORY_TITLE}>
        <StatusMessage
          variant="empty"
          title={COUPON_HISTORY_EMPTY_TITLE}
          message={couponHistoryEmptyMessage(isOwnProfile, isSystemProfile)}
        />
      </BetsPanel>
    );
  }

  return (
    <BetsPanel title={COUPON_HISTORY_TITLE}>
      <div className="space-y-3">
        {coupons.items.map((coupon) => (
          <CouponHistoryCard
            key={coupon.id}
            coupon={coupon}
            currency={currency}
          />
        ))}
      </div>
      <PaginationBar
        basePath={profilePath}
        currentPage={coupons.page}
        totalCount={coupons.total}
        pageSize={coupons.page_size}
        searchParams={searchParams}
      />
    </BetsPanel>
  );
}

interface CouponHistoryCardProps {
  coupon: CouponSummary;
  currency: CurrencyCode;
}

function CouponHistoryCard({ coupon, currency }: CouponHistoryCardProps) {
  const created = coupon.created_at
    ? formatMatchDateTime(coupon.created_at)
    : "—";
  const statusLabel = couponHistoryStatusLabel(
    coupon.settled,
    coupon.outcome,
    coupon.legs,
  );
  return (
    <article className="rounded-xl border border-border bg-surface-raised p-4">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-text">
              {couponShapeLabel(coupon.legs.length)}
            </h3>
            <time className="text-xs text-muted">{created}</time>
            <span
              className={
                "rounded-full border px-2 py-0.5 text-xs font-medium " +
                couponStatusPillClassName(
                  coupon.settled,
                  coupon.outcome,
                  coupon.legs,
                )
              }
            >
              {statusLabel}
            </span>
          </div>
          <CouponStakeLine coupon={coupon} currency={currency} />
        </div>
        <div className="shrink-0 text-right">
          <p className="text-xl font-semibold tabular-nums text-text">
            {formatCouponCombinedOdds(coupon)}
          </p>
          <p className="text-xs text-muted">Kurs</p>
        </div>
      </header>
      <ul className="mt-3 divide-y divide-border border-t border-border">
        {coupon.legs.map((leg) => (
          <HistoryLeg key={leg.id} leg={leg} />
        ))}
      </ul>
    </article>
  );
}

function CouponStakeLine({
  coupon,
  currency,
}: CouponHistoryCardProps) {
  return (
    <p className="mt-2 text-sm text-muted">
      Stawka {formatTipsterAmount(coupon.stake_amount, currency)}
      {coupon.profit === null ? null : (
        <>
          <span aria-hidden="true"> · </span>
          <span className={signedAmountClassName(coupon.profit)}>
            {formatTipsterProfit(coupon.profit, currency)}
          </span>
        </>
      )}
    </p>
  );
}

function HistoryLeg({ leg }: { leg: CouponLegSummary }) {
  const outcomeLabel = legOutcomeLabel(leg.outcome);
  return (
    <li className="flex items-start gap-3 py-3">
      <span
        className={
          "mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full " +
          legOutcomeDotClassName(leg.outcome)
        }
        title={outcomeLabel}
        aria-label={outcomeLabel}
      />
      <Link
        href={`/matches/${leg.match_id}`}
        className="group min-w-0 flex-1"
      >
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-text group-hover:text-accent-text-hover">
            {historyEventLabel(leg)}
          </span>
          {isCombinedLeg(leg.event_ids) ? (
            <span
              className={
                "rounded-md bg-accent-soft px-1.5 py-0.5 text-xs " +
                "font-medium text-accent-text"
              }
            >
              {COMBINED_SELECTION_LABEL}
            </span>
          ) : null}
        </span>
        <span
          className={
            "mt-0.5 block text-sm text-muted " +
            "group-hover:text-accent-text-hover"
          }
        >
          {historyMatchLine(leg)}
        </span>
      </Link>
      <p className="shrink-0 text-sm font-semibold tabular-nums text-text">
        {formatOdds(leg.odds)}
      </p>
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
