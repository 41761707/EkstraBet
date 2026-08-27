"use client";

import type { ReactNode } from "react";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
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

function buildChartLabel(
  point: Pick<
    BasketballTeamHistoryPoint,
    "opponent_name" | "opponent_shortcut" | "match_date"
  >,
  preference: TeamNameDisplayPreference,
): string {
  const opponent = formatTeamName(
    point.opponent_name,
    point.opponent_shortcut,
    preference,
  );
  return `${opponent} ${point.match_date}`;
}

function opponentLabel(
  point: Pick<
    BasketballTeamHistoryPoint,
    "opponent_name" | "opponent_shortcut"
  >,
  preference: TeamNameDisplayPreference,
): string {
  return formatTeamName(
    point.opponent_name,
    point.opponent_shortcut,
    preference,
  );
}

function toChartPoints(
  history: BasketballTeamHistoryPoint[],
  preference: TeamNameDisplayPreference,
  getValue: (point: BasketballTeamHistoryPoint) => number,
): { label: string; value: number }[] {
  return history.map((point) => ({
    label: buildChartLabel(point, preference),
    value: getValue(point),
  }));
}

export function BasketballTeamCharts({
  teamName,
  history,
  ouLine,
  selectedStats,
}: BasketballTeamChartsProps) {
  const { preferences } = usePreferences();
  const teamNameDisplay = preferences.teamNameDisplay;
  const charts: ReactNode[] = [];

  if (selectedStats.includes("Punkty")) {
    charts.push(
      <VerticalStatChart
        key="points"
        title="Łączne punkty w meczach"
        playerName={teamName}
        points={toChartPoints(
          history,
          teamNameDisplay,
          (point) => point.total_points,
        )}
        thresholdLine={ouLine}
        compactScrollAlign="start"
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
        points={toChartPoints(
          history,
          teamNameDisplay,
          (point) => point.team_points,
        )}
        thresholdLine={average(teamPoints)}
        compactScrollAlign="start"
      />,
      <VerticalStatChart
        key="opponent-points"
        title="Liczba punktów przeciwników"
        playerName={teamName}
        points={toChartPoints(
          history,
          teamNameDisplay,
          (point) => point.opponent_points,
        )}
        thresholdLine={average(opponentPoints)}
        compactScrollAlign="start"
      />,
    );
  }

  if (selectedStats.includes("Rezultaty")) {
    charts.push(
      <div
        key="results"
        className="rounded-xl border border-border bg-surface p-4"
      >
        <h4 className="text-sm font-semibold text-text">
          Ostatnie wyniki: {teamName}
        </h4>
        <ul className="mt-3 space-y-2 text-sm text-muted">
          {history.map((point) => (
            <li key={point.match_id}>
              {point.match_date} vs {opponentLabel(point, teamNameDisplay)}:{" "}
              {point.home_team_name} {point.home_points}:{point.away_points}{" "}
              {point.away_team_name} ({point.result})
            </li>
          ))}
        </ul>
      </div>,
    );
  }

  if (charts.length === 0) {
    return (
      <p className="text-sm text-muted">
        Wybrane statystyki nie są jeszcze dostępne w tej wersji (np. rzuty,
        zbiórki).
      </p>
    );
  }

  return <div className="grid gap-4 lg:grid-cols-2">{charts}</div>;
}
