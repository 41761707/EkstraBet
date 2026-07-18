"use client";

import { useState } from "react";
import { StatusMessage } from "@/components/StatusMessage";
import { HOCKEY_SPORT_ID, type SportLeagueStatsResponse } from "@/types/api";

interface SportLeagueStatsSectionProps {
  sportId: number;
  stats: Record<string, SportLeagueStatsResponse | null>;
}

function StatsTable({
  rows,
  columns,
}: {
  rows: SportLeagueStatsResponse["rows"];
  columns: { key: keyof SportLeagueStatsResponse["rows"][number]; label: string }[];
}) {
  if (rows.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak danych"
        message="Brak statystyk dla wybranego sezonu."
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-slate-400">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="px-3 py-2 text-left">
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={`${row.team_name}-${row.team_shortcut}`}
              className="border-t border-slate-800/80 text-slate-200"
            >
              {columns.map((column) => (
                <td key={column.key} className="px-3 py-2">
                  {row[column.key] ?? "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SportLeagueStatsSection({
  sportId,
  stats,
}: SportLeagueStatsSectionProps) {
  const hockeyTabs = [
    { id: "shots", label: "Strzały" },
    { id: "goals", label: "Bramki" },
    { id: "over_under", label: "Over/Under" },
  ];
  const basketballTabs = [
    { id: "shooting", label: "Rzuty" },
    { id: "points", label: "Punkty" },
    { id: "over_under", label: "Over/Under" },
  ];
  const tabs = sportId === HOCKEY_SPORT_ID ? hockeyTabs : basketballTabs;
  const [activeTab, setActiveTab] = useState(tabs[0].id);
  const payload = stats[activeTab];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full px-3 py-1.5 text-sm transition ${
              activeTab === tab.id
                ? "bg-sky-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {!payload ? (
        <StatusMessage
          variant="empty"
          title="Brak statystyk"
          message="Nie udało się załadować statystyk ligowych."
        />
      ) : activeTab === "points" && payload.distribution ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-400">Średnia punktów na mecz</p>
            <p className="text-2xl font-semibold text-white">
              {payload.distribution.average_total}
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-400">Mediana</p>
            <p className="text-2xl font-semibold text-white">
              {payload.distribution.median_total}
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-400">Min / max</p>
            <p className="text-2xl font-semibold text-white">
              {payload.distribution.min_total} / {payload.distribution.max_total}
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-400">Średnia punktów gospodarzy</p>
            <p className="text-2xl font-semibold text-white">
              {payload.distribution.average_home}
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4">
            <p className="text-xs text-slate-400">Średnia punktów gości</p>
            <p className="text-2xl font-semibold text-white">
              {payload.distribution.average_away}
            </p>
          </div>
        </div>
      ) : activeTab === "shots" || activeTab === "goals" ? (
        <StatsTable
          rows={payload.rows}
          columns={[
            { key: "team_name", label: "Drużyna" },
            { key: "team_shortcut", label: "Skrót" },
            { key: "avg_for", label: "Śr. za" },
            { key: "avg_against", label: "Śr. przeciw" },
            { key: "matches_played", label: "Mecze" },
          ]}
        />
      ) : activeTab === "shooting" ? (
        <StatsTable
          rows={payload.rows}
          columns={[
            { key: "team_name", label: "Drużyna" },
            { key: "team_shortcut", label: "Skrót" },
            { key: "field_goal_pct", label: "FG%" },
            { key: "three_point_pct", label: "3P%" },
            { key: "matches_played", label: "Mecze" },
          ]}
        />
      ) : (
        <StatsTable
          rows={payload.rows}
          columns={
            sportId === HOCKEY_SPORT_ID
              ? [
                  { key: "team_name", label: "Drużyna" },
                  { key: "team_shortcut", label: "Skrót" },
                  { key: "over_4_5_pct", label: "Over 4.5" },
                  { key: "over_5_5_pct", label: "Over 5.5" },
                  { key: "over_6_5_pct", label: "Over 6.5" },
                  { key: "over_7_5_pct", label: "Over 7.5" },
                ]
              : [
                  { key: "team_name", label: "Drużyna" },
                  { key: "team_shortcut", label: "Skrót" },
                  { key: "over_210_5_pct", label: "Over 210.5" },
                  { key: "over_220_5_pct", label: "Over 220.5" },
                  { key: "over_230_5_pct", label: "Over 230.5" },
                ]
          }
        />
      )}
    </div>
  );
}
