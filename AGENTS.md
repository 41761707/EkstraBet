# EkstraBet — zasady dla agenta

Ten plik jest żywą ściągą. Dopisuj niżej fakty, których nie widać w kodzie.
Szczegóły stylu są w `.cursor/rules/`, nie powielaj ich tutaj.

## Co to jest

EkstraBet pokazuje przewidywania zdarzeń w meczach piłki nożnej, hokeja
i koszykówki oraz narzędzia wokół nich: kursy, statystyki, kupony typerów,
ranking, Typer LM, czat i panel admina.

Aplikacja **czyta** dzienny stan bazy. Nie jest live-trackerem meczów ani
kursów. Request HTTP nie dociąga danych z internetu i nie przelicza modeli.

## Mapa repozytorium

```
Przeglądarka -> frontend/ (Next.js) -> api/ (FastAPI) -> backend/ -> MySQL
models/ (batch ML) -> MySQL
```

| Katalog | Rola | Ruszaj, gdy |
|---|---|---|
| `frontend/` | UI, App Router, klient HTTP | zmieniasz ekran lub kontrakt po stronie przeglądarki |
| `api/` | Routery HTTP i schematy Pydantic | dodajesz lub zmieniasz endpoint |
| `backend/` | SQL, serwisy, reguły sportowe | zmieniasz logikę lub zapytanie |
| `models/` | Trening, predykcja batch, artefakty | liczysz mecze poza requestem |
| `db_documentation/` | Oficjalny opis schematu MySQL | doszła lub zmieniła się tabela |
| `docs/` | Struktura repo, deploy, notatki domenowe | zmieniasz zasady warstw |
| `tasks/plans/` | Projekty techniczne | projektujesz albo realizujesz zadanie (plany istnieją tylko lokalnie, nie są gitowane) |
| `sql/` | Skrypty, które właściciel odpala ręcznie | zmiana schematu |
| `scripts/` | Backup, sync, narzędzia operacyjne | operacja poza aplikacją |
| `patch_notes/` | Notatki wydań | nowe wydanie |

`api/routers/models.py` zwraca metadane modeli z tabeli `MODELS`.
Katalog `models/` to pipeline i pliki wag. To nie jest ten sam moduł.

## Jak się poruszać

Zanim napiszesz nowy plik, znajdź sąsiada, który już robi podobną rzecz,
i trzymaj się jego kształtu.

- Frontend woła backend wyłącznie przez funkcje z `frontend/src/lib/api.ts`.
  Typy odpowiedzi są w `frontend/src/types/api.ts`.
- Router FastAPI nie zawiera SQL ani liczenia ratingów. SQL jest w
  `backend/repositories/`, obliczenia w `backend/services/`, różnice sportów
  w `backend/sports/{football,hockey,basketball}/`.
- Konfiguracja: `backend/config.py`. Połączenie z MySQL: `backend/database.py`.
- Widoczność danych publicznych i prywatnych: `backend/policies/`.
- Importy: `api` może brać z `backend`. `backend` nie importuje `api` ani
  `frontend`. `frontend` nie importuje Pythona. `models` może użyć
  `backend.config` i `backend.database`, nie woła HTTP.
- Schematu nie zmieniasz z poziomu agenta. Gdy trzeba, przygotuj skrypt SQL
  do ręcznego odpalenia i zaktualizuj `db_documentation/db_documentation.md`
  (skill `db-documentation`). Odczyt bazy: skill `db-context`, tylko SELECT.
- Sekrety (`.env`, hasła) nie wchodzą do gita.

Identyfikatory sportów w `frontend/src/types/api.ts`: piłka `1`, hokej `2`,
koszykówka `3`. NHL ma `league_id` 45. Nie wpisuj tych liczb w JSX, bierz
stałe.
Pozostałe identyfikatory pobieraj z bazy przy pomocy MCP.

Trasy UI (App Router): `/` ligi, `/leagues/[leagueId]`, `/teams/[teamId]`,
`/matches/[matchId]`, `/bets`, `/stats`, `/players`, `/predictions/simulate`,
`/typers`, `/moje-zaklady`, `/typer-lm`, `/profile`, `/chat`, `/admin`,
`/o-modelach`, `/nhl/predictions`.

## Kursy i wyniki — raz na dobę

To jest reguła operacyjna. Kodu pobierania w tym repozytorium nie ma
(`odds_scrapper.py` jest tylko wspomniany w dokumentacji bazy), więc łatwo
uznać, że kursy są żywe. Nie są.

- Kursy bukmacherskie pobieramy **jeden raz**, około północy, **do przodu**
  (na mecze, które dopiero będą). W ciągu dnia kurs w tabeli `ODDS` stoi.
- Wynik meczu zapisujemy **jeden raz**, gdy jest już znany. Nie ma
  dogrywania wyniku na żywo ani serii poprawek.
- API kursów tylko czyta (`backend/services/odds_service.py`). Unikalny
  indeks `(MATCH_ID, BOOKMAKER, EVENT)` to jeden wiersz na trójkę, nie
  historia cen.
- Nie projektuj odświeżania kursu, pollingu, „aktualnego kursu”, porównania
  z kursem otwarcia ani drugiego zapisu wyniku. Jeśli ekran pokazuje kurs,
  pokazuje ten jedyny snapshot.
- Predykcje modeli też powstają wsadowo i lądują w bazie. Request HTTP ich
  nie liczy. Projekcja końca sezonu (Monte Carlo) jest cache w
  `season_projection_runs`; endpoint tylko czyta cache.

## Jak piszemy kod

Reguły szczegółowe:

- Python: `.cursor/rules/python-coding-style.mdc`
- TypeScript: `.cursor/rules/typescript-coding-style.mdc`
- Frontend: `.cursor/rules/frontend-nextjs-architecture.mdc`
  i `.cursor/rules/frontend-theme-tokens.mdc`

Wspólne, niezależnie od języka:

- Nazwy w kodzie, docstringi, logi i wyjątki: **angielski**.
- Komentarze (`#`, `//`): **polski**, i tylko wtedy, gdy tłumaczą dlaczego.
- Teksty na ekranie: **polski**, krótko, tak jak sąsiednie ekrany. Nie
  wymyślaj marketingowego tonu. Właściciel i tak wygładza sformułowania.
- Funkcja do 100 linii. Jedna odpowiedzialność. Wczesny return zamiast
  piramidy `if`.
- Nie dodawaj biblioteki, warstwy cache (React Query, Redux) ani abstrakcji,
  której zadanie nie wymaga.
- Strona Next.js zostaje Server Componentem. `"use client"` tylko tam, gdzie
  jest stan, klik albo API przeglądarki.
- Kolory UI tylko tokenami z `frontend/src/app/globals.css`
  (`bg-page`, `text-text`, `bg-accent`, …). Bez `bg-slate-*`, `text-white`,
  `dark:` i hexów w klasach.

## Testy

Piszemy testy tam, gdzie psuje się logika, a nie tam, gdzie stoi zdanie.

**Zostają**

- Testy jednostkowe backendu (`backend/tests/`, `api/tests/`, `models/tests/`):
  mapowanie, walidacja, matematyka, kontrakt zapytania. To jest główna siatka.
- Testy czystych funkcji frontendu (`*.test.ts` przy `lib/` i modelach bez
  DOM): parsowanie daty, parametry filtrów, grupowanie kursów, skład hokeja.
  Asercja dotyczy wartości zwrotnej, nie tekstu na ekranie.

**Nie piszemy**

- Testów komponentów, które robią `renderToStaticMarkup` (albo Testing
  Library) i sprawdzają, czy w HTML jest polski napis, klasa CSS, `href`
  albo `aria-*`.
- Testów „czy na stronie jest ten tytuł”. Właściciel poprawia potem język
  interfejsu i musi poprawiać też test. Test nie łapie złego layoutu, bo
  nie otwiera przeglądarki.
- Testów integracyjnych i end-to-end frontendu na zapas. Nie zastępują
  powyższych. Ekran sprawdza człowiek; gdy trzeba, skill `ui-test`.

Nie dopisuj stałej z napisem tylko po to, żeby test mógł ją zaimportować.
Nie aktualizuj istniejącego testu HTML przy zmianie copy — taki test jest
do usunięcia, nie do utrzymania. Istniejących plików `*.test.tsx` nie
usuwaj hurtowo przy okazji innego zadania; usuń je, gdy zadanie dotyczy
tego pliku albo gdy właściciel każe posprzątać.

## Jak prowadzimy zadanie

1. Potrzeba biznesowa zamienia się w projekt techniczny (`tasks/plans/`,
   skill `tech-project`).
2. Implementacja trzyma się projektu (skill `develop`). Bez dokładania
   zakresu.
3. Review wobec projektu: skill `cr`. Domknięcie planu: skill `weryfikuj-plan`.
4. Testy według sekcji „Testy” (skill `scenariusze-testowe`).
5. Commit i branch tylko na prośbę. Format z sygnaturą zadania:
   `[EB-123] Opis, co zmienia commit` (skill `git-push`). Push wyłącznie
   po wyraźnej zgodzie.
6. Równoległa kopia repo na innych portach: skill `dev-worktree`.

Nie commituj, jeśli użytkownik o to nie poprosił. Nie zmieniaj `git config`.
Nie rób force push.

## Dopiski

Miejsce na kolejne fakty operacyjne. Dopisuj datę i jedno zdanie.
