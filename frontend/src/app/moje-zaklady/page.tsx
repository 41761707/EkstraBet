import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { StatusMessage } from "@/components/StatusMessage";
import { couponDraftStorageKey } from "@/components/tipsters/couponDraftStorage";
import { loadOwnTipsterBundle } from "@/components/tipsters/loadOwnTipster";
import type { OwnTipsterBundle } from "@/components/tipsters/loadOwnTipster";
import {
  MY_BETS_DESCRIPTION,
  MY_BETS_TITLE,
  MyBetsContent,
} from "@/components/tipsters/MyBetsSection";
import {
  DEFAULT_TIPSTER_PAGE,
  DEFAULT_TIPSTER_PAGE_SIZE,
} from "@/components/tipsters/tipsterModel";
import { ApiError, getCurrentUser } from "@/lib/api";
import { MY_BETS_LINK } from "@/lib/appNavLinks";
import { isAuthEnabled } from "@/lib/authCookie";
import { profilePath } from "@/lib/profilePaths";
import { parsePositiveInt } from "@/lib/searchParams";
import type { UserPublic } from "@/types/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Moje zakłady | EkstraBet",
  description: MY_BETS_DESCRIPTION,
};

interface MyBetsPageProps {
  searchParams: Promise<Record<string, string | undefined>>;
}

export default async function MyBetsPage({ searchParams }: MyBetsPageProps) {
  if (!isAuthEnabled()) {
    redirect("/");
  }

  const query = await searchParams;
  const userResult = await loadSignedInUser();
  if (userResult.kind === "unauthenticated") {
    redirect("/login");
  }
  if (userResult.kind === "unknown") {
    return (
      <StatusMessage
        variant="error"
        title="Nie udało się wczytać konta"
        message="Spróbuj odświeżyć stronę. Jeśli problem wraca, wyloguj się i zaloguj ponownie."
      />
    );
  }

  const tipster = await loadOwnTipsterBundle(
    parsePositiveInt(query.page) ?? DEFAULT_TIPSTER_PAGE,
    parsePositiveInt(query.page_size) ?? DEFAULT_TIPSTER_PAGE_SIZE,
  );

  return (
    <MyBetsPageView query={query} username={userResult.user.username} tipster={tipster} />
  );
}

function MyBetsPageView({
  query,
  username,
  tipster,
}: {
  query: Record<string, string | undefined>;
  username: string;
  tipster: OwnTipsterBundle;
}) {
  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <h1 className="text-3xl font-bold text-text">{MY_BETS_TITLE}</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted sm:text-base">
          {MY_BETS_DESCRIPTION}
        </p>
      </header>
      <MyBetsContent
        {...tipster}
        isOwnProfile
        isSystemProfile={false}
        profilePath={MY_BETS_LINK.href}
        searchParams={query}
        draftStorageKey={couponDraftStorageKey(profilePath(username))}
      />
    </div>
  );
}

type SignedInUserResult =
  | { kind: "ok"; user: UserPublic }
  | { kind: "unauthenticated" }
  | { kind: "unknown" };

async function loadSignedInUser(): Promise<SignedInUserResult> {
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
