"use client";

import {
  CHART_COLOR_DRAW,
  CHART_COLOR_NEGATIVE,
  CHART_COLOR_POSITIVE,
} from "@/lib/chartColors";
import type { MatchModelAssessment } from "@/types/api";
import {
  buildPieSlices,
  buildResultQualityNarrative,
  formatPercent,
  normalizeReplayPercents,
  pickPlayedBetterAssessment,
  verdictLabel,
  type ReplayCellSide,
} from "@/components/matches/playedBetterPresentation";

interface PlayedBetterAssessmentPanelProps {
  assessments: MatchModelAssessment[];
  homeTeamName: string;
  awayTeamName: string;
  homeGoals: number | null;
  awayGoals: number | null;
}

const SIDE_COLORS: Record<ReplayCellSide, string> = {
  home: CHART_COLOR_POSITIVE,
  draw: CHART_COLOR_DRAW,
  away: CHART_COLOR_NEGATIVE,
};

function ProbabilityPieChart({
  homePct,
  drawPct,
  awayPct,
  homeName,
  awayName,
}: {
  homePct: number;
  drawPct: number;
  awayPct: number;
  homeName: string;
  awayName: string;
}) {
  const slices = buildPieSlices({
    home: homePct,
    draw: drawPct,
    away: awayPct,
  });
  const legend = [
    { side: "home" as const, label: homeName, percent: homePct },
    { side: "draw" as const, label: "Remis jakości", percent: drawPct },
    { side: "away" as const, label: awayName, percent: awayPct },
  ];

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-6">
      <svg
        viewBox="0 0 100 100"
        className="h-36 w-36 shrink-0 drop-shadow-sm"
        role="img"
        aria-label={`Gospodarz ${homePct}%, remis ${drawPct}%, gość ${awayPct}%`}
      >
        {slices.map((slice) => {
          if (slice.isFullCircle) {
            return (
              <circle
                key={slice.side}
                cx="50"
                cy="50"
                r="42"
                fill={SIDE_COLORS[slice.side]}
              />
            );
          }
          if (!slice.path) {
            return null;
          }
          return (
            <path
              key={slice.side}
              d={slice.path}
              fill={SIDE_COLORS[slice.side]}
            />
          );
        })}
        <circle cx="50" cy="50" r="22" className="fill-slate-900" />
      </svg>

      <ul className="w-full space-y-2 text-sm">
        {legend.map((item) => (
          <li
            key={item.side}
            className="flex items-center justify-between gap-3 text-slate-300"
          >
            <span className="flex min-w-0 items-center gap-2">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: SIDE_COLORS[item.side] }}
                aria-hidden
              />
              <span className="truncate">{item.label}</span>
            </span>
            <span className="tabular-nums text-slate-200">{item.percent}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ProbabilityBar({
  homePct,
  drawPct,
  awayPct,
  homeName,
  awayName,
}: {
  homePct: number;
  drawPct: number;
  awayPct: number;
  homeName: string;
  awayName: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-slate-300">
        <span className="truncate pr-2">{homeName}</span>
        <span className="truncate pl-2 text-right">{awayName}</span>
      </div>
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full transition-[width] duration-500 ease-out"
          style={{ width: `${homePct}%`, backgroundColor: SIDE_COLORS.home }}
        />
        <div
          className="h-full transition-[width] duration-500 ease-out"
          style={{ width: `${drawPct}%`, backgroundColor: SIDE_COLORS.draw }}
        />
        <div
          className="h-full transition-[width] duration-500 ease-out"
          style={{ width: `${awayPct}%`, backgroundColor: SIDE_COLORS.away }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-400">
        <span>{homePct}%</span>
        <span>{drawPct}%</span>
        <span>{awayPct}%</span>
      </div>
    </div>
  );
}

export function PlayedBetterAssessmentPanel({
  assessments,
  homeTeamName,
  awayTeamName,
  homeGoals,
  awayGoals,
}: PlayedBetterAssessmentPanelProps) {
  const assessment = pickPlayedBetterAssessment(assessments);
  if (!assessment) {
    return null;
  }

  const percents = normalizeReplayPercents(
    assessment.home_played_better_probability,
    assessment.draw_probability,
    assessment.away_played_better_probability,
  );
  const homePct = percents.home;
  const drawPct = percents.draw;
  const awayPct = percents.away;
  const narrative = buildResultQualityNarrative(
    homeGoals,
    awayGoals,
    assessment.final_assessment,
    homeTeamName,
    awayTeamName,
  );
  const title = verdictLabel(
    assessment.final_assessment,
    homeTeamName,
    awayTeamName,
  );

  return (
    <section className="space-y-5 rounded-xl border border-slate-700/80 bg-slate-900/50 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-medium uppercase tracking-wide text-slate-400">
            Na podstawie statystyk: kto zagrał lepiej?
          </h3>
          <p className="mt-1 text-2xl font-semibold text-white">{title}</p>
        </div>
        {assessment.confidence !== null ? (
          <span className="rounded-full border border-slate-600/80 bg-slate-800/80 px-3 py-1 text-xs text-slate-200">
            Pewność werdyktu: {formatPercent(assessment.confidence)}
          </span>
        ) : null}
      </div>

      <ProbabilityPieChart
        homePct={homePct}
        drawPct={drawPct}
        awayPct={awayPct}
        homeName={homeTeamName}
        awayName={awayTeamName}
      />

      <ProbabilityBar
        homePct={homePct}
        drawPct={drawPct}
        awayPct={awayPct}
        homeName={homeTeamName}
        awayName={awayTeamName}
      />

      {narrative ? (
        <div className="rounded-lg border border-slate-700/60 bg-slate-800/40 px-4 py-3 text-sm text-slate-200">
          {narrative.text}
        </div>
      ) : null}

    </section>
  );
}
