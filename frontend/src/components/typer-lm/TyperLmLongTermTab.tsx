"use client";

import {
  useEffect,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import { useRouter } from "next/navigation";

import { StatusMessage } from "@/components/StatusMessage";
import { usePreferences } from "@/components/preferences/PreferencesProvider";
import { formatMatchDateTime } from "@/lib/format";
import {
  ApiError,
  getTyperLongTermHistory,
  saveTyperLongTermPicks,
} from "@/lib/apiClient";
import type { TeamNameDisplayPreference } from "@/lib/preferences";
import { canSaveLongTermExactPicks } from "@/lib/typerLmLongTermExact";
import {
  applySavedLongTermPicks,
  canSaveLongTermPicks,
  displayedRankedTeamIds,
  formatLongTermChangeLine,
  formatLongTermPointsLabel,
  formatLongTermTeamName,
  hasSavedRankedPick,
  isLongTermMarketLockedForUi,
  isLongTermMarketSettled,
  lockLongTermMarket,
  longTermSaveErrorMessage,
  longTermUnsavedPickStatus,
  rankingIdsForMarket,
  selectedTeams,
  takeRecentLongTermChanges,
  updateLongTermDashboardMarket,
} from "@/lib/typerLmLongTerm";
import {
  MARKET_KIND_FREE_TEXT,
  MARKET_KIND_RANKED_TEAM_TABLE,
  MARKET_KIND_SINGLE_TEAM,
  MARKET_KIND_YES_NO,
} from "@/lib/typerLmLongTermRanking";
import type {
  LongTermDashboardResponse,
  LongTermMarketCard,
  LongTermPicksPayload,
  LongTermTeam,
  SaveLongTermPicksResponse,
} from "@/types/api";

import { TyperLmLongTermRankedTable } from "./TyperLmLongTermRankedTable";
import { TyperLmLongTermTeamPicker } from "./TyperLmLongTermTeamPicker";
import { TyperLmLongTermTextPick } from "./TyperLmLongTermTextPick";
import { TyperLmLongTermYesNoPick } from "./TyperLmLongTermYesNoPick";

interface TyperLmLongTermTabProps {
  dashboard: LongTermDashboardResponse | null;
  errorMessage?: string;
  nowMs?: number | null;
  onDashboardChange?: Dispatch<
    SetStateAction<LongTermDashboardResponse | null>
  >;
}

export function TyperLmLongTermTab({
  dashboard,
  errorMessage,
  nowMs = null,
  onDashboardChange,
}: TyperLmLongTermTabProps) {
  const { preferences } = usePreferences();

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
        message="Administrator nie otworzył jeszcze rynku tabeli fazy ligowej."
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
              onDashboardChange?.((current) => {
                if (current == null) {
                  return current;
                }
                return updateLongTermDashboardMarket(
                  current,
                  market.market_id,
                  () => next,
                );
              })
            }
          />
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
  const isLocked = isLongTermMarketLockedForUi(market, nowMs);
  const cardProps = {
    market,
    nowMs,
    teamNameDisplay,
    isLocked,
    onMarketChange,
  };
  if (market.market_kind === MARKET_KIND_RANKED_TEAM_TABLE) {
    return <RankedTeamTableMarketCard {...cardProps} />;
  }
  if (market.market_kind === MARKET_KIND_FREE_TEXT) {
    return <FreeTextMarketCard {...cardProps} />;
  }
  if (market.market_kind === MARKET_KIND_YES_NO) {
    return <YesNoMarketCard {...cardProps} />;
  }
  if (market.market_kind === MARKET_KIND_SINGLE_TEAM) {
    return <SingleTeamMarketCard {...cardProps} />;
  }
  return (
    <section className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <LongTermMarketHeader market={market} isLocked={isLocked} />
      <StatusMessage
        variant="info"
        title="Ten rynek nie jest jeszcze dostępny"
        message="Obsługa tego rodzaju rynku pojawi się w kolejnej wersji."
      />
    </section>
  );
}

function RankedTeamTableMarketCard({
  market,
  nowMs,
  teamNameDisplay,
  isLocked,
  onMarketChange,
}: TyperLmLongTermMarketCardProps & { isLocked: boolean }) {
  const picks = useLongTermMarketPicks(market, nowMs, onMarketChange);
  const isSettled = isLongTermMarketSettled(market);
  const isReadOnly = isLocked || isSettled;
  const teamIds = displayedRankedTeamIds(
    market,
    picks.rankedIds,
    isReadOnly,
  );
  return (
    <LongTermMarketShell
      market={market}
      isLocked={isLocked}
      isSettled={isSettled}
      canSave={picks.canSave}
      isPending={picks.isPending}
      errorMessage={picks.errorMessage}
      onSave={() => void picks.save()}
    >
      {isSettled ? (
        <SettledResultSummary
          market={market}
          teamNameDisplay={teamNameDisplay}
        />
      ) : null}
      <TyperLmLongTermRankedTable
        candidates={market.candidates}
        teamIds={teamIds}
        topZoneSize={market.top_zone_size}
        botZoneSize={market.bot_zone_size}
        isLocked={isLocked || picks.isPending || isSettled}
        resultTeamIds={
          hasSavedRankedPick(market) ? market.result_team_ids : []
        }
        teamNameDisplay={teamNameDisplay}
        onReorder={picks.reorder}
      />
    </LongTermMarketShell>
  );
}

function FreeTextMarketCard({
  market,
  nowMs,
  isLocked,
  onMarketChange,
}: TyperLmLongTermMarketCardProps & { isLocked: boolean }) {
  const picks = useFreeTextMarketPicks(market, nowMs, onMarketChange);
  const isSettled = isLongTermMarketSettled(market);
  return (
    <LongTermMarketShell
      market={market}
      isLocked={isLocked}
      isSettled={isSettled}
      canSave={picks.canSave}
      isPending={picks.isPending}
      errorMessage={picks.errorMessage}
      onSave={() => void picks.save()}
    >
      <ExactSettledPoints market={market} />
      <TyperLmLongTermTextPick
        value={picks.subjectText}
        isLocked={isLocked || picks.isPending || isSettled}
        resultSubjectTexts={isSettled ? market.result_subject_texts : []}
        onChange={picks.setSubjectText}
      />
    </LongTermMarketShell>
  );
}

function YesNoMarketCard({
  market,
  nowMs,
  isLocked,
  onMarketChange,
}: TyperLmLongTermMarketCardProps & { isLocked: boolean }) {
  const picks = useYesNoMarketPicks(market, nowMs, onMarketChange);
  const isSettled = isLongTermMarketSettled(market);
  return (
    <LongTermMarketShell
      market={market}
      isLocked={isLocked}
      isSettled={isSettled}
      canSave={picks.canSave}
      isPending={picks.isPending}
      errorMessage={picks.errorMessage}
      onSave={() => void picks.save()}
    >
      <ExactSettledPoints market={market} />
      <TyperLmLongTermYesNoPick
        value={picks.isTextCorrect}
        isLocked={isLocked || picks.isPending || isSettled}
        resultIsTextCorrect={isSettled ? market.result_is_text_correct : null}
        onChange={picks.setIsTextCorrect}
      />
    </LongTermMarketShell>
  );
}

function SingleTeamMarketCard({
  market,
  nowMs,
  teamNameDisplay,
  isLocked,
  onMarketChange,
}: TyperLmLongTermMarketCardProps & { isLocked: boolean }) {
  const picks = useSingleTeamMarketPicks(market, nowMs, onMarketChange);
  const isSettled = isLongTermMarketSettled(market);
  const hasPick = market.picked_team_ids.length === 1;
  return (
    <LongTermMarketShell
      market={market}
      isLocked={isLocked}
      isSettled={isSettled}
      canSave={picks.canSave}
      isPending={picks.isPending}
      errorMessage={picks.errorMessage}
      onSave={() => void picks.save()}
    >
      <ExactSettledPoints market={market} />
      <TyperLmLongTermTeamPicker
        candidates={market.candidates}
        selectedIds={picks.teamIds}
        selectionSize={1}
        isLocked={isLocked || picks.isPending || isSettled}
        resultTeamIds={hasPick ? market.result_team_ids : []}
        teamNameDisplay={teamNameDisplay}
        onToggle={picks.toggle}
      />
      <OfficialResultTeams
        market={market}
        teamNameDisplay={teamNameDisplay}
      />
    </LongTermMarketShell>
  );
}

function LongTermMarketShell({
  market,
  isLocked,
  isSettled,
  canSave,
  isPending,
  errorMessage,
  onSave,
  children,
}: {
  market: LongTermMarketCard;
  isLocked: boolean;
  isSettled: boolean;
  canSave: boolean;
  isPending: boolean;
  errorMessage: string | null;
  onSave: () => void;
  children: ReactNode;
}) {
  const unsavedStatus = longTermUnsavedPickStatus(
    market,
    isLocked || isSettled,
  );
  return (
    <section className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <LongTermMarketHeader market={market} isLocked={isLocked} />
      {unsavedStatus ? (
        <p
          className="rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm text-text"
          role="status"
        >
          {unsavedStatus}
        </p>
      ) : null}
      {children}
      <TyperLmLongTermMarketFooter
        market={market}
        isLocked={isLocked}
        isSettled={isSettled}
        canSave={canSave}
        isPending={isPending}
        errorMessage={errorMessage}
        onSave={onSave}
      />
    </section>
  );
}

function ExactSettledPoints({ market }: { market: LongTermMarketCard }) {
  if (!isLongTermMarketSettled(market)) {
    return null;
  }
  return (
    <p className="text-sm text-text">
      Wynik zatwierdzony · {formatLongTermPointsLabel(market)}
    </p>
  );
}

function OfficialResultTeams({
  market,
  teamNameDisplay,
}: {
  market: LongTermMarketCard;
  teamNameDisplay: TeamNameDisplayPreference;
}) {
  if (!isLongTermMarketSettled(market) || market.result_team_ids.length === 0) {
    return null;
  }
  const teams = selectedTeams(market.candidates, market.result_team_ids);
  if (teams.length === 0) {
    return null;
  }
  return (
    <p className="text-sm text-muted">
      Oficjalny wynik: {joinOfficialTeamNames(teams, teamNameDisplay)}
    </p>
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
  const officialTop =
    market.top_zone_size > 0
      ? selectedTeams(
          market.candidates,
          market.result_team_ids.slice(0, market.top_zone_size),
        )
      : [];
  const officialBot =
    market.bot_zone_size > 0
      ? selectedTeams(
          market.candidates,
          market.result_team_ids.slice(-market.bot_zone_size),
        )
      : [];
  return (
    <div className="space-y-2 text-sm text-text">
      <p>Wynik zatwierdzony · {formatLongTermPointsLabel(market)}</p>
      {officialTop.length > 0 ? (
        <p className="text-muted">
          Oficjalny TOP {market.top_zone_size}:{" "}
          {joinOfficialTeamNames(officialTop, teamNameDisplay)}
        </p>
      ) : null}
      {officialBot.length > 0 ? (
        <p className="text-muted">
          Oficjalny BOT {market.bot_zone_size}:{" "}
          {joinOfficialTeamNames(officialBot, teamNameDisplay)}
        </p>
      ) : null}
    </div>
  );
}

function joinOfficialTeamNames(
  teams: readonly LongTermTeam[],
  teamNameDisplay: TeamNameDisplayPreference,
): string {
  return teams
    .map((team) => formatLongTermTeamName(team, teamNameDisplay))
    .join(", ");
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

function useLongTermMarketSave(
  market: LongTermMarketCard,
  onMarketChange: (market: LongTermMarketCard) => void,
) {
  const router = useRouter();
  const [isPending, setIsPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function save(payload: LongTermPicksPayload) {
    return runLongTermSave(
      market,
      payload,
      onMarketChange,
      router,
      setIsPending,
      setErrorMessage,
    );
  }

  return { isPending, errorMessage, save };
}

function useLongTermMarketPicks(
  market: LongTermMarketCard,
  nowMs: number | null,
  onMarketChange: (market: LongTermMarketCard) => void,
) {
  const persist = useLongTermMarketSave(market, onMarketChange);
  const [rankedIds, setRankedIds] = useState(() => rankingIdsForMarket(market));
  const savedRankingKey = [
    market.is_locked ? "1" : "0",
    market.settled_at ?? "",
    market.picked_team_ids.join(","),
  ].join("|");

  useEffect(() => {
    setRankedIds(rankingIdsForMarket(market));
    // reset przy zmianie zapisanego typu / lock / settle, nie przy nowej referencji
    // eslint-disable-next-line react-hooks/exhaustive-deps -- savedRankingKey serializuje treść
  }, [savedRankingKey]);

  async function save() {
    if (!canSaveLongTermPicks(market, rankedIds, persist.isPending, nowMs)) {
      return;
    }
    const saved = await persist.save({ teamIds: [...rankedIds] });
    if (saved) {
      setRankedIds(saved.team_ids);
    }
  }

  return {
    rankedIds,
    isPending: persist.isPending,
    errorMessage: persist.errorMessage,
    canSave: canSaveLongTermPicks(market, rankedIds, persist.isPending, nowMs),
    reorder: setRankedIds,
    save,
  };
}

function useFreeTextMarketPicks(
  market: LongTermMarketCard,
  nowMs: number | null,
  onMarketChange: (market: LongTermMarketCard) => void,
) {
  const persist = useLongTermMarketSave(market, onMarketChange);
  const [subjectText, setSubjectText] = useState(
    () => market.picked_subject_text ?? "",
  );
  const savedKey = [
    market.is_locked ? "1" : "0",
    market.settled_at ?? "",
    market.picked_subject_text ?? "",
  ].join("|");

  useEffect(() => {
    setSubjectText(market.picked_subject_text ?? "");
    // reset przy zmianie zapisanego typu / lock / settle
    // eslint-disable-next-line react-hooks/exhaustive-deps -- savedKey serializuje treść
  }, [savedKey]);

  const canSave = canSaveLongTermExactPicks(
    market,
    { subjectText },
    persist.isPending,
    nowMs,
  );

  async function save() {
    if (!canSave) {
      return;
    }
    const saved = await persist.save({ subjectTexts: [subjectText.trim()] });
    if (saved) {
      setSubjectText(saved.subject_texts[0] ?? "");
    }
  }

  return {
    subjectText,
    setSubjectText,
    isPending: persist.isPending,
    errorMessage: persist.errorMessage,
    canSave,
    save,
  };
}

function useYesNoMarketPicks(
  market: LongTermMarketCard,
  nowMs: number | null,
  onMarketChange: (market: LongTermMarketCard) => void,
) {
  const persist = useLongTermMarketSave(market, onMarketChange);
  const [isTextCorrect, setIsTextCorrect] = useState<boolean | null>(
    () => market.picked_is_text_correct,
  );
  const savedKey = [
    market.is_locked ? "1" : "0",
    market.settled_at ?? "",
    String(market.picked_is_text_correct),
  ].join("|");

  useEffect(() => {
    setIsTextCorrect(market.picked_is_text_correct);
    // reset przy zmianie zapisanego typu / lock / settle
    // eslint-disable-next-line react-hooks/exhaustive-deps -- savedKey serializuje treść
  }, [savedKey]);

  const canSave = canSaveLongTermExactPicks(
    market,
    { isTextCorrect },
    persist.isPending,
    nowMs,
  );

  async function save() {
    if (!canSave || isTextCorrect == null) {
      return;
    }
    const saved = await persist.save({ isTextCorrect });
    if (saved) {
      setIsTextCorrect(saved.is_text_correct);
    }
  }

  return {
    isTextCorrect,
    setIsTextCorrect,
    isPending: persist.isPending,
    errorMessage: persist.errorMessage,
    canSave,
    save,
  };
}

function useSingleTeamMarketPicks(
  market: LongTermMarketCard,
  nowMs: number | null,
  onMarketChange: (market: LongTermMarketCard) => void,
) {
  const persist = useLongTermMarketSave(market, onMarketChange);
  const [teamIds, setTeamIds] = useState(() => [...market.picked_team_ids]);
  const savedKey = [
    market.is_locked ? "1" : "0",
    market.settled_at ?? "",
    market.picked_team_ids.join(","),
  ].join("|");

  useEffect(() => {
    setTeamIds([...market.picked_team_ids]);
    // reset przy zmianie zapisanego typu / lock / settle
    // eslint-disable-next-line react-hooks/exhaustive-deps -- savedKey serializuje treść
  }, [savedKey]);

  const canSave = canSaveLongTermExactPicks(
    market,
    { teamIds },
    persist.isPending,
    nowMs,
  );

  function toggle(teamId: number) {
    // jeden slot: klik innej drużyny podmienia wybór (radio), nie wymaga odznaczania
    setTeamIds((current) => (current.includes(teamId) ? [] : [teamId]));
  }

  async function save() {
    if (!canSave) {
      return;
    }
    const saved = await persist.save({ teamIds: [...teamIds] });
    if (saved) {
      setTeamIds(saved.team_ids);
    }
  }

  return {
    teamIds,
    toggle,
    isPending: persist.isPending,
    errorMessage: persist.errorMessage,
    canSave,
    save,
  };
}

async function runLongTermSave(
  market: LongTermMarketCard,
  payload: LongTermPicksPayload,
  onMarketChange: (market: LongTermMarketCard) => void,
  router: { refresh: () => void },
  setIsPending: (value: boolean) => void,
  setErrorMessage: (value: string | null) => void,
): Promise<SaveLongTermPicksResponse | null> {
  setIsPending(true);
  setErrorMessage(null);
  try {
    const saved = await saveTyperLongTermPicks(market.market_id, payload);
    let changes = market.changes;
    if (saved.audit_written) {
      try {
        changes = await getTyperLongTermHistory(market.market_id);
      } catch {
        // zapis wszedł; historia dociągnie się przy odświeżeniu
      }
    }
    onMarketChange(applySavedLongTermPicks(market, saved, changes));
    router.refresh();
    return saved;
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      onMarketChange(lockLongTermMarket(market));
    }
    setErrorMessage(longTermSaveErrorMessage(error, market.market_kind));
    return null;
  } finally {
    setIsPending(false);
  }
}
