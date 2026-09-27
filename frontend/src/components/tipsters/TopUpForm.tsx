"use client";

import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  FIELD_CLASS_NAME,
  SUBMIT_BUTTON_CLASS_NAME,
} from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import { BetsPanel } from "@/components/tipsters/BetsPanel";
import {
  parsePositiveAmount,
  tipsterMutationMessage,
} from "@/components/tipsters/tipsterModel";
import { postMyTopUp } from "@/lib/apiClient";
import type { CurrencyCode } from "@/types/api";

export const TOP_UP_TITLE = "Doładowanie";
export const TOP_UP_HINT =
  "Doładowanie zwiększa kapitał startowy i saldo. Waluta i jednostka zostają bez zmian.";

interface TopUpFormProps {
  currency: CurrencyCode;
}

export function TopUpForm({ currency }: TopUpFormProps) {
  const router = useRouter();
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = parsePositiveAmount(amount);
    if (parsed === null) {
      setError("Kwota doładowania musi być większa od zera.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await postMyTopUp({ amount: parsed });
      setAmount("");
      router.refresh();
    } catch (cause) {
      setError(tipsterMutationMessage(cause));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <BetsPanel title={TOP_UP_TITLE} description={TOP_UP_HINT}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex min-w-0 flex-1 flex-col gap-1.5 text-sm text-muted">
            Kwota ({currency})
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              disabled={isSubmitting}
              onChange={(event) => setAmount(event.target.value)}
              required
              className={FIELD_CLASS_NAME}
            />
          </label>
          <button
            type="submit"
            disabled={isSubmitting}
            className={SUBMIT_BUTTON_CLASS_NAME}
          >
            {isSubmitting ? "Doładowywanie…" : "Doładuj"}
          </button>
        </div>
        {error ? (
          <StatusMessage
            variant="error"
            title="Nie udało się doładować"
            message={error}
          />
        ) : null}
      </form>
    </BetsPanel>
  );
}
