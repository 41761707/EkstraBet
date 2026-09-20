"use client";

import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  FIELD_CLASS_NAME,
  SUBMIT_BUTTON_CLASS_NAME,
} from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import {
  isCurrencyCode,
  parsePositiveAmount,
  TIPSTER_CURRENCIES,
  tipsterMutationMessage,
} from "@/components/tipsters/tipsterModel";
import { putMyBankroll } from "@/lib/apiClient";
import type {
  BankrollConfigureRequest,
  BankrollSettings,
  CurrencyCode,
} from "@/types/api";

export const BANKROLL_SETUP_TITLE = "Ustawienia bankrolla";
export const BANKROLL_ONBOARDING_TITLE = "Konfiguracja bankrolla";

interface BankrollSetupFormProps {
  existing: BankrollSettings | null;
  hasCoupons: boolean;
}

export function BankrollSetupForm({
  existing,
  hasCoupons,
}: BankrollSetupFormProps) {
  const router = useRouter();
  const [currency, setCurrency] = useState<CurrencyCode>(
    existing?.currency ?? "PLN",
  );
  const [initialCapital, setInitialCapital] = useState("");
  const [unitSize, setUnitSize] = useState(
    existing ? existing.unit_size.toFixed(2) : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isOnboarding = existing === null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const request = buildBankrollRequest(
      existing,
      currency,
      initialCapital,
      unitSize,
    );
    if ("error" in request) {
      setError(request.error);
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await putMyBankroll({
        currency: request.currency,
        initial_capital: request.initial_capital,
        unit_size: request.unit_size,
      });
      router.refresh();
    } catch (cause) {
      setError(tipsterMutationMessage(cause));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-sm font-semibold text-text">
        {isOnboarding ? BANKROLL_ONBOARDING_TITLE : BANKROLL_SETUP_TITLE}
      </h3>
      <BankrollFields
        currency={currency}
        initialCapital={
          existing ? existing.initial_capital.toFixed(2) : initialCapital
        }
        unitSize={unitSize}
        isOnboarding={isOnboarding}
        hasCoupons={hasCoupons}
        isSubmitting={isSubmitting}
        onCurrencyChange={setCurrency}
        onInitialCapitalChange={setInitialCapital}
        onUnitSizeChange={setUnitSize}
      />
      {error ? (
        <StatusMessage variant="error" title="Nie udało się zapisać" message={error} />
      ) : null}
      <button type="submit" disabled={isSubmitting} className={SUBMIT_BUTTON_CLASS_NAME}>
        {isSubmitting ? "Zapisywanie…" : isOnboarding ? "Utwórz bankroll" : "Zapisz ustawienia"}
      </button>
    </form>
  );
}

interface BankrollFieldsProps {
  currency: CurrencyCode;
  initialCapital: string;
  unitSize: string;
  isOnboarding: boolean;
  hasCoupons: boolean;
  isSubmitting: boolean;
  onCurrencyChange: (value: CurrencyCode) => void;
  onInitialCapitalChange: (value: string) => void;
  onUnitSizeChange: (value: string) => void;
}

function BankrollFields({
  currency,
  initialCapital,
  unitSize,
  isOnboarding,
  hasCoupons,
  isSubmitting,
  onCurrencyChange,
  onInitialCapitalChange,
  onUnitSizeChange,
}: BankrollFieldsProps) {
  const currencyLocked = !isOnboarding && hasCoupons;
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Waluta
        <select
          value={currency}
          disabled={isSubmitting || currencyLocked}
          onChange={(event) => {
            if (isCurrencyCode(event.target.value)) {
              onCurrencyChange(event.target.value);
            }
          }}
          className={FIELD_CLASS_NAME}
        >
          {TIPSTER_CURRENCIES.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Kapitał startowy
        <input
          type="text"
          inputMode="decimal"
          value={initialCapital}
          disabled={isSubmitting || !isOnboarding}
          onChange={(event) => onInitialCapitalChange(event.target.value)}
          required={isOnboarding}
          className={FIELD_CLASS_NAME}
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Wielkość unita
        <input
          type="text"
          inputMode="decimal"
          value={unitSize}
          disabled={isSubmitting}
          onChange={(event) => onUnitSizeChange(event.target.value)}
          required
          className={FIELD_CLASS_NAME}
        />
      </label>
    </div>
  );
}

function buildBankrollRequest(
  existing: BankrollSettings | null,
  currency: CurrencyCode,
  initialCapitalRaw: string,
  unitSizeRaw: string,
): BankrollConfigureRequest | { error: string } {
  const unitSize = parsePositiveAmount(unitSizeRaw);
  const initialCapital = existing
    ? existing.initial_capital
    : parsePositiveAmount(initialCapitalRaw);
  if (initialCapital === null || unitSize === null) {
    return {
      error:
        "Kapitał i unit muszą być większe od zera po zaokrągleniu do 0.01.",
    };
  }
  return { currency, initial_capital: initialCapital, unit_size: unitSize };
}
