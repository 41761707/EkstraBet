import { getAdminUsers, getCurrentUser } from "@/lib/api";
import { ApiError } from "@/lib/apiShared";
import type { AdminUser, UserPublic } from "@/types/api";

export type AdminPageResult =
  | {
      kind: "ok";
      currentUser: UserPublic;
      users: AdminUser[];
      usersError: string | null;
    }
  | { kind: "unauthenticated" }
  | { kind: "forbidden" }
  | { kind: "error"; message: string };

const GENERIC_ADMIN_LOAD_ERROR =
  "Spróbuj odświeżyć stronę. Jeśli problem wraca, zaloguj się ponownie.";

/** Gates `/admin` on the current user and bootstraps the users list. */
export async function loadAdminPage(): Promise<AdminPageResult> {
  try {
    const currentUser = await getCurrentUser();
    if (!currentUser.is_admin) {
      return { kind: "forbidden" };
    }
    return await loadAdminUsersBootstrap(currentUser);
  } catch (error) {
    return mapAdminGateError(error);
  }
}

async function loadAdminUsersBootstrap(
  currentUser: UserPublic,
): Promise<AdminPageResult> {
  try {
    const users = await getAdminUsers();
    return {
      kind: "ok",
      currentUser,
      users,
      usersError: null,
    };
  } catch (error) {
    const gateError = mapAdminGateError(error);
    if (gateError.kind !== "error") {
      return gateError;
    }
    return {
      kind: "ok",
      currentUser,
      users: [],
      usersError: gateError.message,
    };
  }
}

function mapAdminGateError(error: unknown): AdminPageResult {
  if (error instanceof ApiError && error.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (error instanceof ApiError && error.status === 403) {
    return { kind: "forbidden" };
  }
  const message =
    error instanceof ApiError ? error.message : GENERIC_ADMIN_LOAD_ERROR;
  return { kind: "error", message };
}
