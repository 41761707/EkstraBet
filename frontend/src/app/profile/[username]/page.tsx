import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { ProfilePage } from "@/components/profile/ProfilePage";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getCurrentUser } from "@/lib/api";
import { isAuthEnabled } from "@/lib/authCookie";
import { isOwnProfile } from "@/lib/profilePaths";
import type { UserPublic } from "@/types/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Profil | EkstraBet",
  description: "Panel ustawień zalogowanego użytkownika.",
};

interface ProfileUsernamePageProps {
  params: Promise<{ username: string }>;
}

export default async function ProfileUsernamePage({
  params,
}: ProfileUsernamePageProps) {
  if (!isAuthEnabled()) {
    redirect("/");
  }

  const { username: routeUsername } = await params;
  const result = await loadProfileUser();
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

  if (!isOwnProfile(routeUsername, result.user.username)) {
    notFound();
  }

  const displayName =
    result.user.display_name?.trim() || result.user.username;

  return (
    <ProfilePage
      username={result.user.username}
      displayName={displayName}
    />
  );
}

type ProfileUserResult =
  | { kind: "ok"; user: UserPublic }
  | { kind: "unauthenticated" }
  | { kind: "unknown" };

async function loadProfileUser(): Promise<ProfileUserResult> {
  try {
    const user = await getCurrentUser();
    return { kind: "ok", user };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return { kind: "unauthenticated" };
    }
    return { kind: "unknown" };
  }
}
