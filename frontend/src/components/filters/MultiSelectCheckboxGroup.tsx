"use client";

interface MultiSelectCheckboxGroupProps {
  label: string;
  name: string;
  options: { id: number; label: string }[];
  selectedIds: number[];
  onChange: (selectedIds: number[]) => void;
  maxHeightClassName?: string;
}

export function MultiSelectCheckboxGroup({
  label,
  name,
  options,
  selectedIds,
  onChange,
  maxHeightClassName = "max-h-40",
}: MultiSelectCheckboxGroupProps) {
  function toggleOption(id: number) {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((item) => item !== id));
      return;
    }
    onChange([...selectedIds, id]);
  }

  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-slate-200">{label}</legend>
      <div
        className={`overflow-y-auto rounded-lg border border-slate-700/80 bg-slate-900/50 p-3 ${maxHeightClassName}`}
      >
        {options.length === 0 ? (
          <p className="text-sm text-slate-400">Brak dostępnych opcji.</p>
        ) : (
          <div className="space-y-2">
            {options.map((option) => {
              const inputId = `${name}-${option.id}`;
              return (
                <label
                  key={option.id}
                  htmlFor={inputId}
                  className="flex cursor-pointer items-center gap-2 text-sm text-slate-300"
                >
                  <input
                    id={inputId}
                    type="checkbox"
                    checked={selectedIds.includes(option.id)}
                    onChange={() => toggleOption(option.id)}
                    className="rounded border-slate-600 bg-slate-800 text-sky-500"
                  />
                  <span>{option.label}</span>
                </label>
              );
            })}
          </div>
        )}
      </div>
    </fieldset>
  );
}
