"use client";

import { useEffect, useState } from "react";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { RATING_BASELINE } from "@/components/matches/hockeyGameRatingModel";
import { PlayerGameLogTable } from "@/components/players/PlayerGameLogTable";
import {
  HOCKEY_GOALIE_PLAYER_STATS,
  type PlayerStatDefinition,
  getStatDefinition,
} from "@/components/players/playerStatsConfig";
import { PlayerSummaryTiles } from "@/components/players/PlayerSummaryTiles";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { getPlayerMatchStats } from "@/lib/apiClient";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { formatTeamName } from "@/lib/teamNameDisplay";
import {
  HOCKEY_SPORT_ID,
  type FootballPlayerMatchStat,
  type HockeyPlayerMatchStat,
  type HockeyPlayerMatchStatsResponse,
  type PlayerMatchStatsResponse,
  type PlayerStatKey,
} from "@/types/api";

interface PlayerPanelProps {
  sportId: number;
  playerId: number;
  playerName: string;
  playerPosition: string | null;
  seasonId: number;
  matchLimit: number;
  selectedStats: PlayerStatKey[];
  thresholdLines: Partial<Record<PlayerStatKey, number>>;
}

/** True when the opponent hosted the match, so the player's club was away. */
export function playerPlayedAway(
  match: Pick<
    FootballPlayerMatchStat | HockeyPlayerMatchStat,
    "opponent_name" | "home_team"
  >,
): boolean {
  return match.opponent_name !== "" && match.opponent_name === match.home_team;
}

export function buildChartLabel(
  match: Pick<
    FootballPlayerMatchStat | HockeyPlayerMatchStat,
    "opponent_name" | "opponent_shortcut" | "match_date" | "home_team"
  >,
  preference: TeamNameDisplayPreference,
): string {
  const opponent = formatTeamName(
    match.opponent_name,
    match.opponent_shortcut,
    preference,
  );
  const awayMark = playerPlayedAway(match) ? "@" : "";
  return `${awayMark}${opponent} ${match.match_date}`;
}

export function PlayerPanel({
  sportId,
  playerId,
  playerName,
  playerPosition,
  seasonId,
  matchLimit,
  selectedStats,
  thresholdLines,
}: PlayerPanelProps) {
  const { preferences } = usePreferences();
  const teamNameDisplay = preferences.teamNameDisplay;
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState<PlayerMatchStatsResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
  }, [playerId, seasonId, matchLimit]);

  useEffect(() => {
    if (!isOpen || data) {
      return;
    }

    let cancelled = false;

    async function loadStats() {
      setLoading(true);
      setError(null);
      try {
        const response = await getPlayerMatchStats(sportId, playerId, {
          seasonId,
          limit: matchLimit,
        });
        if (!cancelled) {
          setData(response);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Nie udało się pobrać statystyk zawodnika.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadStats();

    return () => {
      cancelled = true;
    };
  }, [isOpen, data, sportId, playerId, seasonId, matchLimit]);

  return (
    <details
      className="group rounded-xl border border-border bg-surface"
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
    >
      <PlayerPanelSummary playerName={playerName} />
      <div className="space-y-6 border-t border-border px-5 py-4">
        {loading ? (
          <LoadingSpinner label="Ładowanie statystyk zawodnika..." />
        ) : null}
        {error ? (
          <StatusMessage
            variant="error"
            title="Błąd ładowania"
            message={error}
          />
        ) : null}
        {data ? (
          <PlayerPanelLoadedBody
            sportId={sportId}
            playerName={playerName}
            playerPosition={playerPosition}
            selectedStats={selectedStats}
            data={data}
            thresholdLines={thresholdLines}
            teamNameDisplay={teamNameDisplay}
          />
        ) : null}
      </div>
    </details>
  );
}

function PlayerPanelSummary({ playerName }: { playerName: string }) {
  return (
    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-base font-semibold text-accent-text transition hover:bg-surface-muted/40 [&::-webkit-details-marker]:hidden">
      <span>{playerName}</span>
      <span
        className="text-subtle transition group-open:rotate-180"
        aria-hidden="true"
      >
        ▾
      </span>
    </summary>
  );
}

function PlayerPanelLoadedBody({
  sportId,
  playerName,
  playerPosition,
  selectedStats,
  data,
  thresholdLines,
  teamNameDisplay,
}: {
  sportId: number;
  playerName: string;
  playerPosition: string | null;
  selectedStats: PlayerStatKey[];
  data: PlayerMatchStatsResponse;
  thresholdLines: Partial<Record<PlayerStatKey, number>>;
  teamNameDisplay: TeamNameDisplayPreference;
}) {
  const chartMatches = [...data.matches].reverse();
  const playerRole = getPlayerRole(data, playerPosition);
  const displayStats =
    playerRole === "goalie"
      ? HOCKEY_GOALIE_PLAYER_STATS.map((stat) => stat.key)
      : selectedStats;

  return (
    <>
      <PlayerSummaryTiles
        sportId={sportId}
        playerRole={playerRole}
        summary={data.summary}
        averageRating={
          isHockeyResponse(data)
            ? averageStoredRating(data.matches)
            : undefined
        }
      />

      {displayStats.length === 0 ? (
        <StatusMessage
          variant="info"
          title="Brak wybranych statystyk"
          message="Wybierz statystyki do wyświetlenia w sekcji konfiguracji powyżej."
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {displayStats.map((statKey) => {
            const definition = getStatDefinition(
              statKey,
              sportId,
              playerRole,
            );
            const threshold =
              thresholdLines[statKey] ?? definition.defaultLine;
            return (
              <VerticalStatChart
                key={statKey}
                title={definition.chartTitle}
                playerName={playerName}
                thresholdLine={threshold}
                points={playerChartPoints(
                  isHockeyResponse(data) ? chartMatches as HockeyPlayerMatchStat[] : chartMatches as FootballPlayerMatchStat[],
                  statKey,
                  teamNameDisplay,
                )}
              />
            );
          })}
        </div>
      )}

      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-text">Log meczowy</h4>
        <PlayerGameLogTable
          sportId={sportId}
          playerRole={playerRole}
          matches={data.matches}
          selectedStats={displayStats}
        />
      </div>
    </>
  );
}

export function PlayersStatConfig({
  stats,
  selectedStats,
  thresholdLines,
  onSelectedStatsChange,
  onThresholdLineChange,
}: {
  stats: PlayerStatDefinition[];
  selectedStats: PlayerStatKey[];
  thresholdLines: Partial<Record<PlayerStatKey, number>>;
  onSelectedStatsChange: (stats: PlayerStatKey[]) => void;
  onThresholdLineChange: (
    statKey: PlayerStatKey,
    value: number,
  ) => void;
}) {
  function toggleStat(statKey: PlayerStatKey) {
    if (selectedStats.includes(statKey)) {
      onSelectedStatsChange(selectedStats.filter((key) => key !== statKey));
      return;
    }
    onSelectedStatsChange([...selectedStats, statKey]);
  }

  const statsWithSliders = selectedStats.filter(
    (key) => stats.find((stat) => stat.key === key)?.hasLineSlider,
  );

  return (
    <div className="space-y-6 rounded-xl border border-border bg-surface p-5">
      <div className="space-y-3">
        <h3 className="text-base font-semibold text-text">
          Statystyki do wyświetlania
        </h3>
        <div className="flex flex-wrap gap-3">
          {stats.map((stat) => {
            const inputId = `player-stat-${stat.key}`;
            return (
              <label
                key={stat.key}
                htmlFor={inputId}
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-muted"
              >
                <input
                  id={inputId}
                  type="checkbox"
                  checked={selectedStats.includes(stat.key)}
                  onChange={() => toggleStat(stat.key)}
                  className="rounded border-border bg-surface-muted text-accent-text"
                />
                <span>{stat.label}</span>
              </label>
            );
          })}
        </div>
      </div>

      {statsWithSliders.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-base font-semibold text-text">
            Linie progowe dla wykresów
          </h3>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {statsWithSliders.map((statKey) => {
              const definition =
                stats.find((stat) => stat.key === statKey) ??
                getStatDefinition(statKey);
              const value = thresholdLines[statKey] ?? definition.defaultLine;
              return (
                <label
                  key={statKey}
                  className="space-y-2 rounded-lg border border-border bg-surface p-3 text-sm text-muted"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span>{definition.label}</span>
                    <span className="font-semibold text-text">
                      {value.toFixed(1)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={definition.minLine}
                    max={definition.maxLine}
                    step={definition.step}
                    value={value}
                    onChange={(event) =>
                      onThresholdLineChange(statKey, Number(event.target.value))
                    }
                    className="w-full accent-accent"
                  />
                </label>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function isHockeyResponse(
  data: PlayerMatchStatsResponse,
): data is HockeyPlayerMatchStatsResponse {
  return "player_role" in data;
}

function getPlayerRole(
  data: PlayerMatchStatsResponse | null,
  position: string | null,
): "skater" | "goalie" | undefined {
  if (data && isHockeyResponse(data)) {
    return data.player_role;
  }
  return position === "G" ? "goalie" : undefined;
}

/** Mean of stored ratings. A match without a row does not count as zero. */
export function averageStoredRating(
  matches: readonly { rating?: number | null }[],
): number | null {
  let sum = 0;
  let count = 0;
  for (const match of matches) {
    if (match.rating == null) {
      continue;
    }
    sum += match.rating;
    count += 1;
  }
  if (count === 0) {
    return null;
  }
  return sum / count;
}

export function playerChartPoints(
  matches: PlayerMatchStatsResponse["matches"],
  statKey: PlayerStatKey,
  teamNameDisplay: TeamNameDisplayPreference,
): { label: string; value: number }[] {
  const points: { label: string; value: number }[] = [];
  for (const match of matches) {
    if (statKey === "rating" && "rating" in match && match.rating == null) {
      continue;
    }
    const stored = getMatchStatValue(match, statKey);
    points.push({
      label: buildChartLabel(match, teamNameDisplay),
      value: statKey === "rating" ? stored + RATING_BASELINE : stored,
    });
  }
  return points;
}

function getMatchStatValue(
  match: PlayerMatchStatsResponse["matches"][number],
  statKey: PlayerStatKey,
): number {
  const value = (
    match as unknown as Record<PlayerStatKey, number | null | undefined>
  )[statKey];
  return Number(value ?? 0);
}
