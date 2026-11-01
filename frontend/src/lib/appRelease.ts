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
  version: "1.5.2",
  heading: "EkstraBet 1.5.2 - Sezon 1",
  releaseDate: "01.11.2026",
  character:
    "Wydanie funkcjonalne - infografika meczu piłkarskiego i " +
    "poprawione liczenie analityki kuponów",
  changes: [
    "[R-1] Infografika meczu piłkarskiego na `/matches/<match_id>/` " +
      "w zakładce „Infografika meczowa”: prawdopodobieństwa wyniku, " +
      "BTTS i over/under 2.5, najczęstsze wyniki, bezpośrednie " +
      "spotkania i forma oraz pobranie PNG.",
    "[FIX] Poprawka liczenia analityki na `/moje-zaklady` i " +
      "`/profile/<username>/`: zysk rozliczonych kuponów (każdy " +
      "kupon raz), stawka kuponów w obiegu oraz widok per zakład, " +
      "w którym zdarzenie liczy się jak singiel za stawkę kuponu. " +
      "Kwoty można pokazać w walucie albo w jednostce stawki. Na " +
      "`/typers` doprecyzowane opisy średniego wyniku i średniego " +
      "kursu.",
  ],
};

export function getAppReleaseTitle(release: AppRelease = APP_RELEASE): string {
  return `Wersja: ${release.version}`;
}
