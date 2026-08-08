"use client";

import { useEffect, useState } from "react";
import { ProjectedSeasonStandingsTable } from "@/components/leagues/ProjectedSeasonStandingsTable";
import { shouldFetchSeasonProjection } from "@/components/leagues/projectedSeasonStandingsModel";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getSeasonProjection } from "@/lib/apiClient";
import { formatMatchDateTime } from "@/lib/format";
import type { SeasonProjectionResponse } from "@/types/api";

interface ProjectedSeasonStandingsSectionProps {
  leagueId: number;
  seasonId: number;
}

function ProjectionMeta({ data }: { data: SeasonProjectionResponse }) {
  return (
    <div className="space-y-2 text-sm text-slate-400">
      <p>
        Obliczono: {formatMatchDateTime(data.generated_at)} · tryb: od teraz ·{" "}
        {data.n_trials} triali · model {data.model_name} {data.model_version}
      </p>
      <p>
        Stałe mecze: {data.fixed_matches} · losowane: {data.simulated_matches}
      </p>
      <p className="text-slate-500">
        P05–P95 to stabilniejszy zakres punktów niż Min–Max. Min/Max to
        ekstrema z skończonej liczby symulacji Monte Carlo.
      </p>
    </div>
  );
}

export function ProjectedSeasonStandingsContent({
  loading,
  error,
  isNotFound,
  data,
  leagueId,
  seasonId,
}: {
  loading: boolean;
  error: string | null;
  isNotFound: boolean;
  data: SeasonProjectionResponse | null;
  leagueId: number;
  seasonId: number;
}) {
  if (loading) {
    return <LoadingSpinner label="Ładowanie projekcji sezonu..." />;
  }

  if (isNotFound) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak gotowej projekcji"
        message="Dla wybranego sezonu nie ma jeszcze zapisanej projekcji końca sezonu."
      />
    );
  }

  if (error) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się pobrać projekcji"
        message={error}
      />
    );
  }

  if (!data) {
    return (
      <p className="text-sm text-slate-500">
        Otwórz sekcję, aby pobrać projekcję końca sezonu.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {data.is_stale ? (
        <StatusMessage
          variant="info"
          title="Dane mogą być nieaktualne"
          message="Terminarz lub wyniki zmieniły się od ostatniego obliczenia. Wyświetlamy ostatnią zapisaną projekcję."
        />
      ) : null}
      <ProjectionMeta data={data} />
      <ProjectedSeasonStandingsTable
        standings={data.standings}
        seasonId={seasonId}
        leagueId={leagueId}
      />
    </div>
  );
}

export function ProjectedSeasonStandingsSection({
  leagueId,
  seasonId,
}: ProjectedSeasonStandingsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState<SeasonProjectionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isNotFound, setIsNotFound] = useState(false);

  useEffect(() => {
    setData(null);
    setError(null);
    setIsNotFound(false);
  }, [leagueId, seasonId]);

  useEffect(() => {
    if (!shouldFetchSeasonProjection(isOpen, data !== null)) {
      return;
    }

    let cancelled = false;

    async function loadProjection() {
      setLoading(true);
      setError(null);
      setIsNotFound(false);
      try {
        const response = await getSeasonProjection(leagueId, seasonId);
        if (!cancelled) {
          setData(response);
        }
      } catch (loadError) {
        if (cancelled) {
          return;
        }
        if (loadError instanceof ApiError && loadError.status === 404) {
          setIsNotFound(true);
          return;
        }
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Nie udało się pobrać projekcji sezonu.",
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadProjection();

    return () => {
      cancelled = true;
    };
  }, [isOpen, data, leagueId, seasonId]);

  return (
    <details
      className="group min-w-0 overflow-hidden rounded-xl border border-slate-700/80 bg-slate-900/50"
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 text-base font-semibold text-sky-300 transition hover:bg-slate-800/40 [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 break-words">
          Projekcja końca sezonu
        </span>
        <span
          className="shrink-0 text-slate-500 transition group-open:rotate-180"
          aria-hidden="true"
        >
          ▾
        </span>
      </summary>
      <div className="min-w-0 border-t border-slate-700/80 px-5 py-4 text-slate-300">
        <ProjectedSeasonStandingsContent
          loading={loading}
          error={error}
          isNotFound={isNotFound}
          data={data}
          leagueId={leagueId}
          seasonId={seasonId}
        />
      </div>
    </details>
  );
}
