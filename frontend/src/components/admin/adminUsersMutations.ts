import {
  ADMIN_USER_CREATE_ERROR_TITLE,
  ADMIN_USER_TOGGLE_ERROR_TITLE,
  SELF_DEACTIVATE_HINT,
  SELF_REVOKE_ADMIN_HINT,
  canSetUserAdmin,
  canSetUserActive,
  mapAdminUserError,
} from "@/components/admin/adminUsersModel";
import {
  createAdminUser,
  setAdminUserActive,
  setAdminUserAdmin,
} from "@/lib/apiClient";
import type { AdminUser, CreateUserRequest } from "@/types/api";

export type AdminUsersMutationFailure = {
  ok: false;
  errorTitle: string;
  errorMessage: string;
};

export type AdminUsersMutationResult =
  | { ok: true; user: AdminUser }
  | AdminUsersMutationFailure;

/** Returns false when another admin mutation is already in flight. */
export function acquireAdminMutationLock(lock: { current: boolean }): boolean {
  if (lock.current) {
    return false;
  }
  lock.current = true;
  return true;
}

export function releaseAdminMutationLock(lock: { current: boolean }): void {
  lock.current = false;
}

export async function submitCreateAdminUser(
  request: CreateUserRequest,
): Promise<AdminUsersMutationResult> {
  try {
    const user = await createAdminUser(request);
    return { ok: true, user };
  } catch (error) {
    return {
      ok: false,
      errorTitle: ADMIN_USER_CREATE_ERROR_TITLE,
      errorMessage: mapAdminUserError(error),
    };
  }
}

export async function submitToggleUserActive(
  currentUserUuid: string,
  user: AdminUser,
): Promise<AdminUsersMutationResult> {
  const nextActive = !user.is_active;
  if (!canSetUserActive(currentUserUuid, user.uuid, nextActive)) {
    return {
      ok: false,
      errorTitle: ADMIN_USER_TOGGLE_ERROR_TITLE,
      errorMessage: SELF_DEACTIVATE_HINT,
    };
  }
  try {
    const updated = await setAdminUserActive(user.uuid, nextActive);
    return { ok: true, user: updated };
  } catch (error) {
    return {
      ok: false,
      errorTitle: ADMIN_USER_TOGGLE_ERROR_TITLE,
      errorMessage: mapAdminUserError(error),
    };
  }
}

export async function submitToggleUserAdmin(
  currentUserUuid: string,
  user: AdminUser,
): Promise<AdminUsersMutationResult> {
  const nextAdmin = !user.is_admin;
  if (!canSetUserAdmin(currentUserUuid, user.uuid, nextAdmin)) {
    return {
      ok: false,
      errorTitle: ADMIN_USER_TOGGLE_ERROR_TITLE,
      errorMessage: SELF_REVOKE_ADMIN_HINT,
    };
  }
  try {
    const updated = await setAdminUserAdmin(user.uuid, nextAdmin);
    return { ok: true, user: updated };
  } catch (error) {
    return {
      ok: false,
      errorTitle: ADMIN_USER_TOGGLE_ERROR_TITLE,
      errorMessage: mapAdminUserError(error),
    };
  }
}
