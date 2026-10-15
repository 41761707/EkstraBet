"use client";

import { useState } from "react";
import { HockeyLeagueStatsPanels } from "@/components/sport-leagues/HockeyLeagueStatsPanels";
import { StatusMessage } from "@/components/StatusMessage";
import {
  HOCKEY_SPORT_ID,
  type SportLeagueStatsResponse,
  type SportPointsDistributionSummary,
} from "@/types/api";

interface SportLeagueStatsSectionProps {
  sportId: number;
  stats: Record<string, SportLeagueStatsResponse | null>;
}

type StatRow = SportLeagueStatsResponse["rows"][number];
type StatColumn = { key: keyof StatRow; label: string };

function StatsTable({
  rows,
  columns,
}: {
  rows: SportLeagueStatsResponse["rows"];
  columns: StatColumn[];
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
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-muted">
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
              className="border-t border-border text-text"
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

function PointsSummary({
  distribution,
}: {
  distribution: SportPointsDistributionSummary;
}) {
  const cards = [
    { label: "Średnia punktów na mecz", value: distribution.average_total },
    { label: "Mediana", value: distribution.median_total },
    {
      label: "Min / max",
      value: `${distribution.min_total} / ${distribution.max_total}`,
    },
    { label: "Średnia punktów gospodarzy", value: distribution.average_home },
    { label: "Średnia punktów gości", value: distribution.average_away },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl border border-border bg-surface p-4"
        >
          <p className="text-xs text-muted">{card.label}</p>
          <p className="text-2xl font-semibold text-text">{card.value}</p>
        </div>
      ))}
    </div>
  );
}

function categoryColumns(
  sportId: number,
  activeTab: string,
): StatColumn[] {
  if (activeTab === "shots" || activeTab === "goals") {
    return [
      { key: "team_name", label: "Drużyna" },
      { key: "team_shortcut", label: "Skrót" },
      { key: "avg_for", label: "Śr. za" },
      { key: "avg_against", label: "Śr. przeciw" },
      { key: "matches_played", label: "Mecze" },
    ];
  }
  if (activeTab === "shooting") {
    return [
      { key: "team_name", label: "Drużyna" },
      { key: "team_shortcut", label: "Skrót" },
      { key: "field_goal_pct", label: "FG%" },
      { key: "three_point_pct", label: "3P%" },
      { key: "matches_played", label: "Mecze" },
    ];
  }
  if (sportId === HOCKEY_SPORT_ID) {
    return [
      { key: "team_name", label: "Drużyna" },
      { key: "team_shortcut", label: "Skrót" },
      { key: "over_4_5_pct", label: "Over 4.5" },
      { key: "over_5_5_pct", label: "Over 5.5" },
      { key: "over_6_5_pct", label: "Over 6.5" },
      { key: "over_7_5_pct", label: "Over 7.5" },
    ];
  }
  return [
    { key: "team_name", label: "Drużyna" },
    { key: "team_shortcut", label: "Skrót" },
    { key: "over_210_5_pct", label: "Over 210.5" },
    { key: "over_220_5_pct", label: "Over 220.5" },
    { key: "over_230_5_pct", label: "Over 230.5" },
  ];
}

function CategoryBody({
  sportId,
  activeTab,
  payload,
}: {
  sportId: number;
  activeTab: string;
  payload: SportLeagueStatsResponse;
}) {
  if (activeTab === "points" && payload.distribution) {
    return <PointsSummary distribution={payload.distribution} />;
  }
  return (
    <StatsTable
      rows={payload.rows}
      columns={categoryColumns(sportId, activeTab)}
    />
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
                ? "bg-accent text-on-accent"
                : "bg-surface text-muted hover:bg-surface-muted hover:text-text"
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
      ) : (
        <div className="space-y-4">
          {sportId === HOCKEY_SPORT_ID ? (
            <HockeyLeagueStatsPanels
              category={activeTab}
              rows={payload.rows}
              goalsDistribution={payload.goals_distribution}
            />
          ) : null}
          <CategoryBody
            sportId={sportId}
            activeTab={activeTab}
            payload={payload}
          />
        </div>
      )}
    </div>
  );
}
