export const PRIMARY_NAV_LINKS = [
  { href: "/", label: "Strona główna" },
  { href: "/typer-lm", label: "Typer LM" },
  { href: "/stats", label: "Kącik statystyczny" },
  { href: "/bets", label: "Kącik bukmacherski" },
  { href: "/players", label: "Zawodnicy" },
] as const;

export const MORE_NAV_LINKS = [
  { href: "/predictions/simulate", label: "Symulacja" },
  { href: "/o-modelach", label: "O modelach" },
  { href: "/chat", label: "Asystent" },
] as const;

export const PROFILE_LINK = { href: "/profile", label: "Profil" } as const;

export type AppNavLink =
  | (typeof PRIMARY_NAV_LINKS)[number]
  | (typeof MORE_NAV_LINKS)[number]
  | typeof PROFILE_LINK;

/** Flat list for the mobile drawer — same destinations, original order. */
export function getAllNavLinks(showProfile: boolean): AppNavLink[] {
  const links: AppNavLink[] = [...PRIMARY_NAV_LINKS, ...MORE_NAV_LINKS];
  if (!showProfile) {
    return links;
  }
  return [...links, PROFILE_LINK];
}

export function isMoreNavActive(
  pathname: string,
  moreLinks: readonly { href: string }[] = MORE_NAV_LINKS,
): boolean {
  return moreLinks.some(
    (link) => pathname === link.href || pathname.startsWith(`${link.href}/`),
  );
}
