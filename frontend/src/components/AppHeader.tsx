import Link from "next/link";
import { cookies } from "next/headers";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { getAuthCookieName, isAuthEnabled } from "@/lib/auth";

export async function AppHeader() {
  const jar = await cookies();
  const hasSession = Boolean(jar.get(getAuthCookieName())?.value);
  const showLogout = isAuthEnabled() && hasSession;

  return (
    <header className="border-b border-slate-700/80 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link href="/" className="group flex items-center gap-2">
          <span className="text-2xl" aria-hidden="true">
            ⚽
          </span>
          <span className="text-lg font-semibold text-sky-300 group-hover:text-sky-200">
            EkstraBet
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm text-slate-300">
          <Link
            href="/"
            className="rounded-md px-3 py-1.5 transition hover:bg-slate-800 hover:text-white"
          >
            Strona główna
          </Link>
          <Link
            href="/stats"
            className="rounded-md px-3 py-1.5 transition hover:bg-slate-800 hover:text-white"
          >
            Kącik statystyczny
          </Link>
          <Link
            href="/bets"
            className="rounded-md px-3 py-1.5 transition hover:bg-slate-800 hover:text-white"
          >
            Kącik bukmacherski
          </Link>
          <Link
            href="/players"
            className="rounded-md px-3 py-1.5 transition hover:bg-slate-800 hover:text-white"
          >
            Zawodnicy
          </Link>
          <Link
            href="/chat"
            className="rounded-md px-3 py-1.5 transition hover:bg-slate-800 hover:text-white"
          >
            Asystent
          </Link>
          {showLogout ? <LogoutButton /> : null}
        </nav>
      </div>
    </header>
  );
}
