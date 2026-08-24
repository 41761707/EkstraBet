"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useSearchParams } from "next/navigation";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { resolvePostLoginPath } from "@/lib/authCookie";
import { navigateAfterAuth } from "@/lib/clientNavigation";

const LOGIN_INPUT_CLASS_NAME = `rounded-md ${INPUT_CLASS_NAME}`;

export function LoginForm() {
  const searchParams = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ username, password }),
      });
      const payload = (await response.json().catch(() => ({}))) as {
        detail?: string;
        first_login?: boolean;
      };
      if (!response.ok) {
        setError(
          typeof payload.detail === "string"
            ? payload.detail
            : "Nie udało się zalogować",
        );
        return;
      }

      // twardy reload: cookie z Set-Cookie musi trafić do middleware
      navigateAfterAuth(
        resolvePostLoginPath(
          payload.first_login === true,
          searchParams.get("next"),
        ),
      );
    } catch {
      setError("Błąd połączenia. Spróbuj ponownie.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-accent-text">Logowanie</h1>
        <p className="mt-2 text-sm text-muted">
          Zaloguj się, aby korzystać z EkstraBet.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-4 rounded-lg border border-border bg-surface p-6"
      >
        <label className="flex flex-col gap-1.5 text-sm text-muted">
          Nazwa użytkownika
          <input
            type="text"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            className={LOGIN_INPUT_CLASS_NAME}
          />
        </label>

        <label className="flex flex-col gap-1.5 text-sm text-muted">
          Hasło
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            className={LOGIN_INPUT_CLASS_NAME}
          />
        </label>

        {error ? (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Logowanie…" : "Zaloguj"}
        </button>
      </form>
    </div>
  );
}
