/**
 * Hardcoded current release shown on the home-page expander.
 * Git tags and patch_notes/ are not available in the frontend Docker image.
 */

export interface AppRelease {
  version: string;
  heading: string;
  releaseDate: string;
  character: string;
  changes: readonly string[];
}

// Przy nowym tagu skopiuj wersję do `version` oraz treść z
// patch_notes/<tag>.md (złączone kontynuacje punktów w jeden string).

export const APP_RELEASE: AppRelease = {
  version: "1.7.0",
  heading: "EkstraBet 1.7.0 - Sezon 1",
  releaseDate: "20.11.2026",
  character:
    "Wydanie funkcjonalne - profil zawodnika hokejowego, zakłady na " +
    "zawodników i historia meczów przy rekomendacjach drużyn",
  changes: [
    "[EB-35] Profil zawodnika hokejowego na `/players/<player_id>/`: " +
      "sezon, liczba meczów, rywal i partner, protokół z wykresami, " +
      "rozbicie zdarzeń oraz log meczów. Wejście z linku „Profil " +
      "zawodnika” w ekspanderze na `/players`.",
    "[EB-41] Pasek historii ostatnich meczów przy rekomendacjach " +
      "drużyn na `/bets` (okno 5 lub 10 i sortowanie po historii). " +
      "Słupki obu drużyn mają wspólną skalę. Z tabeli zakładów " +
      "zawodników znika kolumna modelu.",
    "[SZP-360] Koperta profilu zawodnika, rejestr źródeł po sporcie " +
      "i błędy domenowe.",
    "[SZP-361] Wspólny odczyt przekroju statystyk hokeja pod profil " +
      "zawodnika.",
    "[SZP-362] Odczyt rozbicia zdarzeń hokejowych na profilu " +
      "zawodnika.",
    "[SZP-363] Serwis profilu zawodnika z dyspozycją po `sport_id` " +
      "(źródło hokeja).",
    "[SZP-364] Endpoint profilu `GET /players/{player_id}/profile`.",
    "[SZP-365] Strona profilu `/players/<player_id>/` oraz parametry " +
      "filtrów w adresie.",
    "[SZP-366] Filtry przekroju na profilu zawodnika: sezon, rywal i " +
      "wyszukiwarka partnera.",
    "[SZP-367] Widok hokejowy profilu: kafelki protokołu, rozbicie " +
      "zdarzeń i log meczów na `/players/<player_id>/`.",
    "[SZP-368] Link „Profil zawodnika” w ekspanderze listy na " +
      "`/players`.",
    "[SZP-450] Reguła trafienia i rozliczenia propsów hokejowych " +
      "(strzały, punkty, asysty, gole).",
    "[SZP-451] Zapytanie strony rekomendacji zakładów na " +
      "zawodników.",
    "[SZP-452] Odczyt ostatnich meczów zawodnika pod pasek historii " +
      "propsu.",
    "[SZP-453] Serwis rekomendacji zakładów na zawodników.",
    "[SZP-454] Endpoint rekomendacji zawodników " +
      "`GET /bets/player-recommendations`.",
    "[SZP-455] Typy i klient HTTP rekomendacji zawodników na " +
      "froncie.",
    "[SZP-456] Parametry filtrów zakładów zawodników w adresie " +
      "`/bets`.",
    "[SZP-457] Gałąź „Zawodnicy” na `/bets` (hokej): filtry i tabela " +
      "rekomendacji propsów.",
    "[SZP-458] Pasek historii w tabeli rekomendacji zawodników na " +
      "`/bets`.",
  ],
};

export function getAppReleaseTitle(release: AppRelease = APP_RELEASE): string {
  return `Wersja: ${release.version}`;
}
