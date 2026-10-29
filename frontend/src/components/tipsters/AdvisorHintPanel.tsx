"use client";

import { useEffect, useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import {
  APPLY_STAKE_ADVICE_LABEL,
  ASK_STAKE_ADVICE_LABEL,
  DEFAULT_STAKE_CONFIDENCE,
  STAKE_ADVICE_CONFIDENCE_LABEL,
  STAKE_ADVICE_DEBOUNCE_MS,
  STAKE_ADVICE_EMPTY_LEGS_HINT,
  STAKE_ADVICE_LOADING_LABEL,
  STAKE_ADVICE_NO_AGENT_LABEL,
  buildAdviseStakeRequest,
  formatAppliedAdviceStake,
  formatStakeAdviceProbability,
  formatStakeAdviceUnits,
  formatTipsterAmount,
  stakeAdviceAgentLines,
  stakeAdviceAssumptions,
  stakeAdviceErrorMessage,
  stakeAdviceReasonLabel,
  stakeAdviceRequestOrNull,
  type DraftCouponLeg,
} from "@/components/tipsters/tipsterModel";
import { adviseMyStake } from "@/lib/apiClient";
import type {
  AdviseStakeResponse,
  CatalogEvent,
  CatalogMatch,
  LegAdvice,
} from "@/types/api";

const ADVICE_ERROR_TITLE = "Nie udało się policzyć rady";
const AGENT_PLAYED_LABEL = "Agent grał";
const BLEND_PROBABILITY_LABEL = "Łączne prawdopodobieństwo";
const RECALCULATING_LABEL = "Przeliczanie…";
const SUGGESTED_STAKE_LABEL = "Sugerowana stawka";
const SUGGESTED_UNITS_LABEL = "Jednostki";

const APPLY_ADVICE_BUTTON_CLASS_NAME =
  "rounded-md border border-border px-4 py-2 text-sm font-medium text-text " +
  "transition hover:bg-surface-raised disabled:cursor-not-allowed " +
  "disabled:opacity-60";

interface AdvisorHintPanelProps {
  legs: DraftCouponLeg[];
  matches: CatalogMatch[];
  events: CatalogEvent[];
  disabled: boolean;
  onApply: (stakeRaw: string) => void;
}

interface StakeAdviceView {
  enabled: boolean;
  confidence: number;
  advice: AdviseStakeResponse | null;
  error: string | null;
  isLoading: boolean;
  setEnabled: (enabled: boolean) => void;
  setConfidence: (confidence: number) => void;
}

export function AdvisorHintPanel({
  legs,
  matches,
  events,
  disabled,
  onApply,
}: AdvisorHintPanelProps) {
  const advice = useStakeAdvice(legs);

  return (
    <div className="space-y-3">
      <AdviceOptIn
        enabled={advice.enabled}
        disabled={disabled}
        onEnabledChange={advice.setEnabled}
      />
      {advice.enabled ? (
        <AdviceBody
          advice={advice}
          legs={legs}
          matches={matches}
          events={events}
          disabled={disabled}
          onApply={onApply}
        />
      ) : null}
    </div>
  );
}

function useStakeAdvice(legs: DraftCouponLeg[]): StakeAdviceView {
  const [enabled, setEnabled] = useState(false);
  const [confidence, setConfidence] = useState(DEFAULT_STAKE_CONFIDENCE);
  const [advice, setAdvice] = useState<AdviseStakeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const request = stakeAdviceRequestOrNull(enabled, legs, confidence);
    // Brak body (checkbox off albo niekompletne zdarzenia) nie odpala POST.
    if (request === null) {
      setAdvice(null);
      setError(null);
      setIsLoading(false);
      return;
    }
    let ignore = false;
    setIsLoading(true);
    setError(null);
    const timer = window.setTimeout(() => {
      void adviseMyStake(request)
        .then((response) => {
          if (ignore) {
            return;
          }
          setAdvice(response);
        })
        .catch((cause: unknown) => {
          if (ignore) {
            return;
          }
          setAdvice(null);
          setError(stakeAdviceErrorMessage(cause));
        })
        .finally(() => {
          if (!ignore) {
            setIsLoading(false);
          }
        });
    }, STAKE_ADVICE_DEBOUNCE_MS);
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [confidence, enabled, legs]);

  return {
    enabled,
    setEnabled,
    confidence,
    setConfidence,
    advice,
    error,
    isLoading,
  };
}

function AdviceOptIn({
  enabled,
  disabled,
  onEnabledChange,
}: {
  enabled: boolean;
  disabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-2 text-sm text-text">
        <input
          type="checkbox"
          checked={enabled}
          disabled={disabled}
          onChange={(event) => onEnabledChange(event.target.checked)}
          className="rounded border-border bg-surface-raised accent-accent"
        />
        {ASK_STAKE_ADVICE_LABEL}
      </label>
    </div>
  );
}

function AdviceBody({
  advice,
  legs,
  matches,
  events,
  disabled,
  onApply,
}: {
  advice: StakeAdviceView;
  legs: DraftCouponLeg[];
  matches: CatalogMatch[];
  events: CatalogEvent[];
  disabled: boolean;
  onApply: (stakeRaw: string) => void;
}) {
  const hint = adviceDraftHint(legs, advice.confidence);
  const loadingLabel = advice.advice
    ? RECALCULATING_LABEL
    : STAKE_ADVICE_LOADING_LABEL;

  return (
    <div className="space-y-3">
      <ConfidenceSlider
        confidence={advice.confidence}
        disabled={disabled}
        onChange={advice.setConfidence}
      />
      <AssumptionList notes={stakeAdviceAssumptions(legs)} />
      {hint ? <p className="text-sm text-muted">{hint}</p> : null}
      {advice.error ? (
        <StatusMessage
          variant="error"
          title={ADVICE_ERROR_TITLE}
          message={advice.error}
        />
      ) : null}
      {advice.isLoading ? (
        <p className="text-sm text-muted">{loadingLabel}</p>
      ) : null}
      {advice.advice && !advice.error ? (
        <AdviceResult
          response={advice.advice}
          matches={matches}
          events={events}
          applyDisabled={disabled || advice.isLoading}
          onApply={onApply}
        />
      ) : null}
    </div>
  );
}

function ConfidenceSlider({
  confidence,
  disabled,
  onChange,
}: {
  confidence: number;
  disabled: boolean;
  onChange: (confidence: number) => void;
}) {
  return (
    <label className="block space-y-2 text-sm text-muted">
      <span className="flex items-center justify-between gap-3">
        <span>{STAKE_ADVICE_CONFIDENCE_LABEL}</span>
        <span className="font-semibold text-text">{confidence}</span>
      </span>
      <input
        type="range"
        min={0}
        max={100}
        step={1}
        value={confidence}
        disabled={disabled}
        onChange={(event) => {
          const value = Number(event.target.value);
          if (Number.isInteger(value)) {
            onChange(value);
          }
        }}
        className="w-full accent-accent"
      />
    </label>
  );
}

function AssumptionList({ notes }: { notes: string[] }) {
  if (notes.length === 0) {
    return null;
  }
  return (
    <ul className="space-y-1 text-xs text-muted">
      {notes.map((note) => (
        <li key={note}>{note}</li>
      ))}
    </ul>
  );
}

function adviceDraftHint(
  legs: DraftCouponLeg[],
  confidence: number,
): string | null {
  const request = buildAdviseStakeRequest(legs, confidence);
  if (!("error" in request)) {
    return null;
  }
  if (legs.length === 0) {
    return STAKE_ADVICE_EMPTY_LEGS_HINT;
  }
  return request.error;
}

function AdviceResult({
  response,
  matches,
  events,
  applyDisabled,
  onApply,
}: {
  response: AdviseStakeResponse;
  matches: CatalogMatch[];
  events: CatalogEvent[];
  applyDisabled: boolean;
  onApply: (stakeRaw: string) => void;
}) {
  const advice = response.advice;
  const canApply = advice.suggested_stake > 0 && !advice.no_bet;

  return (
    <div className="space-y-3 rounded-lg border border-border bg-surface-muted px-3 py-3 text-sm">
      <p className="text-text">{stakeAdviceReasonLabel(advice.reason)}</p>
      <AdviceFigures response={response} />
      <AgentLikedList legs={advice.legs} matches={matches} events={events} />
      <button
        type="button"
        disabled={applyDisabled || !canApply}
        onClick={() => onApply(formatAppliedAdviceStake(advice.suggested_stake))}
        className={APPLY_ADVICE_BUTTON_CLASS_NAME}
      >
        {APPLY_STAKE_ADVICE_LABEL}
      </button>
    </div>
  );
}

function AdviceFigures({ response }: { response: AdviseStakeResponse }) {
  const advice = response.advice;
  return (
    <dl className="grid gap-3 sm:grid-cols-3">
      <AdviceFigure
        label={SUGGESTED_STAKE_LABEL}
        value={formatTipsterAmount(advice.suggested_stake, response.currency)}
      />
      <AdviceFigure
        label={SUGGESTED_UNITS_LABEL}
        value={formatStakeAdviceUnits(advice.suggested_units)}
      />
      <AdviceFigure
        label={BLEND_PROBABILITY_LABEL}
        value={formatStakeAdviceProbability(advice.p_blend)}
      />
    </dl>
  );
}

function AdviceFigure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium text-text">{value}</dd>
    </div>
  );
}

function AgentLikedList({
  legs,
  matches,
  events,
}: {
  legs: LegAdvice[];
  matches: CatalogMatch[];
  events: CatalogEvent[];
}) {
  const lines = stakeAdviceAgentLines(legs, matches, events);
  if (lines.length === 0) {
    return <p className="text-muted">{STAKE_ADVICE_NO_AGENT_LABEL}</p>;
  }
  return (
    <div className="space-y-1">
      <p className="text-muted">{AGENT_PLAYED_LABEL}</p>
      <ul className="list-disc space-y-1 pl-5 text-text">
        {lines.map((line) => (
          <li key={line.key}>{line.label}</li>
        ))}
      </ul>
    </div>
  );
}
