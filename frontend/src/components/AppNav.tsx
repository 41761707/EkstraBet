"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { LogoutButton } from "@/components/auth/LogoutButton";

const NAV_LINKS = [
  { href: "/", label: "Strona główna" },
  { href: "/stats", label: "Kącik statystyczny" },
  { href: "/bets", label: "Kącik bukmacherski" },
  { href: "/players", label: "Zawodnicy" },
  { href: "/predictions/simulate", label: "Symulacja" },
  { href: "/o-modelach", label: "O modelach" },
  { href: "/chat", label: "Asystent" },
] as const;

const PROFILE_LINK = { href: "/profile", label: "Profil" } as const;

type AppNavProps = {
  showLogout: boolean;
  showLinks?: boolean;
  showProfile?: boolean;
};

function getNavLinks(showProfile: boolean) {
  if (!showProfile) {
    return NAV_LINKS;
  }
  return [...NAV_LINKS, PROFILE_LINK];
}

export function AppNav({
  showLogout,
  showLinks = true,
  showProfile = false,
}: AppNavProps) {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const menuId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        toggleRef.current?.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    panelRef.current?.querySelector<HTMLElement>("a, button")?.focus();

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function closeMenu() {
    setIsOpen(false);
    toggleRef.current?.focus();
  }

  const links = getNavLinks(showProfile);
  const linkClassName =
    "rounded-md px-3 py-1.5 transition hover:bg-slate-800 hover:text-white";
  const mobileLinkClassName =
    "block rounded-md px-3 py-3 text-base transition hover:bg-slate-800 hover:text-white";

  const mobileMenu =
    isOpen && isMounted
      ? createPortal(
          <div className="fixed inset-0 z-50 lg:hidden" role="presentation">
            <button
              type="button"
              className="absolute inset-0 bg-slate-950/70"
              aria-label="Zamknij menu"
              onClick={closeMenu}
            />
            <div
              ref={panelRef}
              id={menuId}
              role="dialog"
              aria-modal="true"
              aria-label="Menu nawigacyjne"
              className="absolute right-0 top-0 flex h-full w-[min(100%,20rem)] flex-col border-l border-slate-700/80 bg-slate-950 shadow-xl"
            >
              <div className="flex items-center justify-between border-b border-slate-700/80 px-4 py-4">
                <span className="text-sm font-medium text-slate-200">Menu</span>
                <button
                  type="button"
                  className="inline-flex items-center justify-center rounded-md p-2 text-slate-300 transition hover:bg-slate-800 hover:text-white"
                  aria-label="Zamknij menu"
                  onClick={closeMenu}
                >
                  <CloseIcon />
                </button>
              </div>
              <nav
                className="flex flex-1 flex-col gap-1 overflow-y-auto p-3 text-slate-300"
                aria-label="Główna nawigacja"
              >
                {showLinks
                  ? links.map((link) => (
                      <Link
                        key={link.href}
                        href={link.href}
                        className={mobileLinkClassName}
                        onClick={() => setIsOpen(false)}
                      >
                        {link.label}
                      </Link>
                    ))
                  : null}
                {showLogout ? (
                  <div className="mt-2 border-t border-slate-700/80 pt-2">
                    <LogoutButton />
                  </div>
                ) : null}
              </nav>
            </div>
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      <nav
        className="hidden items-center justify-end gap-1 text-sm text-slate-300 lg:flex"
        aria-label="Główna nawigacja"
      >
        {showLinks
          ? links.map((link) => (
              <Link key={link.href} href={link.href} className={linkClassName}>
                {link.label}
              </Link>
            ))
          : null}
        {showLogout ? <LogoutButton /> : null}
      </nav>

      <div className="lg:hidden">
        {showLinks ? (
          <>
            <button
              ref={toggleRef}
              type="button"
              className="inline-flex items-center justify-center rounded-md p-2 text-slate-300 transition hover:bg-slate-800 hover:text-white"
              aria-expanded={isOpen}
              aria-controls={menuId}
              aria-label={isOpen ? "Zamknij menu" : "Otwórz menu"}
              onClick={() => setIsOpen((open) => !open)}
            >
              {isOpen ? <CloseIcon /> : <MenuIcon />}
            </button>
            {mobileMenu}
          </>
        ) : showLogout ? (
          <LogoutButton />
        ) : null}
      </div>
    </>
  );
}

function MenuIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className="h-6 w-6"
      aria-hidden="true"
    >
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      className="h-6 w-6"
      aria-hidden="true"
    >
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}
