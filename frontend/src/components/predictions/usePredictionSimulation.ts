"use client";

import { FormEvent, useState } from "react";

import { ApiError, previewPrediction } from "@/lib/apiClient";
import type { PredictionPreviewResponse } from "@/types/api";

/** Shown when preview is off in production or blocked by deploy config. */
export const SIMULATION_UNAVAILABLE_MESSAGE =
  "Symulacja predykcji jest obecnie niedostępna na środowisku produkcyjnym. Funkcja działa lokalnie i zostanie udostępniona w kolejnym etapie.";

interface SimulationError {
  message: string;
  unavailable: boolean;
}

interface UsePredictionSimulationResult {
  homeTeamId: number;
  awayTeamId: number;
  leagueId: string;
  asOfDate: string;
  result: PredictionPreviewResponse | null;
  error: SimulationError | null;
  isSubmitting: boolean;
  setHomeTeamId: (value: number) => void;
  setAwayTeamId: (value: number) => void;
  setLeagueId: (value: string) => void;
  setAsOfDate: (value: string) => void;
  handleSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
}

function isPreviewUnavailableError(error: ApiError): boolean {
  if (error.status === 503) {
    return true;
  }
  const detail = error.message.toLowerCase();
  return (
    detail.includes("origin is not allowed") ||
    detail.includes("ml prediction preview is disabled") ||
    detail.includes("ekstrabet_ml_preview") ||
    detail.includes("niedostępna na środowisku produkcyjnym")
  );
}

function toSimulationError(error: unknown): SimulationError {
  if (!(error instanceof ApiError)) {
    return {
      message: "Nie udało się wygenerować symulacji predykcji.",
      unavailable: false,
    };
  }
  if (isPreviewUnavailableError(error)) {
    return {
      message: SIMULATION_UNAVAILABLE_MESSAGE,
      unavailable: true,
    };
  }
  return { message: error.message, unavailable: false };
}

export function usePredictionSimulation(
  initialHomeTeamId: number,
  initialAwayTeamId: number,
): UsePredictionSimulationResult {
  const [homeTeamId, setHomeTeamId] = useState(initialHomeTeamId);
  const [awayTeamId, setAwayTeamId] = useState(initialAwayTeamId);
  const [leagueId, setLeagueId] = useState("");
  const [asOfDate, setAsOfDate] = useState("");
  const [result, setResult] = useState<PredictionPreviewResponse | null>(null);
  const [error, setError] = useState<SimulationError | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);

    if (homeTeamId === awayTeamId) {
      setError({
        message: "Wybierz dwie różne drużyny.",
        unavailable: false,
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = await previewPrediction({
        home_team_id: homeTeamId,
        away_team_id: awayTeamId,
        league_id: leagueId ? Number(leagueId) : undefined,
        as_of_date: asOfDate || undefined,
      });
      setResult(payload);
    } catch (requestError) {
      setError(toSimulationError(requestError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return {
    homeTeamId,
    awayTeamId,
    leagueId,
    asOfDate,
    result,
    error,
    isSubmitting,
    setHomeTeamId,
    setAwayTeamId,
    setLeagueId,
    setAsOfDate,
    handleSubmit,
  };
}
