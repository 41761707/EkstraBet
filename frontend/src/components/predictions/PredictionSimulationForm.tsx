"use client";

import { DateInput } from "@/components/filters/DateInput";
import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { PredictionSimulationResult } from "@/components/predictions/PredictionSimulationResult";
import { teamChartLabel } from "@/components/predictions/predictionChartModel";
import { usePredictionSimulation } from "@/components/predictions/usePredictionSimulation";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import type { TeamSummary } from "@/types/api";

interface PredictionSimulationFormProps {
  teams: TeamSummary[];
}

interface TeamSelectProps {
  label: string;
  value: number;
  teams: TeamSummary[];
  onChange: (value: number) => void;
}

function TeamSelect({ label, value, teams, onChange }: TeamSelectProps) {
  return (
    <label className="space-y-2 text-sm text-muted">
      <span className="block font-medium">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full rounded-md border border-border bg-page px-3 py-2 text-text"
      >
        {teams.map((team) => (
          <option key={team.id} value={team.id}>
            {team.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function findTeamLabel(
  teams: TeamSummary[],
  teamId: number,
  preference: TeamNameDisplayPreference,
): string {
  const team = teams.find((item) => item.id === teamId);
  if (!team) {
    return `Drużyna ${teamId}`;
  }
  return teamChartLabel(team, preference);
}

export function PredictionSimulationForm({
  teams,
}: PredictionSimulationFormProps) {
  const { preferences } = usePreferences();
  const initialAwayId = teams[1]?.id ?? teams[0]?.id ?? 0;
  const simulation = usePredictionSimulation(
    teams[0]?.id ?? 0,
    initialAwayId,
  );

  return (
    <div className="space-y-6">
      <form
        onSubmit={simulation.handleSubmit}
        className="grid gap-4 rounded-xl border border-border bg-surface p-5 md:grid-cols-2"
      >
        <TeamSelect
          label="Gospodarz"
          value={simulation.homeTeamId}
          teams={teams}
          onChange={simulation.setHomeTeamId}
        />
        <TeamSelect
          label="Gość"
          value={simulation.awayTeamId}
          teams={teams}
          onChange={simulation.setAwayTeamId}
        />

        <label className="space-y-2 text-sm text-muted">
          <span className="block font-medium">ID ligi (opcjonalnie)</span>
          <input
            type="number"
            min={1}
            value={simulation.leagueId}
            onChange={(event) => simulation.setLeagueId(event.target.value)}
            className="w-full rounded-md border border-border bg-page px-3 py-2 text-text"
          />
        </label>

        <div className="space-y-2 text-sm text-muted">
          <span className="block font-medium">Stan danych na dzień</span>
          <DateInput
            value={simulation.asOfDate}
            onChange={simulation.setAsOfDate}
            ariaLabel="Stan danych na dzień"
          />
        </div>

        <button
          type="submit"
          disabled={simulation.isSubmitting || teams.length < 2}
          className="rounded-md bg-accent px-4 py-2 font-semibold text-on-accent transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50 md:col-span-2"
        >
          {simulation.isSubmitting
            ? "Obliczanie predykcji…"
            : "Uruchom symulację"}
        </button>
      </form>

      {simulation.isSubmitting ? (
        <StatusMessage
          title="Trwa obliczanie"
          message="Modele przygotowują predykcję dla wybranej pary."
        />
      ) : null}

      {simulation.error ? (
        <StatusMessage
          title={
            simulation.error.unavailable
              ? "Symulacja niedostępna"
              : "Nie udało się obliczyć predykcji"
          }
          message={simulation.error.message}
          variant={simulation.error.unavailable ? "info" : "error"}
        />
      ) : null}

      {simulation.result ? (
        <PredictionSimulationResult
          result={simulation.result}
          homeTeamLabel={findTeamLabel(
            teams,
            simulation.homeTeamId,
            preferences.teamNameDisplay,
          )}
          awayTeamLabel={findTeamLabel(
            teams,
            simulation.awayTeamId,
            preferences.teamNameDisplay,
          )}
        />
      ) : null}
    </div>
  );
}
