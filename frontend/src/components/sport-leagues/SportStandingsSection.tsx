"use client";

import { useState } from "react";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  BasketballStandingRow,
  HockeyStandingRow,
  SportLeagueStatsResponse,
} from "@/types/api";

interface SportStandingsSectionProps {
  sportId: number;
  overallHockey?: HockeyStandingRow[];
  homeHockey?: HockeyStandingRow[];
  awayHockey?: HockeyStandingRow[];
  overallBasketball?: BasketballStandingRow[];
  homeBasketball?: BasketballStandingRow[];
  awayBasketball?: BasketballStandingRow[];
}

type TabId =
  | "overall"
  | "conferences"
  | "divisions"
  | "home"
  | "away";

const hockeyTabs: { id: TabId; label: string }[] = [
  { id: "overall", label: "Tabela sezonu zasadniczego" },
  { id: "conferences", label: "Tabela - konferencje" },
  { id: "divisions", label: "Tabela - dywizje" },
  { id: "home", label: "Tabela domowa" },
  { id: "away", label: "Tabela wyjazdowa" },
];

const basketballTabs: { id: TabId; label: string }[] = [
  { id: "overall", label: "Tabela sezonu zasadniczego" },
  { id: "home", label: "Tabela domowa" },
  { id: "away", label: "Tabela wyjazdowa" },
];

function HockeyTable({ rows }: { rows: HockeyStandingRow[] }) {
  if (rows.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak danych"
        message="Brak meczów do wyliczenia tabeli."
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-slate-400">
          <tr>
            <th className="px-3 py-2 text-left">Miejsce</th>
            <th className="px-3 py-2 text-left">Drużyna</th>
            <th className="px-3 py-2 text-center">Mecze</th>
            <th className="px-3 py-2 text-center">Wygrane</th>
            <th className="px-3 py-2 text-center">Przegrane</th>
            <th className="px-3 py-2 text-center">WPD</th>
            <th className="px-3 py-2 text-center">PPD</th>
            <th className="px-3 py-2 text-center">Bramki</th>
            <th className="px-3 py-2 text-center">Różnica bramek</th>
            <th className="px-3 py-2 text-center">Punkty</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.team_id}
              className="border-t border-slate-800/80 text-slate-200"
            >
              <td className="px-3 py-2">{row.position}</td>
              <td className="px-3 py-2 font-medium">{row.team_name}</td>
              <td className="px-3 py-2 text-center">{row.played}</td>
              <td className="px-3 py-2 text-center">{row.wins}</td>
              <td className="px-3 py-2 text-center">{row.losses}</td>
              <td className="px-3 py-2 text-center">{row.overtime_wins}</td>
              <td className="px-3 py-2 text-center">{row.overtime_losses}</td>
              <td className="px-3 py-2 text-center">
                {row.goals_for}:{row.goals_against}
              </td>
              <td className="px-3 py-2 text-center">{row.goal_difference}</td>
              <td className="px-3 py-2 text-center font-semibold">
                {row.points}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BasketballTable({ rows }: { rows: BasketballStandingRow[] }) {
  if (rows.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak danych"
        message="Brak meczów do wyliczenia tabeli."
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-900/80 text-slate-400">
          <tr>
            <th className="px-3 py-2 text-left">Miejsce</th>
            <th className="px-3 py-2 text-left">Drużyna</th>
            <th className="px-3 py-2 text-center">Mecze</th>
            <th className="px-3 py-2 text-center">Wygrane</th>
            <th className="px-3 py-2 text-center">Przegrane</th>
            <th className="px-3 py-2 text-center">Punkty zdobyte</th>
            <th className="px-3 py-2 text-center">Punkty stracone</th>
            <th className="px-3 py-2 text-center">Różnica punktów</th>
            <th className="px-3 py-2 text-center">Procent wygranych</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.team_id}
              className="border-t border-slate-800/80 text-slate-200"
            >
              <td className="px-3 py-2">{row.position}</td>
              <td className="px-3 py-2 font-medium">{row.team_name}</td>
              <td className="px-3 py-2 text-center">{row.played}</td>
              <td className="px-3 py-2 text-center">{row.wins}</td>
              <td className="px-3 py-2 text-center">{row.losses}</td>
              <td className="px-3 py-2 text-center">{row.points_for}</td>
              <td className="px-3 py-2 text-center">{row.points_against}</td>
              <td className="px-3 py-2 text-center">{row.point_difference}</td>
              <td className="px-3 py-2 text-center">
                {row.win_percentage.toFixed(1)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SportStandingsSection({
  sportId,
  overallHockey,
  homeHockey,
  awayHockey,
  overallBasketball,
  homeBasketball,
  awayBasketball,
}: SportStandingsSectionProps) {
  const tabs = sportId === 2 ? hockeyTabs : basketballTabs;
  const [activeTab, setActiveTab] = useState<TabId>("overall");
  const isHockey = sportId === 2;

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

      {activeTab === "overall" ? (
        <div className="space-y-3">
          <h3 className="text-base font-semibold text-white">Tabela ogólna</h3>
          {isHockey ? (
            <HockeyTable rows={overallHockey ?? []} />
          ) : (
            <BasketballTable rows={overallBasketball ?? []} />
          )}
        </div>
      ) : null}

      {activeTab === "conferences" || activeTab === "divisions" ? (
        <p className="text-sm text-slate-400">
          Tabela z podziałem na{" "}
          {activeTab === "conferences" ? "konferencje" : "dywizje"} — wkrótce.
        </p>
      ) : null}

      {activeTab === "home" ? (
        isHockey ? (
          <HockeyTable rows={homeHockey ?? []} />
        ) : (
          <BasketballTable rows={homeBasketball ?? []} />
        )
      ) : null}

      {activeTab === "away" ? (
        isHockey ? (
          <HockeyTable rows={awayHockey ?? []} />
        ) : (
          <BasketballTable rows={awayBasketball ?? []} />
        )
      ) : null}

      {isHockey ? (
        <p className="text-sm text-slate-500">
          Legenda: WPD - wygrane po dogrywce, PPD - przegrane po dogrywce
        </p>
      ) : null}
    </div>
  );
}
