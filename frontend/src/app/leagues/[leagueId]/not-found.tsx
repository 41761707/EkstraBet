import Link from "next/link";
import { StatusMessage } from "@/components/StatusMessage";

export default function LeagueNotFound() {
  return (
    <div className="space-y-4">
      <StatusMessage
        variant="empty"
        title="League not found"
        message="The requested league does not exist or is not available."
      />
      <Link
        href="/"
        className="inline-block rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500"
      >
        Back to leagues
      </Link>
    </div>
  );
}
