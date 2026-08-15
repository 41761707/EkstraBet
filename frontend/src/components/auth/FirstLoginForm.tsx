"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  mapCompleteFirstLoginError,
  validateFirstLoginForm,
} from "@/components/auth/firstLoginFormModel";
import { PasswordField } from "@/components/auth/PasswordField";

interface FirstLoginFormProps {
  initialUsername: string;
  initialDisplayName: string;
}

interface AuthFieldProps {
  label: string;
  name: string;
  autoComplete: string;
  value: string;
  onChange: (value: string) => void;
}

const INPUT_CLASS_NAME =
  "rounded-md border border-slate-600 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-sky-500";

export function FirstLoginForm({
  initialUsername,
  initialDisplayName,
}: FirstLoginFormProps) {
  const router = useRouter();
  const [username, setUsername] = useState(initialUsername);
  const [displayName, setDisplayName] = useState(initialDisplayName);
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const validationError = validateFirstLoginForm({
      username,
      displayName,
      newPassword,
      newPasswordConfirm,
    });
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const didComplete = await submitCompleteFirstLogin(
        username.trim(),
        displayName.trim(),
        newPassword,
        newPasswordConfirm,
      );
      if (!didComplete.ok) {
        setError(didComplete.error);
        return;
      }
      router.replace("/");
      router.refresh();
    } catch {
      setError("Błąd połączenia. Spróbuj ponownie.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-sky-300">
          Uzupełnij konto
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Ustaw własne hasło, potwierdź nazwę użytkownika i wyświetlaną nazwę,
          aby korzystać z EkstraBet.
        </p>
      </div>

      <FirstLoginFields
        username={username}
        displayName={displayName}
        newPassword={newPassword}
        newPasswordConfirm={newPasswordConfirm}
        error={error}
        isSubmitting={isSubmitting}
        onUsernameChange={setUsername}
        onDisplayNameChange={setDisplayName}
        onNewPasswordChange={setNewPassword}
        onNewPasswordConfirmChange={setNewPasswordConfirm}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

interface FirstLoginFieldsProps {
  username: string;
  displayName: string;
  newPassword: string;
  newPasswordConfirm: string;
  error: string | null;
  isSubmitting: boolean;
  onUsernameChange: (value: string) => void;
  onDisplayNameChange: (value: string) => void;
  onNewPasswordChange: (value: string) => void;
  onNewPasswordConfirmChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function FirstLoginFields({
  username,
  displayName,
  newPassword,
  newPasswordConfirm,
  error,
  isSubmitting,
  onUsernameChange,
  onDisplayNameChange,
  onNewPasswordChange,
  onNewPasswordConfirmChange,
  onSubmit,
}: FirstLoginFieldsProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="flex flex-col gap-4 rounded-lg border border-slate-700/80 bg-slate-900/50 p-6"
    >
      <AuthField
        label="Nazwa użytkownika"
        name="username"
        autoComplete="username"
        value={username}
        onChange={onUsernameChange}
      />
      <AuthField
        label="Wyświetlana nazwa (Nickname)"
        name="display_name"
        autoComplete="nickname"
        value={displayName}
        onChange={onDisplayNameChange}
      />
      <PasswordField
        label="Nowe hasło"
        name="new_password"
        autoComplete="new-password"
        value={newPassword}
        onChange={onNewPasswordChange}
      />
      <PasswordField
        label="Powtórz hasło"
        name="new_password_confirm"
        autoComplete="new-password"
        value={newPasswordConfirm}
        onChange={onNewPasswordConfirmChange}
      />

      {error ? (
        <p className="text-sm text-rose-400" role="alert">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "Zapisywanie…" : "Zapisz"}
      </button>
    </form>
  );
}

function AuthField({
  label,
  name,
  autoComplete,
  value,
  onChange,
}: AuthFieldProps) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-slate-300">
      {label}
      <input
        type="text"
        name={name}
        autoComplete={autoComplete}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
        className={INPUT_CLASS_NAME}
      />
    </label>
  );
}

async function submitCompleteFirstLogin(
  username: string,
  displayName: string,
  newPassword: string,
  newPasswordConfirm: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  const response = await fetch("/api/auth/complete-first-login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      username,
      display_name: displayName,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    }),
  });
  const payload = (await response.json().catch(() => ({}))) as {
    detail?: string;
  };
  if (!response.ok) {
    return { ok: false, error: mapCompleteFirstLoginError(payload.detail) };
  }
  return { ok: true };
}
