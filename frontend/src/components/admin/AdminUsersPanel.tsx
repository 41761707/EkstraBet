"use client";

import { useRef, useState } from "react";

import { AddUserForm } from "@/components/admin/AddUserForm";
import { AdminUserRow } from "@/components/admin/AdminUserRow";
import {
  ADMIN_USERS_BUSY_HINT,
  ADMIN_USERS_DESCRIPTION,
  ADMIN_USERS_LOAD_ERROR_TITLE,
  ADMIN_USERS_TITLE,
  EMPTY_ADMIN_USERS_MESSAGE,
  EMPTY_ADMIN_USERS_TITLE,
  prependAdminUser,
  replaceAdminUser,
} from "@/components/admin/adminUsersModel";
import {
  acquireAdminMutationLock,
  releaseAdminMutationLock,
  submitCreateAdminUser,
  submitToggleUserActive,
  submitToggleUserAdmin,
  type AdminUsersMutationFailure,
  type AdminUsersMutationResult,
} from "@/components/admin/adminUsersMutations";
import { StatusMessage } from "@/components/StatusMessage";
import type { AdminUser, CreateUserRequest } from "@/types/api";

interface AdminUsersPanelProps {
  currentUserUuid: string;
  initialUsers: AdminUser[];
  usersError?: string | null;
}

export function AdminUsersStatus({
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

export function AdminUsersPanel({
  currentUserUuid,
  initialUsers,
  usersError = null,
}: AdminUsersPanelProps) {
  const list = useAdminUserList(currentUserUuid, initialUsers, usersError);

  return (
    <section
      aria-busy={list.isBusy}
      className="space-y-4 rounded-xl border border-border bg-surface p-4"
    >
      <header className="space-y-1">
        <h2 className="text-lg font-semibold text-text">{ADMIN_USERS_TITLE}</h2>
        <p className="text-sm text-muted">{ADMIN_USERS_DESCRIPTION}</p>
      </header>
      <AddUserForm isSubmitting={list.isBusy} onSubmit={list.createUser} />
      <AdminUsersStatus title={list.errorTitle} message={list.errorMessage} />
      {list.isBusy ? (
        <p className="text-sm text-muted" aria-live="polite">
          {ADMIN_USERS_BUSY_HINT}
        </p>
      ) : null}
      <AdminUsersList
        users={list.users}
        currentUserUuid={currentUserUuid}
        pendingUuid={list.pendingUuid}
        areActionsLocked={list.isBusy}
        hasError={Boolean(list.errorMessage)}
        onToggleActive={list.toggleActive}
        onToggleAdmin={list.toggleAdmin}
      />
    </section>
  );
}

interface AdminUsersListProps {
  users: AdminUser[];
  currentUserUuid: string;
  pendingUuid: string | null;
  areActionsLocked: boolean;
  hasError: boolean;
  onToggleActive: (user: AdminUser) => void;
  onToggleAdmin: (user: AdminUser) => void;
}

function AdminUsersList({
  users,
  currentUserUuid,
  pendingUuid,
  areActionsLocked,
  hasError,
  onToggleActive,
  onToggleAdmin,
}: AdminUsersListProps) {
  if (users.length === 0) {
    if (hasError) {
      return null;
    }
    return (
      <StatusMessage
        variant="empty"
        title={EMPTY_ADMIN_USERS_TITLE}
        message={EMPTY_ADMIN_USERS_MESSAGE}
      />
    );
  }

  return (
    <ul className="space-y-2">
      {users.map((user) => (
        <AdminUserRow
          key={user.uuid}
          user={user}
          currentUserUuid={currentUserUuid}
          isSaving={pendingUuid === user.uuid}
          areActionsLocked={areActionsLocked}
          onToggleActive={onToggleActive}
          onToggleAdmin={onToggleAdmin}
        />
      ))}
    </ul>
  );
}

function useAdminUserList(
  currentUserUuid: string,
  initialUsers: AdminUser[],
  usersError: string | null,
) {
  const mutationLockRef = useRef(false);
  const [users, setUsers] = useState(initialUsers);
  const [errorTitle, setErrorTitle] = useState<string | null>(
    usersError ? ADMIN_USERS_LOAD_ERROR_TITLE : null,
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(usersError);
  const [pendingUuid, setPendingUuid] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  async function createUser(request: CreateUserRequest) {
    if (!acquireAdminMutationLock(mutationLockRef)) {
      // formularz nie resetuje się przy odrzuceniu Promise
      return Promise.reject(new Error("Admin mutation already in progress"));
    }
    setErrorTitle(null);
    setErrorMessage(null);
    setIsCreating(true);
    try {
      await applyCreateResult(await submitCreateAdminUser(request));
    } finally {
      setIsCreating(false);
      releaseAdminMutationLock(mutationLockRef);
    }
  }

  async function applyCreateResult(result: AdminUsersMutationResult) {
    if (!result.ok) {
      applyMutationFailure(result, setErrorTitle, setErrorMessage);
      throw new Error(result.errorMessage);
    }
    setUsers((current) => prependAdminUser(current, result.user));
  }

  async function toggleActive(user: AdminUser) {
    await runUserToggle(user.uuid, () =>
      submitToggleUserActive(currentUserUuid, user),
    );
  }

  async function toggleAdmin(user: AdminUser) {
    await runUserToggle(user.uuid, () =>
      submitToggleUserAdmin(currentUserUuid, user),
    );
  }

  async function runUserToggle(
    uuid: string,
    mutate: () => Promise<AdminUsersMutationResult>,
  ) {
    if (!acquireAdminMutationLock(mutationLockRef)) {
      return;
    }
    setErrorTitle(null);
    setErrorMessage(null);
    setPendingUuid(uuid);
    try {
      const result = await mutate();
      if (!result.ok) {
        applyMutationFailure(result, setErrorTitle, setErrorMessage);
        return;
      }
      setUsers((current) => replaceAdminUser(current, result.user));
    } finally {
      setPendingUuid(null);
      releaseAdminMutationLock(mutationLockRef);
    }
  }

  return {
    users,
    errorTitle,
    errorMessage,
    pendingUuid,
    isBusy: isCreating || pendingUuid !== null,
    createUser,
    toggleActive,
    toggleAdmin,
  };
}

function applyMutationFailure(
  result: AdminUsersMutationFailure,
  setErrorTitle: (title: string) => void,
  setErrorMessage: (message: string) => void,
) {
  setErrorTitle(result.errorTitle);
  setErrorMessage(result.errorMessage);
}
