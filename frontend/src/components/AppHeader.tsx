import Link from "next/link";
import { cookies } from "next/headers";

import { AppNav } from "@/components/AppNav";
import { getAuthCookieName, isAuthEnabled } from "@/lib/authCookie";
import { FIRST_LOGIN_PATH } from "@/lib/firstLogin";
import { isFirstLoginPending } from "@/lib/firstLoginGate";

export async function AppHeader() {
  const jar = await cookies();
  const hasSession = Boolean(jar.get(getAuthCookieName())?.value);
  const showLogout = isAuthEnabled() && hasSession;
  const hideAppLinks = showLogout && (await isFirstLoginPending());
  const homeHref = hideAppLinks ? FIRST_LOGIN_PATH : "/";

  return (
    <header className="border-b border-border bg-page/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href={homeHref} className="group flex shrink-0 items-center gap-2">
          <span className="text-2xl" aria-hidden="true">
            ⚽
          </span>
          <span className="text-lg font-semibold text-accent-text group-hover:text-accent-text-hover">
            EkstraBet
          </span>
        </Link>
        <AppNav
          showLogout={showLogout}
          showLinks={!hideAppLinks}
          showProfile={showLogout}
        />
      </div>
    </header>
  );
}
