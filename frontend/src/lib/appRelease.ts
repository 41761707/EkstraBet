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
  version: "1.5.1",
  heading: "EkstraBet 1.5.1 - Sezon 1",
  releaseDate: "31.10.2026",
  character:
    "Wydanie funkcjonalne - doradca stawki, sugestie zdarzeń i próg " +
    "kursu kuponów agentów",
  changes: [
    "[EB-20] Opcjonalna podpowiedź stawki w kreatorze kuponu na " +
      "`/moje-zaklady` (pewność użytkownika, Kelly i limity bankrolla). " +
      "Meta-model i kupony agentów pomijają zdarzenia poniżej kursu 1.5, " +
      "a iloczyn kursów kuponu agenta ma sufit 6.",
    "[EB-38] Sugestie zdarzeń w kreatorze kuponu na `/moje-zaklady`: " +
      "tiery S/A/B z historii kuponów, pasma kursów i werdyktu komputera, " +
      "dodawane na kupon ręcznie. Przewinięcie do kuponu po dodaniu " +
      "zdarzenia oraz link do `/stats` w FAQ na stronie głównej.",
    "[SZP-306] Wagi pewności, blending prawdopodobieństwa i matematyka " +
      "fractional Kelly w doradcy stawki.",
    "[SZP-307] Serwis rady stawki: bankroll, prawdopodobieństwo modelu, " +
      "flaga agenta i twarde limity stawki.",
    "[SZP-308] Endpoint podpowiedzi stawki " +
      "`POST /tipsters/me/advise-stake`.",
    "[SZP-309] Panel rady stawki w kreatorze na `/moje-zaklady` oraz " +
      "podpowiedź kursu katalogowego razem z bukmacherem.",
    "[SZP-318] Profil gustu, scoring i przydział tierów S/A/B w doradcy " +
      "zdarzeń.",
    "[SZP-319] Odczyt historii zakładów użytkownika i puli przyszłych " +
      "zdarzeń pod sugestie.",
    "[SZP-320] Serwis sugestii zdarzeń (profil, werdykt komputera, tiery).",
    "[SZP-321] Endpoint sugestii zdarzeń `POST /tipsters/me/suggest-events`.",
    "[SZP-322] Przycisk i panel tierów S/A/B w kreatorze kuponu na " +
      "`/moje-zaklady`.",
    "[FIX] Poprawka kompilacji panelu zawodnika (`/players`) przy " +
      "średniej ocenie hokejowej i punktach wykresu.",
    "[TECH] Odświeżenie tabeli rankingu na `/typer-lm` (oznaczenia miejsc " +
      "i „Ty”) oraz korekta opisów regulaminu.",
    "[TECH] Zasady pracy agenta w pliku `AGENTS.md`.",
    "[TECH] Usunięcie starego frontendu Streamlit (`web_code`).",
    "[TECH] Usunięcie testów wyglądu frontendu; zostają testy logiki.",
  ],
};

export function getAppReleaseTitle(release: AppRelease = APP_RELEASE): string {
  return `Wersja: ${release.version}`;
}
