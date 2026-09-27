"use client";

import { FIELD_CLASS_NAME } from "@/components/inputStyles";
import {
  formatTipsterAmount,
  parsePositiveAmount,
  previewCouponCombinedOdds,
  previewPotentialWin,
  previewStakeMoney,
  type DraftCouponLeg,
} from "@/components/tipsters/tipsterModel";
import { formatOdds } from "@/lib/format";
import type { CurrencyCode, StakeInputMode } from "@/types/api";

export const COUPON_ODDS_PREVIEW_LABEL = "Kurs kuponu";
export const POTENTIAL_WIN_LABEL = "Potencjalna wygrana";

interface CouponStakeFieldsProps {
  legs: DraftCouponLeg[];
  mode: StakeInputMode;
  stakeRaw: string;
  unitSize: number;
  currency: CurrencyCode;
  applyTax?: boolean;
  isSubmitting: boolean;
  onModeChange: (mode: StakeInputMode) => void;
  onStakeChange: (value: string) => void;
}

export function CouponStakeFields({
  legs,
  mode,
  stakeRaw,
  unitSize,
  currency,
  applyTax = false,
  isSubmitting,
  onModeChange,
  onStakeChange,
}: CouponStakeFieldsProps) {
  const preview = parseStakePreview(mode, stakeRaw, unitSize);

  return (
    <>
      <DraftCouponPreview
        legs={legs}
        mode={mode}
        stakeRaw={stakeRaw}
        unitSize={unitSize}
        currency={currency}
        applyTax={applyTax}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <fieldset className="space-y-2">
          <legend className="text-sm text-muted">Tryb stawki</legend>
          <label className="flex items-center gap-2 text-sm text-text">
            <input
              type="radio"
              name="stake-mode"
              checked={mode === "money"}
              disabled={isSubmitting}
              onChange={() => onModeChange("money")}
              className="accent-accent"
            />
            Kwota ({currency})
          </label>
          <label className="flex items-center gap-2 text-sm text-text">
            <input
              type="radio"
              name="stake-mode"
              checked={mode === "units"}
              disabled={isSubmitting}
              onChange={() => onModeChange("units")}
              className="accent-accent"
            />
            Jednostki
          </label>
        </fieldset>
        <label className="flex flex-col gap-1.5 text-sm text-muted">
          {mode === "money" ? `Stawka (${currency})` : "Liczba jednostek"}
          <input
            type="text"
            inputMode="decimal"
            value={stakeRaw}
            disabled={isSubmitting}
            onChange={(event) => onStakeChange(event.target.value)}
            className={FIELD_CLASS_NAME}
          />
          {mode === "units" && preview !== null ? (
            <span>Podgląd: {formatTipsterAmount(preview, currency)}</span>
          ) : null}
        </label>
      </div>
    </>
  );
}

function DraftCouponPreview({
  legs,
  mode,
  stakeRaw,
  unitSize,
  currency,
  applyTax,
}: {
  legs: DraftCouponLeg[];
  mode: StakeInputMode;
  stakeRaw: string;
  unitSize: number;
  currency: CurrencyCode;
  applyTax: boolean;
}) {
  if (legs.length === 0) {
    return null;
  }
  const combinedOdds = previewCouponCombinedOdds(legs);
  const stake = parseStakePreview(mode, stakeRaw, unitSize);
  const potentialWin = previewPotentialWin(stake, combinedOdds, applyTax);
  return (
    <dl className="grid gap-3 text-sm sm:grid-cols-2">
      <div className="rounded-lg border border-border bg-surface-muted px-3 py-2">
        <dt className="text-muted">{COUPON_ODDS_PREVIEW_LABEL}</dt>
        <dd className="font-medium text-text">
          {combinedOdds === null ? "—" : formatOdds(combinedOdds)}
        </dd>
      </div>
      <div className="rounded-lg border border-border bg-surface-muted px-3 py-2">
        <dt className="text-muted">{POTENTIAL_WIN_LABEL}</dt>
        <dd className="font-medium text-text">
          {formatTipsterAmount(potentialWin, currency)}
        </dd>
      </div>
    </dl>
  );
}

function parseStakePreview(
  mode: StakeInputMode,
  stakeRaw: string,
  unitSize: number,
): number | null {
  const parsed = parsePositiveAmount(stakeRaw);
  if (parsed === null) {
    return null;
  }
  return previewStakeMoney(
    mode,
    mode === "money" ? parsed : null,
    mode === "units" ? parsed : null,
    unitSize,
  );
}
