"use client";

import Link from "next/link";
import { useState } from "react";
import { StatusMessage } from "@/components/StatusMessage";
import {
  HOCKEY_SPORT_ID,
  type BasketballStandingRow,
  type HockeyStandingRow,
} from "@/types/api";

interface SportStandingsSectionProps {
  sportId: number;
  seasonId?: number;
  leagueId?: number;
  overallHockey?: HockeyStandingRow[];
  homeHockey?: HockeyStandingRow[];
  awayHockey?: HockeyStandingRow[];
  overallBasketball?: BasketballStandingRow[];
  homeBasketball?: BasketballStandingRow[];
  awayBasketball?: BasketballStandingRow[];
}

function teamHref(
  teamId: number,
  seasonId?: number,
  leagueId?: number,
): string {
  const params = new URLSearchParams();
  if (seasonId) {
    params.set("season_id", String(seasonId));
  }
  if (leagueId) {
    params.set("league_id", String(leagueId));
  }
  const query = params.toString();
  return query ? `/teams/${teamId}?${query}` : `/teams/${teamId}`;
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

function HockeyTable({
  rows,
  seasonId,
  leagueId,
}: {
  rows: HockeyStandingRow[];
  seasonId?: number;
  leagueId?: number;
}) {
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
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-muted">
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
              className="border-t border-border text-text"
            >
              <td className="px-3 py-2">{row.position}</td>
              <td className="px-3 py-2 font-medium">
                <Link
                  href={teamHref(row.team_id, seasonId, leagueId)}
                  className="text-text transition hover:text-accent-text"
                >
                  {row.team_name}
                </Link>
              </td>
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
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface text-muted">
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
              className="border-t border-border text-text"
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
  seasonId,
  leagueId,
  overallHockey,
  homeHockey,
  awayHockey,
  overallBasketball,
  homeBasketball,
  awayBasketball,
}: SportStandingsSectionProps) {
  const isHockey = sportId === HOCKEY_SPORT_ID;
  const tabs = isHockey ? hockeyTabs : basketballTabs;
  const [activeTab, setActiveTab] = useState<TabId>("overall");

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

      {activeTab === "overall" ? (
        <div className="space-y-3">
          <h3 className="text-base font-semibold text-text">Tabela ogólna</h3>
          {isHockey ? (
            <HockeyTable
              rows={overallHockey ?? []}
              seasonId={seasonId}
              leagueId={leagueId}
            />
          ) : (
            <BasketballTable rows={overallBasketball ?? []} />
          )}
        </div>
      ) : null}

      {activeTab === "conferences" || activeTab === "divisions" ? (
        <p className="text-sm text-muted">
          Tabela z podziałem na{" "}
          {activeTab === "conferences" ? "konferencje" : "dywizje"} — wkrótce.
        </p>
      ) : null}

      {activeTab === "home" ? (
        isHockey ? (
          <HockeyTable
            rows={homeHockey ?? []}
            seasonId={seasonId}
            leagueId={leagueId}
          />
        ) : (
          <BasketballTable rows={homeBasketball ?? []} />
        )
      ) : null}

      {activeTab === "away" ? (
        isHockey ? (
          <HockeyTable
            rows={awayHockey ?? []}
            seasonId={seasonId}
            leagueId={leagueId}
          />
        ) : (
          <BasketballTable rows={awayBasketball ?? []} />
        )
      ) : null}

      {isHockey ? (
        <p className="text-sm text-subtle">
          Legenda: WPD - wygrane po dogrywce, PPD - przegrane po dogrywce
        </p>
      ) : null}
    </div>
  );
}
