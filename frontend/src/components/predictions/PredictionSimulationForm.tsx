"use client";

import { StatusMessage } from "@/components/StatusMessage";
import { PredictionSimulationResult } from "@/components/predictions/PredictionSimulationResult";
import { usePredictionSimulation } from "@/components/predictions/usePredictionSimulation";
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
    <label className="space-y-2 text-sm text-slate-300">
      <span className="block font-medium">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2 text-white"
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

export function PredictionSimulationForm({
  teams,
}: PredictionSimulationFormProps) {
  const initialAwayId = teams[1]?.id ?? teams[0]?.id ?? 0;
  const simulation = usePredictionSimulation(
    teams[0]?.id ?? 0,
    initialAwayId,
  );

  return (
    <div className="space-y-6">
      <form
        onSubmit={simulation.handleSubmit}
        className="grid gap-4 rounded-xl border border-slate-700 bg-slate-900/60 p-5 md:grid-cols-2"
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

        <label className="space-y-2 text-sm text-slate-300">
          <span className="block font-medium">ID ligi (opcjonalnie)</span>
          <input
            type="number"
            min={1}
            value={simulation.leagueId}
            onChange={(event) => simulation.setLeagueId(event.target.value)}
            className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2 text-white"
          />
        </label>

        <label className="space-y-2 text-sm text-slate-300">
          <span className="block font-medium">Stan danych na dzień</span>
          <input
            type="date"
            value={simulation.asOfDate}
            onChange={(event) => simulation.setAsOfDate(event.target.value)}
            className="w-full rounded-md border border-slate-600 bg-slate-950 px-3 py-2 text-white"
          />
        </label>

        <button
          type="submit"
          disabled={simulation.isSubmitting || teams.length < 2}
          className="rounded-md bg-sky-500 px-4 py-2 font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50 md:col-span-2"
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
          title="Nie udało się obliczyć predykcji"
          message={simulation.error}
          variant="error"
        />
      ) : null}

      {simulation.result ? (
        <PredictionSimulationResult result={simulation.result} />
      ) : null}
    </div>
  );
}
