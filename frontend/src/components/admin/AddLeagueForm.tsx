"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import {
  type AddLeagueFormValues,
  ADMIN_LEAGUE_DICTIONARIES_ERROR_TITLE,
  ADMIN_LEAGUE_SEASONS_ERROR_TITLE,
  MAX_LEAGUE_NAME_LENGTH,
  buildCreateLeagueRequest,
  validateAddLeagueForm,
} from "@/components/admin/adminLeaguesModel";
import { INPUT_CLASS_NAME } from "@/components/inputStyles";
import { StatusMessage } from "@/components/StatusMessage";
import type {
  AdminCountry,
  AdminSeason,
  AdminSport,
  CreateLeagueRequest,
} from "@/types/api";

const FIELD_CLASS_NAME = `w-full rounded-md ${INPUT_CLASS_NAME}`;
const CHECKBOX_CLASS_NAME =
  "rounded border-border bg-surface-raised accent-accent";

function formatCountryOptionLabel(country: AdminCountry): string {
  const name = country.name?.trim() ? country.name : "—";
  return country.emoji ? `${country.emoji} ${name}` : name;
}

export const ADD_LEAGUE_FORM_TITLE = "Nowa liga";
export const ADD_LEAGUE_FORM_HINT =
  "Kraj i sport są wymagane. Sezon i poziom możesz uzupełnić później.";

interface AddLeagueFormProps {
  isSubmitting: boolean;
  countries: AdminCountry[];
  sports: AdminSport[];
  seasons: AdminSeason[];
  dictionariesError?: string | null;
  seasonsError?: string | null;
  onSubmit: (request: CreateLeagueRequest) => Promise<void>;
}

const EMPTY_FORM: AddLeagueFormValues = {
  name: "",
  countryId: "",
  sportId: "",
  currentSeasonId: "",
  tier: "",
  hasPlayerStats: false,
};

export function AddLeagueForm({
  isSubmitting,
  countries,
  sports,
  seasons,
  dictionariesError = null,
  seasonsError = null,
  onSubmit,
}: AddLeagueFormProps) {
  const [values, setValues] = useState<AddLeagueFormValues>(EMPTY_FORM);
  const [validationError, setValidationError] = useState<string | null>(null);
  const areFieldsDisabled = isSubmitting || Boolean(dictionariesError);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (dictionariesError) {
      return;
    }
    const error = validateAddLeagueForm(values, countries, sports, seasons);
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    try {
      await onSubmit(buildCreateLeagueRequest(values));
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
        <h3 className="text-sm font-semibold text-text">{ADD_LEAGUE_FORM_TITLE}</h3>
        <p className="text-sm text-muted">{ADD_LEAGUE_FORM_HINT}</p>
      </div>
      {dictionariesError ? (
        <StatusMessage
          variant="error"
          title={ADMIN_LEAGUE_DICTIONARIES_ERROR_TITLE}
          message={dictionariesError}
        />
      ) : (
        <AddLeagueFields
          values={values}
          isSubmitting={areFieldsDisabled}
          countries={countries}
          sports={sports}
          seasons={seasons}
          seasonsError={seasonsError}
          onChange={setValues}
        />
      )}
      {validationError ? (
        <StatusMessage
          variant="error"
          title="Sprawdź dane formularza"
          message={validationError}
        />
      ) : null}
      <button
        type="submit"
        disabled={areFieldsDisabled}
        className={
          "rounded-md bg-accent px-4 py-2 text-sm font-medium text-on-accent " +
          "transition hover:bg-accent-hover disabled:cursor-not-allowed " +
          "disabled:opacity-60"
        }
      >
        {isSubmitting ? "Tworzenie…" : "Utwórz ligę"}
      </button>
    </form>
  );
}

interface AddLeagueFieldsProps {
  values: AddLeagueFormValues;
  isSubmitting: boolean;
  countries: AdminCountry[];
  sports: AdminSport[];
  seasons: AdminSeason[];
  seasonsError: string | null;
  onChange: (values: AddLeagueFormValues) => void;
}

function AddLeagueFields({
  values,
  isSubmitting,
  countries,
  sports,
  seasons,
  seasonsError,
  onChange,
}: AddLeagueFieldsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Nazwa ligi
        <input
          type="text"
          name="name"
          autoComplete="off"
          value={values.name}
          disabled={isSubmitting}
          maxLength={MAX_LEAGUE_NAME_LENGTH}
          onChange={(event) => onChange({ ...values, name: event.target.value })}
          required
          className={FIELD_CLASS_NAME}
        />
      </label>
      <LeagueSelectField
        label="Kraj"
        name="country_id"
        value={values.countryId}
        disabled={isSubmitting}
        placeholder="Wybierz kraj"
        options={countries.map((country) => ({
          id: country.id,
          label: formatCountryOptionLabel(country),
        }))}
        onChange={(countryId) => onChange({ ...values, countryId })}
      />
      <LeagueSelectField
        label="Sport"
        name="sport_id"
        value={values.sportId}
        disabled={isSubmitting}
        placeholder="Wybierz sport"
        options={sports.map((sport) => ({ id: sport.id, label: sport.name }))}
        onChange={(sportId) => onChange({ ...values, sportId })}
      />
      <div className="space-y-2 sm:col-span-2">
        <LeagueSelectField
          label="Aktualny sezon (opcjonalnie)"
          name="current_season_id"
          value={values.currentSeasonId}
          disabled={isSubmitting || Boolean(seasonsError)}
          placeholder="Brak"
          options={seasons.map((season) => ({
            id: season.id,
            label: season.years,
          }))}
          onChange={(currentSeasonId) => onChange({ ...values, currentSeasonId })}
        />
        {seasonsError ? (
          <StatusMessage
            variant="info"
            title={ADMIN_LEAGUE_SEASONS_ERROR_TITLE}
            message={seasonsError}
          />
        ) : null}
      </div>
      <label className="flex flex-col gap-1.5 text-sm text-muted">
        Poziom (opcjonalnie)
        <input
          type="number"
          name="tier"
          value={values.tier}
          disabled={isSubmitting}
          onChange={(event) => onChange({ ...values, tier: event.target.value })}
          className={FIELD_CLASS_NAME}
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-text sm:self-end">
        <input
          type="checkbox"
          name="has_player_stats"
          checked={values.hasPlayerStats}
          disabled={isSubmitting}
          onChange={(event) =>
            onChange({ ...values, hasPlayerStats: event.target.checked })
          }
          className={CHECKBOX_CLASS_NAME}
        />
        Statystyki zawodników
      </label>
    </div>
  );
}

interface LeagueSelectFieldProps {
  label: string;
  name: string;
  value: string;
  disabled: boolean;
  placeholder: string;
  options: { id: number; label: string }[];
  onChange: (value: string) => void;
}

function LeagueSelectField({
  label,
  name,
  value,
  disabled,
  placeholder,
  options,
  onChange,
}: LeagueSelectFieldProps) {
  return (
    <label className="flex flex-col gap-1.5 text-sm text-muted">
      {label}
      <select
        name={name}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={FIELD_CLASS_NAME}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
