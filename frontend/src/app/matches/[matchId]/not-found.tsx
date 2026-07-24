import Link from "next/link";
import { StatusMessage } from "@/components/StatusMessage";

export default function MatchNotFound() {
  return (
    <div className="space-y-4">
      <StatusMessage
        variant="empty"
        title="Nie znaleziono meczu"
        message="Żądany mecz nie istnieje lub jest niedostępny."
      />
      <Link
        href="/"
        className="inline-block rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500"
      >
        Powrót do lig
      </Link>
    </div>
  );
}
