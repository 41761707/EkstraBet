"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";

import { LogoutButton } from "@/components/auth/LogoutButton";
import { NavMoreMenu } from "@/components/NavMoreMenu";
import {
  getAllNavLinks,
  getMoreNavLinks,
  PRIMARY_NAV_LINKS,
  PROFILE_LINK,
  type AppNavLink,
} from "@/lib/appNavLinks";

type AppNavProps = {
  showLogout: boolean;
  showLinks?: boolean;
  showProfile?: boolean;
  showAdmin?: boolean;
};

const HAMBURGER_CLASS_NAME =
  "inline-flex items-center justify-center rounded-md p-2 text-muted " +
  "transition hover:bg-surface-raised hover:text-text";

const DESKTOP_LINK_CLASS_NAME =
  "whitespace-nowrap rounded-md px-2.5 py-1.5 transition " +
  "hover:bg-surface-raised hover:text-text";

function useMobileMenu() {
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

  return { isOpen, setIsOpen, isMounted, menuId, toggleRef, panelRef, closeMenu };
}

export function AppNav({
  showLogout,
  showLinks = true,
  showProfile = false,
  showAdmin = false,
}: AppNavProps) {
  const { isOpen, setIsOpen, isMounted, menuId, toggleRef, panelRef, closeMenu } =
    useMobileMenu();
  const mobileLinks = getAllNavLinks(showProfile, showAdmin);
  const moreLinks = getMoreNavLinks(showAdmin);
  const mobileLinkClassName =
    "block rounded-md px-3 py-3 text-base transition hover:bg-surface-raised hover:text-text";

  const mobileMenu =
    isOpen && isMounted
      ? createPortal(
          <MobileNavPanel
            menuId={menuId}
            panelRef={panelRef}
            links={mobileLinks}
            showLinks={showLinks}
            showLogout={showLogout}
            mobileLinkClassName={mobileLinkClassName}
            onClose={closeMenu}
            onNavigate={() => setIsOpen(false)}
          />,
          document.body,
        )
      : null;

  return (
    <>
      <nav
        className="hidden items-center justify-end gap-0.5 text-sm text-muted lg:flex"
        aria-label="Główna nawigacja"
      >
        {showLinks ? (
          <>
            {PRIMARY_NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={DESKTOP_LINK_CLASS_NAME}
              >
                {link.label}
              </Link>
            ))}
            <NavMoreMenu
              links={moreLinks}
              linkClassName={DESKTOP_LINK_CLASS_NAME}
            />
            {showProfile ? (
              <Link href={PROFILE_LINK.href} className={DESKTOP_LINK_CLASS_NAME}>
                {PROFILE_LINK.label}
              </Link>
            ) : null}
          </>
        ) : null}
        {showLogout ? <LogoutButton /> : null}
      </nav>

      <div className="lg:hidden">
        {showLinks ? (
          <>
            <button
              ref={toggleRef}
              type="button"
              className={HAMBURGER_CLASS_NAME}
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

interface MobileNavPanelProps {
  menuId: string;
  panelRef: RefObject<HTMLDivElement | null>;
  links: AppNavLink[];
  showLinks: boolean;
  showLogout: boolean;
  mobileLinkClassName: string;
  onClose: () => void;
  onNavigate: () => void;
}

function MobileNavPanel({
  menuId,
  panelRef,
  links,
  showLinks,
  showLogout,
  mobileLinkClassName,
  onClose,
  onNavigate,
}: MobileNavPanelProps) {
  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-overlay"
        aria-label="Zamknij menu"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        id={menuId}
        role="dialog"
        aria-modal="true"
        aria-label="Menu nawigacyjne"
        className={
          "absolute right-0 top-0 flex h-full w-[min(100%,20rem)] flex-col " +
          "border-l border-border bg-page shadow-xl"
        }
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-4">
          <span className="text-sm font-medium text-text">Menu</span>
          <button
            type="button"
            className={HAMBURGER_CLASS_NAME}
            aria-label="Zamknij menu"
            onClick={onClose}
          >
            <CloseIcon />
          </button>
        </div>
        <nav
          className="flex flex-1 flex-col gap-1 overflow-y-auto p-3 text-muted"
          aria-label="Główna nawigacja"
        >
          {showLinks
            ? links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={mobileLinkClassName}
                  onClick={onNavigate}
                >
                  {link.label}
                </Link>
              ))
            : null}
          {showLogout ? (
            <div className="mt-2 border-t border-border pt-2">
              <LogoutButton />
            </div>
          ) : null}
        </nav>
      </div>
    </div>
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
