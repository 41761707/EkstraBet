/** Contest rules shown in the Typer LM expander (source: plan section 6.7). */

export const TYPER_LM_RULES_TITLE = "Regulamin Typera LM";

export interface TyperLmRulesSection {
  heading: string;
  items: readonly string[];
}

export const TYPER_LM_RULES_SECTIONS: readonly TyperLmRulesSection[] = [
  {
    heading: "Regulamin rozgrywek",
    items: [
      "Konkurs obejmuje Ligę Mistrzów w sezonie 2026/2027.",
      "W fazie ligowej (kolejki 1–8) administrator publikuje dokładnie " +
        "9 meczów na kolejkę. Typujesz tylko te spotkania. "+ 
        "Uwaga: Liczba meczów deklarowana przez administratora może ulec zmianie",
      "Od baraży o 1/8 finału typujesz wszystkie opublikowane mecze danej rundy pucharowej.",
      "Użytkownicy typują wyłącznie rezultat spotkania (1/X/2) w regulaminowym czasie gry. " +
        "Wynik w dogrywce i rzutach karnych nie jest uwzględniany w punktacji." + 
        "(1 - wygrana gospodarzy, X - remis, 2 - wygrana gości)"
    ]
  },
  {
    heading: "Jak typować",
    items: [
      "Dla każdego opublikowanego meczu wybierasz jedną opcję: Gospodarz, Gość bądź Remis ",
      "W konfiguracji profilu możesz zmienić sposób wyświetlania opcji między skrótami a pełnymi nazwami",
      "Typ można zapisać i zmieniać do chwili rozpoczęcia meczu. Po starcie " +
        "zapis jest zablokowany."
    ]
  },
  {
    heading: "Zasady punktacji",
    items: [
      "Trafiony typ: liczba punktów równa kursowi Superbet 1/X/2 z tabeli " +
        "kursów.",
      "Nietrafiony typ: 0 punktów.",
      "Zablokowanie kursów (czyli również punktacji) odbywa się nie później niż 30 minut przed rozpoczęciem spotkania",
      "Ranking: suma punktów, potem liczba trafień, potem nazwa " +
        "wyświetlana. Typy innych osób nie są publiczne.",
    ],
  },
];
