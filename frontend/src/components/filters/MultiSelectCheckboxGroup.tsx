"use client";

interface CheckboxOption {
  id: number;
  label: string;
}

export interface CheckboxSection {
  title: string;
  options: CheckboxOption[];
}

interface MultiSelectCheckboxGroupProps {
  label: string;
  name: string;
  options?: CheckboxOption[];
  sections?: CheckboxSection[];
  selectedIds: number[];
  onChange: (selectedIds: number[]) => void;
  maxHeightClassName?: string;
  showClearAll?: boolean;
}

export function MultiSelectCheckboxGroup({
  label,
  name,
  options,
  sections,
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

  const resolvedSections = resolveCheckboxSections(sections, options);
  const hasOptions = resolvedSections.some(
    (section) => section.options.length > 0,
  );
  const isClearDisabled = selectedIds.length === 0;

  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-text">{label}</legend>
      <div
        className={`overflow-y-auto rounded-lg border border-border bg-surface-muted p-3 ${maxHeightClassName}`}
      >
        {hasOptions ? (
          <div className="space-y-4">
            {resolvedSections.map((section, index) => (
              <CheckboxSectionList
                key={section.title || `section-${index}`}
                name={name}
                section={section}
                selectedIds={selectedIds}
                onToggle={toggleOption}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">Brak dostępnych opcji.</p>
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

function resolveCheckboxSections(
  sections: CheckboxSection[] | undefined,
  options: CheckboxOption[] | undefined,
): CheckboxSection[] {
  if (sections && sections.length > 0) {
    return sections.filter((section) => section.options.length > 0);
  }
  return [{ title: "", options: options ?? [] }];
}

interface CheckboxSectionListProps {
  name: string;
  section: CheckboxSection;
  selectedIds: number[];
  onToggle: (id: number) => void;
}

function CheckboxSectionList({
  name,
  section,
  selectedIds,
  onToggle,
}: CheckboxSectionListProps) {
  return (
    <div className="space-y-2">
      {section.title ? (
        <p className="text-xs font-semibold text-text">{section.title}</p>
      ) : null}
      {section.options.map((option) => {
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
              onChange={() => onToggle(option.id)}
              className="rounded border-border bg-surface-raised accent-accent"
            />
            <span>{option.label}</span>
          </label>
        );
      })}
    </div>
  );
}
