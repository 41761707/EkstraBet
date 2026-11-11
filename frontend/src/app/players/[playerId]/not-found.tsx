import Link from "next/link";
import { StatusMessage } from "@/components/StatusMessage";

export default function PlayerProfileNotFound() {
  return (
    <div className="space-y-4">
      <StatusMessage
        variant="empty"
        title="Nie znaleziono zawodnika"
        message="Ten zawodnik nie istnieje albo profil nie jest dostępny dla jego sportu."
      />
      <Link
        href="/players"
        className="inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-accent-hover"
      >
        Wróć do zawodników
      </Link>
    </div>
  );
}
