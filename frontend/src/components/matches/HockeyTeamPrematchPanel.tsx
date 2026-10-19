"use client";

import { HockeyTeamPrematchCharts } from "@/components/matches/HockeyTeamPrematchCharts";
import { StatusMessage } from "@/components/StatusMessage";
import type { HockeyScheduleSide, TeamSeasonMatchPoint } from "@/types/api";

interface HockeyTeamPrematchPanelProps {
  teamName: string;
  history: TeamSeasonMatchPoint[];
  lookback: number;
  ouLine: number;
  schedule?: HockeyScheduleSide | null;
}

function completedGamesLast7Days(gamesLast7Days: number): number {
  // Cecha modelu dolicza bieżący, jeszcze nierozegrany mecz.
  return Math.max(0, gamesLast7Days - 1);
}

function formatRestDays(restDays: number, isB2b: boolean): string {
  // 0 bez B2B to brak wcześniejszego meczu, nie gra tego samego dnia
  if (restDays <= 0 && !isB2b) {
    return "brak poprzedniego meczu";
  }
  if (restDays === 1) {
    return "1 dzień";
  }
  return `${restDays} dni`;
}

function ScheduleStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-subtle">{label}</p>
      <p className="mt-1 text-lg font-semibold text-text">{value}</p>
    </div>
  );
}

function HockeyScheduleContextCard({ side }: { side: HockeyScheduleSide }) {
  return (
    <div className="grid gap-3 rounded-xl border border-border bg-surface p-4 sm:grid-cols-3">
      <ScheduleStat
        label="Dni odpoczynku"
        value={formatRestDays(side.rest_days, side.is_b2b)}
      />
      <ScheduleStat label="Back-to-back" value={side.is_b2b ? "Tak" : "Nie"} />
      <ScheduleStat
        label="Mecze w ostatnich 7 dniach"
        value={String(completedGamesLast7Days(side.games_last_7_days))}
      />
    </div>
  );
}

export function HockeyTeamPrematchPanel({
  teamName,
  history,
  lookback,
  ouLine,
  schedule = null,
}: HockeyTeamPrematchPanelProps) {
  const scheduleCard = schedule ? (
    <HockeyScheduleContextCard side={schedule} />
  ) : null;

  if (history.length === 0) {
    return (
      <div className="min-w-0 space-y-4">
        {scheduleCard}
        <StatusMessage
          variant="empty"
          title="Brak historii meczów"
          message={`Nie znaleziono rozegranych meczów przed datą spotkania dla ${teamName}.`}
        />
      </div>
    );
  }

  return (
    <div className="min-w-0 space-y-4">
      {scheduleCard}
      <HockeyTeamPrematchCharts
        teamName={teamName}
        history={history}
        lookback={lookback}
        ouLine={ouLine}
      />
    </div>
  );
}
