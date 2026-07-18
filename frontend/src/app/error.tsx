"use client";

import { StatusMessage } from "@/components/StatusMessage";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <div className="space-y-4">
      <StatusMessage
        variant="error"
        title="Something went wrong"
        message={error.message}
      />
      <button
        type="button"
        onClick={reset}
        className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500"
      >
        Try again
      </button>
    </div>
  );
}
