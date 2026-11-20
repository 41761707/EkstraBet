"use client";

import { useState } from "react";

import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import {
  playerChartPoints,
  PlayersStatConfig,
} from "@/components/players/PlayerPanel";
import { toProfileChartMatch } from "@/components/players/profileChartMatch";
import {
  HOCKEY_GOALIE_PLAYER_STATS,
  HOCKEY_SKATER_PLAYER_STATS,
  getStatDefinition,
  type PlayerStatDefinition,
} from "@/components/players/playerStatsConfig";
import { StatusMessage } from "@/components/StatusMessage";
import { parsePlayerStatKeys } from "@/lib/playerFilterParams";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import {
  HOCKEY_SPORT_ID,
  type HockeyPlayerMatchStat,
  type HockeyPlayerSliceMatch,
  type PlayerStatKey,
} from "@/types/api";

interface HockeyPlayerProfileChartsProps {
  playerName: string;
  playerRole: "skater" | "goalie";
  matches: HockeyPlayerSliceMatch[];
}

export function HockeyPlayerProfileCharts({
  playerName,
  playerRole,
  matches,
}: HockeyPlayerProfileChartsProps) {
  const { preferences } = usePreferences();
  const stats = statsForRole(playerRole);
  const [selectedStats, setSelectedStats] = useState<PlayerStatKey[]>(() =>
    initialStats(playerRole),
  );
  const [thresholdLines, setThresholdLines] = useState(() =>
    defaultLines(stats),
  );
  const chartMatches = [...matches].reverse().map(toProfileChartMatch);

  return (
    <div className="space-y-4">
      <PlayersStatConfig
        stats={stats}
        selectedStats={selectedStats}
        thresholdLines={thresholdLines}
        onSelectedStatsChange={setSelectedStats}
        onThresholdLineChange={(statKey, value) =>
          setThresholdLines((current) => ({
            ...current,
            [statKey]: value,
          }))
        }
      />
      {selectedStats.length === 0 ? (
        <StatusMessage
          variant="info"
          title="Brak wybranych statystyk"
          message="Wybierz statystyki do wyświetlenia w sekcji konfiguracji powyżej."
        />
      ) : (
        <ProfileChartGrid
          playerName={playerName}
          playerRole={playerRole}
          selectedStats={selectedStats}
          thresholdLines={thresholdLines}
          chartMatches={chartMatches}
          teamNameDisplay={preferences.teamNameDisplay}
        />
      )}
    </div>
  );
}

function ProfileChartGrid({
  playerName,
  playerRole,
  selectedStats,
  thresholdLines,
  chartMatches,
  teamNameDisplay,
}: {
  playerName: string;
  playerRole: "skater" | "goalie";
  selectedStats: PlayerStatKey[];
  thresholdLines: Partial<Record<PlayerStatKey, number>>;
  chartMatches: HockeyPlayerMatchStat[];
  teamNameDisplay: TeamNameDisplayPreference;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {selectedStats.map((statKey) => {
        const definition = getStatDefinition(
          statKey,
          HOCKEY_SPORT_ID,
          playerRole,
        );
        const threshold = thresholdLines[statKey] ?? definition.defaultLine;
        return (
          <VerticalStatChart
            key={statKey}
            title={definition.chartTitle}
            playerName={playerName}
            thresholdLine={threshold}
            points={playerChartPoints(
              chartMatches,
              statKey,
              teamNameDisplay,
            )}
          />
        );
      })}
    </div>
  );
}

function statsForRole(
  playerRole: "skater" | "goalie",
): PlayerStatDefinition[] {
  if (playerRole === "goalie") {
    return HOCKEY_GOALIE_PLAYER_STATS;
  }
  return HOCKEY_SKATER_PLAYER_STATS;
}

function initialStats(playerRole: "skater" | "goalie"): PlayerStatKey[] {
  if (playerRole === "goalie") {
    return HOCKEY_GOALIE_PLAYER_STATS.map((stat) => stat.key);
  }
  return parsePlayerStatKeys(undefined, HOCKEY_SPORT_ID);
}

function defaultLines(
  stats: readonly PlayerStatDefinition[],
): Partial<Record<PlayerStatKey, number>> {
  return Object.fromEntries(
    stats.map((stat) => [stat.key, stat.defaultLine]),
  );
}
