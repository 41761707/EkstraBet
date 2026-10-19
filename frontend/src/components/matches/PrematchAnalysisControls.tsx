import {
  MATCH_H2H_MAX,
  MATCH_H2H_MIN,
  MATCH_OU_LINE_MAX,
  MATCH_OU_LINE_MIN,
  MATCH_OU_LINE_STEP,
} from "@/components/matches/matchChartConfig";

interface OuBounds {
  min: number;
  max: number;
  step: number;
}

interface LookbackBounds {
  min: number;
  max: number;
}

interface PrematchAnalysisControlsProps {
  h2hLimit: number;
  ouLine: number;
  lookback: number;
  effectiveLookback: number;
  isHockey: boolean;
  ouBounds: OuBounds | null;
  lookbackBounds: LookbackBounds;
  onH2hLimitChange: (value: number) => void;
  onOuLineChange: (value: number) => void;
  onLookbackChange: (value: number) => void;
}

function RangeControl({
  label,
  valueLabel,
  min,
  max,
  step,
  value,
  disabled = false,
  hint,
  onChange,
}: {
  label: string;
  valueLabel: string;
  min: number;
  max: number;
  step: number;
  value: number;
  disabled?: boolean;
  hint?: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="space-y-2 rounded-lg border border-border bg-surface p-4 text-sm text-muted">
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium text-text">{label}</span>
        <span className="font-semibold text-text">{valueLabel}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-accent"
        disabled={disabled}
      />
      {hint ? <p className="text-xs text-subtle">{hint}</p> : null}
    </label>
  );
}

export function PrematchAnalysisControls({
  h2hLimit,
  ouLine,
  lookback,
  effectiveLookback,
  isHockey,
  ouBounds,
  lookbackBounds,
  onH2hLimitChange,
  onOuLineChange,
  onLookbackChange,
}: PrematchAnalysisControlsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <RangeControl
        label="Liczba prezentowanych spotkań H2H"
        valueLabel={String(h2hLimit)}
        min={MATCH_H2H_MIN}
        max={MATCH_H2H_MAX}
        step={1}
        value={h2hLimit}
        onChange={onH2hLimitChange}
      />
      <RangeControl
        label="Linia Over/Under"
        valueLabel={ouLine.toFixed(1)}
        min={isHockey && ouBounds ? ouBounds.min : MATCH_OU_LINE_MIN}
        max={isHockey && ouBounds ? ouBounds.max : MATCH_OU_LINE_MAX}
        step={isHockey && ouBounds ? ouBounds.step : MATCH_OU_LINE_STEP}
        value={ouLine}
        onChange={onOuLineChange}
      />
      <RangeControl
        label="Liczba analizowanych spotkań wstecz"
        valueLabel={String(effectiveLookback)}
        min={lookbackBounds.min}
        max={lookbackBounds.max}
        step={1}
        value={lookback}
        disabled={lookbackBounds.max <= 0}
        hint="Statystyki i wykresy z N ostatnich meczów przed datą tego spotkania."
        onChange={onLookbackChange}
      />
    </div>
  );
}
