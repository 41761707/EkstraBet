import { redirect } from "next/navigation";

import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getCurrentUser } from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import { profilePath } from "@/lib/profilePaths";

export const dynamic = "force-dynamic";

export default async function ProfileAliasPage() {
  if (!isAuthEnabled()) {
    redirect("/");
  }

  const result = await loadProfileOwner();
  if (result.kind === "unauthenticated") {
    redirect("/login");
  }
  if (result.kind === "unknown") {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać profilu"
        message="Spróbuj odświeżyć stronę. Jeśli problem wraca, wyloguj się i zaloguj ponownie."
      />
    );
  }

  redirect(profilePath(result.username));
}

type ProfileOwnerResult =
  | { kind: "ok"; username: string }
  | { kind: "unauthenticated" }
  | { kind: "unknown" };

async function loadProfileOwner(): Promise<ProfileOwnerResult> {
  try {
    const user = await getCurrentUser();
    return { kind: "ok", username: user.username };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthenticated" };
    }
    return { kind: "unknown" };
  }
}
