const FAVORITE_BADGE_CLASS =
  "inline-block shrink-0 rounded-sm border border-accent/70 bg-accent/15 " +
  "px-1 py-px text-[9px] font-semibold uppercase leading-none text-accent-text";

/** Lekki znacznik, żeby „faworyt” odcinał się od nazwy, nie zabierając jej miejsca. */
export function FavoriteBadge() {
  return <span className={FAVORITE_BADGE_CLASS}>faworyt</span>;
}
