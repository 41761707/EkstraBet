"use client";

/** Pill switch shared by analytics and the result calendar. */
interface ChoiceTabsProps<T extends string> {
  label: string;
  tabs: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
}

export function ChoiceTabs<T extends string>({
  label,
  tabs,
  value,
  onChange,
}: ChoiceTabsProps<T>) {
  return (
    <div className="flex flex-wrap gap-2" role="tablist" aria-label={label}>
      {tabs.map((tab) => {
        const isActive = tab.id === value;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`rounded-full px-3 py-1.5 text-sm transition ${
              isActive
                ? "bg-accent text-on-accent"
                : "bg-surface text-muted hover:bg-surface-muted hover:text-text"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
