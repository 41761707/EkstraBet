"use client";

import { useMemo, useState } from "react";
import { MatchCard } from "@/components/MatchCard";
import { BttsMatchChart } from "@/components/charts/BttsMatchChart";
import { TeamResultsChart } from "@/components/charts/TeamResultsChart";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { ExpandableSection } from "@/components/ExpandableSection";
import { StatusMessage } from "@/components/StatusMessage";
import { TeamFormStrip } from "@/components/TeamFormStrip";
import { TeamTripleStatCharts } from "@/components/teams/TeamTripleStatCharts";
import {
  buildDefaultStatLines,
  resolvePerspectiveSliderLabel,
  TEAM_MATCH_STAT_CHARTS,
  TEAM_MATCH_STAT_PERSPECTIVES,
  type TeamMatchStatLineKey,
  type TeamMatchStatPerspective,
} from "@/components/teams/teamMatchStatsConfig";
import {
  resolveLookbackBounds,
  TEAM_OU_LINE_DEFAULT,
  TEAM_OU_LINE_MAX,
  TEAM_OU_LINE_MIN,
  TEAM_OU_LINE_STEP,
} from "@/components/teams/teamChartConfig";
import { formatMatchDateShort } from "@/lib/format";
import type { MatchSummary, TeamSeasonMatchPoint } from "@/types/api";

interface TeamSeasonChartsSectionProps {
  teamId: number;
  teamName: string;
  seasonId: number;
  leagueId?: number;
  seasonMatches: TeamSeasonMatchPoint[];
  recentMatches: MatchSummary[];
}

function buildChartLabel(match: TeamSeasonMatchPoint): string {
  return `${match.opponent_shortcut} ${formatMatchDateShort(match.match_date)}`;
}

function resolveEffectiveLookback(
  lookback: number,
  bounds: ReturnType<typeof resolveLookbackBounds>,
): number {
  if (bounds.max <= 0) {
    return 0;
  }
  return Math.min(Math.max(lookback, bounds.min || 1), bounds.max);
}

export function TeamSeasonChartsSection({
  teamId,
  teamName,
  seasonId,
  leagueId,
  seasonMatches,
  recentMatches,
}: TeamSeasonChartsSectionProps) {
  const lookbackBounds = useMemo(
    () => resolveLookbackBounds(seasonMatches.length),
    [seasonMatches.length],
  );
  const [ouLine, setOuLine] = useState(TEAM_OU_LINE_DEFAULT);
  const [statLines, setStatLines] = useState(buildDefaultStatLines);
  const [lookback, setLookback] = useState(lookbackBounds.defaultValue);

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

  const effectiveLookback = resolveEffectiveLookback(lookback, lookbackBounds);

  const chartMatches = useMemo(() => {
    if (seasonMatches.length === 0) {
      return [];
    }
    return [...seasonMatches]
      .slice(0, effectiveLookback)
      .reverse();
  }, [effectiveLookback, seasonMatches]);

  const displayedRecentMatches = useMemo(
    () => recentMatches.slice(0, effectiveLookback),
    [effectiveLookback, recentMatches],
  );

  const form = useMemo(
    () => chartMatches.map((match) => match.result),
    [chartMatches],
  );

  if (seasonMatches.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak meczów do wykresów"
        message="Nie znaleziono rozegranych meczów w wybranym sezonie."
      />
    );
  }

  return (
    <div className="space-y-4">
      <ExpandableSection title="Konfiguracja analizy" defaultOpen>
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-slate-200">
                  Linia Over/Under
                </span>
                <span className="font-semibold text-white">
                  {ouLine.toFixed(1)}
                </span>
              </div>
              <input
                type="range"
                min={TEAM_OU_LINE_MIN}
                max={TEAM_OU_LINE_MAX}
                step={TEAM_OU_LINE_STEP}
                value={ouLine}
                onChange={(event) => setOuLine(Number(event.target.value))}
                className="w-full accent-sky-400"
              />
              <p className="text-xs text-slate-500">
                Próg dla wykresu bramek i hitrate Over.
              </p>
            </label>

            <label className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-4 text-sm text-slate-300">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-slate-200">
                  Liczba analizowanych spotkań wstecz
                </span>
                <span className="font-semibold text-white">
                  {lookback === lookbackBounds.max
                    ? `Cały sezon (${lookback})`
                    : lookback}
                </span>
              </div>
              <input
                type="range"
                min={lookbackBounds.min}
                max={lookbackBounds.max}
                step={1}
                value={lookback}
                onChange={(event) => setLookback(Number(event.target.value))}
                className="w-full accent-sky-400"
              />
              <p className="text-xs text-slate-500">
                Domyślnie cały sezon. Zmniejsz wartość, aby zobaczyć ostatnią
                tendencję.
              </p>
            </label>
          </div>

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
                          {resolvePerspectiveSliderLabel(
                            perspective,
                            teamName,
                          )}
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
                      <p className="text-xs text-slate-500">
                        Próg dla wykresu:{" "}
                        {perspective === "team"
                          ? definition.teamChartTitle.toLowerCase()
                          : perspective === "opponent"
                            ? definition.opponentChartTitle.toLowerCase()
                            : definition.totalChartTitle.toLowerCase()}
                        .
                      </p>
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
        <ExpandableSection key={definition.expanderTitle} title={definition.expanderTitle}>
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

      <ExpandableSection
        title={`Ostatnie mecze (${displayedRecentMatches.length})`}
      >
        {displayedRecentMatches.length === 0 ? (
          <StatusMessage
            variant="empty"
            title="No recent matches"
            message="No played matches found for the selected lookback."
          />
        ) : (
          <div className="grid gap-3">
            {displayedRecentMatches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                highlightTeamId={teamId}
                seasonId={seasonId}
                leagueId={leagueId}
              />
            ))}
          </div>
        )}
      </ExpandableSection>
    </div>
  );
}
