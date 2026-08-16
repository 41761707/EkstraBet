import { useEffect, useState } from "react";

import {
  mapRatingProgressLoadError,
  type RatingProgressLoadStatus,
} from "@/components/leagues/ratingProgressLoadModel";
import { getLeagueRatingProgress } from "@/lib/apiClient";
import type { RatingProgressResponse } from "@/types/api";

interface LeagueRatingProgressState {
  status: RatingProgressLoadStatus;
  data: RatingProgressResponse | null;
  error: string | null;
  compute: () => void;
}

export function useLeagueRatingProgress(
  leagueId: number,
  seasonId: number,
): LeagueRatingProgressState {
  const [status, setStatus] = useState<RatingProgressLoadStatus>("idle");
  const [data, setData] = useState<RatingProgressResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState(0);

  useEffect(() => {
    setStatus("idle");
    setData(null);
    setError(null);
    setRequestId(0);
  }, [leagueId, seasonId]);

  useEffect(() => {
    if (requestId === 0) {
      return;
    }
    let cancelled = false;
    setStatus("loading");
    setError(null);
    void getLeagueRatingProgress(leagueId, seasonId)
      .then((response) => {
        if (cancelled) {
          return;
        }
        setData(response);
        setStatus("success");
      })
      .catch((loadError: unknown) => {
        if (cancelled) {
          return;
        }
        const mapped = mapRatingProgressLoadError(loadError);
        setData(null);
        setError(mapped.status === "error" ? mapped.message : null);
        setStatus(mapped.status);
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId, seasonId, requestId]);

  return {
    status,
    data,
    error,
    compute: () => setRequestId((current) => current + 1),
  };
}
