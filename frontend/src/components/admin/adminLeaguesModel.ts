import { ApiError } from "@/lib/apiShared";
import type {
  AdminCountry,
  AdminLeague,
  AdminSeason,
  AdminSport,
  CreateLeagueRequest,
} from "@/types/api";

export const MAX_LEAGUE_NAME_LENGTH = 45;

export const ADMIN_LEAGUES_TITLE = "Ligi";
export const ADMIN_LEAGUES_DESCRIPTION =
  "Twórz ligi i włączaj albo wyłączaj istniejące. " +
  "Wyłączenie nie usuwa rekordu ani danych zależnych.";

export const EMPTY_ADMIN_LEAGUES_TITLE = "Brak lig";
export const EMPTY_ADMIN_LEAGUES_MESSAGE =
  "Dodaj pierwszą ligę, aby pojawiła się na liście.";

export const ADMIN_LEAGUES_LOAD_ERROR_TITLE = "Nie udało się wczytać listy lig";
export const ADMIN_LEAGUE_CREATE_ERROR_TITLE = "Nie udało się utworzyć ligi";
export const ADMIN_LEAGUE_TOGGLE_ERROR_TITLE = "Nie udało się zapisać zmiany";
export const ADMIN_LEAGUE_DICTIONARIES_ERROR_TITLE =
  "Nie udało się wczytać list krajów lub sportów";
export const ADMIN_LEAGUE_SEASONS_ERROR_TITLE =
  "Nie udało się wczytać listy sezonów";

export const GENERIC_ADMIN_LEAGUE_ERROR =
  "Nie udało się wykonać operacji. Spróbuj ponownie.";

export const ADMIN_LEAGUES_BUSY_HINT =
  "Trwa zapisywanie. Poczekaj na zakończenie operacji.";

const ADMIN_LEAGUE_API_ERRORS: Record<string, string> = {
  "Country not found": "Nie znaleziono kraju",
  "Sport not found": "Nie znaleziono sportu",
  "Season not found": "Nie znaleziono sezonu",
  "League not found": "Nie znaleziono ligi",
  "League name is required": "Nazwa ligi jest wymagana",
  "Invalid country, sport or season": "Nieprawidłowy kraj, sport lub sezon",
  "Invalid league record": "Nieprawidłowy rekord ligi",
};

export interface AddLeagueFormValues {
  name: string;
  countryId: string;
  sportId: string;
  currentSeasonId: string;
  tier: string;
  hasPlayerStats: boolean;
}

export function validateAddLeagueForm(
  input: AddLeagueFormValues,
  countries: readonly AdminCountry[],
  sports: readonly AdminSport[],
  seasons: readonly AdminSeason[],
): string | null {
  const name = input.name.trim();
  if (!name) {
    return "Nazwa ligi jest wymagana";
  }
  if (name.length > MAX_LEAGUE_NAME_LENGTH) {
    return `Nazwa ligi może mieć maksymalnie ${MAX_LEAGUE_NAME_LENGTH} znaków`;
  }
  const countryId = parseRequiredId(input.countryId);
  if (countryId === null || !countries.some((row) => row.id === countryId)) {
    return "Wybierz kraj";
  }
  const sportId = parseRequiredId(input.sportId);
  if (sportId === null || !sports.some((row) => row.id === sportId)) {
    return "Wybierz sport";
  }
  const seasonId = parseOptionalId(input.currentSeasonId);
  if (seasonId === "invalid") {
    return "Wybierz sezon";
  }
  if (seasonId !== null && !seasons.some((row) => row.id === seasonId)) {
    return "Wybierz sezon";
  }
  const tier = parseOptionalInt(input.tier);
  if (tier === "invalid") {
    return "Poziom ligi musi być liczbą całkowitą";
  }
  return null;
}

export function buildCreateLeagueRequest(
  input: AddLeagueFormValues,
): CreateLeagueRequest {
  const countryId = requirePositiveId(input.countryId, "country_id");
  const sportId = requirePositiveId(input.sportId, "sport_id");
  const seasonId = parseOptionalId(input.currentSeasonId);
  const tier = parseOptionalInt(input.tier);
  return {
    name: input.name.trim(),
    country_id: countryId,
    sport_id: sportId,
    current_season_id: seasonId === "invalid" ? null : seasonId,
    tier: tier === "invalid" ? null : tier,
    has_player_stats: input.hasPlayerStats,
  };
}

export function mapAdminLeagueError(error: unknown): string {
  if (error instanceof ApiError) {
    return mapAdminLeagueApiDetail(error.message);
  }
  return GENERIC_ADMIN_LEAGUE_ERROR;
}

export function mapAdminLeagueApiDetail(detail: string | undefined): string {
  if (!detail) {
    return GENERIC_ADMIN_LEAGUE_ERROR;
  }
  const mapped = ADMIN_LEAGUE_API_ERRORS[detail];
  if (mapped) {
    return mapped;
  }
  if (detail.startsWith("League name must be at most")) {
    return `Nazwa ligi może mieć maksymalnie ${MAX_LEAGUE_NAME_LENGTH} znaków`;
  }
  return detail;
}

export function replaceAdminLeague(
  leagues: readonly AdminLeague[],
  updated: AdminLeague,
): AdminLeague[] {
  return leagues.map((league) => (league.id === updated.id ? updated : league));
}

export function prependAdminLeague(
  leagues: readonly AdminLeague[],
  created: AdminLeague,
): AdminLeague[] {
  if (leagues.some((league) => league.id === created.id)) {
    return replaceAdminLeague(leagues, created);
  }
  return [created, ...leagues];
}

export function leagueSeasonLabel(
  seasons: readonly AdminSeason[],
  seasonId: number | null,
): string {
  if (seasonId === null) {
    return "—";
  }
  const match = seasons.find((season) => season.id === seasonId);
  return match?.years ?? String(seasonId);
}

export function leagueCountryLabel(league: AdminLeague): string {
  const name = league.country_name?.trim() || "—";
  const emoji = league.country_emoji?.trim();
  return emoji ? `${emoji} ${name}` : name;
}

function parseRequiredId(raw: string): number | null {
  const parsed = parseOptionalId(raw);
  if (parsed === "invalid" || parsed === null) {
    return null;
  }
  return parsed;
}

function requirePositiveId(raw: string, field: string): number {
  const parsed = parseRequiredId(raw);
  if (parsed === null) {
    throw new Error(`${field} is required`);
  }
  return parsed;
}

function parseOptionalId(raw: string): number | null | "invalid" {
  const parsed = parseOptionalInt(raw);
  if (parsed === "invalid") {
    return "invalid";
  }
  if (parsed === null) {
    return null;
  }
  if (parsed < 1) {
    return "invalid";
  }
  return parsed;
}

function parseOptionalInt(raw: string): number | null | "invalid" {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return null;
  }
  if (!/^-?\d+$/.test(trimmed)) {
    return "invalid";
  }
  return Number(trimmed);
}
