"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import { isMoreNavActive } from "@/lib/appNavLinks";

interface NavMoreMenuProps {
  links: readonly { href: string; label: string }[];
  linkClassName: string;
}

export function NavMoreMenu({ links, linkClassName }: NavMoreMenuProps) {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const menuId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const isActive = isMoreNavActive(pathname, links);

  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  if (links.length === 0) {
    return null;
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        className={
          `${linkClassName} inline-flex items-center gap-1 whitespace-nowrap` +
          (isActive || isOpen ? " text-text" : "")
        }
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={menuId}
        onClick={() => setIsOpen((open) => !open)}
      >
        Więcej
        <span className="text-xs" aria-hidden="true">
          {isOpen ? "▴" : "▾"}
        </span>
      </button>
      {isOpen ? (
        <ul
          id={menuId}
          role="menu"
          className={
            "absolute right-0 z-40 mt-1 min-w-44 rounded-lg border border-border " +
            "bg-surface py-1 shadow-xl"
          }
        >
          {links.map((link) => (
            <li key={link.href} role="none">
              <Link
                role="menuitem"
                href={link.href}
                className={
                  "block px-3 py-2 text-sm text-muted transition " +
                  "hover:bg-surface-muted hover:text-text"
                }
                onClick={() => setIsOpen(false)}
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
