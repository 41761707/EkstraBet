"use client";

import { useEffect, useState } from "react";
import { VerticalStatChart } from "@/components/charts/VerticalStatChart";
import { PlayerGameLogTable } from "@/components/players/PlayerGameLogTable";
import {
  HOCKEY_GOALIE_PLAYER_STATS,
  type PlayerStatDefinition,
  getStatDefinition,
} from "@/components/players/playerStatsConfig";
import { PlayerSummaryTiles } from "@/components/players/PlayerSummaryTiles";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatusMessage } from "@/components/StatusMessage";
import { getPlayerMatchStats } from "@/lib/api";
import type {
  HockeyPlayerMatchStatsResponse,
  PlayerMatchStatsResponse,
  PlayerStatKey,
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

  const chartMatches = data ? [...data.matches].reverse() : [];
  const playerRole = getPlayerRole(data, playerPosition);
  const displayStats =
    playerRole === "goalie"
      ? HOCKEY_GOALIE_PLAYER_STATS.map((stat) => stat.key)
      : selectedStats;

  return (
    <details
      className="group rounded-xl border border-slate-700/80 bg-slate-900/50"
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-base font-semibold text-sky-300 transition hover:bg-slate-800/40 [&::-webkit-details-marker]:hidden">
        <span>{playerName}</span>
        <span
          className="text-slate-500 transition group-open:rotate-180"
          aria-hidden="true"
        >
          ▾
        </span>
      </summary>
      <div className="space-y-6 border-t border-slate-700/80 px-5 py-4">
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
          <>
            <PlayerSummaryTiles
              sportId={sportId}
              playerRole={playerRole}
              summary={data.summary}
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
                      points={chartMatches.map((match) => ({
                        label: `${match.opponent_shortcut} ${match.match_date}`,
                        value: getMatchStatValue(match, statKey),
                      }))}
                    />
                  );
                })}
              </div>
            )}

            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-white">
                Log meczowy
              </h4>
              <PlayerGameLogTable
                sportId={sportId}
                playerRole={playerRole}
                matches={data.matches}
                selectedStats={displayStats}
              />
            </div>
          </>
        ) : null}
      </div>
    </details>
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
    <div className="space-y-6 rounded-xl border border-slate-700/80 bg-slate-900/40 p-5">
      <div className="space-y-3">
        <h3 className="text-base font-semibold text-white">
          Statystyki do wyświetlania
        </h3>
        <div className="flex flex-wrap gap-3">
          {stats.map((stat) => {
            const inputId = `player-stat-${stat.key}`;
            return (
              <label
                key={stat.key}
                htmlFor={inputId}
                className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-300"
              >
                <input
                  id={inputId}
                  type="checkbox"
                  checked={selectedStats.includes(stat.key)}
                  onChange={() => toggleStat(stat.key)}
                  className="rounded border-slate-600 bg-slate-800 text-sky-500"
                />
                <span>{stat.label}</span>
              </label>
            );
          })}
        </div>
      </div>

      {statsWithSliders.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-base font-semibold text-white">
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
                  className="space-y-2 rounded-lg border border-slate-700/80 bg-slate-900/60 p-3 text-sm text-slate-300"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span>{definition.label}</span>
                    <span className="font-semibold text-white">
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
                    className="w-full accent-sky-400"
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

function getMatchStatValue(
  match: PlayerMatchStatsResponse["matches"][number],
  statKey: PlayerStatKey,
): number {
  const value = (
    match as unknown as Record<PlayerStatKey, number | null | undefined>
  )[statKey];
  return Number(value ?? 0);
}
