import { classifyExactSubjectPick } from "@/lib/typerLmLongTermExact";

const YES_LABEL = "TAK";
const NO_LABEL = "NIE";
const SELECTED_BUTTON_CLASS_NAME = "border-accent bg-accent text-on-accent";
const IDLE_BUTTON_CLASS_NAME =
  "border-border bg-surface text-text hover:border-accent/40 " +
  "hover:bg-surface-muted";
const BASE_BUTTON_CLASS_NAME =
  "rounded-lg border px-3 py-2 text-center text-sm font-semibold " +
  "transition disabled:cursor-not-allowed disabled:opacity-60";

interface TyperLmLongTermYesNoPickProps {
  value: boolean | null;
  isLocked: boolean;
  resultIsTextCorrect: boolean | null;
  onChange: (value: boolean) => void;
}

export function TyperLmLongTermYesNoPick({
  value,
  isLocked,
  resultIsTextCorrect,
  onChange,
}: TyperLmLongTermYesNoPickProps) {
  return (
    <div className="space-y-3">
      <div
        className="grid grid-cols-2 gap-2"
        role="group"
        aria-label="TAK albo NIE"
      >
        <YesNoOptionButton
          option
          label={YES_LABEL}
          value={value}
          isLocked={isLocked}
          resultIsTextCorrect={resultIsTextCorrect}
          onChange={onChange}
        />
        <YesNoOptionButton
          option={false}
          label={NO_LABEL}
          value={value}
          isLocked={isLocked}
          resultIsTextCorrect={resultIsTextCorrect}
          onChange={onChange}
        />
      </div>
      {resultIsTextCorrect == null ? null : (
        <p className="text-sm text-muted">
          Oficjalny wynik: {resultIsTextCorrect ? YES_LABEL : NO_LABEL}
        </p>
      )}
    </div>
  );
}

function YesNoOptionButton({
  option,
  label,
  value,
  isLocked,
  resultIsTextCorrect,
  onChange,
}: {
  option: boolean;
  label: string;
  value: boolean | null;
  isLocked: boolean;
  resultIsTextCorrect: boolean | null;
  onChange: (value: boolean) => void;
}) {
  const isSelected = value === option;
  const status =
    !isSelected || resultIsTextCorrect == null
      ? "pending"
      : classifyExactSubjectPick(option, [resultIsTextCorrect]);

  return (
    <button
      type="button"
      disabled={isLocked}
      aria-pressed={isSelected}
      aria-label={label}
      onClick={() => onChange(option)}
      className={`${BASE_BUTTON_CLASS_NAME} ${optionToneClass(isSelected, status)}`}
    >
      {label}
      {status === "pending" ? null : (
        <span className="ml-2 text-xs font-medium">
          {status === "hit" ? "trafienie" : "pudło"}
        </span>
      )}
    </button>
  );
}

function optionToneClass(
  isSelected: boolean,
  status: "pending" | "hit" | "miss",
): string {
  if (status === "hit") {
    return "border-success-border bg-success-bg text-success-text";
  }
  if (status === "miss") {
    return "border-danger-border bg-danger-bg text-danger-text";
  }
  return isSelected ? SELECTED_BUTTON_CLASS_NAME : IDLE_BUTTON_CLASS_NAME;
}
