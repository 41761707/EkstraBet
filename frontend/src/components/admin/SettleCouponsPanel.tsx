"use client";

import { useState } from "react";

import {
  SETTLE_COUPONS_BUSY,
  SETTLE_COUPONS_BUTTON,
  SETTLE_COUPONS_DESCRIPTION,
  SETTLE_COUPONS_ERROR_TITLE,
  SETTLE_COUPONS_TITLE,
  formatSettlementSummary,
  mapSettleCouponsError,
} from "@/components/admin/settleCouponsModel";
import { StatusMessage } from "@/components/StatusMessage";
import { settleOpenCoupons } from "@/lib/apiClient";

export function SettleCouponsPanel() {
  const [isBusy, setIsBusy] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function onSettle() {
    setIsBusy(true);
    setErrorMessage(null);
    try {
      const result = await settleOpenCoupons();
      setSummary(formatSettlementSummary(result));
    } catch (error) {
      setSummary(null);
      setErrorMessage(mapSettleCouponsError(error));
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="space-y-3 rounded-xl border border-border bg-surface p-4">
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-text">
          {SETTLE_COUPONS_TITLE}
        </h2>
        <p className="text-sm text-muted">{SETTLE_COUPONS_DESCRIPTION}</p>
      </header>
      <button
        type="button"
        className={
          "rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent " +
          "transition hover:bg-accent-hover disabled:cursor-not-allowed " +
          "disabled:opacity-50"
        }
        disabled={isBusy}
        onClick={() => {
          void onSettle();
        }}
      >
        {isBusy ? SETTLE_COUPONS_BUSY : SETTLE_COUPONS_BUTTON}
      </button>
      {summary ? (
        <p className="text-sm text-success-text" role="status">
          {summary}
        </p>
      ) : null}
      {errorMessage ? (
        <StatusMessage
          variant="error"
          title={SETTLE_COUPONS_ERROR_TITLE}
          message={errorMessage}
        />
      ) : null}
    </section>
  );
}
