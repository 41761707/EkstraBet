"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { StatusMessage } from "@/components/StatusMessage";
import {
  getTyperLongTermAutoResult,
  settleTyperLongTermMarket,
} from "@/lib/apiClient";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import {
  canSettleLongTermSelection,
  defaultAdminResultIds,
  formatLongTermCompleteness,
  formatLongTermStandingLine,
  longTermAutoResultErrorMessage,
  longTermSettleErrorMessage,
  toggleLongTermTeamId,
} from "@/lib/typerLmLongTerm";
import type {
  LongTermAutoResultResponse,
  LongTermMarketCard,
  SettleLongTermResponse,
} from "@/types/api";

import { TyperLmLongTermAdminAuditLookup } from "./TyperLmLongTermAdminAuditLookup";
import { TyperLmLongTermTeamPicker } from "./TyperLmLongTermTeamPicker";

interface TyperLmLongTermAdminPanelProps {
  market: LongTermMarketCard;
  initialAutoResult: LongTermAutoResultResponse | null;
  teamNameDisplay: TeamNameDisplayPreference;
  onSettled?: (settled: SettleLongTermResponse) => void;
}

export function TyperLmLongTermAdminPanel({
  market,
  initialAutoResult,
  teamNameDisplay,
  onSettled,
}: TyperLmLongTermAdminPanelProps) {
  const settlement = useLongTermSettlement(
    market,
    initialAutoResult,
    onSettled,
  );

  return (
    <section className="space-y-4 border-t border-border pt-6">
      <header className="space-y-1">
        <h3 className="text-sm font-semibold text-text">
          Rozliczenie — {market.title}
        </h3>
        <p className="text-sm text-muted">
          Propozycja TOP 8 nie przyznaje punktów. Zatwierdzenie lub korekta
          rozlicza rynek.
        </p>
      </header>
      <AdminResultBody
        market={market}
        teamNameDisplay={teamNameDisplay}
        settlement={settlement}
      />
      <TyperLmLongTermAdminAuditLookup
        seasonId={market.season_id}
        marketId={market.market_id}
      />
    </section>
  );
}

interface AdminResultBodyProps {
  market: LongTermMarketCard;
  teamNameDisplay: TeamNameDisplayPreference;
  settlement: ReturnType<typeof useLongTermSettlement>;
}

function AdminResultBody({
  market,
  teamNameDisplay,
  settlement,
}: AdminResultBodyProps) {
  if (settlement.isLoading) {
    return <StatusMessage variant="info" title="Ładowanie propozycji TOP 8" />;
  }
  if (settlement.autoResult === null) {
    return (
      <div className="space-y-3">
        <StatusMessage
          variant="error"
          title="Nie udało się wczytać propozycji"
          message={settlement.errorMessage ?? "Spróbuj ponownie."}
        />
        <button
          type="button"
          onClick={() => void settlement.reload()}
          className="rounded-lg bg-accent px-3 py-2 text-sm font-medium text-on-accent"
        >
          Ponów
        </button>
      </div>
    );
  }
  return (
    <AdminSettlementForm
      market={market}
      autoResult={settlement.autoResult}
      selectedIds={settlement.selectedIds}
      query={settlement.query}
      isSaving={settlement.isSaving}
      isConfirming={settlement.isConfirming}
      errorMessage={settlement.errorMessage}
      teamNameDisplay={teamNameDisplay}
      onQueryChange={settlement.setQuery}
      onToggle={settlement.toggleTeam}
      onRequestSettle={() => settlement.setIsConfirming(true)}
      onCancelSettle={() => settlement.setIsConfirming(false)}
      onConfirmSettle={() => void settlement.confirmSettle()}
    />
  );
}

interface AdminSettlementFormProps {
  market: LongTermMarketCard;
  autoResult: LongTermAutoResultResponse;
  selectedIds: readonly number[];
  query: string;
  isSaving: boolean;
  isConfirming: boolean;
  errorMessage: string | null;
  teamNameDisplay: TeamNameDisplayPreference;
  onQueryChange: (query: string) => void;
  onToggle: (teamId: number) => void;
  onRequestSettle: () => void;
  onCancelSettle: () => void;
  onConfirmSettle: () => void;
}

function AdminSettlementForm({
  market,
  autoResult,
  selectedIds,
  query,
  isSaving,
  isConfirming,
  errorMessage,
  teamNameDisplay,
  onQueryChange,
  onToggle,
  onRequestSettle,
  onCancelSettle,
  onConfirmSettle,
}: AdminSettlementFormProps) {
  const canSettle = canSettleLongTermSelection(autoResult, selectedIds);
  const settleLabel = autoResult.settled_at
    ? "Skoryguj wynik"
    : "Zatwierdź wynik";

  return (
    <div className="space-y-4">
      <StatusMessage
        variant={autoResult.is_complete ? "info" : "empty"}
        title={autoResult.is_complete ? "Propozycja TOP 8" : "Faza niekompletna"}
        message={formatLongTermCompleteness(autoResult)}
      />
      <ProposedTeamsList
        autoResult={autoResult}
        teamNameDisplay={teamNameDisplay}
      />
      <TyperLmLongTermTeamPicker
        candidates={market.candidates}
        selectedIds={selectedIds}
        selectionSize={market.selection_size}
        query={query}
        isLocked={isSaving || !autoResult.is_complete}
        resultTeamIds={[]}
        teamNameDisplay={teamNameDisplay}
        onQueryChange={onQueryChange}
        onToggle={onToggle}
      />
      {errorMessage ? (
        <p className="text-sm text-danger-text" role="alert">
          {errorMessage}
        </p>
      ) : null}
      <SettleActions
        settleLabel={settleLabel}
        canSettle={canSettle}
        isSaving={isSaving}
        isConfirming={isConfirming}
        onRequestSettle={onRequestSettle}
        onCancelSettle={onCancelSettle}
        onConfirmSettle={onConfirmSettle}
      />
    </div>
  );
}

function ProposedTeamsList({
  autoResult,
  teamNameDisplay,
}: {
  autoResult: LongTermAutoResultResponse;
  teamNameDisplay: TeamNameDisplayPreference;
}) {
  if (autoResult.proposed_teams.length === 0) {
    return null;
  }
  return (
    <ul className="space-y-1 text-sm text-text">
      {autoResult.proposed_teams.map((team) => (
        <li key={team.team_id}>
          {formatLongTermStandingLine(team, teamNameDisplay)}
        </li>
      ))}
    </ul>
  );
}

function SettleActions({
  settleLabel,
  canSettle,
  isSaving,
  isConfirming,
  onRequestSettle,
  onCancelSettle,
  onConfirmSettle,
}: {
  settleLabel: string;
  canSettle: boolean;
  isSaving: boolean;
  isConfirming: boolean;
  onRequestSettle: () => void;
  onCancelSettle: () => void;
  onConfirmSettle: () => void;
}) {
  if (!isConfirming) {
    return (
      <button
        type="button"
        disabled={!canSettle || isSaving}
        onClick={onRequestSettle}
        className={
          "rounded-lg bg-accent px-3 py-2 text-sm font-medium " +
          "text-on-accent disabled:opacity-50"
        }
      >
        {settleLabel}
      </button>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        disabled={isSaving}
        onClick={onConfirmSettle}
        className={
          "rounded-lg bg-accent px-3 py-2 text-sm font-medium " +
          "text-on-accent disabled:opacity-50"
        }
      >
        {isSaving ? "Zapisywanie…" : "Potwierdź rozliczenie"}
      </button>
      <button
        type="button"
        disabled={isSaving}
        onClick={onCancelSettle}
        className="rounded-lg border border-border px-3 py-2 text-sm text-text"
      >
        Anuluj
      </button>
    </div>
  );
}

function useLongTermSettlement(
  market: LongTermMarketCard,
  initialAutoResult: LongTermAutoResultResponse | null,
  onSettled?: (settled: SettleLongTermResponse) => void,
) {
  const router = useRouter();
  const [autoResult, setAutoResult] = useState(initialAutoResult);
  const [selectedIds, setSelectedIds] = useState(() =>
    defaultAdminResultIds(initialAutoResult),
  );
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function reload() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const payload = await getTyperLongTermAutoResult(market.market_id);
      setAutoResult(payload);
      setSelectedIds(defaultAdminResultIds(payload));
    } catch (error) {
      setAutoResult(null);
      setErrorMessage(longTermAutoResultErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  function toggleTeam(teamId: number) {
    setIsConfirming(false);
    setSelectedIds((current) =>
      toggleLongTermTeamId(current, teamId, market.selection_size),
    );
  }

  async function confirmSettle() {
    if (
      autoResult === null ||
      !canSettleLongTermSelection(autoResult, selectedIds)
    ) {
      return;
    }
    setIsSaving(true);
    setErrorMessage(null);
    try {
      const settled = await settleTyperLongTermMarket(
        market.market_id,
        [...selectedIds],
      );
      setAutoResult({
        ...autoResult,
        settled_at: settled.settled_at,
        settled_by_uuid: settled.settled_by_uuid,
        settled_by_display_name: settled.settled_by_display_name,
        result_team_ids: settled.result_team_ids,
      });
      setIsConfirming(false);
      onSettled?.(settled);
      router.refresh();
    } catch (error) {
      setErrorMessage(longTermSettleErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  return {
    autoResult,
    selectedIds,
    query,
    isLoading,
    isSaving,
    isConfirming,
    errorMessage,
    setQuery,
    setIsConfirming,
    reload,
    toggleTeam,
    confirmSettle,
  };
}
