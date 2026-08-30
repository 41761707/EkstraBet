export type TyperLmTab = "round" | "ranking";

interface TyperLmViewTabsProps {
  activeTab: TyperLmTab;
  onChange: (tab: TyperLmTab) => void;
}

const TABS: { id: TyperLmTab; label: string }[] = [
  { id: "round", label: "Kolejka" },
  { id: "ranking", label: "Ranking" },
];

export function TyperLmViewTabs({ activeTab, onChange }: TyperLmViewTabsProps) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-border pb-3">
      {TABS.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            type="button"
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
