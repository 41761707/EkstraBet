"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
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
  toggleLongTermTeamId,
} from "@/lib/typerLmLongTerm";
import {
  canSettleFreeTextResults,
  canSettleSingleTeamResults,
  canSettleYesNoResult,
  defaultAdminSubjectTexts,
  SUBJECT_TEXT_MAX_LENGTH,
  uniqueTrimmedSubjectTexts,
} from "@/lib/typerLmLongTermExact";
import {
  MARKET_KIND_FREE_TEXT,
  MARKET_KIND_RANKED_TEAM_TABLE,
  MARKET_KIND_SINGLE_TEAM,
  MARKET_KIND_YES_NO,
} from "@/lib/typerLmLongTermRanking";
import type {
  LongTermAutoResultResponse,
  LongTermMarketCard,
  LongTermPicksPayload,
  LongTermStandingTeam,
  SettleLongTermResponse,
} from "@/types/api";

import { TyperLmLongTermAdminAuditLookup } from "./TyperLmLongTermAdminAuditLookup";
import { TyperLmLongTermRankedTable } from "./TyperLmLongTermRankedTable";
import { TyperLmLongTermTeamPicker } from "./TyperLmLongTermTeamPicker";
import { TyperLmLongTermYesNoPick } from "./TyperLmLongTermYesNoPick";

const RANKED_SETTLE_DESCRIPTION =
  "Propozycja tabeli nie przyznaje punktów. Zatwierdzenie lub korekta " +
  "rozlicza rynek.";
const FREE_TEXT_SETTLE_DESCRIPTION =
  "Wpisz oficjalne imię i nazwisko. Przy remisie dodaj każdego zwycięzcę. " +
  "Zatwierdzenie lub korekta rozlicza rynek.";
const YES_NO_SETTLE_DESCRIPTION =
  "Wybierz TAK albo NIE. Zatwierdzenie lub korekta rozlicza rynek.";
const SINGLE_TEAM_SETTLE_DESCRIPTION =
  "Zaznacz jedną lub więcej drużyn (remis). Zatwierdzenie lub korekta " +
  "rozlicza rynek.";
const ADD_WINNER_LABEL = "Dodaj zwycięzcę";
const NAME_FIELD_LABEL = "Imię i nazwisko";

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
  if (market.market_kind === MARKET_KIND_RANKED_TEAM_TABLE) {
    return (
      <RankedLongTermAdminPanel
        market={market}
        initialAutoResult={initialAutoResult}
        teamNameDisplay={teamNameDisplay}
        onSettled={onSettled}
      />
    );
  }
  if (market.market_kind === MARKET_KIND_FREE_TEXT) {
    return <FreeTextLongTermAdminPanel market={market} onSettled={onSettled} />;
  }
  if (market.market_kind === MARKET_KIND_YES_NO) {
    return <YesNoLongTermAdminPanel market={market} onSettled={onSettled} />;
  }
  if (market.market_kind === MARKET_KIND_SINGLE_TEAM) {
    return (
      <SingleTeamLongTermAdminPanel
        market={market}
        teamNameDisplay={teamNameDisplay}
        onSettled={onSettled}
      />
    );
  }
  return null;
}

function RankedLongTermAdminPanel({
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
    <AdminSettleShell
      title={market.title}
      description={RANKED_SETTLE_DESCRIPTION}
      seasonId={market.season_id}
      marketId={market.market_id}
    >
      <AdminResultBody
        market={market}
        teamNameDisplay={teamNameDisplay}
        settlement={settlement}
      />
    </AdminSettleShell>
  );
}

function FreeTextLongTermAdminPanel({
  market,
  onSettled,
}: {
  market: LongTermMarketCard;
  onSettled?: (settled: SettleLongTermResponse) => void;
}) {
  const settlement = useExactLongTermSettle(market, onSettled);
  const [subjectTexts, setSubjectTexts] = useState(() =>
    defaultAdminSubjectTexts(market.result_subject_texts),
  );
  const canSettle = canSettleFreeTextResults(subjectTexts);

  function updateSubjectTexts(next: string[]) {
    settlement.setIsConfirming(false);
    setSubjectTexts(next);
  }

  return (
    <AdminSettleShell
      title={market.title}
      description={FREE_TEXT_SETTLE_DESCRIPTION}
      seasonId={market.season_id}
      marketId={market.market_id}
    >
      <AdminFreeTextFields
        values={subjectTexts}
        isSaving={settlement.isSaving}
        onChange={updateSubjectTexts}
      />
      <ExactSettleFooter
        settlement={settlement}
        canSettle={canSettle}
        onConfirm={() =>
          void settlement.confirmSettle(
            { subjectTexts: uniqueTrimmedSubjectTexts(subjectTexts) },
            (settled) =>
              setSubjectTexts(defaultAdminSubjectTexts(settled.subject_texts)),
          )
        }
      />
    </AdminSettleShell>
  );
}

function YesNoLongTermAdminPanel({
  market,
  onSettled,
}: {
  market: LongTermMarketCard;
  onSettled?: (settled: SettleLongTermResponse) => void;
}) {
  const settlement = useExactLongTermSettle(market, onSettled);
  const [isTextCorrect, setIsTextCorrect] = useState<boolean | null>(
    market.result_is_text_correct,
  );
  const canSettle = canSettleYesNoResult(isTextCorrect);

  function updateIsTextCorrect(value: boolean) {
    settlement.setIsConfirming(false);
    setIsTextCorrect(value);
  }

  return (
    <AdminSettleShell
      title={market.title}
      description={YES_NO_SETTLE_DESCRIPTION}
      seasonId={market.season_id}
      marketId={market.market_id}
    >
      <TyperLmLongTermYesNoPick
        value={isTextCorrect}
        isLocked={settlement.isSaving}
        resultIsTextCorrect={null}
        onChange={updateIsTextCorrect}
      />
      <ExactSettleFooter
        settlement={settlement}
        canSettle={canSettle}
        onConfirm={() => {
          if (isTextCorrect == null) {
            return;
          }
          void settlement.confirmSettle(
            { isTextCorrect },
            (settled) => setIsTextCorrect(settled.is_text_correct),
          );
        }}
      />
    </AdminSettleShell>
  );
}

function SingleTeamLongTermAdminPanel({
  market,
  teamNameDisplay,
  onSettled,
}: {
  market: LongTermMarketCard;
  teamNameDisplay: TeamNameDisplayPreference;
  onSettled?: (settled: SettleLongTermResponse) => void;
}) {
  const settlement = useExactLongTermSettle(market, onSettled);
  const [teamIds, setTeamIds] = useState(() => [...market.result_team_ids]);
  const [query, setQuery] = useState("");
  const selectionSize = market.candidates.length;
  const canSettle = canSettleSingleTeamResults(
    teamIds,
    market.candidates.map((team) => team.team_id),
  );

  function toggle(teamId: number) {
    settlement.setIsConfirming(false);
    setTeamIds((current) =>
      toggleLongTermTeamId(current, teamId, selectionSize),
    );
  }

  return (
    <AdminSettleShell
      title={market.title}
      description={SINGLE_TEAM_SETTLE_DESCRIPTION}
      seasonId={market.season_id}
      marketId={market.market_id}
    >
      <TyperLmLongTermTeamPicker
        candidates={market.candidates}
        selectedIds={teamIds}
        selectionSize={selectionSize}
        query={query}
        isLocked={settlement.isSaving}
        resultTeamIds={[]}
        teamNameDisplay={teamNameDisplay}
        onQueryChange={setQuery}
        onToggle={toggle}
      />
      <ExactSettleFooter
        settlement={settlement}
        canSettle={canSettle}
        onConfirm={() =>
          void settlement.confirmSettle({ teamIds: [...teamIds] }, (settled) =>
            setTeamIds([...settled.result_team_ids]),
          )
        }
      />
    </AdminSettleShell>
  );
}

function AdminSettleShell({
  title,
  description,
  seasonId,
  marketId,
  children,
}: {
  title: string;
  description: string;
  seasonId: number;
  marketId: number;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4 border-t border-border pt-6">
      <header className="space-y-1">
        <h3 className="text-sm font-semibold text-text">
          Rozliczenie — {title}
        </h3>
        <p className="text-sm text-muted">{description}</p>
      </header>
      {children}
      <TyperLmLongTermAdminAuditLookup
        seasonId={seasonId}
        marketId={marketId}
      />
    </section>
  );
}

function AdminFreeTextFields({
  values,
  isSaving,
  onChange,
}: {
  values: readonly string[];
  isSaving: boolean;
  onChange: (values: string[]) => void;
}) {
  return (
    <div className="space-y-3">
      {values.map((value, index) => (
        <label
          key={index}
          className="flex flex-col gap-1 text-sm text-muted"
        >
          {NAME_FIELD_LABEL}
          <input
            type="text"
            value={value}
            placeholder={NAME_FIELD_LABEL}
            autoComplete="off"
            maxLength={SUBJECT_TEXT_MAX_LENGTH}
            disabled={isSaving}
            onChange={(event) => {
              const next = [...values];
              next[index] = event.target.value;
              onChange(next);
            }}
            className={`w-full rounded-md ${INPUT_CLASS_NAME} disabled:opacity-60`}
          />
        </label>
      ))}
      <button
        type="button"
        disabled={isSaving}
        onClick={() => onChange([...values, ""])}
        className="rounded-lg border border-border px-3 py-2 text-sm text-text"
      >
        {ADD_WINNER_LABEL}
      </button>
    </div>
  );
}

function ExactSettleFooter({
  settlement,
  canSettle,
  onConfirm,
}: {
  settlement: ReturnType<typeof useExactLongTermSettle>;
  canSettle: boolean;
  onConfirm: () => void;
}) {
  return (
    <div className="space-y-4">
      {settlement.errorMessage ? (
        <p className="text-sm text-danger-text" role="alert">
          {settlement.errorMessage}
        </p>
      ) : null}
      <SettleActions
        settleLabel={settlement.settledAt ? "Skoryguj wynik" : "Zatwierdź wynik"}
        canSettle={canSettle}
        isSaving={settlement.isSaving}
        isConfirming={settlement.isConfirming}
        onRequestSettle={() => settlement.setIsConfirming(true)}
        onCancelSettle={() => settlement.setIsConfirming(false)}
        onConfirmSettle={onConfirm}
      />
    </div>
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

function useExactLongTermSettle(
  market: LongTermMarketCard,
  onSettled?: (settled: SettleLongTermResponse) => void,
) {
  const router = useRouter();
  const [isSaving, setIsSaving] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [settledAt, setSettledAt] = useState(market.settled_at);

  async function confirmSettle(
    payload: LongTermPicksPayload,
    onSuccess?: (settled: SettleLongTermResponse) => void,
  ) {
    setIsSaving(true);
    setErrorMessage(null);
    try {
      const settled = await settleTyperLongTermMarket(market.market_id, payload);
      setSettledAt(settled.settled_at);
      setIsConfirming(false);
      onSuccess?.(settled);
      onSettled?.(settled);
      router.refresh();
    } catch (error) {
      setErrorMessage(
        longTermSettleErrorMessage(error, market.market_kind),
      );
    } finally {
      setIsSaving(false);
    }
  }

  return {
    isSaving,
    isConfirming,
    errorMessage,
    settledAt,
    setIsConfirming,
    confirmSettle,
  };
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
      setErrorMessage(
        longTermSettleErrorMessage(error, market.market_kind),
      );
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
