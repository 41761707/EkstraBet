"use client";

import { useMemo, useState } from "react";
import { BttsMatchChart } from "@/components/charts/BttsMatchChart";
import { TeamResultsChart } from "@/components/charts/TeamResultsChart";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { ExpandableSection } from "@/components/ExpandableSection";
import { computeSplitStatsFromHistory } from "@/components/matches/matchTeamStatsUtils";
import { StatusMessage } from "@/components/StatusMessage";
import { TeamFormStrip } from "@/components/TeamFormStrip";
import { TeamSplitStatsTable } from "@/components/TeamSplitStatsTable";
import { TeamTripleStatCharts } from "@/components/teams/TeamTripleStatCharts";
import {
  buildDefaultStatLines,
  resolvePerspectiveSliderLabel,
  TEAM_MATCH_STAT_CHARTS,
  TEAM_MATCH_STAT_PERSPECTIVES,
  type TeamMatchStatLineKey,
  type TeamMatchStatPerspective,
} from "@/components/teams/teamMatchStatsConfig";
import { formatMatchDateShort } from "@/lib/format";
import type { TeamSeasonMatchPoint } from "@/types/api";

interface MatchTeamPrematchPanelProps {
  teamName: string;
  history: TeamSeasonMatchPoint[];
  lookback: number;
  ouLine: number;
}

function buildChartLabel(match: TeamSeasonMatchPoint): string {
  return `${match.opponent_shortcut} ${formatMatchDateShort(match.match_date)}`;
}

export function MatchTeamPrematchPanel({
  teamName,
  history,
  lookback,
  ouLine,
}: MatchTeamPrematchPanelProps) {
  const [statLines, setStatLines] = useState(buildDefaultStatLines);

  const splitStats = useMemo(
    () => computeSplitStatsFromHistory(history),
    [history],
  );

  const chartMatches = useMemo(() => {
    if (history.length === 0) {
      return [];
    }
    return [...history].slice(0, lookback).reverse();
  }, [history, lookback]);

  const form = useMemo(
    () => chartMatches.map((match) => match.result),
    [chartMatches],
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

  if (history.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak historii meczów"
        message={`Nie znaleziono rozegranych meczów przed datą spotkania dla ${teamName}.`}
      />
    );
  }

  return (
    <div className="space-y-4">
      <ExpandableSection title="Statystyki sezonowe" defaultOpen>
        <TeamSplitStatsTable
          overall={splitStats.overall}
          home={splitStats.home}
          away={splitStats.away}
        />
      </ExpandableSection>

      <ExpandableSection title="Konfiguracja statystyk" defaultOpen>
        <div className="space-y-4">
          {TEAM_MATCH_STAT_CHARTS.map((definition) => (
            <div
              key={definition.key}
              className="space-y-3 rounded-xl border border-slate-700/80 bg-slate-900/40 p-4"
            >
              <h4 className="text-sm font-semibold text-sky-300">
                {definition.configGroupTitle}
              </h4>
              <div className="grid gap-4 md:grid-cols-3">
                {TEAM_MATCH_STAT_PERSPECTIVES.map((perspective) => {
                  const perspectiveConfig =
                    definition.perspectiveConfig[perspective];
                  return (
                    <label
                      key={`${definition.key}-${perspective}`}
                      className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-medium text-slate-200">
                          {resolvePerspectiveSliderLabel(perspective, teamName)}
                        </span>
                        <span className="font-semibold text-white">
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
                          updateStatLine(
                            definition.key,
                            perspective,
                            Number(event.target.value),
                          )
                        }
                        className="w-full accent-sky-400"
                      />
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </ExpandableSection>

      <ExpandableSection title="Forma" defaultOpen>
        <TeamFormStrip form={form} />
      </ExpandableSection>

      <ExpandableSection title="Bramki i BTTS w meczach" defaultOpen>
        <div className="grid gap-4 xl:grid-cols-2">
          <VerticalStatChart
            title="Bramki w meczach"
            playerName={teamName}
            thresholdLine={ouLine}
            points={chartMatches.map((match) => ({
              label: buildChartLabel(match),
              value: match.total_goals,
            }))}
          />
          <BttsMatchChart
            title="BTTS w meczach"
            teamName={teamName}
            points={chartMatches.map((match) => ({
              label: buildChartLabel(match),
              btts: match.btts,
            }))}
          />
        </div>
      </ExpandableSection>

      {TEAM_MATCH_STAT_CHARTS.map((definition) => (
        <ExpandableSection
          key={definition.expanderTitle}
          title={definition.expanderTitle}
        >
          <TeamTripleStatCharts
            teamName={teamName}
            chartMatches={chartMatches}
            buildLabel={buildChartLabel}
            definition={definition}
            thresholdLines={statLines[definition.key]}
          />
        </ExpandableSection>
      ))}

      <ExpandableSection title="Rezultaty meczów (1X2)">
        <TeamResultsChart
          teamName={teamName}
          results={chartMatches.map((match) => match.result)}
        />
      </ExpandableSection>
    </div>
  );
}
