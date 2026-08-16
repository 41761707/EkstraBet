import { ApiError } from "@/lib/apiShared";

export type RatingProgressLoadStatus =
  | "idle"
  | "loading"
  | "success"
  | "empty"
  | "error";

export const COMPUTE_RATING_PROGRESS_LABEL = "Oblicz progres ELO";

export const COMPUTE_RATING_PROGRESS_HINT =
  "Przeliczenie ratingów ze wszystkich meczów sezonu jest kosztowne. " +
  "Uruchom je tylko, gdy chcesz zobaczyć wykres.";

export const LOADING_RATING_PROGRESS_LABEL = "Liczenie progresu ELO...";

export const EMPTY_RATING_PROGRESS_TITLE = "Brak progresu ratingów";

export const EMPTY_RATING_PROGRESS_MESSAGE =
  "Progres pojawi się po rozegraniu pierwszych meczów sezonu.";

export const ERROR_RATING_PROGRESS_TITLE =
  "Nie udało się obliczyć progresu ELO";

const FALLBACK_ERROR_MESSAGE =
  "Spróbuj ponownie za chwilę. Jeśli problem się powtórzy, odśwież stronę.";

export function mapRatingProgressLoadError(error: unknown): {
  status: "empty" | "error";
  message: string;
} {
  if (error instanceof ApiError && error.status === 404) {
    return {
      status: "empty",
      message: EMPTY_RATING_PROGRESS_MESSAGE,
    };
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return { status: "error", message: error.message };
  }
  return { status: "error", message: FALLBACK_ERROR_MESSAGE };
}
