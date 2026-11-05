"use client";

/** Switch shared by analytics (pills) and the result calendar (one track per group). */
interface ChoiceTabsProps<T extends string> {
  label: string;
  tabs: { id: T; label: string }[];
  value: T;
  onChange: (id: T) => void;
  variant?: "pills" | "segmented";
}

export function ChoiceTabs<T extends string>({
  label,
  tabs,
  value,
  onChange,
  variant = "pills",
}: ChoiceTabsProps<T>) {
  return (
    <div
      className={trackClassName(variant)}
      role="tablist"
      aria-label={label}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === value;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={tabClassName(variant, isActive)}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

function trackClassName(variant: "pills" | "segmented"): string {
  if (variant === "segmented") {
    return "inline-flex max-w-full flex-wrap rounded-lg border border-border bg-page p-0.5";
  }
  return "flex flex-wrap gap-2";
}

function tabClassName(variant: "pills" | "segmented", isActive: boolean): string {
  if (variant === "segmented") {
    return `rounded-md px-3 py-1.5 text-sm transition ${
      isActive
        ? "bg-accent text-on-accent"
        : "text-muted hover:bg-surface hover:text-text"
    }`;
  }
  return `rounded-full px-3 py-1.5 text-sm transition ${
    isActive
      ? "bg-accent text-on-accent"
      : "bg-surface text-muted hover:bg-surface-muted hover:text-text"
  }`;
}
