"use client";

import type { ReactNode } from "react";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import type { HockeyTeamHistoryPoint } from "@/types/api";

interface HockeyTeamChartsProps {
  teamName: string;
  history: HockeyTeamHistoryPoint[];
  ouLine: number;
  selectedStats: string[];
}

function average(values: number[]): number {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function HockeyTeamCharts({
  teamName,
  history,
  ouLine,
  selectedStats,
}: HockeyTeamChartsProps) {
  const labels = history.map(
    (point) => `${point.opponent_shortcut} ${point.match_date}`,
  );

  const charts: ReactNode[] = [];

  if (selectedStats.includes("Bramki")) {
    charts.push(
      <VerticalStatChart
        key="goals"
        title="Bramki w meczach"
        playerName={teamName}
        points={history.map((point, index) => ({
          label: labels[index],
          value: point.total_goals,
        }))}
        thresholdLine={ouLine}
      />,
    );
  }

  if (selectedStats.includes("Bramki w pierwszej tercji")) {
    const firstPeriodValues = history
      .map((point) => point.first_period_goals)
      .filter((value): value is number => value !== null && value !== undefined);
    if (firstPeriodValues.length > 0) {
      charts.push(
        <VerticalStatChart
          key="first-period-goals"
          title="Bramki w pierwszej tercji"
          playerName={teamName}
          points={history
            .filter(
              (point) =>
                point.first_period_goals !== null &&
                point.first_period_goals !== undefined,
            )
            .map((point, index) => ({
              label: labels[index],
              value: point.first_period_goals ?? 0,
            }))}
          thresholdLine={1.5}
        />,
      );
    }
  }

  if (selectedStats.includes("Bramki drużyny/przeciwników")) {
    const teamGoals = history.map((point) => point.team_goals);
    const opponentGoals = history.map((point) => point.opponent_goals);
    charts.push(
      <VerticalStatChart
        key="team-goals"
        title="Liczba bramek drużyny"
        playerName={teamName}
        points={history.map((point, index) => ({
          label: labels[index],
          value: point.team_goals,
        }))}
        thresholdLine={average(teamGoals)}
      />,
      <VerticalStatChart
        key="opponent-goals"
        title="Liczba bramek przeciwników"
        playerName={teamName}
        points={history.map((point, index) => ({
          label: labels[index],
          value: point.opponent_goals,
        }))}
        thresholdLine={average(opponentGoals)}
      />,
    );
  }

  if (selectedStats.includes("Strzały celne")) {
    const teamShots = history
      .map((point) => point.team_shots_on_goal)
      .filter((value): value is number => value !== null);
    const opponentShots = history
      .map((point) => point.opponent_shots_on_goal)
      .filter((value): value is number => value !== null);
    if (teamShots.length > 0) {
      charts.push(
        <VerticalStatChart
          key="team-sog"
          title="Liczba strzałów celnych drużyny"
          playerName={teamName}
          points={history
            .filter((point) => point.team_shots_on_goal !== null)
            .map((point, index) => ({
              label: labels[index],
              value: point.team_shots_on_goal ?? 0,
            }))}
          thresholdLine={average(teamShots)}
        />,
        <VerticalStatChart
          key="opponent-sog"
          title="Liczba strzałów przeciwników"
          playerName={teamName}
          points={history
            .filter((point) => point.opponent_shots_on_goal !== null)
            .map((point, index) => ({
              label: labels[index],
              value: point.opponent_shots_on_goal ?? 0,
            }))}
          thresholdLine={average(opponentShots)}
        />,
      );
    }
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
              {point.home_goals}:{point.away_goals} {point.away_team_name} (
              {point.result})
            </li>
          ))}
        </ul>
      </div>,
    );
  }

  if (charts.length === 0) {
    return null;
  }

  return <div className="grid gap-4 lg:grid-cols-2">{charts}</div>;
}
