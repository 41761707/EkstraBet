import { redirect } from "next/navigation";

import { FirstLoginForm } from "@/components/auth/FirstLoginForm";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getCurrentUser } from "@/lib/api";

export default async function FirstLoginPage() {
  const result = await loadFirstLoginUser();
  if (result.kind === "unauthenticated") {
    redirect("/login");
  }
  if (result.kind === "completed") {
    redirect("/");
  }
  if (result.kind === "unknown") {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać danych konta"
        message="Spróbuj odświeżyć stronę. Jeśli problem wraca, wyloguj się i zaloguj ponownie."
      />
    );
  }
  return (
    <FirstLoginForm
      initialUsername={result.username}
      initialDisplayName={result.displayName}
    />
  );
}

type FirstLoginUserResult =
  | { kind: "ok"; username: string; displayName: string }
  | { kind: "completed" }
  | { kind: "unauthenticated" }
  | { kind: "unknown" };

async function loadFirstLoginUser(): Promise<FirstLoginUserResult> {
  try {
    const user = await getCurrentUser();
    if (!user.first_login) {
      return { kind: "completed" };
    }
    return {
      kind: "ok",
      username: user.username,
      displayName: user.display_name?.trim() || user.username,
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthenticated" };
    }
    return { kind: "unknown" };
  }
}
