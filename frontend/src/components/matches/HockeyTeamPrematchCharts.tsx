"use client";

import { useMemo, useState } from "react";

import { HockeyResultsChart } from "@/components/charts/HockeyResultsChart";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { ExpandableSection } from "@/components/ExpandableSection";
import { computeSplitStatsFromHistory } from "@/components/matches/matchTeamStatsUtils";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { TeamFormStrip } from "@/components/TeamFormStrip";
import { TeamSplitStatsTable } from "@/components/TeamSplitStatsTable";
import { TeamTripleStatCharts } from "@/components/teams/TeamTripleStatCharts";
import {
  buildHockeyDefaultStatLines,
  HOCKEY_TEAM_MATCH_STAT_CHARTS,
} from "@/components/teams/hockeyTeamMatchStatsConfig";
import {
  resolvePerspectiveSliderLabel,
  TEAM_MATCH_STAT_PERSPECTIVES,
  type TeamMatchStatLineKey,
  type TeamMatchStatPerspective,
  type TeamMatchStatThresholds,
} from "@/components/teams/teamMatchStatsConfig";
import { formatMatchDateShort } from "@/lib/format";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import type { HockeyFormResult, TeamSeasonMatchPoint } from "@/types/api";

interface HockeyTeamPrematchChartsProps {
  teamName: string;
  history: TeamSeasonMatchPoint[];
  lookback: number;
  ouLine: number;
}

interface ChartPoint {
  label: string;
  value: number;
}

type StatLines = Record<TeamMatchStatLineKey, TeamMatchStatThresholds>;

function buildChartLabel(
  match: TeamSeasonMatchPoint,
  preference: TeamNameDisplayPreference,
): string {
  const opponent = formatTeamName(
    match.opponent_name,
    match.opponent_shortcut,
    preference,
  );
  return `${opponent} ${formatMatchDateShort(match.match_date)}`;
}

function HockeyStatThresholdControls({
  teamName,
  statLines,
  onChange,
}: {
  teamName: string;
  statLines: StatLines;
  onChange: (
    key: TeamMatchStatLineKey,
    perspective: TeamMatchStatPerspective,
    value: number,
  ) => void;
}) {
  return (
    <ExpandableSection title="Konfiguracja statystyk" defaultOpen>
      <div className="space-y-4">
        {HOCKEY_TEAM_MATCH_STAT_CHARTS.map((definition) => (
          <div
            key={definition.key}
            className="space-y-3 rounded-xl border border-border bg-surface p-4"
          >
            <h4 className="text-sm font-semibold text-accent-text">
              {definition.configGroupTitle}
            </h4>
            <div className="grid gap-4 md:grid-cols-3">
              {TEAM_MATCH_STAT_PERSPECTIVES.map((perspective) => {
                const perspectiveConfig = definition.perspectiveConfig[perspective];
                return (
                  <label
                    key={`${definition.key}-${perspective}`}
                    className="space-y-2 rounded-lg border border-border bg-surface p-4 text-sm text-muted"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-text">
                        {resolvePerspectiveSliderLabel(perspective, teamName)}
                      </span>
                      <span className="font-semibold text-text">
                        {statLines[definition.key][perspective].toFixed(1)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={perspectiveConfig.minLine}
                      max={perspectiveConfig.maxLine}
                      step={definition.lineStep}
                      value={statLines[definition.key][perspective]}
                      onChange={(event) =>
                        onChange(
                          definition.key,
                          perspective,
                          Number(event.target.value),
                        )
                      }
                      className="w-full accent-accent"
                    />
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </ExpandableSection>
  );
}

function HockeyGoalsCharts({
  teamName,
  ouLine,
  chartMatches,
  firstPeriodPoints,
  labelFor,
}: {
  teamName: string;
  ouLine: number;
  chartMatches: TeamSeasonMatchPoint[];
  firstPeriodPoints: ChartPoint[];
  labelFor: (match: TeamSeasonMatchPoint) => string;
}) {
  return (
    <ExpandableSection title="Bramki w meczach" defaultOpen>
      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <VerticalStatChart
          title="Bramki w meczach"
          playerName={teamName}
          thresholdLine={ouLine}
          points={chartMatches.map((match) => ({
            label: labelFor(match),
            value: match.total_goals,
          }))}
        />
        {firstPeriodPoints.length > 0 ? (
          <VerticalStatChart
            title="Bramki w pierwszej tercji"
            playerName={teamName}
            thresholdLine={1.5}
            points={firstPeriodPoints}
          />
        ) : null}
      </div>
    </ExpandableSection>
  );
}

function HockeyMatchStatSections({
  teamName,
  chartMatches,
  statLines,
  labelFor,
}: {
  teamName: string;
  chartMatches: TeamSeasonMatchPoint[];
  statLines: StatLines;
  labelFor: (match: TeamSeasonMatchPoint) => string;
}) {
  return (
    <>
      {HOCKEY_TEAM_MATCH_STAT_CHARTS.map((definition) => (
        <ExpandableSection
          key={definition.expanderTitle}
          title={definition.expanderTitle}
        >
          <TeamTripleStatCharts
            teamName={teamName}
            chartMatches={chartMatches}
            buildLabel={labelFor}
            definition={definition}
            thresholdLines={statLines[definition.key]}
          />
        </ExpandableSection>
      ))}
    </>
  );
}

export function HockeyTeamPrematchCharts({
  teamName,
  history,
  lookback,
  ouLine,
}: HockeyTeamPrematchChartsProps) {
  const { preferences } = usePreferences();
  const teamNameDisplay = preferences.teamNameDisplay;
  const [statLines, setStatLines] = useState(buildHockeyDefaultStatLines);
  const analyzedMatches = useMemo(() => history.slice(0, lookback), [history, lookback]);
  const splitStats = useMemo(
    () => computeSplitStatsFromHistory(analyzedMatches, "hockey"),
    [analyzedMatches],
  );
  const chartMatches = useMemo(
    () => [...analyzedMatches].reverse(),
    [analyzedMatches],
  );
  const form = useMemo(
    () => chartMatches.map((match) => match.result),
    [chartMatches],
  );
  const labelFor = (match: TeamSeasonMatchPoint) =>
    buildChartLabel(match, teamNameDisplay);
  const firstPeriodPoints = useMemo(
    () =>
      chartMatches
        .filter((match) => match.first_period_goals !== null)
        .map((match) => ({
          label: buildChartLabel(match, teamNameDisplay),
          value: match.first_period_goals ?? 0,
        })),
    [chartMatches, teamNameDisplay],
  );

  const updateStatLine = (
    key: TeamMatchStatLineKey,
    perspective: TeamMatchStatPerspective,
    value: number,
  ) => {
    setStatLines((current) => ({
      ...current,
      [key]: { ...current[key], [perspective]: value },
    }));
  };

  return (
    <>
      <ExpandableSection title="Statystyki" defaultOpen>
        <TeamSplitStatsTable
          variant="hockey"
          overall={splitStats.overall}
          home={splitStats.home}
          away={splitStats.away}
        />
      </ExpandableSection>
      <HockeyStatThresholdControls
        teamName={teamName}
        statLines={statLines}
        onChange={updateStatLine}
      />
      <ExpandableSection title="Forma" defaultOpen>
        <TeamFormStrip form={form} />
      </ExpandableSection>
      <HockeyGoalsCharts
        teamName={teamName}
        ouLine={ouLine}
        chartMatches={chartMatches}
        firstPeriodPoints={firstPeriodPoints}
        labelFor={labelFor}
      />
      <HockeyMatchStatSections
        teamName={teamName}
        chartMatches={chartMatches}
        statLines={statLines}
        labelFor={labelFor}
      />
      <ExpandableSection title="Rezultaty meczów">
        <HockeyResultsChart
          teamName={teamName}
          results={chartMatches.map((match) => match.result as HockeyFormResult)}
        />
      </ExpandableSection>
    </>
  );
}
