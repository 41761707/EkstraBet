"use client";

import { useMemo, useState } from "react";
import type { MatchPlayerStat } from "@/types/api";

interface MatchBoxscorePanelProps {
  homeTeamId: number;
  homeTeamName: string;
  awayTeamId: number;
  awayTeamName: string;
  players: MatchPlayerStat[];
}

type BoxscoreTab = "all" | "home" | "away";

interface HighlightStat {
  key: keyof MatchPlayerStat;
  label: string;
  accent?: boolean;
}

const HIGHLIGHT_STATS: HighlightStat[] = [
  { key: "goals", label: "G", accent: true },
  { key: "assists", label: "A", accent: true },
  { key: "shots", label: "Shots" },
  { key: "shots_on_target", label: "SoT" },
  { key: "passes", label: "Passes" },
  { key: "tackles", label: "Tackles" },
  { key: "yellow_cards", label: "Yellow Cards" },
  { key: "red_cards", label: "Red Cards" },
];

function formatStatValue(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return String(value);
}

function hasMeaningfulStats(player: MatchPlayerStat): boolean {
  return HIGHLIGHT_STATS.some((stat) => {
    const value = player[stat.key];
    return typeof value === "number" && value > 0;
  });
}

function PlayerCard({ player }: { player: MatchPlayerStat }) {
  const visibleStats = HIGHLIGHT_STATS.filter((stat) => {
    const value = player[stat.key];
    return value !== null && value !== undefined;
  });

  return (
    <article className="rounded-xl border border-slate-700/80 bg-slate-900/50 p-4 transition hover:border-sky-500/30">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold text-white">{player.player_name}</h4>
          <p className="text-xs text-slate-500">{player.team_name}</p>
        </div>
        <div className="flex gap-2">
          {typeof player.goals === "number" && player.goals > 0 ? (
            <span className="rounded-full bg-emerald-500/20 px-2 py-1 text-xs font-semibold text-emerald-300">
              {player.goals} G
            </span>
          ) : null}
          {typeof player.assists === "number" && player.assists > 0 ? (
            <span className="rounded-full bg-sky-500/20 px-2 py-1 text-xs font-semibold text-sky-300">
              {player.assists} A
            </span>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">
        {visibleStats.map((stat) => {
          const value = player[stat.key];
          return (
            <div
              key={stat.key}
              className={`rounded-lg px-2 py-2 text-center ${
                stat.accent
                  ? "bg-slate-800/80"
                  : "bg-slate-800/40"
              }`}
            >
              <div
                className={`text-sm font-bold ${
                  stat.accent ? "text-white" : "text-slate-200"
                }`}
              >
                {formatStatValue(typeof value === "number" ? value : null)}
              </div>
              <div className="text-[10px] uppercase tracking-wide text-slate-500">
                {stat.label}
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}

export function MatchBoxscorePanel({
  homeTeamId,
  homeTeamName,
  awayTeamId,
  awayTeamName,
  players,
}: MatchBoxscorePanelProps) {
  const [activeTab, setActiveTab] = useState<BoxscoreTab>("all");

  const filteredPlayers = useMemo(() => {
    const meaningful = players.filter(hasMeaningfulStats);
    if (activeTab === "home") {
      return meaningful.filter((player) => player.team_id === homeTeamId);
    }
    if (activeTab === "away") {
      return meaningful.filter((player) => player.team_id === awayTeamId);
    }
    return meaningful;
  }, [activeTab, awayTeamId, homeTeamId, players]);

  const tabs: { id: BoxscoreTab; label: string }[] = [
    { id: "all", label: "Wszyscy" },
    { id: "home", label: homeTeamName },
    { id: "away", label: awayTeamName },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-full px-3 py-1.5 text-sm transition ${
                isActive
                  ? "bg-sky-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {filteredPlayers.length === 0 ? (
        <p className="text-sm text-slate-400">
          Brak statystyk zawodników dla wybranej drużyny.
        </p>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {filteredPlayers.map((player) => (
            <PlayerCard key={`${player.player_id}-${player.team_id}`} player={player} />
          ))}
        </div>
      )}
    </div>
  );
}
