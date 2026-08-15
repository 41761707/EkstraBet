"use client";

import { useState } from "react";

import { navigateAfterAuth } from "@/lib/clientNavigation";

export function LogoutButton() {
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // i tak czyścimy sesję po stronie UI
    } finally {
      navigateAfterAuth("/login");
      setIsLoggingOut(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      disabled={isLoggingOut}
      className="rounded-md px-3 py-1.5 text-sm text-slate-300 transition hover:bg-slate-800 hover:text-white disabled:opacity-60"
    >
      {isLoggingOut ? "Wylogowywanie…" : "Wyloguj"}
    </button>
  );
}
