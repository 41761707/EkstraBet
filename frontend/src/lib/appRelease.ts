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
  version: "1.4.0",
  heading: "EkstraBet 1.4.0 - Sezon 1",
  releaseDate: "21.10.2026",
  character:
    "Wydanie funkcjonalne — predykcje meczów NHL, składy drużyn i statystyki " +
    "ligowe oraz ranking zdarzeń zawodników",
  changes: [
    "[EB-33] Predykcje meczów NHL z aktualnego składu: rynki drużynowe " +
      "i propsy zawodników na karcie meczu (`/matches/<match_id>/`), " +
      "sortowanie tabel składu na stronie drużyny (`/teams/<team_id>/`) " +
      "oraz jeden przebieg modelu zamiast osobnej predykcji pierwotnej " +
      "i ostatecznej.",
    "[SZP-235] Zmiany bazodanowe pod przewidywania hokejowe oraz aktualizacja " +
      "dokumentacji schematu.",
    "[SZP-236] Stałe i backend do obliczania wyników rynków hokejowych.",
    "[SZP-237] Rozliczanie zdarzeń z dyspozycją per sport (piłka i hokej) " +
      "w statystykach modeli.",
    "[SZP-238] Repozytorium historii meczów hokejowych dla pipeline'u predykcji.",
    "[SZP-239] Cechy terminarza hokejowego w modelu (przerwy, mecze dzień po dniu).",
    "[SZP-240] Ratingi drużyn i bramkarzy hokejowych.",
    "[SZP-241] Model bazowy hokeja i macierz rynków meczowych.",
    "[SZP-242] Komenda CLI `predict-hockey` i zapis predykcji hokejowych do bazy.",
    "[SZP-243] Sloty linii i ratingi zawodników hokejowych.",
    "[SZP-244] Siła składu i korekta modelu bazowego hokeja.",
    "[SZP-245] Model startu bramkarza w pipeline hokejowym.",
    "[SZP-246] Model ML goli drużynowych `HOCKEY_GOALS_GBM_V1`.",
    "[SZP-247] Generator przewidywanego składu hokejowego.",
    "[SZP-248] Model beta propsów zawodników hokejowych (gole, asysty, punkty, " +
      "strzały).",
    "[SZP-249] Predykcja pierwotna i ostateczna hokeja oraz skrypty przebiegu modelu.",
    "[SZP-250] API szczegółów meczu hokejowego: skład, kontekst terminarza " +
      "i predykcje zawodników.",
    "[SZP-251] API i widok składu drużyny hokejowej na `/teams/<team_id>/`.",
    "[SZP-252] Karta meczu NHL (`/matches/<match_id>/`): przewidywany skład, " +
      "kontekst przedmeczowy i predykcje zawodników.",
    "[SZP-253] Predykcje, zakłady i statystyki hokejowe na `/bets`, `/stats` " +
      "i w składzie drużyny.",
    "[SZP-254] Wynik NHL z dogrywką oraz statystyki sezonowe W/L/OT na " +
      "`/teams/<team_id>/` i w panelu przedmeczowym.",
    "[SZP-255] Tabela NHL i wykresy statystyk ligowych na `/leagues/<league_id>/`.",
    "[SZP-256] Ranking skumulowanych predykcji zdarzeń zawodników NHL " +
      "na `/nhl/predictions`.",
    "[SZP-258] Wykresy rozkładu goli na karcie meczu NHL (`/matches/<match_id>/`).",
    "[SZP-259] Statystyki drużyn specjalnych (przewaga i osłabienie) na stronie " +
      "ligi `/leagues/<league_id>/`.",
    "[NEW] Oznaczenie poprawnych odpowiedzi w tabeli ujawnionych typów " +
      "na `/typer-lm`.",
    "[NEW] Znak „@” przy meczach wyjazdowych w dzienniku meczów na panelu " +
      "zawodnika (`/players`).",
    "[FIX] Poprawka liczenia rozegranych meczów w tabeli hokejowej.",
    "[TECH] Dopisanie nowych tabel hokejowych do skryptu synchronizacji " +
      "local→prod (`scripts/sync_local_to_prod.py`).",
    "[INFO] Notatki wydania 1.3.0 w ekspanderze wersji na stronie głównej `/`.",
  ],
};

export function getAppReleaseTitle(release: AppRelease = APP_RELEASE): string {
  return `Wersja: ${release.version}`;
}
