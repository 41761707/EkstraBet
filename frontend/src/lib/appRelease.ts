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
  version: "1.3.0",
  heading: "EkstraBet 1.3.0 - Sezon 1",
  releaseDate: "28.09.2026",
  character:
    "Wydanie funkcjonalne — moje zakłady i ranking typerów, przebieg meczu " +
    "NHL oraz predykcja mistrza, awansu i spadku na stronie ligi",
  changes: [
    "[EB-11] Moje zakłady i ranking typerów: strona `/moje-zaklady` " +
      "(bankroll, kupony, historia i wyniki) w menu oraz ranking na " +
      "`/typers`; sekcja przeniesiona z profilu, z dopracowaniem filtrów " +
      "i podatku od wygranej po testach.",
    "[EB-31] Zakładka „Przebieg meczu” na stronie meczu NHL " +
      "(`/matches/<match_id>/`) — gole, kary, gra w przewadze i puste bramki.",
    "[EB-32] Predykcja końca sezonu na stronie ligi `/leagues/<league_id>/`: " +
      "tabela punktów oraz kluczowe miejsca (mistrz, awans do pucharów, spadek).",
    "[SZP-141] Migracja bankrolla typerów i wycofanie starych tabel kuponów " +
      "ze skryptu sync local→prod; konta systemowe nie logują się hasłem.",
    "[SZP-142] Wyliczanie poprawności zdarzeń piłkarskich na kuponie.",
    "[SZP-143] Repozytorium bankrolla typerów (kapitał startowy i jednostka).",
    "[SZP-144] Repozytorium kuponów typerów.",
    "[SZP-145] Rozliczanie kuponów typerów po zakończeniu zdarzeń.",
    "[SZP-146] Ranking i analityka zakładów (profit, ROI, skuteczność) " +
      "w repozytorium typerów.",
    "[SZP-147] Serwis zakładów gracza — bankroll, kupony i wyniki.",
    "[SZP-148] Router i schematy API sekcji zakładów użytkownika.",
    "[SZP-149] Typy TypeScript i klient frontendowy zakładów użytkownika.",
    "[SZP-150] Sekcja „Moje zakłady”: bankroll, budowanie kuponu, historia " +
      "i podsumowanie wyników.",
    "[SZP-226] Repozytorium slotów awansu i spadku dla lig piłkarskich.",
    "[SZP-227] Helpery slotów ligowych (mistrz, puchary, spadek).",
    "[SZP-228] Serwis, schemat i router projekcji sezonu ze slotami awansu i spadku.",
    "[SZP-229] Model UI i tabela kluczowych miejsc (mistrz, awans, spadek) " +
      "w projekcji sezonu.",
    "[SZP-230] Zakładki „Punkty” i „Kluczowe miejsca” w oknie projekcji " +
      "sezonu na `/leagues/<league_id>/`.",
    "[SZP-231] Synchronizacja kolumny slotów w skrypcie local→prod oraz " +
      "aktualizacja dokumentacji bazy.",
    "[SZP-232] Ranking typerów na `/typers` — filtry, tabela wyników i link " +
      "w nawigacji.",
    "[SZP-233] Poprawki dokumentacji bazy dla struktur typowania (bankroll i kupony).",
    "[TECH] Paczka SQL do podpinania terminarza pod symulację sezonu " +
      "(`sql/simulate_season.sql`).",
    "[TECH] Wykluczenie credentiali Cursora z repozytorium (`.gitignore`).",
  ],
};

export function getAppReleaseTitle(release: AppRelease = APP_RELEASE): string {
  return `Wersja: ${release.version}`;
}
