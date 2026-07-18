"use client";

import Link from "next/link";
import { useState } from "react";
import {
  PlayerPanel,
  PlayersStatConfig,
} from "@/components/players/PlayerPanel";
import {
  PlayersFilters,
  type PlayersFilterValues,
} from "@/components/players/PlayersFilters";
import { getConfigurablePlayerStats } from "@/components/players/playerStatsConfig";
import { FOOTBALL_SPORT_ID, HOCKEY_SPORT_ID } from "@/lib/playerFilterParams";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  FootballPlayerSummary,
  PlayerStatKey,
  PlayerCountryOption,
  PlayerSeasonOption,
  PlayerTeamOption,
} from "@/types/api";

interface FootballPlayersSectionProps {
  countries: PlayerCountryOption[];
  teams: PlayerTeamOption[];
  seasons: PlayerSeasonOption[];
  players: FootballPlayerSummary[];
  filters: PlayersFilterValues;
  initialSelectedStats: PlayerStatKey[];
}

function buildDefaultThresholdLines(): Partial<
  Record<PlayerStatKey, number>
> {
  return Object.fromEntries(
    [
      ...getConfigurablePlayerStats(FOOTBALL_SPORT_ID),
      ...getConfigurablePlayerStats(HOCKEY_SPORT_ID),
    ].map((stat) => [stat.key, stat.defaultLine]),
  ) as Partial<Record<PlayerStatKey, number>>;
}

export function FootballPlayersSection({
  countries,
  teams,
  seasons,
  players,
  filters,
  initialSelectedStats,
}: FootballPlayersSectionProps) {
  const [selectedStats, setSelectedStats] =
    useState<PlayerStatKey[]>(initialSelectedStats);
  const [thresholdLines, setThresholdLines] = useState(
    buildDefaultThresholdLines,
  );
  const configurableStats = getConfigurablePlayerStats(filters.sportId);

  return (
    <div className="space-y-6">
      <PlayersFilters
        countries={countries}
        teams={teams}
        seasons={seasons}
        values={filters}
      />

      <PlayersStatConfig
        stats={configurableStats}
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

      {players.length === 0 ? (
        <StatusMessage
          variant="info"
          title="Brak wyników"
          message="Brak zawodników dla wybranych filtrów."
        />
      ) : (
        <div className="space-y-3">
          {players.map((player) => (
            <PlayerPanel
              key={player.id}
              sportId={filters.sportId}
              playerId={player.id}
              playerName={player.common_name}
              playerPosition={player.position}
              seasonId={filters.seasonId ?? 0}
              matchLimit={filters.matchLimit}
              selectedStats={selectedStats}
              thresholdLines={thresholdLines}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface PlayersSportTabsProps {
  sports: {
    sport_id: number;
    label: string;
    emoji: string;
    available: boolean;
  }[];
  currentSportId: number;
}

export function PlayersSportTabs({
  sports,
  currentSportId,
}: PlayersSportTabsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {sports.map((sport) => {
        const isActive = sport.sport_id === currentSportId;
        const className = [
          "rounded-lg px-4 py-2 text-sm font-medium transition",
          isActive
            ? "bg-sky-500/20 text-sky-200 ring-1 ring-sky-400/40"
            : "bg-slate-900/60 text-slate-300 hover:bg-slate-800 hover:text-white",
          !sport.available ? "opacity-70" : "",
        ].join(" ");

        if (!sport.available) {
          return (
            <span
              key={sport.sport_id}
              className={className}
              title="Wkrótce w nowej wersji"
            >
              {sport.emoji} {sport.label}
              <span className="ml-1 text-xs text-slate-500">(wkrótce)</span>
            </span>
          );
        }

        return (
          <Link
            key={sport.sport_id}
            href={
              sport.sport_id === FOOTBALL_SPORT_ID
                ? "/players"
                : `/players?sport_id=${sport.sport_id}`
            }
            className={className}
          >
            {sport.emoji} {sport.label}
          </Link>
        );
      })}
    </div>
  );
}
