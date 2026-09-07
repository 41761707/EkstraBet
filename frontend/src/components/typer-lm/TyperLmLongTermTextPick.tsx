import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import {
  classifyFreeTextPick,
  SUBJECT_TEXT_MAX_LENGTH,
  type ExactSubjectPickStatus,
} from "@/lib/typerLmLongTermExact";

const TEXT_PLACEHOLDER = "Imię i nazwisko";
const CHIP_BASE =
  "inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs";

interface TyperLmLongTermTextPickProps {
  value: string;
  isLocked: boolean;
  resultSubjectTexts: readonly string[];
  onChange: (value: string) => void;
}

export function TyperLmLongTermTextPick({
  value,
  isLocked,
  resultSubjectTexts,
  onChange,
}: TyperLmLongTermTextPickProps) {
  const status =
    resultSubjectTexts.length === 0 || value.trim() === ""
      ? "pending"
      : classifyFreeTextPick(value, resultSubjectTexts);

  return (
    <div className="space-y-3">
      <label className="flex flex-col gap-1 text-sm text-muted">
        {TEXT_PLACEHOLDER}
        <input
          type="text"
          value={value}
          placeholder={TEXT_PLACEHOLDER}
          autoComplete="off"
          maxLength={SUBJECT_TEXT_MAX_LENGTH}
          disabled={isLocked}
          onChange={(event) => onChange(event.target.value)}
          className={`w-full rounded-md ${INPUT_CLASS_NAME} disabled:opacity-60`}
        />
      </label>
      {status === "pending" ? null : (
        <p className={`${CHIP_BASE} ${chipToneClass(status)}`}>
          {value}
          <span className="text-xs">
            {status === "hit" ? "trafienie" : "pudło"}
          </span>
        </p>
      )}
      <OfficialSubjectNames names={resultSubjectTexts} />
    </div>
  );
}

function OfficialSubjectNames({ names }: { names: readonly string[] }) {
  if (names.length === 0) {
    return null;
  }
  return (
    <p className="text-sm text-muted">
      Oficjalny wynik: {names.join(", ")}
    </p>
  );
}

function chipToneClass(status: ExactSubjectPickStatus): string {
  if (status === "hit") {
    return "border-success-border bg-success-bg text-success-text";
  }
  if (status === "miss") {
    return "border-danger-border bg-danger-bg text-danger-text";
  }
  return "border-accent bg-accent-soft text-text";
}
