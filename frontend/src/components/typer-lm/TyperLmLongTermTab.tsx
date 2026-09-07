"use client";

import { useEffect, useState } from "react";
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
import { MARKET_KIND_RANKED_TEAM_TABLE } from "@/lib/typerLmLongTermRanking";
import type {
  LongTermDashboardResponse,
  LongTermMarketCard,
  LongTermTeam,
} from "@/types/api";

import { TyperLmLongTermRankedTable } from "./TyperLmLongTermRankedTable";

interface TyperLmLongTermTabProps {
  dashboard: LongTermDashboardResponse | null;
  errorMessage?: string;
  nowMs?: number | null;
  onDashboardChange?: (dashboard: LongTermDashboardResponse) => void;
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
              onDashboardChange?.(
                updateLongTermDashboardMarket(
                  dashboard,
                  market.market_id,
                  () => next,
                ),
              )
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
  if (market.market_kind !== MARKET_KIND_RANKED_TEAM_TABLE) {
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
  return (
    <RankedTeamTableMarketCard
      market={market}
      nowMs={nowMs}
      teamNameDisplay={teamNameDisplay}
      isLocked={isLocked}
      onMarketChange={onMarketChange}
    />
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
  const unsavedStatus = longTermUnsavedPickStatus(market, isReadOnly);

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

function useLongTermMarketPicks(
  market: LongTermMarketCard,
  nowMs: number | null,
  onMarketChange: (market: LongTermMarketCard) => void,
) {
  const router = useRouter();
  const [rankedIds, setRankedIds] = useState(() => rankingIdsForMarket(market));
  const [isPending, setIsPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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

  function reorder(teamIds: number[]) {
    setRankedIds(teamIds);
  }

  async function save() {
    if (!canSaveLongTermPicks(market, rankedIds, isPending, nowMs)) {
      return;
    }
    setIsPending(true);
    setErrorMessage(null);
    try {
      const saved = await saveTyperLongTermPicks(market.market_id, {
        teamIds: [...rankedIds],
      });
      let changes = market.changes;
      if (saved.audit_written) {
        try {
          changes = await getTyperLongTermHistory(market.market_id);
        } catch {
          // zapis wszedł; historia dociągnie się przy odświeżeniu
        }
      }
      onMarketChange(applySavedLongTermPicks(market, saved, changes));
      setRankedIds(saved.team_ids);
      router.refresh();
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
    rankedIds,
    isPending,
    errorMessage,
    canSave: canSaveLongTermPicks(market, rankedIds, isPending, nowMs),
    reorder,
    save,
  };
}
