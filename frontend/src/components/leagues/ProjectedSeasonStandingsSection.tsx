"use client";

import { useState } from "react";
import {
  EXPANDABLE_SECTION_BODY_CLASS_NAME,
  EXPANDABLE_SECTION_CHEVRON_CLASS_NAME,
  EXPANDABLE_SECTION_CLASS_NAME,
  EXPANDABLE_SECTION_SUMMARY_CLASS_NAME,
} from "@/components/expandableSectionStyles";
import { ProjectedSeasonStandingsTable } from "@/components/leagues/ProjectedSeasonStandingsTable";
import {
  availableSeasonProjectionModes,
  PROJECTION_COLUMN_LEGEND,
  SEASON_PROJECTION_MODE_LABELS,
} from "@/components/leagues/projectedSeasonStandingsModel";
import { useProjectedSeasonStandings } from "@/components/leagues/useProjectedSeasonStandings";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  SeasonProjectionMode,
  SeasonProjectionModeFlags,
  SeasonProjectionResponse,
} from "@/types/api";

interface ProjectedSeasonStandingsSectionProps {
  leagueId: number;
  seasonId: number;
}

interface ProjectedSeasonStandingsContentProps {
  loading: boolean;
  error: string | null;
  isNotFound: boolean;
  data: SeasonProjectionResponse | null;
  leagueId: number;
  seasonId: number;
  modeFlags: Pick<
    SeasonProjectionModeFlags,
    "from_now" | "from_season_start"
  > | null;
  selectedMode: SeasonProjectionMode | null;
  onSelectMode: (mode: SeasonProjectionMode) => void;
}

const MODE_BUTTON_ACTIVE =
  "rounded-full bg-accent px-3 py-1.5 text-sm text-on-accent transition hover:bg-accent-hover";
const MODE_BUTTON_IDLE =
  "rounded-full bg-surface px-3 py-1.5 text-sm text-muted transition hover:bg-surface-muted";

export function ProjectionModeToggle({
  flags,
  selectedMode,
  onSelectMode,
}: {
  flags: Pick<SeasonProjectionModeFlags, "from_now" | "from_season_start">;
  selectedMode: SeasonProjectionMode | null;
  onSelectMode: (mode: SeasonProjectionMode) => void;
}) {
  const modes = availableSeasonProjectionModes(flags);
  if (modes.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {modes.map((mode) => (
        <button
          key={mode}
          type="button"
          onClick={() => onSelectMode(mode)}
          className={
            selectedMode === mode ? MODE_BUTTON_ACTIVE : MODE_BUTTON_IDLE
          }
          aria-pressed={selectedMode === mode}
        >
          {SEASON_PROJECTION_MODE_LABELS[mode]}
        </button>
      ))}
    </div>
  );
}

export function ProjectionColumnLegend() {
  return (
    <dl className="grid gap-x-4 gap-y-1 text-xs text-subtle sm:grid-cols-2">
      {PROJECTION_COLUMN_LEGEND.map((item) => (
        <div key={item.symbol} className="flex gap-2">
          <dt className="shrink-0 font-semibold text-muted">{item.symbol}</dt>
          <dd>{item.meaning}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ProjectedSeasonStandingsContent({
  loading,
  error,
  isNotFound,
  data,
  leagueId,
  seasonId,
  modeFlags,
  selectedMode,
  onSelectMode,
}: ProjectedSeasonStandingsContentProps) {
  return (
    <div className="space-y-4">
      {modeFlags ? (
        <ProjectionModeToggle
          flags={modeFlags}
          selectedMode={selectedMode}
          onSelectMode={onSelectMode}
        />
      ) : null}
      <ProjectionBody
        loading={loading}
        error={error}
        isNotFound={isNotFound}
        data={data}
        leagueId={leagueId}
        seasonId={seasonId}
      />
    </div>
  );
}

function ProjectionBody({
  loading,
  error,
  isNotFound,
  data,
  leagueId,
  seasonId,
}: Omit<
  ProjectedSeasonStandingsContentProps,
  "modeFlags" | "selectedMode" | "onSelectMode"
>) {
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
      <p className="text-sm text-subtle">
        Otwórz sekcję, aby pobrać projekcję końca sezonu.
      </p>
    );
  }

  return (
    <>
      {data.is_stale ? (
        <StatusMessage
          variant="info"
          title="Dane mogą być nieaktualne"
          message="Terminarz lub wyniki zmieniły się od ostatniego obliczenia. Wyświetlamy ostatnią zapisaną projekcję."
        />
      ) : null}
      <ProjectionColumnLegend />
      <ProjectedSeasonStandingsTable
        standings={data.standings}
        seasonId={seasonId}
        leagueId={leagueId}
      />
    </>
  );
}

export function ProjectedSeasonStandingsSection({
  leagueId,
  seasonId,
}: ProjectedSeasonStandingsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const projection = useProjectedSeasonStandings(leagueId, seasonId, isOpen);

  return (
    <details
      className={EXPANDABLE_SECTION_CLASS_NAME}
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
    >
      <summary className={EXPANDABLE_SECTION_SUMMARY_CLASS_NAME}>
        <span className="min-w-0 break-words">Projekcja końca sezonu</span>
        <span
          className={EXPANDABLE_SECTION_CHEVRON_CLASS_NAME}
          aria-hidden="true"
        >
          ▾
        </span>
      </summary>
      <div className={EXPANDABLE_SECTION_BODY_CLASS_NAME}>
        <ProjectedSeasonStandingsContent
          loading={projection.loading && projection.data === null}
          error={projection.error}
          isNotFound={projection.isNotFound}
          data={projection.data}
          leagueId={leagueId}
          seasonId={seasonId}
          modeFlags={projection.modeFlags}
          selectedMode={projection.selectedMode}
          onSelectMode={projection.selectMode}
        />
      </div>
    </details>
  );
}
