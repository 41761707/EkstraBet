"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import {
  type AddUserFormValues,
  buildCreateUserRequest,
  validateAddUserForm,
} from "@/components/admin/adminUsersModel";
import { PasswordField } from "@/components/auth/PasswordField";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import type { CreateUserRequest } from "@/types/api";

const FIELD_CLASS_NAME = `w-full rounded-md ${INPUT_CLASS_NAME}`;
const CHECKBOX_CLASS_NAME =
  "rounded border-border bg-surface-raised accent-accent";

export const ADD_USER_FORM_TITLE = "Nowe konto";
export const ADD_USER_PASSWORD_HINT =
  "Hasło tymczasowe nie wraca w liście kont. " +
  "Przekaż je użytkownikowi poza aplikacją.";

interface AddUserFormProps {
  isSubmitting: boolean;
  onSubmit: (request: CreateUserRequest) => Promise<void>;
}

const EMPTY_FORM: AddUserFormValues = {
  username: "",
  temporaryPassword: "",
  displayName: "",
  isAdmin: false,
};

export function AddUserForm({ isSubmitting, onSubmit }: AddUserFormProps) {
  const [values, setValues] = useState<AddUserFormValues>(EMPTY_FORM);
  const [validationError, setValidationError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const error = validateAddUserForm(values);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    try {
      await onSubmit(buildCreateUserRequest(values));
      setValues(EMPTY_FORM);
    } catch {
      // komunikat API pokazuje panel; wartości zostają, żeby dało się poprawić
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-lg border border-border bg-surface-muted p-4"
    >
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-text">{ADD_USER_FORM_TITLE}</h3>
        <p className="text-sm text-muted">{ADD_USER_PASSWORD_HINT}</p>
      </div>
      <AddUserFields
        values={values}
        isSubmitting={isSubmitting}
        onChange={setValues}
      />
      {validationError ? (
        <StatusMessage
          variant="error"
          title="Sprawdź dane formularza"
          message={validationError}
        />
      ) : null}
      <button
        type="submit"
        disabled={isSubmitting}
        className={
          "rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent " +
          "transition hover:bg-accent-hover disabled:cursor-not-allowed " +
          "disabled:opacity-60"
        }
      >
        {isSubmitting ? "Tworzenie…" : "Utwórz konto"}
      </button>
    </form>
  );
}

interface AddUserFieldsProps {
  values: AddUserFormValues;
  isSubmitting: boolean;
  onChange: (values: AddUserFormValues) => void;
}

function AddUserFields({ values, isSubmitting, onChange }: AddUserFieldsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Nazwa użytkownika
        <input
          type="text"
          name="username"
          autoComplete="off"
          value={values.username}
          disabled={isSubmitting}
          onChange={(event) =>
            onChange({ ...values, username: event.target.value })
          }
          required
          className={FIELD_CLASS_NAME}
        />
      </label>
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Wyświetlana nazwa (opcjonalnie)
        <input
          type="text"
          name="display_name"
          autoComplete="off"
          value={values.displayName}
          disabled={isSubmitting}
          onChange={(event) =>
            onChange({ ...values, displayName: event.target.value })
          }
          className={FIELD_CLASS_NAME}
        />
      </label>
      <PasswordField
        label="Hasło tymczasowe"
        name="temporary_password"
        autoComplete="new-password"
        value={values.temporaryPassword}
        onChange={(temporaryPassword) =>
          onChange({ ...values, temporaryPassword })
        }
      />
      <label className="flex items-center gap-2 text-sm text-text sm:self-end">
        <input
          type="checkbox"
          name="is_admin"
          checked={values.isAdmin}
          disabled={isSubmitting}
          onChange={(event) =>
            onChange({ ...values, isAdmin: event.target.checked })
          }
          className={CHECKBOX_CLASS_NAME}
        />
        Nadaj rolę administratora
      </label>
    </div>
  );
}
