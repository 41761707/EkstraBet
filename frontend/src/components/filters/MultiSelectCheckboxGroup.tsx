"use client";

interface MultiSelectCheckboxGroupProps {
  label: string;
  name: string;
  options: { id: number; label: string }[];
  selectedIds: number[];
  onChange: (selectedIds: number[]) => void;
  maxHeightClassName?: string;
  showClearAll?: boolean;
}

export function MultiSelectCheckboxGroup({
  label,
  name,
  options,
  selectedIds,
  onChange,
  maxHeightClassName = "max-h-40",
  showClearAll = false,
}: MultiSelectCheckboxGroupProps) {
  function toggleOption(id: number) {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((item) => item !== id));
      return;
    }
    onChange([...selectedIds, id]);
  }

  const isClearDisabled = selectedIds.length === 0;

  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-text">{label}</legend>
      <div
        className={`overflow-y-auto rounded-lg border border-border bg-surface-muted p-3 ${maxHeightClassName}`}
      >
        {options.length === 0 ? (
          <p className="text-sm text-muted">Brak dostępnych opcji.</p>
        ) : (
          <div className="space-y-2">
            {options.map((option) => {
              const inputId = `${name}-${option.id}`;
              return (
                <label
                  key={option.id}
                  htmlFor={inputId}
                  className="flex cursor-pointer items-center gap-2 text-sm text-muted"
                >
                  <input
                    id={inputId}
                    type="checkbox"
                    checked={selectedIds.includes(option.id)}
                    onChange={() => toggleOption(option.id)}
                    className="rounded border-border bg-surface-raised accent-accent"
                  />
                  <span>{option.label}</span>
                </label>
              );
            })}
          </div>
        )}
      </div>
      {showClearAll ? (
        <button
          type="button"
          disabled={isClearDisabled}
          onClick={() => onChange([])}
          className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text transition hover:bg-surface-muted disabled:cursor-not-allowed disabled:border-border disabled:text-subtle disabled:hover:bg-transparent"
        >
          Odznacz wszystkie
        </button>
      ) : null}
    </fieldset>
  );
}
