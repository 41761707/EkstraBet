"use client";

import {
  useEffect,
  useState,
  type Dispatch,
  type FormEvent,
  type SetStateAction,
} from "react";

import { DateInput } from "@/components/filters/DateInput";
import { MultiSelectCheckboxGroup } from "@/components/filters/MultiSelectCheckboxGroup";
import {
  areScopedDateFiltersValid,
  hasScopedModelOptions,
  resetScopedPredictionStatsFilters,
  scopedPredictionStatsFiltersKey,
  type ScopedPredictionStatsFiltersState,
} from "@/components/stats/scopedPredictionStatsModel";
import type { FilterOption } from "@/types/api";

export const INVALID_SCOPED_DATE_RANGE_MESSAGE =
  "Data Od nie może być późniejsza niż data Do.";

const APPLY_BUTTON_CLASS_NAME =
  "rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent " +
  "transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60";

const RESET_BUTTON_CLASS_NAME =
  "rounded-lg border border-border px-4 py-2 text-sm text-text " +
  "transition hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-60";

const TAX_CHECKBOX_CLASS_NAME =
  "rounded border-border bg-surface-muted text-accent-text";

interface ScopedPredictionStatsFiltersProps {
  resultModels: FilterOption[];
  ouModels: FilterOption[];
  bttsModels: FilterOption[];
  values: ScopedPredictionStatsFiltersState;
  onApply: (filters: ScopedPredictionStatsFiltersState) => void;
  isLoading?: boolean;
}

export function ScopedPredictionStatsFilters({
  resultModels,
  ouModels,
  bttsModels,
  values,
  onApply,
  isLoading = false,
}: ScopedPredictionStatsFiltersProps) {
  const [draft, setDraft] = useState(values);
  const areDatesValid = areScopedDateFiltersValid(draft.dateFrom, draft.dateTo);
  const valuesKey = scopedPredictionStatsFiltersKey(values);
  const models = {
    result: resultModels,
    ou: ouModels,
    btts: bttsModels,
  };
  const canReset = !isLoading && hasScopedModelOptions(models);
  const canApply = canReset && areDatesValid;

  useEffect(() => {
    setDraft({
      dateFrom: values.dateFrom,
      dateTo: values.dateTo,
      applyTax: values.applyTax,
      modelResultIds: values.modelResultIds,
      modelOuIds: values.modelOuIds,
      modelBttsIds: values.modelBttsIds,
    });
    // treść filtrów, nie referencja `values` — nowy literał z tymi samymi polami nie kasuje draftu
    // eslint-disable-next-line react-hooks/exhaustive-deps -- patrz komentarz powyżej
  }, [valuesKey]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canApply) {
      return;
    }
    onApply(draft);
  }

  function handleReset() {
    if (!canReset) {
      return;
    }
    const resetState = resetScopedPredictionStatsFilters(models);
    setDraft(resetState);
    onApply(resetState);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <ModelFamilyCheckboxGroups
        resultModels={resultModels}
        ouModels={ouModels}
        bttsModels={bttsModels}
        draft={draft}
        setDraft={setDraft}
      />
      <DateAndTaxFields draft={draft} setDraft={setDraft} />
      {areDatesValid ? null : (
        <p className="text-sm text-danger-text" role="alert">
          {INVALID_SCOPED_DATE_RANGE_MESSAGE}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={!canApply}
          className={APPLY_BUTTON_CLASS_NAME}
        >
          Zastosuj filtry
        </button>
        <button
          type="button"
          disabled={!canReset}
          onClick={handleReset}
          className={RESET_BUTTON_CLASS_NAME}
        >
          Resetuj
        </button>
      </div>
    </form>
  );
}

type DraftSetter = Dispatch<
  SetStateAction<ScopedPredictionStatsFiltersState>
>;

interface DraftFieldsProps {
  draft: ScopedPredictionStatsFiltersState;
  setDraft: DraftSetter;
}

function ModelFamilyCheckboxGroups({
  resultModels,
  ouModels,
  bttsModels,
  draft,
  setDraft,
}: DraftFieldsProps & {
  resultModels: FilterOption[];
  ouModels: FilterOption[];
  bttsModels: FilterOption[];
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <MultiSelectCheckboxGroup
        label="Modele rezultatu"
        name="scoped-result-models"
        options={resultModels}
        selectedIds={draft.modelResultIds}
        onChange={(modelResultIds) =>
          setDraft((current) => ({ ...current, modelResultIds }))
        }
      />
      <MultiSelectCheckboxGroup
        label="Modele OU"
        name="scoped-ou-models"
        options={ouModels}
        selectedIds={draft.modelOuIds}
        onChange={(modelOuIds) =>
          setDraft((current) => ({ ...current, modelOuIds }))
        }
      />
      <MultiSelectCheckboxGroup
        label="Modele BTTS"
        name="scoped-btts-models"
        options={bttsModels}
        selectedIds={draft.modelBttsIds}
        onChange={(modelBttsIds) =>
          setDraft((current) => ({ ...current, modelBttsIds }))
        }
      />
    </div>
  );
}

function DateAndTaxFields({ draft, setDraft }: DraftFieldsProps) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2 text-sm">
          <span className="font-medium text-text">Od</span>
          <DateInput
            value={draft.dateFrom}
            onChange={(dateFrom) =>
              setDraft((current) => ({ ...current, dateFrom }))
            }
            ariaLabel="Od"
          />
        </div>
        <div className="space-y-2 text-sm">
          <span className="font-medium text-text">Do</span>
          <DateInput
            value={draft.dateTo}
            onChange={(dateTo) =>
              setDraft((current) => ({ ...current, dateTo }))
            }
            ariaLabel="Do"
          />
        </div>
      </div>
      <label className="flex items-center gap-2 text-sm text-text">
        <input
          type="checkbox"
          checked={draft.applyTax}
          onChange={(event) =>
            setDraft((current) => ({
              ...current,
              applyTax: event.target.checked,
            }))
          }
          className={TAX_CHECKBOX_CLASS_NAME}
        />
        Uwzględnij podatek 12%
      </label>
    </div>
  );
}
