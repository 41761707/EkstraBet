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
        href="/#ligy"
        className="text-sm text-sky-300 transition hover:text-sky-200"
      >
        ← Strona główna
      </Link>
      <h1 className="text-3xl font-bold text-white">{name}</h1>
      {meta ? <p className="text-slate-300">{meta}</p> : null}
      {lastUpdate ? (
        <p className="text-sm text-slate-500">
          Ostatnia aktualizacja: {lastUpdate}
        </p>
      ) : null}
    </section>
  );
}
