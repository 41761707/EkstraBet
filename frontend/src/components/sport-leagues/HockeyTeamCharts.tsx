"use client";

import type { ReactNode } from "react";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
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

function buildChartLabel(
  point: Pick<
    HockeyTeamHistoryPoint,
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
  point: Pick<HockeyTeamHistoryPoint, "opponent_name" | "opponent_shortcut">,
  preference: TeamNameDisplayPreference,
): string {
  return formatTeamName(
    point.opponent_name,
    point.opponent_shortcut,
    preference,
  );
}

function toChartPoints(
  history: HockeyTeamHistoryPoint[],
  preference: TeamNameDisplayPreference,
  getValue: (point: HockeyTeamHistoryPoint) => number,
): { label: string; value: number }[] {
  return history.map((point) => ({
    label: buildChartLabel(point, preference),
    value: getValue(point),
  }));
}

interface HockeyChartBuildContext {
  teamName: string;
  history: HockeyTeamHistoryPoint[];
  ouLine: number;
  selectedStats: string[];
  teamNameDisplay: TeamNameDisplayPreference;
}

function collectGoalCharts(ctx: HockeyChartBuildContext): ReactNode[] {
  const { teamName, history, ouLine, selectedStats, teamNameDisplay } = ctx;
  const charts: ReactNode[] = [];

  if (selectedStats.includes("Bramki")) {
    charts.push(
      <VerticalStatChart
        key="goals"
        title="Bramki w meczach"
        playerName={teamName}
        points={toChartPoints(
          history,
          teamNameDisplay,
          (point) => point.total_goals,
        )}
        thresholdLine={ouLine}
        compactScrollAlign="start"
      />,
    );
  }

  if (selectedStats.includes("Bramki w pierwszej tercji")) {
    const firstPeriodHistory = history.filter(
      (point) =>
        point.first_period_goals !== null &&
        point.first_period_goals !== undefined,
    );
    if (firstPeriodHistory.length > 0) {
      charts.push(
        <VerticalStatChart
          key="first-period-goals"
          title="Bramki w pierwszej tercji"
          playerName={teamName}
          points={toChartPoints(
            firstPeriodHistory,
            teamNameDisplay,
            (point) => point.first_period_goals ?? 0,
          )}
          thresholdLine={1.5}
          compactScrollAlign="start"
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
        points={toChartPoints(
          history,
          teamNameDisplay,
          (point) => point.team_goals,
        )}
        thresholdLine={average(teamGoals)}
        compactScrollAlign="start"
      />,
      <VerticalStatChart
        key="opponent-goals"
        title="Liczba bramek przeciwników"
        playerName={teamName}
        points={toChartPoints(
          history,
          teamNameDisplay,
          (point) => point.opponent_goals,
        )}
        thresholdLine={average(opponentGoals)}
        compactScrollAlign="start"
      />,
    );
  }

  return charts;
}

function collectShotCharts(ctx: HockeyChartBuildContext): ReactNode[] {
  const { teamName, history, selectedStats, teamNameDisplay } = ctx;
  if (!selectedStats.includes("Strzały celne")) {
    return [];
  }

  const teamShotHistory = history.filter(
    (point) => point.team_shots_on_goal !== null,
  );
  const opponentShotHistory = history.filter(
    (point) => point.opponent_shots_on_goal !== null,
  );
  if (teamShotHistory.length === 0) {
    return [];
  }

  return [
    <VerticalStatChart
      key="team-sog"
      title="Liczba strzałów celnych drużyny"
      playerName={teamName}
      points={toChartPoints(
        teamShotHistory,
        teamNameDisplay,
        (point) => point.team_shots_on_goal ?? 0,
      )}
      thresholdLine={average(
        teamShotHistory.map((point) => point.team_shots_on_goal ?? 0),
      )}
      compactScrollAlign="start"
    />,
    <VerticalStatChart
      key="opponent-sog"
      title="Liczba strzałów przeciwników"
      playerName={teamName}
      points={toChartPoints(
        opponentShotHistory,
        teamNameDisplay,
        (point) => point.opponent_shots_on_goal ?? 0,
      )}
      thresholdLine={average(
        opponentShotHistory.map((point) => point.opponent_shots_on_goal ?? 0),
      )}
      compactScrollAlign="start"
    />,
  ];
}

function collectResultsChart(ctx: HockeyChartBuildContext): ReactNode[] {
  const { teamName, history, selectedStats, teamNameDisplay } = ctx;
  if (!selectedStats.includes("Rezultaty")) {
    return [];
  }

  return [
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
            {point.home_team_name} {point.home_goals}:{point.away_goals}{" "}
            {point.away_team_name} ({point.result})
          </li>
        ))}
      </ul>
    </div>,
  ];
}

export function HockeyTeamCharts({
  teamName,
  history,
  ouLine,
  selectedStats,
}: HockeyTeamChartsProps) {
  const { preferences } = usePreferences();
  const ctx: HockeyChartBuildContext = {
    teamName,
    history,
    ouLine,
    selectedStats,
    teamNameDisplay: preferences.teamNameDisplay,
  };
  const charts = [
    ...collectGoalCharts(ctx),
    ...collectShotCharts(ctx),
    ...collectResultsChart(ctx),
  ];

  if (charts.length === 0) {
    return null;
  }

  return <div className="grid min-w-0 gap-4 lg:grid-cols-2">{charts}</div>;
}
