"use client";

import { useMemo, useState } from "react";

import { RatingProgressChart } from "@/components/charts/RatingProgressChart";
import {
  colorForTeam,
  DEFAULT_VISIBLE_TEAMS,
  filterTeamsByIds,
  selectBottomTeamIds,
  selectDefaultTeamIds,
  sortTeamsByCurrentRating,
  teamDisplayLabel,
} from "@/components/charts/ratingProgressChartModel";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  RatingProgressResponse,
  TeamRatingProgress,
} from "@/types/api";

type SelectionPreset = "top" | "bottom" | "all" | "custom";

const PRESET_BUTTON_ACTIVE =
  "rounded-full bg-sky-600 px-3 py-1.5 text-sm text-white transition hover:bg-sky-500";
const PRESET_BUTTON_IDLE =
  "rounded-full bg-slate-800 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-700";

function formatRating(value: number): string {
  return value.toFixed(1);
}

function formatChange(value: number): string {
  const rounded = value.toFixed(1);
  if (value > 0) {
    return `+${rounded}`;
  }
  return rounded;
}

function changeClassName(value: number): string {
  if (value > 0) {
    return "text-emerald-400";
  }
  if (value < 0) {
    return "text-rose-400";
  }
  return "text-slate-300";
}

function LeaderCard({
  title,
  team,
}: {
  title: string;
  team: TeamRatingProgress | null;
}) {
  if (!team) {
    return null;
  }
  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-900/40 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-sm font-semibold text-white">
        {teamDisplayLabel(team)}
      </p>
      <p className={`mt-1 text-sm ${changeClassName(team.change)}`}>
        {formatChange(team.change)} ({formatRating(team.start_rating)} →{" "}
        {formatRating(team.current_rating)})
      </p>
    </div>
  );
}

function TeamSelector({
  teams,
  selectedIds,
  activePreset,
  highlightedTeamId,
  onToggle,
  onSelectTop,
  onSelectBottom,
  onSelectAll,
  onHighlightTeam,
}: {
  teams: TeamRatingProgress[];
  selectedIds: number[];
  activePreset: SelectionPreset;
  highlightedTeamId: number | null;
  onToggle: (teamId: number) => void;
  onSelectTop: () => void;
  onSelectBottom: () => void;
  onSelectAll: () => void;
  onHighlightTeam: (teamId: number | null) => void;
}) {
  const selected = new Set(selectedIds);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onSelectTop}
          className={
            activePreset === "top" ? PRESET_BUTTON_ACTIVE : PRESET_BUTTON_IDLE
          }
          aria-pressed={activePreset === "top"}
        >
          Top {DEFAULT_VISIBLE_TEAMS}
        </button>
        <button
          type="button"
          onClick={onSelectBottom}
          className={
            activePreset === "bottom" ? PRESET_BUTTON_ACTIVE : PRESET_BUTTON_IDLE
          }
          aria-pressed={activePreset === "bottom"}
        >
          Bot {DEFAULT_VISIBLE_TEAMS}
        </button>
        <button
          type="button"
          onClick={onSelectAll}
          className={
            activePreset === "all" ? PRESET_BUTTON_ACTIVE : PRESET_BUTTON_IDLE
          }
          aria-pressed={activePreset === "all"}
        >
          Wszystkie
        </button>
      </div>
      <div
        className="flex flex-wrap gap-2"
        onPointerLeave={() => onHighlightTeam(null)}
      >
        {teams.map((team) => {
          const isSelected = selected.has(team.team_id);
          const color = colorForTeam(team.team_id);
          const isDimmed =
            highlightedTeamId !== null &&
            highlightedTeamId !== team.team_id &&
            isSelected;
          return (
            <button
              key={team.team_id}
              type="button"
              onClick={() => onToggle(team.team_id)}
              onPointerEnter={() => {
                if (isSelected) {
                  onHighlightTeam(team.team_id);
                }
              }}
              className={`rounded-full border px-3 py-1.5 text-sm transition ${
                isSelected
                  ? "border-transparent text-white"
                  : "border-slate-700 bg-slate-900/60 text-slate-400 hover:border-slate-500"
              }`}
              style={
                isSelected
                  ? {
                      backgroundColor: isDimmed ? "#64748b" : color,
                      opacity: isDimmed ? 0.45 : 1,
                    }
                  : { borderColor: `${color}66` }
              }
            >
              {teamDisplayLabel(team)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RatingSummaryTable({ teams }: { teams: TeamRatingProgress[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-700/80">
      <table className="min-w-full text-left text-sm text-slate-300">
        <thead className="bg-slate-900/80 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">#</th>
            <th className="px-3 py-2 font-medium">Drużyna</th>
            <th className="px-3 py-2 font-medium">Start</th>
            <th className="px-3 py-2 font-medium">Bieżący</th>
            <th className="px-3 py-2 font-medium">Zmiana</th>
          </tr>
        </thead>
        <tbody>
          {teams.map((team) => (
            <tr key={team.team_id} className="border-t border-slate-800/80">
              <td className="px-3 py-2">{team.current_rank}</td>
              <td className="px-3 py-2">
                <span
                  className="mr-2 inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: colorForTeam(team.team_id) }}
                  aria-hidden="true"
                />
                {team.team_name}
              </td>
              <td className="px-3 py-2 tabular-nums">
                {formatRating(team.start_rating)}
              </td>
              <td className="px-3 py-2 tabular-nums">
                {formatRating(team.current_rating)}
              </td>
              <td
                className={`px-3 py-2 tabular-nums ${changeClassName(team.change)}`}
              >
                {formatChange(team.change)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface RatingProgressViewProps {
  data: RatingProgressResponse;
}

export function RatingProgressView({ data }: RatingProgressViewProps) {
  const rankedTeams = useMemo(
    () => sortTeamsByCurrentRating(data.teams),
    [data.teams],
  );
  const [selectedIds, setSelectedIds] = useState(() =>
    selectDefaultTeamIds(rankedTeams),
  );
  const [activePreset, setActivePreset] = useState<SelectionPreset>("top");
  const [highlightedTeamId, setHighlightedTeamId] = useState<number | null>(
    null,
  );
  const visibleTeams = useMemo(
    () => filterTeamsByIds(rankedTeams, selectedIds),
    [rankedTeams, selectedIds],
  );

  const toggleTeam = (teamId: number) => {
    setActivePreset("custom");
    setSelectedIds((current) => {
      if (current.includes(teamId)) {
        if (highlightedTeamId === teamId) {
          setHighlightedTeamId(null);
        }
        return current.filter((id) => id !== teamId);
      }
      return [...current, teamId];
    });
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        Sezon {data.season_years} · metryka {data.metric.toUpperCase()} ·
        wartości zgodne z pipeline ML
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <LeaderCard title="Największy wzrost" team={data.biggest_rise} />
        <LeaderCard title="Największy spadek" team={data.biggest_fall} />
      </div>
      <TeamSelector
        teams={rankedTeams}
        selectedIds={selectedIds}
        activePreset={activePreset}
        highlightedTeamId={highlightedTeamId}
        onToggle={toggleTeam}
        onSelectTop={() => {
          setActivePreset("top");
          setSelectedIds(selectDefaultTeamIds(rankedTeams));
          setHighlightedTeamId(null);
        }}
        onSelectBottom={() => {
          setActivePreset("bottom");
          setSelectedIds(selectBottomTeamIds(rankedTeams));
          setHighlightedTeamId(null);
        }}
        onSelectAll={() => {
          setActivePreset("all");
          setSelectedIds(rankedTeams.map((team) => team.team_id));
          setHighlightedTeamId(null);
        }}
        onHighlightTeam={setHighlightedTeamId}
      />
      {visibleTeams.length === 0 ? (
        <StatusMessage
          variant="empty"
          title="Brak wybranych drużyn"
          message="Zaznacz co najmniej jedną drużynę, aby zobaczyć wykres."
        />
      ) : (
        <RatingProgressChart
          teams={visibleTeams}
          lastPlayedAt={data.last_played_at}
          title={`Progres ELO — ${data.league_name} ${data.season_years}`}
          description="Interaktywny wykres zmiany ratingu ELO w sezonie. Oś X to kolejny mecz drużyny (1., 2., 3.… po dacie rozegrania), tooltip zawiera też numer kolejki. Najedź na linię lub legendę, aby wyróżnić drużynę."
          highlightedTeamId={highlightedTeamId}
          onHighlightedTeamIdChange={setHighlightedTeamId}
        />
      )}
      <RatingSummaryTable teams={visibleTeams} />
    </div>
  );
}
