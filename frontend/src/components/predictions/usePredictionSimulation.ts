"use client";

import { FormEvent, useState } from "react";

import { ApiError, previewPrediction } from "@/lib/api";
import type { PredictionPreviewResponse } from "@/types/api";

interface UsePredictionSimulationResult {
  homeTeamId: number;
  awayTeamId: number;
  leagueId: string;
  asOfDate: string;
  result: PredictionPreviewResponse | null;
  error: string | null;
  isSubmitting: boolean;
  setHomeTeamId: (value: number) => void;
  setAwayTeamId: (value: number) => void;
  setLeagueId: (value: string) => void;
  setAsOfDate: (value: string) => void;
  handleSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
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
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);

    if (homeTeamId === awayTeamId) {
      setError("Wybierz dwie różne drużyny.");
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
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Nie udało się wygenerować symulacji predykcji.",
      );
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
