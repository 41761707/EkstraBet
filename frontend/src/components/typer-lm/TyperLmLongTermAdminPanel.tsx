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
  longTermAutoResultErrorMessage,
  longTermSettleErrorMessage,
} from "@/lib/typerLmLongTerm";
import { MARKET_KIND_RANKED_TEAM_TABLE } from "@/lib/typerLmLongTermRanking";
import type {
  LongTermAutoResultResponse,
  LongTermMarketCard,
  LongTermStandingTeam,
  SettleLongTermResponse,
} from "@/types/api";

import { TyperLmLongTermAdminAuditLookup } from "./TyperLmLongTermAdminAuditLookup";
import { TyperLmLongTermRankedTable } from "./TyperLmLongTermRankedTable";

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

  if (market.market_kind !== MARKET_KIND_RANKED_TEAM_TABLE) {
    return null;
  }

  return (
    <section className="space-y-4 border-t border-border pt-6">
      <header className="space-y-1">
        <h3 className="text-sm font-semibold text-text">
          Rozliczenie — {market.title}
        </h3>
        <p className="text-sm text-muted">
          Propozycja tabeli nie przyznaje punktów. Zatwierdzenie lub korekta
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
    return (
      <StatusMessage variant="info" title="Ładowanie propozycji tabeli" />
    );
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
      rankedIds={settlement.rankedIds}
      isSaving={settlement.isSaving}
      isConfirming={settlement.isConfirming}
      errorMessage={settlement.errorMessage}
      teamNameDisplay={teamNameDisplay}
      onReorder={settlement.reorder}
      onRequestSettle={() => settlement.setIsConfirming(true)}
      onCancelSettle={() => settlement.setIsConfirming(false)}
      onConfirmSettle={() => void settlement.confirmSettle()}
    />
  );
}

interface AdminSettlementFormProps {
  market: LongTermMarketCard;
  autoResult: LongTermAutoResultResponse;
  rankedIds: readonly number[];
  isSaving: boolean;
  isConfirming: boolean;
  errorMessage: string | null;
  teamNameDisplay: TeamNameDisplayPreference;
  onReorder: (teamIds: number[]) => void;
  onRequestSettle: () => void;
  onCancelSettle: () => void;
  onConfirmSettle: () => void;
}

function AdminSettlementForm({
  market,
  autoResult,
  rankedIds,
  isSaving,
  isConfirming,
  errorMessage,
  teamNameDisplay,
  onReorder,
  onRequestSettle,
  onCancelSettle,
  onConfirmSettle,
}: AdminSettlementFormProps) {
  const canSettle = canSettleLongTermSelection(autoResult, rankedIds);
  const settleLabel = autoResult.settled_at
    ? "Skoryguj wynik"
    : "Zatwierdź wynik";

  return (
    <div className="space-y-4">
      <StatusMessage
        variant={autoResult.is_complete ? "info" : "empty"}
        title={
          autoResult.is_complete ? "Propozycja tabeli" : "Faza niekompletna"
        }
        message={formatLongTermCompleteness(autoResult)}
      />
      {rankedIds.length > 0 ? (
        <TyperLmLongTermRankedTable
          candidates={market.candidates}
          teamIds={rankedIds}
          topZoneSize={market.top_zone_size}
          botZoneSize={market.bot_zone_size}
          isLocked={isSaving || !autoResult.is_complete}
          resultTeamIds={[]}
          teamNameDisplay={teamNameDisplay}
          standings={settlementStandings(autoResult)}
          onReorder={onReorder}
        />
      ) : null}
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

function settlementStandings(
  autoResult: LongTermAutoResultResponse,
): readonly LongTermStandingTeam[] {
  if (autoResult.standings.length > 0) {
    return autoResult.standings;
  }
  return autoResult.proposed_teams;
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
  const [rankedIds, setRankedIds] = useState(() =>
    defaultAdminResultIds(initialAutoResult),
  );
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
      setRankedIds(defaultAdminResultIds(payload));
    } catch (error) {
      setAutoResult(null);
      setErrorMessage(longTermAutoResultErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  function reorder(teamIds: number[]) {
    setIsConfirming(false);
    setRankedIds(teamIds);
  }

  async function confirmSettle() {
    if (
      autoResult === null ||
      !canSettleLongTermSelection(autoResult, rankedIds)
    ) {
      return;
    }
    setIsSaving(true);
    setErrorMessage(null);
    try {
      const settled = await settleTyperLongTermMarket(market.market_id, {
        teamIds: [...rankedIds],
      });
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
    rankedIds,
    isLoading,
    isSaving,
    isConfirming,
    errorMessage,
    setIsConfirming,
    reload,
    reorder,
    confirmSettle,
  };
}
