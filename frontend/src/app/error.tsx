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
        title="Coś poszło nie tak"
        message={error.message}
      />
      <button
        type="button"
        onClick={reset}
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-accent-hover"
      >
        Spróbuj ponownie
      </button>
    </div>
  );
}
