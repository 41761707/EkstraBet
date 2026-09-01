"use client";

import { useState } from "react";

import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { formatMatchDateTime } from "@/lib/format";
import {
  ApiError,
  getTyperLongTermHistory,
  saveTyperLongTermPicks,
} from "@/lib/apiClient";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import {
  applySavedLongTermPicks,
  applySettledLongTermResult,
  canSaveLongTermPicks,
  formatLongTermChangeLine,
  formatLongTermHitsLabel,
  formatLongTermPointsLabel,
  formatLongTermTeamName,
  isLongTermMarketLockedForUi,
  isLongTermMarketSettled,
  lockLongTermMarket,
  longTermSaveErrorMessage,
  selectedTeams,
  takeRecentLongTermChanges,
  toggleLongTermTeamId,
  updateLongTermDashboardMarket,
} from "@/lib/typerLmLongTerm";
import type {
  LongTermAutoResultResponse,
  LongTermDashboardResponse,
  LongTermMarketCard,
} from "@/types/api";

import { TyperLmLongTermAdminPanel } from "./TyperLmLongTermAdminPanel";
import { TyperLmLongTermTeamPicker } from "./TyperLmLongTermTeamPicker";

interface TyperLmLongTermTabProps {
  dashboard: LongTermDashboardResponse | null;
  errorMessage?: string;
  isAdmin: boolean;
  autoResults: Record<number, LongTermAutoResultResponse | null>;
  nowMs?: number | null;
}

export function TyperLmLongTermTab({
  dashboard: initialDashboard,
  errorMessage,
  isAdmin,
  autoResults,
  nowMs = null,
}: TyperLmLongTermTabProps) {
  const { preferences } = usePreferences();
  const [dashboard, setDashboard] = useState(initialDashboard);

  if (errorMessage) {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się załadować długoterminowych"
        message={errorMessage}
      />
    );
  }
  if (dashboard === null || dashboard.markets.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak rynków długoterminowych"
        message="Administrator nie otworzył jeszcze rynku TOP 8."
      />
    );
  }

  return (
    <div className="space-y-6">
      {dashboard.markets.map((market) => (
        <article key={market.market_id} className="space-y-4">
          <TyperLmLongTermMarketCard
            market={market}
            nowMs={nowMs}
            teamNameDisplay={preferences.teamNameDisplay}
            onMarketChange={(next) =>
              setDashboard((current) =>
                current
                  ? updateLongTermDashboardMarket(
                      current,
                      market.market_id,
                      () => next,
                    )
                  : current,
              )
            }
          />
          {isAdmin ? (
            <TyperLmLongTermAdminPanel
              market={market}
              initialAutoResult={autoResults[market.market_id] ?? null}
              teamNameDisplay={preferences.teamNameDisplay}
              onSettled={(settled) =>
                setDashboard((current) =>
                  current
                    ? updateLongTermDashboardMarket(
                        current,
                        market.market_id,
                        (row) => applySettledLongTermResult(row, settled),
                      )
                    : current,
                )
              }
            />
          ) : null}
        </article>
      ))}
    </div>
  );
}

interface TyperLmLongTermMarketCardProps {
  market: LongTermMarketCard;
  nowMs: number | null;
  teamNameDisplay: TeamNameDisplayPreference;
  onMarketChange: (market: LongTermMarketCard) => void;
}

export function TyperLmLongTermMarketCard({
  market,
  nowMs,
  teamNameDisplay,
  onMarketChange,
}: TyperLmLongTermMarketCardProps) {
  const picks = useLongTermMarketPicks(market, nowMs, onMarketChange);
  const isLocked = isLongTermMarketLockedForUi(market, nowMs);
  const isSettled = isLongTermMarketSettled(market);

  return (
    <section className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <LongTermMarketHeader market={market} isLocked={isLocked} />
      {isSettled ? (
        <SettledResultSummary
          market={market}
          teamNameDisplay={teamNameDisplay}
        />
      ) : null}
      <TyperLmLongTermTeamPicker
        candidates={market.candidates}
        selectedIds={picks.selectedIds}
        selectionSize={market.selection_size}
        query={picks.query}
        isLocked={isLocked || picks.isPending || isSettled}
        resultTeamIds={market.result_team_ids}
        teamNameDisplay={teamNameDisplay}
        onQueryChange={picks.setQuery}
        onToggle={picks.toggleTeam}
      />
      <TyperLmLongTermMarketFooter
        market={market}
        isLocked={isLocked}
        isSettled={isSettled}
        canSave={picks.canSave}
        isPending={picks.isPending}
        errorMessage={picks.errorMessage}
        onSave={() => void picks.save()}
      />
    </section>
  );
}

function LongTermMarketHeader({
  market,
  isLocked,
}: {
  market: LongTermMarketCard;
  isLocked: boolean;
}) {
  const deadlineLabel = market.deadline_at
    ? formatMatchDateTime(market.deadline_at)
    : null;
  return (
    <header className="space-y-1">
      <h2 className="text-lg font-semibold text-text">{market.title}</h2>
      {market.description ? (
        <p className="text-sm text-muted">{market.description}</p>
      ) : null}
      <p className="text-xs text-muted">
        {isLocked
          ? "Typowanie zablokowane"
          : deadlineLabel
            ? `Zapis do ${deadlineLabel}`
            : "Zapis do startu fazy ligowej"}
      </p>
    </header>
  );
}

function SettledResultSummary({
  market,
  teamNameDisplay,
}: {
  market: LongTermMarketCard;
  teamNameDisplay: TeamNameDisplayPreference;
}) {
  const hitsLabel = formatLongTermHitsLabel(market);
  const official = selectedTeams(market.candidates, market.result_team_ids);
  return (
    <div className="space-y-2 text-sm text-text">
      <p>
        Wynik zatwierdzony
        {hitsLabel ? ` · ${hitsLabel}` : ""} · {formatLongTermPointsLabel(market)}
      </p>
      {official.length > 0 ? (
        <p className="text-muted">
          Oficjalny TOP 8:{" "}
          {official
            .map((team) => formatLongTermTeamName(team, teamNameDisplay))
            .join(", ")}
        </p>
      ) : null}
    </div>
  );
}

export function TyperLmLongTermMarketFooter({
  market,
  isLocked,
  isSettled,
  canSave,
  isPending,
  errorMessage,
  onSave,
}: {
  market: LongTermMarketCard;
  isLocked: boolean;
  isSettled: boolean;
  canSave: boolean;
  isPending: boolean;
  errorMessage: string | null;
  onSave: () => void;
}) {
  const recentChanges = takeRecentLongTermChanges(market.changes);
  return (
    <div className="space-y-2">
      {isSettled || isLocked ? null : (
        <button
          type="button"
          disabled={!canSave}
          onClick={onSave}
          className={
            "rounded-lg bg-accent px-3 py-2 text-sm font-medium " +
            "text-on-accent disabled:opacity-50"
          }
        >
          Zapisz typ
        </button>
      )}
      {isPending ? (
        <p className="text-sm text-accent-text" role="status">
          Zapisywanie typu…
        </p>
      ) : null}
      {errorMessage ? (
        <p className="text-sm text-danger-text" role="alert">
          {errorMessage}
        </p>
      ) : null}
      {recentChanges.length > 0 ? (
        <ul className="space-y-1 text-xs text-subtle">
          {recentChanges.map((change) => (
            <li key={`${change.id}-${change.changed_at}`}>
              {formatLongTermChangeLine(change)}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function useLongTermMarketPicks(
  market: LongTermMarketCard,
  nowMs: number | null,
  onMarketChange: (market: LongTermMarketCard) => void,
) {
  const [selectedIds, setSelectedIds] = useState(() => [
    ...market.picked_team_ids,
  ]);
  const [query, setQuery] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  function toggleTeam(teamId: number) {
    setSelectedIds((current) =>
      toggleLongTermTeamId(current, teamId, market.selection_size),
    );
  }

  async function save() {
    if (!canSaveLongTermPicks(market, selectedIds, isPending, nowMs)) {
      return;
    }
    setIsPending(true);
    setErrorMessage(null);
    try {
      const saved = await saveTyperLongTermPicks(market.market_id, [
        ...selectedIds,
      ]);
      let changes = market.changes;
      if (saved.audit_written) {
        try {
          changes = await getTyperLongTermHistory(market.market_id);
        } catch {
          // zapis wszedł; historia dociągnie się przy odświeżeniu
        }
      }
      onMarketChange(applySavedLongTermPicks(market, saved, changes));
      setSelectedIds(saved.team_ids);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        onMarketChange(lockLongTermMarket(market));
      }
      setErrorMessage(longTermSaveErrorMessage(error));
    } finally {
      setIsPending(false);
    }
  }

  return {
    selectedIds,
    query,
    isPending,
    errorMessage,
    canSave: canSaveLongTermPicks(market, selectedIds, isPending, nowMs),
    setQuery,
    toggleTeam,
    save,
  };
}
