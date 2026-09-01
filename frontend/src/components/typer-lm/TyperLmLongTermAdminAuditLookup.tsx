"use client";

import { useState, type FormEvent } from "react";

import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import { getTyperLongTermAdminHistory } from "@/lib/apiClient";
import { parseOptionalPositiveInt } from "@/lib/typerLmAdmin";
import {
  formatAdminLongTermChangeLine,
  longTermAdminAuditErrorMessage,
} from "@/lib/typerLmLongTerm";
import type { LongTermPickChange } from "@/types/api";

interface TyperLmLongTermAdminAuditLookupProps {
  seasonId: number;
  marketId: number;
}

export function TyperLmLongTermAdminAuditLookup({
  seasonId,
  marketId,
}: TyperLmLongTermAdminAuditLookupProps) {
  const [userUuid, setUserUuid] = useState("");
  const [marketIdInput, setMarketIdInput] = useState(String(marketId));
  const [rows, setRows] = useState<LongTermPickChange[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const uuid = userUuid.trim();
    if (uuid === "") {
      setErrorMessage("Podaj publiczne UUID użytkownika.");
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const history = await getTyperLongTermAdminHistory({
        userUuid: uuid,
        marketId: parseOptionalPositiveInt(marketIdInput),
        seasonId,
      });
      setRows(history);
    } catch (error) {
      setRows(null);
      setErrorMessage(longTermAdminAuditErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-medium text-text">Audyt typów długoterminowych</h3>
      <p className="text-sm text-muted">
        Odtwórz historię zestawu TOP 8 wskazanego użytkownika. Typów nie można
        tu zmieniać.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-56 flex-1 flex-col gap-1 text-sm text-muted">
          UUID użytkownika
          <input
            type="text"
            value={userUuid}
            onChange={(event) => setUserUuid(event.target.value)}
            className={`w-full rounded-md ${INPUT_CLASS_NAME}`}
            autoComplete="off"
          />
        </label>
        <label className="flex w-36 flex-col gap-1 text-sm text-muted">
          ID rynku (opcjonalnie)
          <input
            type="number"
            min={1}
            value={marketIdInput}
            onChange={(event) => setMarketIdInput(event.target.value)}
            className={`w-full rounded-md ${INPUT_CLASS_NAME}`}
          />
        </label>
        <button
          type="submit"
          disabled={isLoading}
          className={
            "rounded-lg bg-accent px-3 py-2 text-sm font-medium " +
            "text-on-accent disabled:opacity-50"
          }
        >
          Pokaż historię
        </button>
      </form>
      {errorMessage ? (
        <StatusMessage
          variant="error"
          title="Nie udało się wczytać audytu"
          message={errorMessage}
        />
      ) : null}
      <TyperLmLongTermAdminAuditResults rows={rows} isLoading={isLoading} />
    </section>
  );
}

export function TyperLmLongTermAdminAuditResults({
  rows,
  isLoading,
}: {
  rows: LongTermPickChange[] | null;
  isLoading: boolean;
}) {
  if (isLoading) {
    return <StatusMessage variant="info" title="Ładowanie historii typów" />;
  }
  if (rows === null) {
    return null;
  }
  if (rows.length === 0) {
    return (
      <StatusMessage
        variant="empty"
        title="Brak wpisów audytu"
        message="Dla podanego UUID i filtrów nie ma zapisanych zmian zestawu."
      />
    );
  }
  return (
    <ul className="space-y-1 text-sm text-text">
      {rows.map((row) => (
        <li key={`${row.id}-${row.changed_at}`}>
          {formatAdminLongTermChangeLine(row)}
        </li>
      ))}
    </ul>
  );
}
