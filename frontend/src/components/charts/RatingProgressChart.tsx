"use client";

import { useState } from "react";
import {
  buildRatingProgressChartModel,
  type ChartPlotPoint,
  type ChartSeriesView,
  type RatingProgressChartModel,
} from "@/components/charts/ratingProgressChartModel";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { CHART_COLOR_NEUTRAL } from "@/lib/chartColors";
import type { TeamRatingProgress } from "@/types/api";

interface RatingProgressChartProps {
  teams: TeamRatingProgress[];
  lastPlayedAt?: string | null;
  title?: string;
  description?: string;
  /** External hover (e.g. legend pill); chart still manages its own pointer hover. */
  highlightedTeamId?: number | null;
  onHighlightedTeamIdChange?: (teamId: number | null) => void;
}

const DIMMED_STROKE = CHART_COLOR_NEUTRAL;
const DIMMED_OPACITY = 0.32;
const ACTIVE_STROKE_WIDTH = 3.25;
const DEFAULT_STROKE_WIDTH = 2.25;
const HIT_STROKE_WIDTH = 14;

function pointTitle(point: ChartPlotPoint, label: string): string {
  const rating = point.rating.toFixed(1);
  if (point.isBaseline) {
    return `${label}: start ${rating}`;
  }
  const matchSlot = `mecz ${point.axisIndex}`;
  const round =
    point.roundNumber !== null ? `, kolejka ${point.roundNumber}` : "";
  return `${label}: ${matchSlot}${round}, ${rating}`;
}

function ChartAxes({ model }: { model: RatingProgressChartModel }) {
  return (
    <g aria-hidden="true">
      <line
        x1={model.plotLeft}
        y1={model.plotBottom}
        x2={model.plotRight}
        y2={model.plotBottom}
        className="stroke-chart-axis"
        strokeWidth="1"
      />
      <line
        x1={model.plotLeft}
        y1={model.plotTop}
        x2={model.plotLeft}
        y2={model.plotBottom}
        className="stroke-chart-axis"
        strokeWidth="1"
      />
      {model.yTicks.map((tick) => (
        <g key={`y-${tick.label}-${tick.position}`}>
          <line
            x1={model.plotLeft}
            y1={tick.position}
            x2={model.plotRight}
            y2={tick.position}
            className="stroke-chart-grid"
            strokeWidth="1"
            strokeDasharray="3 4"
          />
          <text
            x={model.plotLeft - 8}
            y={tick.position}
            textAnchor="end"
            dominantBaseline="middle"
            className="fill-muted"
            fontSize="10"
          >
            {tick.label}
          </text>
        </g>
      ))}
      {model.xTicks.map((tick) => (
        <text
          key={`x-${tick.label}-${tick.position}`}
          x={tick.position}
          y={model.height - 12}
          textAnchor="middle"
          className="fill-muted"
          fontSize="10"
        >
          {tick.label}
        </text>
      ))}
    </g>
  );
}

function SeriesLayer({
  series,
  dimmed,
  active,
  onPointerEnter,
}: {
  series: ChartSeriesView;
  dimmed: boolean;
  active: boolean;
  onPointerEnter: () => void;
}) {
  const color = dimmed ? DIMMED_STROKE : series.color;
  const opacity = dimmed ? DIMMED_OPACITY : 1;
  const strokeWidth = active ? ACTIVE_STROKE_WIDTH : DEFAULT_STROKE_WIDTH;

  return (
    <g
      opacity={opacity}
      onPointerEnter={onPointerEnter}
      style={{ cursor: "pointer" }}
    >
      {series.pathD ? (
        <>
          {/* Wider invisible stroke so dense lines are easier to target. */}
          <path
            d={series.pathD}
            fill="none"
            stroke="transparent"
            strokeWidth={HIT_STROKE_WIDTH}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <path
            d={series.pathD}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </>
      ) : null}
      {series.points.map((point, index) => (
        <circle
          key={`${series.teamId}-${point.matchId ?? "start"}-${index}`}
          cx={point.x}
          cy={point.y}
          r={active ? (point.isBaseline ? 3.25 : 4) : point.isBaseline ? 2.5 : 3.25}
          fill={color}
        >
          <title>{pointTitle(point, series.label)}</title>
        </circle>
      ))}
      {series.endLabel ? (
        <g>
          {series.endLabel.showLeader ? (
            <line
              x1={series.endLabel.x - 8}
              y1={series.endLabel.markerY}
              x2={series.endLabel.x}
              y2={series.endLabel.labelY}
              stroke={color}
              strokeWidth="1"
              opacity={dimmed ? 1 : 0.75}
            />
          ) : null}
          <text
            x={series.endLabel.x}
            y={series.endLabel.labelY}
            dominantBaseline="middle"
            className="font-semibold"
            fill={color}
            fontSize={active ? 12 : 11}
          >
            {series.endLabel.text}
          </text>
        </g>
      ) : null}
    </g>
  );
}

function ChartSeries({
  model,
  highlightedTeamId,
  onHighlight,
}: {
  model: RatingProgressChartModel;
  highlightedTeamId: number | null;
  onHighlight: (teamId: number | null) => void;
}) {
  const ordered =
    highlightedTeamId === null
      ? model.series
      : [...model.series].sort((a, b) => {
          if (a.teamId === highlightedTeamId) return 1;
          if (b.teamId === highlightedTeamId) return -1;
          return 0;
        });

  return (
    <>
      {ordered.map((series) => {
        const active =
          highlightedTeamId !== null && highlightedTeamId === series.teamId;
        const dimmed =
          highlightedTeamId !== null && highlightedTeamId !== series.teamId;
        return (
          <SeriesLayer
            key={series.teamId}
            series={series}
            dimmed={dimmed}
            active={active}
            onPointerEnter={() => onHighlight(series.teamId)}
          />
        );
      })}
    </>
  );
}

export function RatingProgressChart({
  teams,
  lastPlayedAt = null,
  title = "Progres ELO w sezonie",
  description = "Wykres zmiany siły drużyn w wybranym sezonie.",
  highlightedTeamId = null,
  onHighlightedTeamIdChange,
}: RatingProgressChartProps) {
  const [localHighlight, setLocalHighlight] = useState<number | null>(null);
  const { preferences } = usePreferences();
  const controlled = onHighlightedTeamIdChange !== undefined;
  const activeHighlight = controlled ? highlightedTeamId : localHighlight;

  const setHighlight = (teamId: number | null) => {
    if (controlled) {
      onHighlightedTeamIdChange(teamId);
    } else {
      setLocalHighlight(teamId);
    }
  };

  if (teams.length === 0) {
    return null;
  }

  const model = buildRatingProgressChartModel(teams, {
    lastPlayedAt,
    teamNameDisplay: preferences.teamNameDisplay,
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface p-3">
      <svg
        viewBox={`0 0 ${model.width} ${model.height}`}
        className="min-h-[240px] w-full min-w-[520px] text-muted"
        role="img"
        aria-labelledby="rating-progress-title rating-progress-desc"
        onPointerLeave={() => setHighlight(null)}
      >
        <title id="rating-progress-title">{title}</title>
        <desc id="rating-progress-desc">{description}</desc>
        <ChartAxes model={model} />
        <ChartSeries
          model={model}
          highlightedTeamId={activeHighlight}
          onHighlight={setHighlight}
        />
      </svg>
    </div>
  );
}
