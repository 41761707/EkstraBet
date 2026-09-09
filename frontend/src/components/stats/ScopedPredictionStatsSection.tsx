"use client";

import { useState } from "react";

import { ExpandableSection } from "@/components/ExpandableSection";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { StatusMessage } from "@/components/StatusMessage";
import { AnalyticsCategoryPanel } from "@/components/stats/AnalyticsCategoryPanel";
import { ScopedPredictionStatsFilters } from "@/components/stats/ScopedPredictionStatsFilters";
import {
  EMPTY_SCOPED_PREDICTION_STATS_MESSAGE,
  type ScopedPredictionStatsFiltersState,
  type ScopedPredictionStatsScope,
} from "@/components/stats/scopedPredictionStatsModel";
import {
  useScopedPredictionStats,
  type ScopedPredictionStatsStatus,
} from "@/components/stats/useScopedPredictionStats";
import type { ModelsByFamily } from "@/lib/modelsByFamily";
import type { ModelAnalyticsResponse } from "@/types/api";

const SCOPED_CATEGORY_ORDER = ["ou", "btts", "result"] as const;

const SCOPED_CATEGORY_TITLES: Record<
  (typeof SCOPED_CATEGORY_ORDER)[number],
  string
> = {
  ou: "Over/Under",
  btts: "BTTS",
  result: "1X2",
};

const LOADING_SCOPED_STATS_LABEL = "Ładowanie statystyk predykcji...";
const ERROR_SCOPED_STATS_TITLE = "Nie udało się pobrać statystyk predykcji";
const EMPTY_SCOPED_STATS_TITLE = "Brak statystyk";
const IDLE_SCOPED_STATS_HINT =
  "Otwórz sekcję, aby pobrać statystyki predykcji.";

export function ScopedPredictionStatsSection(
  scope: ScopedPredictionStatsScope,
) {
  const [isOpen, setIsOpen] = useState(false);
  const stats = useScopedPredictionStats(scope, isOpen);

  return (
    <ExpandableSection
      title={scope.heading}
      defaultOpen={false}
      onToggle={setIsOpen}
    >
      <ScopedPredictionStatsContent
        description={scope.description}
        status={stats.status}
        error={stats.error}
        analytics={stats.analytics}
        modelsByFamily={stats.modelsByFamily}
        appliedFilters={stats.appliedFilters}
        onApply={stats.applyFilters}
      />
    </ExpandableSection>
  );
}

export interface ScopedPredictionStatsContentProps {
  description: string;
  status: ScopedPredictionStatsStatus;
  error: string | null;
  analytics: ModelAnalyticsResponse | null;
  modelsByFamily: ModelsByFamily;
  appliedFilters: ScopedPredictionStatsFiltersState;
  onApply: (filters: ScopedPredictionStatsFiltersState) => void;
}

export function ScopedPredictionStatsContent({
  description,
  status,
  error,
  analytics,
  modelsByFamily,
  appliedFilters,
  onApply,
}: ScopedPredictionStatsContentProps) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted">{description}</p>
      <ScopedPredictionStatsFiltersBlock
        status={status}
        modelsByFamily={modelsByFamily}
        appliedFilters={appliedFilters}
        onApply={onApply}
      />
      <ScopedPredictionStatsStatusView
        status={status}
        error={error}
        analytics={analytics}
      />
    </div>
  );
}

function ScopedPredictionStatsFiltersBlock({
  status,
  modelsByFamily,
  appliedFilters,
  onApply,
}: {
  status: ScopedPredictionStatsStatus;
  modelsByFamily: ModelsByFamily;
  appliedFilters: ScopedPredictionStatsFiltersState;
  onApply: (filters: ScopedPredictionStatsFiltersState) => void;
}) {
  if (status === "idle") {
    return null;
  }

  return (
    <ScopedPredictionStatsFilters
      resultModels={modelsByFamily.result}
      ouModels={modelsByFamily.ou}
      bttsModels={modelsByFamily.btts}
      values={appliedFilters}
      onApply={onApply}
      isLoading={status === "loading"}
    />
  );
}

function ScopedPredictionStatsStatusView({
  status,
  error,
  analytics,
}: {
  status: ScopedPredictionStatsStatus;
  error: string | null;
  analytics: ModelAnalyticsResponse | null;
}) {
  if (status === "idle") {
    return <p className="text-sm text-subtle">{IDLE_SCOPED_STATS_HINT}</p>;
  }

  if (status === "loading") {
    return <LoadingSpinner label={LOADING_SCOPED_STATS_LABEL} />;
  }

  if (status === "error") {
    return (
      <StatusMessage
        variant="error"
        title={ERROR_SCOPED_STATS_TITLE}
        message={scopedStatsErrorDetail(error)}
      />
    );
  }

  if (status === "empty" || analytics === null) {
    return (
      <StatusMessage
        variant="empty"
        title={EMPTY_SCOPED_STATS_TITLE}
        message={EMPTY_SCOPED_PREDICTION_STATS_MESSAGE}
      />
    );
  }

  return <ScopedPredictionStatsPanels analytics={analytics} />;
}

function scopedStatsErrorDetail(error: string | null): string | undefined {
  if (!error) {
    return undefined;
  }
  const withoutPeriod = error.endsWith(".") ? error.slice(0, -1) : error;
  if (withoutPeriod === ERROR_SCOPED_STATS_TITLE) {
    return undefined;
  }
  return error;
}

function ScopedPredictionStatsPanels({
  analytics,
}: {
  analytics: ModelAnalyticsResponse;
}) {
  return (
    <div className="space-y-10">
      {SCOPED_CATEGORY_ORDER.map((key) => {
        const category = analytics.categories[key];
        if (!category) {
          return null;
        }
        return (
          <AnalyticsCategoryPanel
            key={key}
            title={SCOPED_CATEGORY_TITLES[key]}
            category={category}
          />
        );
      })}
    </div>
  );
}
