"use client";

import { ExpandableSection } from "@/components/ExpandableSection";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { RatingProgressView } from "@/components/leagues/RatingProgressView";
import {
  COMPUTE_RATING_PROGRESS_HINT,
  COMPUTE_RATING_PROGRESS_LABEL,
  EMPTY_RATING_PROGRESS_MESSAGE,
  EMPTY_RATING_PROGRESS_TITLE,
  ERROR_RATING_PROGRESS_TITLE,
  LOADING_RATING_PROGRESS_LABEL,
  type RatingProgressLoadStatus,
} from "@/components/leagues/ratingProgressLoadModel";
import { useLeagueRatingProgress } from "@/components/leagues/useLeagueRatingProgress";
import { StatusMessage } from "@/components/StatusMessage";
import type { RatingProgressResponse } from "@/types/api";

interface LeagueRatingProgressSectionProps {
  leagueId: number;
  seasonId: number;
}

interface RatingProgressLoadBodyProps {
  status: RatingProgressLoadStatus;
  data: RatingProgressResponse | null;
  error: string | null;
  onCompute: () => void;
}

const COMPUTE_BUTTON_CLASS =
  "rounded-full bg-accent px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-accent-hover";

export function RatingProgressIdlePanel({
  onCompute,
}: {
  onCompute: () => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">{COMPUTE_RATING_PROGRESS_HINT}</p>
      <button
        type="button"
        onClick={onCompute}
        className={COMPUTE_BUTTON_CLASS}
      >
        {COMPUTE_RATING_PROGRESS_LABEL}
      </button>
    </div>
  );
}

export function RatingProgressLoadBody({
  status,
  data,
  error,
  onCompute,
}: RatingProgressLoadBodyProps) {
  if (status === "idle") {
    return <RatingProgressIdlePanel onCompute={onCompute} />;
  }
  if (status === "loading") {
    return <LoadingSpinner label={LOADING_RATING_PROGRESS_LABEL} />;
  }
  if (status === "empty") {
    return (
      <StatusMessage
        variant="empty"
        title={EMPTY_RATING_PROGRESS_TITLE}
        message={EMPTY_RATING_PROGRESS_MESSAGE}
      />
    );
  }
  if (status === "error") {
    return (
      <div className="space-y-4">
        <StatusMessage
          variant="error"
          title={ERROR_RATING_PROGRESS_TITLE}
          message={error ?? undefined}
        />
        <button
          type="button"
          onClick={onCompute}
          className={COMPUTE_BUTTON_CLASS}
        >
          {COMPUTE_RATING_PROGRESS_LABEL}
        </button>
      </div>
    );
  }
  if (data === null) {
    return <RatingProgressIdlePanel onCompute={onCompute} />;
  }
  return <RatingProgressView data={data} />;
}

export function LeagueRatingProgressSection({
  leagueId,
  seasonId,
}: LeagueRatingProgressSectionProps) {
  const progress = useLeagueRatingProgress(leagueId, seasonId);
  return (
    <ExpandableSection title="Progres siły drużyn (ELO)">
      <RatingProgressLoadBody
        status={progress.status}
        data={progress.data}
        error={progress.error}
        onCompute={progress.compute}
      />
    </ExpandableSection>
  );
}
