"use client";

import type { ReactNode } from "react";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import type { BasketballTeamHistoryPoint } from "@/types/api";

interface BasketballTeamChartsProps {
  teamName: string;
  history: BasketballTeamHistoryPoint[];
  ouLine: number;
  selectedStats: string[];
}

function average(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function BasketballTeamCharts({
  teamName,
  history,
  ouLine,
  selectedStats,
}: BasketballTeamChartsProps) {
  const labels = history.map(
    (point) => `${point.opponent_shortcut} ${point.match_date}`,
  );
  const charts: ReactNode[] = [];

  if (selectedStats.includes("Punkty")) {
    charts.push(
      <VerticalStatChart
        key="points"
        title="Łączne punkty w meczach"
        playerName={teamName}
        points={history.map((point, index) => ({
          label: labels[index],
          value: point.total_points,
        }))}
        thresholdLine={ouLine}
      />,
    );
  }

  if (selectedStats.includes("Punkty drużyny/przeciwników")) {
    const teamPoints = history.map((point) => point.team_points);
    const opponentPoints = history.map((point) => point.opponent_points);
    charts.push(
      <VerticalStatChart
        key="team-points"
        title="Liczba punktów drużyny"
        playerName={teamName}
        points={history.map((point, index) => ({
          label: labels[index],
          value: point.team_points,
        }))}
        thresholdLine={average(teamPoints)}
      />,
      <VerticalStatChart
        key="opponent-points"
        title="Liczba punktów przeciwników"
        playerName={teamName}
        points={history.map((point, index) => ({
          label: labels[index],
          value: point.opponent_points,
        }))}
        thresholdLine={average(opponentPoints)}
      />,
    );
  }

  if (selectedStats.includes("Rezultaty")) {
    charts.push(
      <div
        key="results"
        className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-4"
      >
        <h4 className="text-sm font-semibold text-white">
          Ostatnie wyniki: {teamName}
        </h4>
        <ul className="mt-3 space-y-2 text-sm text-slate-300">
          {history.map((point) => (
            <li key={point.match_id}>
              {point.match_date} vs {point.opponent_shortcut}: {point.home_team_name}{" "}
              {point.home_points}:{point.away_points} {point.away_team_name} (
              {point.result})
            </li>
          ))}
        </ul>
      </div>,
    );
  }

  if (charts.length === 0) {
    return (
      <p className="text-sm text-slate-400">
        Wybrane statystyki nie są jeszcze dostępne w tej wersji (np. rzuty, zbiórki).
      </p>
    );
  }

  return <div className="grid gap-4 lg:grid-cols-2">{charts}</div>;
}
