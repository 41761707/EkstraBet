import { getCurrentUser } from "@/lib/api";
import { ApiError } from "@/lib/apiShared";
import type { UserPublic } from "@/types/api";

export type AdminPageResult =
  | { kind: "ok"; currentUser: UserPublic }
  | { kind: "unauthenticated" }
  | { kind: "forbidden" }
  | { kind: "error"; message: string };

const GENERIC_ADMIN_LOAD_ERROR =
  "Spróbuj odświeżyć stronę. Jeśli problem wraca, zaloguj się ponownie.";

/** Gates `/admin` on the current user; list bootstrap belongs to SZP-169/170. */
export async function loadAdminPage(): Promise<AdminPageResult> {
  try {
    const currentUser = await getCurrentUser();
    if (!currentUser.is_admin) {
      return { kind: "forbidden" };
    }
    return { kind: "ok", currentUser };
  } catch (error) {
    return mapAdminLoadError(error);
  }
}

function mapAdminLoadError(error: unknown): AdminPageResult {
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
