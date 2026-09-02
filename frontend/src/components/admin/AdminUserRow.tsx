import {
  ADMIN_DANGER_BUTTON_CLASS,
  ADMIN_SECONDARY_BUTTON_CLASS,
  StatusBadge,
} from "@/components/admin/adminChrome";
import {
  ADMIN_USERS_BUSY_HINT,
  SELF_ACCOUNT_HINT,
  SELF_DEACTIVATE_HINT,
  SELF_REVOKE_ADMIN_HINT,
  canSetUserActive,
  canSetUserAdmin,
  isSameAdminUser,
} from "@/components/admin/adminUsersModel";
import { formatMatchDateTime } from "@/lib/format";
import type { AdminUser } from "@/types/api";

interface AdminUserRowProps {
  user: AdminUser;
  currentUserUuid: string;
  isSaving: boolean;
  areActionsLocked: boolean;
  onToggleActive: (user: AdminUser) => void;
  onToggleAdmin: (user: AdminUser) => void;
}

export function AdminUserRow({
  user,
  currentUserUuid,
  isSaving,
  areActionsLocked,
  onToggleActive,
  onToggleAdmin,
}: AdminUserRowProps) {
  const isSelf = isSameAdminUser(currentUserUuid, user.uuid);
  const canToggleActive = canSetUserActive(
    currentUserUuid,
    user.uuid,
    !user.is_active,
  );
  const canToggleAdmin = canSetUserAdmin(
    currentUserUuid,
    user.uuid,
    !user.is_admin,
  );
  const displayName = user.display_name?.trim() ? user.display_name : "—";
  const createdLabel = user.created_at
    ? formatMatchDateTime(user.created_at)
    : "—";

  return (
    <li className="rounded-lg border border-border bg-surface-muted px-3 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1 space-y-2">
          <p className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1">
            <span className="truncate font-medium text-text">{user.username}</span>
            <span className="break-all font-mono text-sm font-normal text-muted">
              UUID {user.uuid}
            </span>
          </p>
          <p className="truncate text-sm text-muted">{displayName}</p>
          <UserStatusBadges user={user} isSelf={isSelf} />
          <p className="text-xs text-muted">Utworzono: {createdLabel}</p>
        </div>
        <UserActionButtons
          user={user}
          isSaving={isSaving}
          areActionsLocked={areActionsLocked}
          canToggleActive={canToggleActive}
          canToggleAdmin={canToggleAdmin}
          onToggleActive={onToggleActive}
          onToggleAdmin={onToggleAdmin}
        />
      </div>
    </li>
  );
}

function UserStatusBadges({
  user,
  isSelf,
}: {
  user: AdminUser;
  isSelf: boolean;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {isSelf ? <StatusBadge label={SELF_ACCOUNT_HINT} tone="accent" /> : null}
      <StatusBadge
        label={user.is_active ? "Aktywne" : "Zawieszone"}
        tone={user.is_active ? "success" : "danger"}
      />
      <StatusBadge
        label={user.is_admin ? "Administrator" : "Użytkownik"}
        tone={user.is_admin ? "accent" : "muted"}
      />
      {user.first_login ? (
        <StatusBadge label="Pierwsze logowanie" tone="muted" />
      ) : null}
    </div>
  );
}

interface UserActionButtonsProps {
  user: AdminUser;
  isSaving: boolean;
  areActionsLocked: boolean;
  canToggleActive: boolean;
  canToggleAdmin: boolean;
  onToggleActive: (user: AdminUser) => void;
  onToggleAdmin: (user: AdminUser) => void;
}

function UserActionButtons({
  user,
  isSaving,
  areActionsLocked,
  canToggleActive,
  canToggleAdmin,
  onToggleActive,
  onToggleAdmin,
}: UserActionButtonsProps) {
  const activeLabel = user.is_active ? "Zawieś" : "Wznów";
  const adminLabel = user.is_admin ? "Odbierz rolę admina" : "Nadaj rolę admina";
  const busyHint = areActionsLocked ? ADMIN_USERS_BUSY_HINT : undefined;
  const activeHint = canToggleActive ? busyHint : SELF_DEACTIVATE_HINT;
  const adminHint = canToggleAdmin ? busyHint : SELF_REVOKE_ADMIN_HINT;

  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        disabled={areActionsLocked || !canToggleActive}
        title={activeHint}
        onClick={() => onToggleActive(user)}
        className={user.is_active ? ADMIN_DANGER_BUTTON_CLASS : ADMIN_SECONDARY_BUTTON_CLASS}
      >
        {isSaving ? "Zapisywanie…" : activeLabel}
      </button>
      <button
        type="button"
        disabled={areActionsLocked || !canToggleAdmin}
        title={adminHint}
        onClick={() => onToggleAdmin(user)}
        className={ADMIN_SECONDARY_BUTTON_CLASS}
      >
        {isSaving ? "Zapisywanie…" : adminLabel}
      </button>
    </div>
  );
}
