"use client";

import { useState } from "react";

import {
  MatchDetailTabPanel,
  type MatchTab,
} from "@/components/matches/MatchDetailTabPanel";
import {
  BASKETBALL_SPORT_ID,
  HOCKEY_SPORT_ID,
  type MatchDetails,
} from "@/types/api";

interface MatchDetailTabsProps {
  match: MatchDetails;
}

interface MatchTabButton {
  id: MatchTab;
  label: string;
  visible: boolean;
}

const TAB_ACTIVE_CLASS = "border-accent text-accent-text-hover";
const TAB_IDLE_CLASS = "border-transparent text-muted hover:text-text";

function visibleMatchTabs(match: MatchDetails): MatchTabButton[] {
  const tabs: MatchTabButton[] = [
    { id: "prematch", label: "Statystyki przedmeczowe", visible: true },
    { id: "predictions", label: "Predykcje i kursy", visible: true },
    {
      id: "lineups",
      label: "Składy",
      visible:
        match.sport_id === HOCKEY_SPORT_ID ||
        match.sport_id === BASKETBALL_SPORT_ID,
    },
    {
      id: "players",
      label: "Zawodnicy (beta)",
      visible: match.sport_id === HOCKEY_SPORT_ID && !match.is_played,
    },
    {
      id: "events",
      label: "Przebieg meczu",
      visible: match.sport_id === HOCKEY_SPORT_ID && match.is_played,
    },
    {
      id: "stats",
      label: "Statystyki pomeczowe",
      visible:
        match.is_played &&
        (match.stats !== null || match.hockey_stats !== null),
    },
    {
      id: "boxscore",
      label: "Boxscore - statystyki zawodników",
      visible: match.has_player_stats && match.is_played,
    },
  ];
  return tabs.filter((tab) => tab.visible);
}

function MatchDetailTabBar({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: MatchTabButton[];
  activeTab: MatchTab;
  onChange: (tab: MatchTab) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-border pb-1">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`border-b-2 px-3 py-2 text-sm font-medium transition ${
              isActive ? TAB_ACTIVE_CLASS : TAB_IDLE_CLASS
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export function MatchDetailTabs({ match }: MatchDetailTabsProps) {
  const [activeTab, setActiveTab] = useState<MatchTab>("prematch");
  const visibleTabs = visibleMatchTabs(match);
  const resolvedTab = visibleTabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : "prematch";

  return (
    <div className="min-w-0 space-y-6">
      <MatchDetailTabBar
        tabs={visibleTabs}
        activeTab={resolvedTab}
        onChange={setActiveTab}
      />
      <MatchDetailTabPanel match={match} tab={resolvedTab} />
    </div>
  );
}
