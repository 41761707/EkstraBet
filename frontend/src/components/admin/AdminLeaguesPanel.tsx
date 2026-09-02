"use client";

import { useRef, useState } from "react";

import { AddLeagueForm } from "@/components/admin/AddLeagueForm";
import { AdminLeagueRow } from "@/components/admin/AdminLeagueRow";
import {
  ADMIN_LEAGUES_BUSY_HINT,
  ADMIN_LEAGUES_DESCRIPTION,
  ADMIN_LEAGUES_LOAD_ERROR_TITLE,
  ADMIN_LEAGUES_TITLE,
  EMPTY_ADMIN_LEAGUES_MESSAGE,
  EMPTY_ADMIN_LEAGUES_TITLE,
  prependAdminLeague,
  replaceAdminLeague,
} from "@/components/admin/adminLeaguesModel";
import {
  submitCreateAdminLeague,
  submitToggleLeagueActive,
  type AdminLeaguesMutationFailure,
  type AdminLeaguesMutationResult,
} from "@/components/admin/adminLeaguesMutations";
import {
  acquireAdminMutationLock,
  releaseAdminMutationLock,
} from "@/components/admin/adminMutationLock";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
  CreateLeagueRequest,
} from "@/types/api";

interface AdminLeaguesPanelProps {
  initialLeagues: AdminLeague[];
  countries: AdminCountry[];
  sports: AdminSport[];
  seasons: AdminSeason[];
  leaguesError?: string | null;
  dictionariesError?: string | null;
  seasonsError?: string | null;
}

export function AdminLeaguesStatus({
  title,
  message,
}: {
  title: string | null;
  message: string | null;
}) {
  if (!title || !message) {
    return null;
  }
  return <StatusMessage variant="error" title={title} message={message} />;
}

export function AdminLeaguesPanel({
  initialLeagues,
  countries,
  sports,
  seasons,
  leaguesError = null,
  dictionariesError = null,
  seasonsError = null,
}: AdminLeaguesPanelProps) {
  const list = useAdminLeagueList(initialLeagues, leaguesError);

  return (
    <section
      aria-busy={list.isBusy}
      className="space-y-4 rounded-xl border border-border bg-surface p-4"
    >
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-text">{ADMIN_LEAGUES_TITLE}</h2>
        <p className="text-sm text-muted">{ADMIN_LEAGUES_DESCRIPTION}</p>
      </header>
      <AddLeagueForm
        isSubmitting={list.isBusy}
        countries={countries}
        sports={sports}
        seasons={seasons}
        dictionariesError={dictionariesError}
        seasonsError={seasonsError}
        onSubmit={list.createLeague}
      />
      <AdminLeaguesStatus title={list.errorTitle} message={list.errorMessage} />
      {list.isBusy ? (
        <p className="text-sm text-muted" aria-live="polite">
          {ADMIN_LEAGUES_BUSY_HINT}
        </p>
      ) : null}
      <AdminLeaguesList
        leagues={list.leagues}
        seasons={seasons}
        pendingId={list.pendingId}
        areActionsLocked={list.isBusy}
        hasError={Boolean(list.errorMessage)}
        onToggleActive={list.toggleActive}
      />
    </section>
  );
}

interface AdminLeaguesListProps {
  leagues: AdminLeague[];
  seasons: AdminSeason[];
  pendingId: number | null;
  areActionsLocked: boolean;
  hasError: boolean;
  onToggleActive: (league: AdminLeague) => void;
}

function AdminLeaguesList({
  leagues,
  seasons,
  pendingId,
  areActionsLocked,
  hasError,
  onToggleActive,
}: AdminLeaguesListProps) {
  if (leagues.length === 0) {
    if (hasError) {
      return null;
    }
    return (
      <StatusMessage
        variant="empty"
        title={EMPTY_ADMIN_LEAGUES_TITLE}
        message={EMPTY_ADMIN_LEAGUES_MESSAGE}
      />
    );
  }

  return (
    <ul className="space-y-2">
      {leagues.map((league) => (
        <AdminLeagueRow
          key={league.id}
          league={league}
          seasons={seasons}
          isSaving={pendingId === league.id}
          areActionsLocked={areActionsLocked}
          onToggleActive={onToggleActive}
        />
      ))}
    </ul>
  );
}

function useAdminLeagueList(
  initialLeagues: AdminLeague[],
  leaguesError: string | null,
) {
  const mutationLockRef = useRef(false);
  const [leagues, setLeagues] = useState(initialLeagues);
  const [errorTitle, setErrorTitle] = useState<string | null>(
    leaguesError ? ADMIN_LEAGUES_LOAD_ERROR_TITLE : null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(leaguesError);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  async function createLeague(request: CreateLeagueRequest) {
    if (!acquireAdminMutationLock(mutationLockRef)) {
      return Promise.reject(new Error("Admin mutation already in progress"));
    }
    setErrorTitle(null);
    setErrorMessage(null);
    setIsCreating(true);
    try {
      await applyCreateResult(await submitCreateAdminLeague(request));
    } finally {
      setIsCreating(false);
      releaseAdminMutationLock(mutationLockRef);
    }
  }

  async function applyCreateResult(result: AdminLeaguesMutationResult) {
    if (!result.ok) {
      applyMutationFailure(result, setErrorTitle, setErrorMessage);
      throw new Error(result.errorMessage);
    }
    setLeagues((current) => prependAdminLeague(current, result.league));
  }

  async function toggleActive(league: AdminLeague) {
    if (!acquireAdminMutationLock(mutationLockRef)) {
      return;
    }
    setErrorTitle(null);
    setErrorMessage(null);
    setPendingId(league.id);
    try {
      const result = await submitToggleLeagueActive(league);
      if (!result.ok) {
        applyMutationFailure(result, setErrorTitle, setErrorMessage);
        return;
      }
      setLeagues((current) => replaceAdminLeague(current, result.league));
    } finally {
      setPendingId(null);
      releaseAdminMutationLock(mutationLockRef);
    }
  }

  return {
    leagues,
    errorTitle,
    errorMessage,
    pendingId,
    isBusy: isCreating || pendingId !== null,
    createLeague,
    toggleActive,
  };
}

function applyMutationFailure(
  result: AdminLeaguesMutationFailure,
  setErrorTitle: (title: string) => void,
  setErrorMessage: (message: string) => void,
) {
  setErrorTitle(result.errorTitle);
  setErrorMessage(result.errorMessage);
}
