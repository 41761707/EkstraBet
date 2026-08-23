import Link from "next/link";

interface LeagueHeaderProps {
  name: string;
  countryEmoji: string | null;
  countryName: string | null;
  sportName: string | null;
  lastUpdate: string | null;
}

export function LeagueHeader({
  name,
  countryEmoji,
  countryName,
  sportName,
  lastUpdate,
}: LeagueHeaderProps) {
  const meta = [countryEmoji, countryName, sportName]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className="space-y-2">
      <Link
        href="/#ligi"
        className="text-sm text-accent-text transition hover:text-accent-text-hover"
      >
        ← Strona główna
      </Link>
      <h1 className="text-3xl font-bold text-text">{name}</h1>
      {meta ? <p className="text-muted">{meta}</p> : null}
      {lastUpdate ? (
        <p className="text-sm text-subtle">
          Ostatnia aktualizacja: {lastUpdate}
        </p>
      ) : null}
    </section>
  );
}
