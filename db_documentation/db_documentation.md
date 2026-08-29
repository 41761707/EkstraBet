# OFICJALNA DOKUMENTACJA BAZODANOWA

###### Ostatnia data modyfikacji: 29.08.2026

## Opis struktury bazy

Dokumentacja opisuje schemat MySQL projektu Ekstrabet
Diagram relacji: [`db_erd.mermaid`](db_erd.mermaid).

## Wszystkie tabele w bazie danych

- [BASKETBALL_CURRENT_ROSTER](#basketball_current_roster) (Aktualne składy drużyn koszykarskich)
- [BASKETBALL_MATCH_PLAYER_STATS](#basketball_match_player_stats) (Statystyki graczy w meczu koszykarskim)
- [BASKETBALL_MATCHES_ADD](#basketball_matches_add) (Dodatkowe statystyki meczów koszykarskich)
- [BASKETBALL_MATCH_ROSTERS](#basketball_match_rosters) (Składy drużyn koszykarskich w danym spotkaniu)
- [BETS](#bets) (Wszystkie możliwe do zrealizowania zakłady)
- [BOOKMAKERS](#bookmakers) (Wszyscy bukmacherzy brani pod uwagę w ramach badania)
- [CHAMPIONS_LEAGUE_TYPER_MATCHES](#champions_league_typer_matches) (Opublikowane mecze konkursu Typer LM)
- [CHAMPIONS_LEAGUE_TYPER_PREDICTIONS](#champions_league_typer_predictions) (Bieżące typy 1X2 użytkowników Typera LM)
- [CHAMPIONS_LEAGUE_TYPER_PREDICTION_CHANGES](#champions_league_typer_prediction_changes) (Append-only audyt zmian typów Typera LM)
- [CONFERENCE_DIVISIONS](#conference_divisions) (Dywizje przypisane do konferencji (dotyczy lig północnoamerykańskich))
- [CONFERENCES](#conferences) (Podział lig (głównie północnoamerykańskich) na konferencje)
- [COUNTRIES](#countries) (Kraje, z których pochodzą analizowane ligi)
- [DIVISION_TEAMS](#division_teams) (Przydział drużyn do dywizji)
- [DIVISIONS](#divisions) (Dywizje w ligach północnoamerykańskich)
- [EVENT_FAMILIES](#event_families) (Rodziny typów zdarzeń w systemie)
- [EVENT_FAMILY_MAPPINGS](#event_family_mappings) (Mapowania zdarzeń do rodzin zdarzeń)
- [EVENT_MODEL_FAMILIES](#event_model_families) (Powiązania modeli z rodzinami zdarzeń)
- [EVENTS](#events) (Typy zakładów)
- [FINAL_PREDICTIONS](#final_predictions) (Wskaźniki predykcji ostatecznych)
- [FOOTBALL_PLAYER_STATS](#football_player_stats) (Boxscore meczowy w piłce nożnej)
- [FOOTBALL_SPECIAL_ROUND_ADD](#football_special_round_add) (rundy specjalne w piłce - dodatkowe informacje (głównie chodzi o puchary))
- [GAMBLER_PARLAYS](#gambler_parlays) (kupony graczy)
- [GAMBLERS](#gamblers) (zadeklarowani gracze)
- [HOCKEY_MATCH_EVENTS](#hockey_match_events) (zdarzenia występujące w danym meczu hokejowym)
- [HOCKEY_MATCH_PLAYER_STATS](#hockey_match_player_stats) (statystyki każdego gracza w danym meczu)
- [HOCKEY_MATCH_ROSTERS](#hockey_match_rosters) (składy drużyn hokejowych w danym spotkaniu)
- [HOCKEY_MATCHES_ADD](#hockey_matches_add) (dodatkowe statystyki specyficzne dla meczu hokejowego)
- [HOCKEY_ROSTERS](#hockey_rosters) (aktualne składy drużyn hokejowych)
- [LEAGUES](#leagues) (spis analizowanych lig)
- [MATCHES](#matches) (wszystkie analizowane mecze)
- [MATCH_MODEL_ASSESSMENTS](#match_model_assessments) (oceny meczów po fakcie z modeli assessment)
- [MODELS](#models) (lista stworzonych modeli predykcyjnych)
- [MODEL_TRAINING_RUNS](#model_training_runs) (audyt przebiegów trenowania / ewaluacji modeli)
- [ODDS](#odds) (pobrane kursy dla danego meczu dla danego zdrarzenia)
- [PARLAY_EVENTS](#parlay_events) (Szczegóły kuponów)
- [PLAYER_NAME_MAPPINGS](#player_name_mappings) (mapowania nazw zawodników dla różnych bukmacherów)
- [PLAYER_PROS_LINES] (#player_pros_lines) (linie na zdarzenia dla graczy w poszczególnych sportach)
- [PLAYERS](#players) (lista graczy)
- [PREDICTIONS](#predictions) (WSZYSTKIE predykcje dla każdego zdarzenia)
- [SCHEDULE](#schedule) (Stabilny terminarz sezonu piłkarskiego — źródło listy spotkań projekcji końca sezonu)
- [SEASONS](#seasons) (Tabela z sezonami)
- [SEASON_PROJECTION_RUNS](#season_projection_runs) (Cache przebiegów Monte Carlo projekcji końca sezonu)
- [SEASON_PROJECTION_TEAM_ROWS](#season_projection_team_rows) (Statystyki drużyn w ramach udanego runu projekcji)
- [SPECIAL_ROUNDS](#special_rounds) (Tabela z nazwami rund specjalnych)
- [SPORTS](#sports) (Tabela z analizowanymi sportami)
- [TEAMS](#teams) (Tabela z drużynami)
- [TRANSFERS](#transfers) (Zapis transferów zawodników między klubami)
- [USER_FAVORITE_LEAGUES](#user_favorite_leagues) (Ulubione ligi wybranych użytkowników aplikacji)
- [USER_PREFERENCES](#user_preferences) (Skalarne preferencje UI konta, m.in. motyw i nazwy drużyn)
- [USERS](#users) (Konta użytkowników aplikacji web / API)

## Legenda

- Pole **pogrubione** oznacza KLUCZ GŁÓWNY w tabeli
- Pole *kursywą* oznacza KLUCZ OBCY w tabeli
- Wartości domyslne **-1** w miejscach, gdzie zbiór wartości to [0, +inf) oznaczają "brak danych"

## Opisy poszczególnych tabel

### BASKETBALL_CURRENT_ROSTER

(Tabela z aktualnymi składami drużyn koszykarskich)


| POLE        | DOMENA | ZAKRES | UWAGI                                                                       | WARTOŚC DOMYŚLNA         |
| ----------- | ------ | ------ | --------------------------------------------------------------------------- | ------------------------ |
| **ID**      | INT    | INT    | Klucz główny, automatycznie generowany                                      | AUTOMATYCZNIE GENEROWANE |
| *TEAM_ID*   | INT    | INT    | Klucz obcy, powiązanie z tabelą *teams*                                     | NULL                     |
| *PLAYER_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *players*                                   | NULL                     |
| NUMBER      | INT    | INT    | Numer zawodnika w drużynie                                                  | NULL                     |
| STARTER     | INT    | {0,1}  | Flaga, czy zawodnik jest podstawowym zawodnikiem drużyny (1 - tak, 0 - nie) | 0                        |
| IS_INJURED  | INT    | {0,1}  | Flaga, czy zawodnik jest kontuzjowany (1 - tak, 0 - nie)                    | 0                        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- **Unikalny indeks**: `TEAM_ID`, `PLAYER_ID` (zapobiega duplikatom zawodników w ramach jednego zespołu)
**Sposób generowania danych do tabeli**:
Dane do tabeli generowane są w ramach działania modułu **basketball_scrapper.py**

---

### BASKETBALL_MATCH_PLAYER_STATS

(Statystyki graczy w meczu koszykarskim)


| POLE                     | DOMENA     | ZAKRES              | UWAGI                                                               | WARTOŚC DOMYŚLNA         |
| ------------------------ | ---------- | ------------------- | ------------------------------------------------------------------- | ------------------------ |
| **ID**                   | INT        | INT                 | ID przypisania                                                      | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*               | INT        | INT                 | Klucz obcy, powiązanie z tabelą *matches*                           | NULL                     |
| *TEAM_ID*                | INT        | INT                 | Klucz obcy, powiązanie z tabelą *teams*                             | NULL                     |
| *PLAYER_ID*              | INT        | INT                 | Klucz obcy, powiązanie z tabelą *players*                           | NULL                     |
| POINTS                   | INT        | INT                 | Liczba punktów zdobytych przez zawodnika w meczu                    | -1                       |
| REBOUNDS                 | INT        | INT                 | Liczba zbiórek zdobytych przez zawodnika w meczu                    | -1                       |
| ASSISTS                  | INT        | INT                 | Liczba asyst wykonanych przez zawodnika w meczu                     | -1                       |
| TIME_PLAYED              | VARCHAR(9) | 00:00:00 - 99:59:59 | Czas gry zawodnika w meczu (w minutach)                             | -1                       |
| FIELD_GOALS_MADE         | INT        | INT                 | Liczba trafionych rzutów z gry przez zawodnika w meczu              | -1                       |
| FIELD_GOALS_ATTEMPTS     | INT        | INT                 | Liczba oddanych rzutów z gry przez zawodnika w meczu                | -1                       |
| 2_P_FIELD_GOALS_MADE     | INT        | INT                 | Liczba trafionych rzutów za 2 punkty przez zawodnika w meczu        | -1                       |
| 2_P_FIELD_GOALS_ATTEMPTS | INT        | INT                 | Liczba oddanych rzutów za 2 punkty przez zawodnika w meczu          | -1                       |
| 3_P_FIELD_GOALS_MADE     | INT        | INT                 | Liczba trafionych rzutów za 3 punkty przez zawodnika w meczu        | -1                       |
| 3_P_FIELD_GOALS_ATTEMPTS | INT        | INT                 | Liczba oddanych rzutów za 3 punkty przez zawodnika w meczu          | -1                       |
| FT_MADE                  | INT        | INT                 | Liczba trafionych rzutów wolnych przez zawodnika w meczu            | -1                       |
| FT_ATTEMPTS              | INT        | INT                 | Liczba oddanych rzutów wolnych przez zawodnika w meczu              | -1                       |
| PLUS_MINUS               | INT        | INT                 | Wskaźnik plus/minus zawodnika w meczu                               | -1                       |
| OFF_REBOUNDS             | INT        | INT                 | Liczba ofensywnych zbiórek zdobytych przez zawodnika w meczu        | -1                       |
| DEF_REBOUNDS             | INT        | INT                 | Liczba defensywnych zbiórek zdobytych przez zawodnika w meczu       | -1                       |
| PERSONAL_FOULS           | INT        | INT                 | Liczba przewinień osobistych popełnionych przez zawodnika w meczu   | -1                       |
| STEALS                   | INT        | INT                 | Liczba przechwytów dokonanych przez zawodnika w meczu               | -1                       |
| TURNOVERS                | INT        | INT                 | Liczba strat popełnionych przez zawodnika w meczu                   | -1                       |
| BLOCKED_SHOTS            | INT        | INT                 | Liczba zablokowanych rzutów dokonanych przez zawodnika w meczu      | -1                       |
| BLOCKS_AGAINST           | INT        | INT                 | Liczba zablokowanych rzutów przeciwko zawodnikowi w meczu           | -1                       |
| TECHNICAL_FOULS          | INT        | INT                 | Liczba przewinień technicznych popełnionych przez zawodnika w meczu | -1                       |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- **Unikalny indeks**: `MATCH_ID`, `TEAM_ID`, `PLAYER_ID` (zapobiega duplikatom statystyk dla tego samego zawodnika w danym meczu)

**Sposób generowania danych do tabeli**:
Dane do tabeli generowane są w ramach działania modułu **basketball_scrapper.py**

---

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- **Unikalny indeks**: `MATCH_ID`, `TEAM_ID`, `PLAYER_ID` (zapobiega duplikatom statystyk dla tego samego zawodnika w danym meczu)

## **Sposób generowania danych do tabeli**:

Dane do tabeli generowane są w ramach działania modułu **basketball_scrapper.py**

### BASKETBALL_MATCH_ROSTERS

(Składy drużyn koszykarskich w danym spotkaniu)


| POLE        | DOMENA | ZAKRES | UWAGI                                                                              | WARTOŚC DOMYŚLNA         |
| ----------- | ------ | ------ | ---------------------------------------------------------------------------------- | ------------------------ |
| **ID**      | INT    | INT    | ID przypisania                                                                     | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*  | INT    | INT    | Klucz obcy, powiązanie z tabelą *matches*                                          | NULL                     |
| *TEAM_ID*   | INT    | INT    | Klucz obcy, powiązanie z tabelą *teams*                                            | NULL                     |
| *PLAYER_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *players*                                          | NULL                     |
| NUMBER      | INT    | INT    | Numer zawodnika w meczu                                                            | -1                       |
| STARTER     | INT    | {0,1}  | Flaga, czy zawodnik był podstawowym zawodnikiem drużyny w meczu (1 - tak, 0 - nie) | 0                        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- **Unikalny indeks**: `MATCH_ID`, `TEAM_ID`, `PLAYER_ID` (zapobiega duplikatom zawodników w ramach jednego meczu i drużyny)

**Sposób generowania danych do tabeli**:
Dane do tabeli generowane są w ramach działania modułu **basketball_scrapper.py**

---

### BASKETBALL_MATCHES_ADD

(Dodatkowe statystyki meczów koszykarskich)


| POLE                               | DOMENA | ZAKRES | UWAGI                                                                        | WARTOŚC DOMYŚLNA         |
| ---------------------------------- | ------ | ------ | ---------------------------------------------------------------------------- | ------------------------ |
| **ID**                             | INT    | INT    | ID przypisania                                                               | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*                         | INT    | INT    | Klucz obcy, powiązanie z tabelą *matches*                                    | NULL                     |
| HOME_TEAM_FIELD_GOALS_ATTEMPTS     | INT    | INT    | Liczba oddanych rzutów z gry przez drużynę gospodarzy w meczu                | -1                       |
| AWAY_TEAM_FIELD_GOALS_ATTEMPTS     | INT    | INT    | Liczba oddanych rzutów z gry przez drużynę gości w meczu                     | -1                       |
| HOME_TEAM_FIELD_GOALS_MADE         | INT    | INT    | Liczba trafionych rzutów z gry przez drużynę gospodarzy w meczu              | -1                       |
| AWAY_TEAM_FIELD_GOALS_MADE         | INT    | INT    | Liczba trafionych rzutów z gry przez drużynę gości w meczu                   | -1                       |
| HOME_TEAM_FIELD_GOALS_ACC          | FLOAT  | FLOAT  | Skuteczność rzutów z gry drużyny gospodarzy w meczu                          | -1                       |
| AWAY_TEAM_FIELD_GOALS_ACC          | FLOAT  | FLOAT  | Skuteczność rzutów z gry drużyny gości w meczu                               | -1                       |
| HOME_TEAM_2_P_FIELD_GOALS_ATTEMPTS | INT    | INT    | Liczba oddanych rzutów za 2 punkty przez drużynę gospodarzy w meczu          | -1                       |
| AWAY_TEAM_2_P_FIELD_GOALS_ATTEMPTS | INT    | INT    | Liczba oddanych rzutów za 2 punkty przez drużynę gości w meczu               | -1                       |
| HOME_TEAM_2_P_FIELD_GOALS_MADE     | INT    | INT    | Liczba trafionych rzutów za 2 punkty przez drużynę gospodarzy w meczu        | -1                       |
| AWAY_TEAM_2_P_FIELD_GOALS_MADE     | INT    | INT    | Liczba trafionych rzutów za 2 punkty przez drużynę gości w meczu             | -1                       |
| HOME_TEAM_2_P_ACC                  | FLOAT  | FLOAT  | Skuteczność rzutów za 2 punkty drużyny gospodarzy w meczu                    | -1                       |
| AWAY_TEAM_2_P_ACC                  | FLOAT  | FLOAT  | Skuteczność rzutów za 2 punkty drużyny gości w meczu                         | -1                       |
| HOME_TEAM_3_P_FIELD_GOALS_ATTEMPTS | INT    | INT    | Liczba oddanych rzutów za 3 punkty przez drużynę gospodarzy w meczu          | -1                       |
| AWAY_TEAM_3_P_FIELD_GOALS_ATTEMPTS | INT    | INT    | Liczba oddanych rzutów za 3 punkty przez drużynę gości w meczu               | -1                       |
| HOME_TEAM_3_P_FIELD_GOALS_MADE     | INT    | INT    | Liczba trafionych rzutów za 3 punkty przez drużynę gospodarzy w meczu        | -1                       |
| AWAY_TEAM_3_P_FIELD_GOALS_MADE     | INT    | INT    | Liczba trafionych rzutów za 3 punkty przez drużynę gości w meczu             | -1                       |
| HOME_TEAM_3_P_ACC                  | FLOAT  | FLOAT  | Skuteczność rzutów za 3 punkty drużyny gospodarzy w meczu                    | -1                       |
| AWAY_TEAM_3_P_ACC                  | FLOAT  | FLOAT  | Skuteczność rzutów za 3 punkty drużyny gości w meczu                         | -1                       |
| HOME_TEAM_FT_ATTEMPTS              | INT    | INT    | Liczba oddanych rzutów wolnych przez drużynę gospodarzy w meczu              | -1                       |
| AWAY_TEAM_FT_ATTEMPTS              | INT    | INT    | Liczba oddanych rzutów wolnych przez drużynę gości w meczu                   | -1                       |
| HOME_TEAM_FT_MADE                  | INT    | INT    | Liczba trafionych rzutów wolnych przez drużynę gospodarzy w meczu            | -1                       |
| AWAY_TEAM_FT_MADE                  | INT    | INT    | Liczba trafionych rzutów wolnych przez drużynę gości w meczu                 | -1                       |
| HOME_TEAM_FT_ACC                   | FLOAT  | FLOAT  | Skuteczność rzutów wolnych drużyny gospodarzy w meczu                        | -1                       |
| AWAY_TEAM_FT_ACC                   | FLOAT  | FLOAT  | Skuteczność rzutów wolnych drużyny gości w meczu                             | -1                       |
| HOME_TEAM_OFF_REBOUNDS             | INT    | INT    | Liczba ofensywnych zbiórek zdobytych przez drużynę gospodarzy w meczu        | -1                       |
| AWAY_TEAM_OFF_REBOUNDS             | INT    | INT    | Liczba ofensywnych zbiórek zdobytych przez drużynę gości w meczu             | -1                       |
| HOME_TEAM_DEF_REBOUNDS             | INT    | INT    | Liczba defensywnych zbiórek zdobytych przez drużynę gospodarzy w meczu       | -1                       |
| AWAY_TEAM_DEF_REBOUNDS             | INT    | INT    | Liczba defensywnych zbiórek zdobytych przez drużynę gości w meczu            | -1                       |
| HOME_TEAM_REBOUNDS_TOTAL           | INT    | INT    | Łączna liczba zbiórek zdobytych przez drużynę gospodarzy w meczu             | -1                       |
| AWAY_TEAM_REBOUNDS_TOTAL           | INT    | INT    | Łączna liczba zbiórek zdobytych przez drużynę gości w meczu                  | -1                       |
| HOME_TEAM_ASSISTS                  | INT    | INT    | Liczba asyst wykonanych przez drużynę gospodarzy w meczu                     | -1                       |
| AWAY_TEAM_ASSISTS                  | INT    | INT    | Liczba asyst wykonanych przez drużynę gości w meczu                          | -1                       |
| HOME_TEAM_BLOCKS                   | INT    | INT    | Liczba zablokowanych rzutów dokonanych przez drużynę gospodarzy w meczu      | -1                       |
| AWAY_TEAM_BLOCKS                   | INT    | INT    | Liczba zablokowanych rzutów dokonanych przez drużynę gości w meczu           | -1                       |
| HOME_TEAM_TURNOVERS                | INT    | INT    | Liczba strat popełnionych przez drużynę gospodarzy w meczu                   | -1                       |
| AWAY_TEAM_TURNOVERS                | INT    | INT    | Liczba strat popełnionych przez drużynę gości w meczu                        | -1                       |
| HOME_TEAM_STEALS                   | INT    | INT    | Liczba przechwytów dokonanych przez drużynę gospodarzy w meczu               | -1                       |
| AWAY_TEAM_STEALS                   | INT    | INT    | Liczba przechwytów dokonanych przez drużynę gości w meczu                    | -1                       |
| HOME_TEAM_PERSONAL_FOULS           | INT    | INT    | Liczba przewinień osobistych popełnionych przez drużynę gospodarzy w meczu   | -1                       |
| AWAY_TEAM_PERSONAL_FOULS           | INT    | INT    | Liczba przewinień osobistych popełnionych przez drużynę gości w meczu        | -1                       |
| HOME_TEAM_TECHNICAL_FOULS          | INT    | INT    | Liczba przewinień technicznych popełnionych przez drużynę gospodarzy w meczu | -1                       |
| AWAY_TEAM_TECHNICAL_FOULS          | INT    | INT    | Liczba przewinień technicznych popełnionych przez drużynę gości w meczu      | -1                       |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- **Unikalny indeks**: `MATCH_ID` (zapobiega duplikatom dodatkowych statystyk dla tego samego meczu)

## **Sposób generowania danych do tabeli**:

Dane do tabeli generowane są w ramach działania modułu **basketball_scrapper.py**

### BETS

(Wszystkie możliwe do zrealizowania zakłady)


| POLE        | DOMENA | ZAKRES                                                                   | UWAGI                                                                                                                                                            | WARTOŚC DOMYŚLNA         |
| ----------- | ------ | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**      | INT    | INT                                                                      | Klucz główny, automatycznie generowany                                                                                                                           | AUTOMATYCZNIE GENEROWANE |
| *MATCH_ID*  | INT    | INT                                                                      | Klucz obcy, powiązanie z tabelą *matches*                                                                                                                        | NULL                     |
| *EVENT_ID*  | INT    | INT                                                                      | Klucz obcy, powiązanie z tabelą *events*                                                                                                                         | NULL                     |
| ODDS        | FLOAT  | >= 1.0                                                                   | Kurs danego zdarzenia                                                                                                                                            | NULL                     |
| EV          | FLOAT  | Teoretycznie (-inf, +inf), ale z reguły sensownie wartości są do [-1, 1] | Expected value: `round((predictions.value / 100) * odds - 1, 4)`. `predictions.value` jest w skali 0–100. Wartości EV > 0 uznawane są za „interesujące”          | NULL                     |
| *BOOKMAKER* | INT    | INT                                                                      | Klucz obcy, powiązanie z tabelą *bookmakers*                                                                                                                     | NULL                     |
| OUTCOME     | INT    | {0, 1, NULL}                                                             | `NULL` = oczekujący, `0` = nietrafiony, `1` = trafiony. Proces utrzymania utrzymuje outcome tylko dla rynków kursowych (event_id: 1, 2, 3, 6, 8, 12, 172)       | NULL (to istotne)        |
| CUSTOM_BET  | INT    | {0, 1}                                                                   | 0 jeśli zakład wygenerowany przez model, 1 jeśli zakład dodany ręcznie przez użytkownika                                                                         | 0                        |
| *MODEL_ID*  | INT    | INT                                                                      | Klucz obcy, powiązanie z tabelą *models*. `NULL` oznacza zakład użytkownika (nie modelowy)                                                                       | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `EVENT_ID` → `events(ID)`
- Klucz obcy: `BOOKMAKER` → `bookmakers(ID)`
- Klucz obcy: `MODEL_ID` → `models(ID)`
- **Unikalny indeks** `unique_model_bet`: `(MATCH_ID, EVENT_ID, MODEL_ID)` — jeden automatyczny zakład modelu na mecz, event i model. W MySQL wiele wierszy z `MODEL_ID IS NULL` (zakłady użytkownika) nadal jest dozwolone.

**Źródła danych i utrzymanie:**

- Automatyczne zakłady modelu generuje i rozlicza proces `refresh-statistics`
  (`backend/services/model_statistics_maintenance_service.py`), uruchamiany przez
  `models/scripts/model_runner.py refresh-statistics` lub
  `models/scripts/run_model_statistics.bat`.
- Generowanie i rozliczanie `bets` dotyczy wyłącznie eventów z kursami w `odds`:
  **1, 2, 3** (1X2), **6 / 172** (BTTS), **8 / 12** (O/U 2.5).
- Rodziny GOALS / EXACT **nie** tworzą ani nie rozliczają rekordów w `bets`
  (brak kursów); ich wynik trafia tylko do `final_predictions.outcome`.
- Upsert aktualizuje kurs i EV, ale **nigdy nie zeruje** istniejącego `OUTCOME`.
- Przed pierwszym produkcyjnym `--write-db` administrator uruchamia ręcznie
  skrypt `sql/model_statistics_maintenance.sql` (kontrola duplikatów + indeks).
  Implementacja aplikacji **nie** wykonuje DDL.


---

### BOOKMAKERS

(Wszyscy bukmacherzy brani pod uwagę w ramach badania)


| POLE   | DOMENA      | ZAKRES | UWAGI            | WARTOŚC DOMYŚLNA         |
| ------ | ----------- | ------ | ---------------- | ------------------------ |
| **ID** | INT         | INT    | ID bukmachera    | AUTOMATYCZNIE GENEROWANY |
| NAZWA  | VARCHAR(45) | STRING | Nazwa bukmachera | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### CHAMPIONS_LEAGUE_TYPER_MATCHES

(Opublikowane mecze konkursu Typer LM — rejestr publikacji **bez kursów**)


| POLE            | DOMENA                  | ZAKRES              | UWAGI                                                                                          | WARTOŚC DOMYŚLNA         |
| --------------- | ----------------------- | ------------------- | ---------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**          | INT                     | INT                 | ID wiersza publikacji                                                                          | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*      | INT                     | INT                 | Klucz obcy, powiązanie z tabelą *matches* (UNIQUE — jeden mecz publikowany raz)                | NULL                     |
| *SEASON_ID*     | INT                     | INT                 | Klucz obcy, powiązanie z tabelą *seasons*                                                      | NULL                     |
| ROUND_NUMBER    | INT                     | INT                 | Kolejka fazy ligowej (1–8) albo `matches.round` rundy pucharowej (>= 900). Faza wynika z tej wartości — brak osobnej kolumny. | NULL                     |
| *PUBLISHED_BY*  | INT                     | INT                 | Klucz obcy, powiązanie z tabelą *users* (administrator, który opublikował zestaw)              | NULL                     |
| PUBLISHED_AT    | DATETIME                | DATETIME            | Moment publikacji meczu w Typerze                                                              | CURRENT_TIMESTAMP        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- **Unikalny indeks:** `uq_cl_typer_matches_match` (`MATCH_ID`) — jeden mecz może być opublikowany tylko raz
- Indeks: `idx_cl_typer_matches_season_round` (`SEASON_ID`, `ROUND_NUMBER`)
- Klucz obcy: `MATCH_ID` → `matches(ID)` **ON DELETE RESTRICT**
- Klucz obcy: `SEASON_ID` → `seasons(ID)` **ON DELETE RESTRICT**
- Klucz obcy: `PUBLISHED_BY` → `users(ID)` **ON DELETE RESTRICT**
- Tabela **nie przechowuje kursów**. Kursy 1/X/2 Superbet są w `odds` (`bookmaker = 1`, eventy `1/2/3`) i mogą pojawić się po publikacji. Brak kursu nie blokuje publikacji ani typowania.

**Sposób generowania danych do tabeli:**

Wiersze wstawia administrator przez API Typera LM (`POST /typer-lm/admin/publications`) w jednej transakcji dla całego zestawu rundy. Korekta pomyłki (usunięcie publikacji bez typów) to `DELETE /typer-lm/admin/publications/{match_id}`. Aplikacja nie kopiuje kursów do tej tabeli i nie wstawia wierszy do `odds`.

---

### CHAMPIONS_LEAGUE_TYPER_PREDICTIONS

(Bieżący typ 1X2 użytkownika dla opublikowanego meczu Typera LM)


| POLE                 | DOMENA   | ZAKRES     | UWAGI                                                                 | WARTOŚC DOMYŚLNA         |
| -------------------- | -------- | ---------- | --------------------------------------------------------------------- | ------------------------ |
| **ID**               | INT      | INT        | ID bieżącego typu                                                     | AUTOMATYCZNIE GENEROWANY |
| *TYPER_MATCH_ID*     | INT      | INT        | Klucz obcy, powiązanie z tabelą *champions_league_typer_matches*      | NULL                     |
| *USER_ID*            | INT      | INT        | Klucz obcy, powiązanie z tabelą *users* (właściciel typu)             | NULL                     |
| *SELECTED_EVENT_ID*  | INT      | {1, 2, 3}  | Klucz obcy, powiązanie z tabelą *events*; wyłącznie 1 (gospodarz), 2 (remis), 3 (gość) | NULL                     |
| CREATED_AT           | DATETIME | DATETIME   | Moment pierwszego zapisu typu                                         | CURRENT_TIMESTAMP        |
| UPDATED_AT           | DATETIME | DATETIME   | Moment ostatniej realnej zmiany typu (`ON UPDATE CURRENT_TIMESTAMP`) | CURRENT_TIMESTAMP        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- **Unikalny indeks:** `uq_cl_typer_pred_match_user` (`TYPER_MATCH_ID`, `USER_ID`) — jeden bieżący typ na użytkownika i opublikowany mecz
- Indeks: `idx_cl_typer_pred_user_updated` (`USER_ID`, `UPDATED_AT`)
- Klucz obcy: `TYPER_MATCH_ID` → `champions_league_typer_matches(ID)` **ON DELETE RESTRICT** (nie można usunąć publikacji, gdy istnieją typy)
- Klucz obcy: `USER_ID` → `users(ID)` **ON DELETE RESTRICT**
- Klucz obcy: `SELECTED_EVENT_ID` → `events(ID)` **ON DELETE RESTRICT**
- **CHECK:** `SELECTED_EVENT_ID IN (1, 2, 3)`

**Sposób generowania danych do tabeli:**

Zalogowany użytkownik zapisuje lub zmienia typ przez API (`PUT /typer-lm/predictions/{match_id}`) do chwili `matches.game_date`. Backend wykonuje UPSERT bieżącego wiersza. Identyczny wybór (no-op) nie dodaje wiersza audytu.

---

### CHAMPIONS_LEAGUE_TYPER_PREDICTION_CHANGES

(Append-only audyt zmian typów Typera LM — rozstrzyganie sporów o treść zapisu)


| POLE                          | DOMENA   | ZAKRES         | UWAGI                                                                 | WARTOŚC DOMYŚLNA         |
| ----------------------------- | -------- | -------------- | --------------------------------------------------------------------- | ------------------------ |
| **ID**                        | INT      | INT            | ID wpisu audytu                                                       | AUTOMATYCZNIE GENEROWANY |
| *PREDICTION_ID*               | INT      | INT            | Klucz obcy, powiązanie z tabelą *champions_league_typer_predictions*  | NULL                     |
| *CHANGED_BY*                  | INT      | INT            | Klucz obcy, powiązanie z tabelą *users* (użytkownik JWT, który zapisał typ; w obecnym API zawsze właściciel typu) | NULL                     |
| *PREVIOUS_SELECTED_EVENT_ID*  | INT      | {1, 2, 3, NULL}| Klucz obcy, powiązanie z tabelą *events*; `NULL` przy pierwszym typie | NULL                     |
| *NEW_SELECTED_EVENT_ID*       | INT      | {1, 2, 3}      | Klucz obcy, powiązanie z tabelą *events*; wyłącznie 1/2/3             | NULL                     |
| CHANGED_AT                    | DATETIME | DATETIME       | Moment pierwszego zapisu albo realnej zmiany typu                     | CURRENT_TIMESTAMP        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Indeks: `idx_cl_typer_chg_pred_at` (`PREDICTION_ID`, `CHANGED_AT`)
- Indeks: `idx_cl_typer_chg_by_at` (`CHANGED_BY`, `CHANGED_AT`)
- Klucz obcy: `PREDICTION_ID` → `champions_league_typer_predictions(ID)` **ON DELETE RESTRICT**
- Klucz obcy: `CHANGED_BY` → `users(ID)` **ON DELETE RESTRICT**
- Klucz obcy: `PREVIOUS_SELECTED_EVENT_ID` → `events(ID)` **ON DELETE RESTRICT** (NULL pomija sprawdzenie FK)
- Klucz obcy: `NEW_SELECTED_EVENT_ID` → `events(ID)` **ON DELETE RESTRICT**
- **CHECK:** `PREVIOUS_SELECTED_EVENT_ID IS NULL OR PREVIOUS_SELECTED_EVENT_ID IN (1, 2, 3)`
- **CHECK:** `NEW_SELECTED_EVENT_ID IN (1, 2, 3)`
- Wiersze są tylko dokładane. Aplikacja **nie** wykonuje `UPDATE` ani `DELETE` na tej tabeli. Służą rozstrzyganiu sporów o treść typu (kto, z jakiego eventu na jaki, kiedy).

**Sposób generowania danych do tabeli:**

INSERT w tej samej transakcji co UPSERT bieżącego typu: pierwszy zapis (`PREVIOUS_SELECTED_EVENT_ID = NULL`) oraz każda realna zmiana (np. `1 → 2`). Identyczny wybór nie dodaje wiersza. Użytkownik odczytuje wyłącznie własną historię; cudzy audyt widzi tylko administrator (`GET /typer-lm/admin/prediction-history`).

---

### CONFERENCE_DIVISIONS

(Dywizje przypisane do konferencji (dotyczy lig północnoamerykańskich))


| POLE            | DOMENA | ZAKRES | UWAGI                                         | WARTOŚC DOMYŚLNA         |
| --------------- | ------ | ------ | --------------------------------------------- | ------------------------ |
| **ID**          | INT    | INT    | ID przypisania                                | AUTOMATYCZNIE GENEROWANY |
| *CONFERENCE_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *conferences* | NULL                     |
| *DIVISION_ID*   | INT    | INT    | Klucz obcy, powiązanie z tabelą *divisions*   | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `CONFERENCE_ID` → `conferences(ID)`
- Klucz obcy: `DIVISION_ID` → `divisions(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### CONFERENCES

(Podział lig (głównie północnoamerykańskich) na konferencje)


| POLE        | DOMENA      | ZAKRES | UWAGI                                     | WARTOŚC DOMYŚLNA         |
| ----------- | ----------- | ------ | ----------------------------------------- | ------------------------ |
| **ID**      | INT         | INT    | ID przypisania                            | AUTOMATYCZNIE GENEROWANY |
| *LEAGUE_ID* | INT         | INT    | Klucz obcy, powiązanie z tabelą *leagues* | NULL                     |
| NAME        | VARCHAR(45) | STRING | Nazwa konferencji                         | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `LEAGUE_ID` → `leagues(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### COUNTRIES

(Kraje, z których pochodzą analizowane ligi)


| POLE   | DOMENA      | ZAKRES | UWAGI                                                  | WARTOŚC DOMYŚLNA         |
| ------ | ----------- | ------ | ------------------------------------------------------ | ------------------------ |
| **ID** | INT         | INT    | ID kraju                                               | AUTOMATYCZNIE GENEROWANY |
| NAME   | VARCHAR(45) | STRING | Nazwa kraju (PL)                                       | NULL                     |
| SHORT  | VARCHAR(3)  | STRING | Skrót kraju (max 3 litery)                             | NULL                     |
| EMOJI  | VARCHAR(45) | STRING | Napis, który reprezentuje flagę kraju w postaci emotki | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### DIVISION_TEAMS

(Przydział drużyn do dywizji)


| POLE          | DOMENA | ZAKRES | UWAGI                                       | WARTOŚC DOMYŚLNA         |
| ------------- | ------ | ------ | ------------------------------------------- | ------------------------ |
| **ID**        | INT    | INT    | ID przypisania                              | AUTOMATYCZNIE GENEROWANY |
| *TEAM_ID*     | INT    | INT    | Klucz obcy, powiązanie z tabelą *teams*     | NULL                     |
| *DIVISION_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *divisions* | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `DIVISION_ID` → `divisions(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### DIVISIONS

(Dywizje w ligach północnoamerykańskich)


| POLE        | DOMENA      | ZAKRES | UWAGI                                     | WARTOŚC DOMYŚLNA         |
| ----------- | ----------- | ------ | ----------------------------------------- | ------------------------ |
| **ID**      | INT         | INT    | ID przypisania                            | AUTOMATYCZNIE GENEROWANY |
| *LEAGUE_ID* | INT         | INT    | Klucz obcy, powiązanie z tabelą *leagues* | NULL                     |
| NAME        | VARCHAR(45) | STRING | Nazwa dywizji                             | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `LEAGUE_ID` → `leagues(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### EVENT_FAMILIES

(Rodziny typów zdarzeń w systemie)


| POLE        | DOMENA       | ZAKRES | UWAGI                                                 | WARTOŚC DOMYŚLNA         |
| ----------- | ------------ | ------ | ----------------------------------------------------- | ------------------------ |
| **ID**      | INT          | INT    | ID rodziny zdarzeń                                    | AUTOMATYCZNIE GENEROWANY |
| *SPORT_ID*  | INT          | INT    | Klucz obcy, powiązanie z tabelą *sports*              | NULL                     |
| NAME        | VARCHAR(45)  | STRING | Nazwa rodziny zdarzeń (np. REZULTAT, OU, BTTS, EXACT) | NULL                     |
| DESCRIPTION | VARCHAR(200) | STRING | Opis rodziny zdarzeń                                  | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `SPORT_ID` → `sports(ID)`
- **Unikalny indeks**: `SPORT_ID`, `NAME` (zapobiega duplikatom nazw rodzin w ramach tego samego sportu)

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### EVENT_FAMILY_MAPPINGS

(Mapowania zdarzeń do rodzin zdarzeń)


| POLE              | DOMENA | ZAKRES | UWAGI                                            | WARTOŚC DOMYŚLNA         |
| ----------------- | ------ | ------ | ------------------------------------------------ | ------------------------ |
| **ID**            | INT    | INT    | ID mapowania                                     | AUTOMATYCZNIE GENEROWANY |
| *EVENT_ID*        | INT    | INT    | Klucz obcy, powiązanie z tabelą *events*         | NULL                     |
| *EVENT_FAMILY_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *event_families* | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `EVENT_ID` → `events(ID)`
- Klucz obcy: `EVENT_FAMILY_ID` → `event_families(ID)`
- **Unikalny indeks**: `EVENT_ID`, `EVENT_FAMILY_ID` (zapobiega duplikatom mapowań tego samego zdarzenia do tej samej rodziny)

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### EVENT_MODEL_FAMILIES

(Powiązania modeli z rodzinami zdarzeń)


| POLE              | DOMENA | ZAKRES | UWAGI                                            | WARTOŚC DOMYŚLNA         |
| ----------------- | ------ | ------ | ------------------------------------------------ | ------------------------ |
| **ID**            | INT    | INT    | ID powiązania                                    | AUTOMATYCZNIE GENEROWANY |
| *MODEL_ID*        | INT    | INT    | Klucz obcy, powiązanie z tabelą *models*         | NULL                     |
| *EVENT_FAMILY_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *event_families* | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MODEL_ID` → `models(ID)`
- Klucz obcy: `EVENT_FAMILY_ID` → `event_families(ID)`
- **Unikalny indeks**: `MODEL_ID`, `EVENT_FAMILY_ID` (zapobiega duplikatom powiązań tego samego modelu z tą samą rodziną zdarzeń)

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### EVENTS

(Typy zakładów)


| POLE   | DOMENA      | ZAKRES | UWAGI           | WARTOŚC DOMYŚLNA         |
| ------ | ----------- | ------ | --------------- | ------------------------ |
| **ID** | INT         | INT    | ID zdarzenia    | AUTOMATYCZNIE GENEROWANY |
| NAME   | VARCHAR(45) | STRING | Nazwa zdarzenia | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### FINAL_PREDICTIONS

(Wskaźniki predykcji ostatecznych)


| POLE             | DOMENA    | ZAKRES       | UWAGI                                                                                         | WARTOŚĆ DOMYŚLNA         |
| ---------------- | --------- | ------------ | --------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**           | INT       | INT>0        | Klucz główny, automatycznie generowany                                                        | AUTOMATYCZNIE GENEROWANY |
| *PREDICTIONS_ID* | INT       | INT>0        | Klucz obcy, powiązanie z tabelą *predictions*                                                 | NULL                     |
| CREATED_AT       | TIMESTAMP | TIMESTAMP    | Data utworzenia wpisu (timestamp generowany automatycznie)                                    | CURRENT_TIMESTAMP        |
| OUTCOME          | INT       | {0, 1, NULL} | `NULL` = oczekujący, `0` = nietrafiony, `1` = trafiony. Uzupełniane po zakończeniu meczu     | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PREDICTIONS_ID` → `predictions(ID)`
- **Unikalny indeks:** `PREDICTIONS_ID` (zapobiega duplikatom predykcji)

**Źródła danych i utrzymanie:**

- Wiersze finałowe zapisuje pipeline
  (`models/pipeline/persistence/prediction_writer.py`) przy predykcji batch /
  pair — osobno dla rodzin RESULT (REZULTAT), BTTS, GOALS, O/U i EXACT.
- Rozliczanie `OUTCOME` wykonuje proces `refresh-statistics` dla **wszystkich**
  obsługiwanych rodzin (w tym GOALS i EXACT), niezależnie od obecności kursu
  w `odds`. Kandydaci: `OUTCOME IS NULL` oraz mecz z `result IN ('1','X','2')`.
- Nieznany event lub niespójny wynik meczu jest pomijany (bez oznaczania jako
  przegrana) i trafia do ostrzeżeń raportu cyklu.
- Statystyki modeli w API (`analytics_service`) liczone są przy odczycie z
  zapisanych `fp.outcome` / `b.outcome`; nie ma osobnej tabeli statystyk do
  przebudowy.

---

### FOOTBALL_PLAYER_STATS

(Boxscore meczowy w piłce nożnej)


| POLE            | DOMENA | ZAKRES  | UWAGI                                                               | WARTOŚĆ DOMYŚLNA         |
| --------------- | ------ | ------- | ------------------------------------------------------------------- | ------------------------ |
| **ID**          | INT    | INT>0   | Klucz główny, automatycznie generowany                              | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*      | INT    | INT>0   | Klucz obcy, powiązanie z tabelą *matches*                           | NULL                     |
| *PLAYER_ID*     | INT    | INT>0   | Klucz obcy, powiązanie z tabelą *players*                           | NULL                     |
| *TEAM_ID*       | INT    | INT>0   | Klucz obcy, powiązanie z tabelą *teams*                             | NULL                     |
| GOALS           | INT    | INT>0   | Liczba goli strzelonych przez zawodnika w meczu                     | -1                       |
| ASSISTS         | INT    | INT>0   | Liczba asyst wykonanych przez zawodnika w meczu                     | -1                       |
| RED_CARDS       | INT    | {0,1}   | Liczba czerwonych kartek otrzymanych przez zawodnika w meczu        | -1                       |
| YELLOW_CARDS    | INT    | {0,1,2} | Liczba żółtych kartek otrzymanych przez zawodnika w meczu           | -1                       |
| CORNERS_WON     | INT    | INT>0   | Liczba rzutów rożnych wygranych przez zawodnika                     | -1                       |
| SHOTS           | INT    | INT>0   | Liczba strzałów oddanych przez zawodnika                            | -1                       |
| SHOTS_ON_TARGET | INT    | INT>0   | Liczba strzałów na bramkę oddanych przez zawodnika                  | -1                       |
| BLOCKED_SHOTS   | INT    | INT>0   | Liczba zablokowanych strzałów przez zawodnika                       | -1                       |
| PASSES          | INT    | INT>0   | Liczba wszystkich podań wykonanych przez zawodnika                  | -1                       |
| CROSSES         | INT    | INT>0   | Liczba wrzutek wykonanych przez zawodnika                           | -1                       |
| TACKLES         | INT    | INT>0   | Liczba wślizgów wykonanych przez zawodnika                          | -1                       |
| OFFSIDES        | INT    | INT>0   | Liczba sytuacji, w których zawodnik znalazł się na pozycji spalonej | -1                       |
| FOULS_CONCEDED  | INT    | INT>0   | Liczba poprzełnionych fauli przez zawodnika                         | -1                       |
| FOULS_WON       | INT    | INT>0   | Liczba fauli popełnionych na zawodniku                              | -1                       |
| SAVES           | INT    | INT>0   | Liczba obronionych strzałów (dotyczy jedynie bramkarzy)             | -1                       |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- **Unikalny indeks:** `MATCH_ID`, `PLAYER_ID`, `TEAM_ID` (zapobiega duplikatom statystyk dla tego samego zawodnika w danym meczu)

**Sposób generowania danych do tabeli**:

Dane do tabeli generowane są w ramach działania modułu **opta_scrapper.py**

---

### FOOTBALL_SPECIAL_ROUND_ADD

(rundy specjalne w piłce - dodatkowe informacje (głównie chodzi o puchary))


| POLE                   | DOMENA | ZAKRES | UWAGI                                                                                                                                                     | WARTOŚC DOMYŚLNA         |
| ---------------------- | ------ | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**                 | INT    | INT    | ID dodatkowych danych meczowych w piłce                                                                                                                   | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*             | INT    | INT    | Klucz obcy, powiązanie z tabelą *matches*                                                                                                                 | NULL                     |
| OT                     | INT    | {0,1}  | Flaga, czy w meczu odbyła się dogrywka (teoretycznie z aktualną strukturą bazy to flaga zawsze będzie równa 1, jednak w przyszłości może się to zmienić!) | 1                        |
| PEN                    | INT    | {0,1}  | Flaga, czy w meczu odbyła się seria jedynastek                                                                                                            | 0                        |
| home_team_goals_post_ot | INT    | INT    | Liczba bramek strzelona przez drużynę gospodarzy podczas regularnego czasu gry                                                                            | NULL                     |
| away_team_goals_post_ot | INT    | INT    | Liczba bramek strzelona przez drużynę gości podczas regularnego czasu gry                                                                                 | NULL                     |
| home_team_pen_score    | INT    | INT    | Liczba trafionych karnych przez gospodarzy w ramach konkursu jedynastek                                                                                   | NULL                     |
| away_team_pen_score    | INT    | INT    | Liczba trafionych karnych przez gości w ramach konkursu jedynastek                                                                                        | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`

**Sposób generowania danych do tabeli**:

Dane do tabeli **BĘDĄ** (jeszcze aktualnie nie są) naliczane w ramach scrapperów (głównie **scrapper.py** oraz **update_scrapper.py**)

---

### GAMBLER_PARLAYS

(kupony graczy)


| POLE           | DOMENA    | ZAKRES                                | UWAGI                                                                                                                                                                                                                                                                                                          | WARTOŚC DOMYŚLNA         |
| -------------- | --------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**         | INT       | INT                                   | ID kuponu                                                                                                                                                                                                                                                                                                      | AUTOMATYCZNIE GENEROWANY |
| *GAMBLER_ID*   | INT       | INT                                   | Klucz obcy, powiązanie z tabelą *gamblers*                                                                                                                                                                                                                                                                     | NULL                     |
| PARLAY_ODDS    | FLOAT     | > 1                                   | Kurs całego kuponu (mnożenie kursów wszystkich zdarzeń)                                                                                                                                                                                                                                                        | NULL                     |
| STAKE          | FLOAT     | > 0                                   | Wkład gracza (ile pieniędzy postawił w ramach kuponu), w unitach                                                                                                                                                                                                                                               | 1                        |
| SETTLED        | INT       | {0,1}                                 | Czy kupon rozliczony (0 - nie, 1 - tak)                                                                                                                                                                                                                                                                        | 0                        |
| PARLAY_OUTCOME | INT       | {0,1}                                 | Wynik kuponu (0 - przegrany, 1 - wygrany)                                                                                                                                                                                                                                                                      | 0                        |
| PROFIT         | FLOAT     | {-stake, parlay_odds * stake - stake} | Zysk / Strata gracza w zależności od tego, czy kupon został wygrany czy przegrany. Jeśli kupon wygrany, profitem nazywamy iloczyn stawki oraz kursu kuponu pomniejszonego o jedną stawkę (wkład początkowy nie jest w żadnym wypadku profitem z zakładu). Jeśli kupon przegrany, gracz traci poświęconą stawkę | 0                        |
| CREATION_DATE  | TIMESTAMP | TIMESTAMP                             | Data utworzenia kuponu                                                                                                                                                                                                                                                                                         | CURRENT_TIMESTAMP        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `GAMBLER_ID` → `gamblers(ID)`

**Sposób generowania danych do tabeli**:

Aktualnie dane do tabeli dodawane są tylko i wyłącznie **ręcznie** (w przyszłości przewidywane jest dodawaniez zdarzeń poprzez moduł "Kupony Graczy"). Dane aktualizowane są w ramach modułu **recalc_parlay.py** 

---

### GAMBLERS

(zadeklarowani gracze) 


| POLE           | DOMENA      | ZAKRES | UWAGI                                                              | WARTOŚC DOMYŚLNA         |
| -------------- | ----------- | ------ | ------------------------------------------------------------------ | ------------------------ |
| **ID**         | INT         | INT    | ID kuponu                                                          | AUTOMATYCZNIE GENEROWANY |
| GAMBLER_NAME   | VARCHAR(30) | STRING | Nazwa typera                                                       | NULL                     |
| PARLAYS_PLAYED | INT         | >= 0   | Liczba kuponów zagranych przez typera                              | 0                        |
| PARLAYS_WON    | INT         | >= 0   | Liczba kuponów wygranych przez typera                              | 0                        |
| BALANCE        | FLOAT       | FLOAT  | Aktualny stan konta typera                                         | 0                        |
| ACTIVE         | INT         | {0, 1} | Flaga, czy gracz jest aktywny (0 - nie, 1 - tak)                   | 1                        |
| IS_HUMAN       | INT         | {0, 1} | Flaga, czy gracz jest człowiekiem czy automatem (0 - nie, 1 - tak) | 0                        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są **ręcznie** (Możliwe rozszerzenie na tworzenie nowych typerów przez innych ludzi (np. tworzenie kont w serwisie), jednak jest to BARDZO przyszłościowe rozszerzenie)

---

### HOCKEY_MATCH_EVENTS

(zdarzenia występujące w danym meczu hokejowym)


| POLE        | DOMENA       | ZAKRES      | UWAGI                                                                                                                                                                         | WARTOŚC DOMYŚLNA         |
| ----------- | ------------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**      | INT          | INT         | ID kuponu                                                                                                                                                                     | AUTOMATYCZNIE GENEROWANY |
| *EVENT_ID*  | INT          | INT         | Klucz obcy, powiązanie z tabelą *events*                                                                                                                                      | NULL                     |
| *MATCH_ID*  | INT          | INT         | Klucz obcy, powiązanie z tabelą *matches*                                                                                                                                     | NULL                     |
| *TEAM_ID*   | INT          | INT         | Klucz obcy, powiązanie z tabelą *teams*                                                                                                                                       | NULL                     |
| *PLAYER_ID* | INT          | INT         | Klucz obcy, powiązanie z tabelą *players*                                                                                                                                     | NULL                     |
| PERIOD      | INT          | {1,2,3,4,5} | Tercja, w której zdarzenie miało miejsce. Jeśli PERIOD = 4 to zdarzenie miało miejsce w dogrywce, jeśli 5 - w rzutach karnych                                                 | NULL                     |
| EVENT_TIME  | VARCHAR(9)   | <20:00:00   | Czas w tercji, w którym zdarzenie miało miejsce. W karnych rundy konwertowane są na czas w następujący sposób: 1 runda karnych -> 00:00:01, 2 runda karnych -> 00:00:02, etc. | NULL                     |
| PP_FLAG     | INT          | {0,1}       | Czy gol padł w przewadze? (1 - tak, 0 - nie)                                                                                                                                  | NULL                     |
| EN_FLAG     | INT          | {0,1}       | Czy gol padł do pustej bramki? (1 - tak, 0 - nie)                                                                                                                             | NULL                     |
| DESCRPTION  | VARCHAR(100) | STRING      | Opis zdarzenia (np. kto asystował)                                                                                                                                            | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `EVENT_ID` → `events(ID)`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`

**Sposób generowania danych do tabeli**:
Dane do tabeli dodawane są bezpośrednio przy pomocy modułu **nhl_all_scraper.py**

---

### HOCKEY_MATCH_PLAYER_STATS

(statystyki każdego gracza w danym meczu)


| POLE            | DOMENA      | ZAKRES     | UWAGI                                                                                                                                                                  | WARTOŚC DOMYŚLNA         |
| --------------- | ----------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**          | INT         | INT        | ID statystyk danego zawodnika w danym meczu hokejowym                                                                                                                  | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*      | INT         | INT        | Klucz obcy, powiązanie z tabelą *matches*                                                                                                                              | NULL                     |
| *PLAYER_ID*     | INT         | INT        | Klucz obcy, powiązanie z tabelą *players*                                                                                                                              | NULL                     |
| *TEAM_ID*       | INT         | INT        | Klucz obcy, powiązanie z tabelą *teams*                                                                                                                                | NULL                     |
| GOALS           | INT         | >=0        | Liczba bramek strzelona przez hokeistę                                                                                                                                 | NULL                     |
| ASSISTS         | INT         | >=0        | Liczba asysty zdobyta przez hokeistę                                                                                                                                   | NULL                     |
| POINTS          | INT         | >=0        | Liczba punktów kanadyjskich (GOALS + ASSISTS)                                                                                                                          | NULL                     |
| PLUS_MINUS      | INT         | INT        | Indywidualna statystyka w hokeju na lodzie, która stanowi punktację liczoną za przebywanie na lodzie w momencie zdobycia (+) i straty gola (-) przez drużynę zawodnika | NULL                     |
| PENALTY_MINUTES | INT         | >=0        | Liczba minut spędzonych na ławce kar przez zawodnika                                                                                                                   | NULL                     |
| SOG             | INT         | >=0        | Liczba CELNYCH strzałów na bramkę                                                                                                                                      | NULL                     |
| BLOCKED         | INT         | >=0        | Liczba zablokowanych strzałów (zawodnik z pola)                                                                                                                        | NULL                     |
| SHOTS_ACC       | FLOAT       | [0,100]"%" | Celność strzałów                                                                                                                                                       | NULL                     |
| TURNOVERS       | INT         | >=0        | Liczba straconych "posiadań" przez zawodnika (utraty krążka wynikające z błędu własnego)                                                                               | NULL                     |
| STEALS          | INT         | >=0        | Liczba przechwytów                                                                                                                                                     | NULL                     |
| FACEOFF         | INT         | >=0        | Liczba wznowień, w których zawodnik brał udział                                                                                                                        | NULL                     |
| FACEOFF_WON     | INT         | >=0        | Liczba wznowień wygranych przez zawodnika                                                                                                                              | NULL                     |
| FACEOFF_ACC     | FLOAT       | [0,100]"%" | Skuteczność wznowień                                                                                                                                                   | NULL                     |
| HITS            | INT         | >=0        | Liczba legalnych uderzeń wykonanych przez gracza                                                                                                                       | NULL                     |
| TOI             | VARCHAR(9)  | >=0        | Czas spędzony przez gracza na lodzie (TOI = Time On Ice)                                                                                                               | NULL                     |
| SHOTS_AGAINST   | INT         | >=0        | Liczba strzałów oddanych przez przeciwników na bramkę danego zawodnika (TYLKO BRAMKARZE)                                                                               | NULL                     |
| SHOTS_SAVED     | INT         | >=0        | Liczba obronionych strzałów (TYLKO BRAMKARZE)                                                                                                                          | NULL                     |
| SAVES_ACC       | INT         | >=0        | Skuteczność obron (TYLKO BRAMKARZE)                                                                                                                                    | NULL                     |
| TOI_STR         | VARCHAR(10) | STRING     | Prezentacja TOI w formie stringa (były problemy z formtowaniem więc załatwiłem to przez dodatkową kolumnę, nieoptymalnie, ale na razie niech będzie)                   | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- **Unikalny indeks**: `MATCH_ID`, `PLAYER_ID` (zapobiega duplikatom statystyk dla tego samego zawodnika w danym meczu)

**Sposób generowania danych do tabeli**:
Dane do tabeli dodawane są bezpośrednio przy pomocy modułu **nhl_all_scraper.py**

---

### HOCKEY_MATCH_ROSTERS

(dodatkowe statystyki specyficzne dla meczu hokejowego)


| POLE        | DOMENA     | ZAKRES            | UWAGI                                                                                                              | WARTOŚC DOMYŚLNA         |
| ----------- | ---------- | ----------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| **ID**      | INT        | INT               | ID dodatkowych statystyk hokejowych dla danego meczu                                                               | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*  | INT        | INT               | Klucz obcy, powiązanie z tabelą *matches*                                                                          | NULL                     |
| *PLAYER_ID* | INT        | INT               | Klucz obcy, powiązanie z tabelą *players*                                                                          | NULL                     |
| *TEAM_ID*   | INT        | INT               | Klucz obcy, powiązanie z tabelą *teams*                                                                            | NULL                     |
| POSITION    | VARCHAR(5) | {G, D, LW, C, RW} | Pozycja zawodnika na lodzie (G - bramkarz, D - obrońca, LW - lewy skrzydłowy, C - środkowy, RW - prawy skrzydłowy) | NULL                     |
| LINE        | INT        | {1,2,3,4}         | Linia, w której gra zawodnik                                                                                       | NULL                     |
| NUMBER      | INT        | [0, 99]           | Numer na koszulce zawodnika                                                                                        | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- **Unikalny indeks**: `MATCH_ID`, `PLAYER_ID` (zapobiega duplikatom składu dla tego samego zawodnika w danym meczu)

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są bezpośrednio przy pomocy modułu **nhl_all_scraper.py**

---

### HOCKEY_MATCHES_ADD

(dodatkowe statystyki specyficzne dla meczu hokejowego)


| POLE                   | DOMENA | ZAKRES  | UWAGI                                                                                                                     | WARTOŚC DOMYŚLNA         |
| ---------------------- | ------ | ------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**                 | INT    | INT     | ID dodatkowych statystyk hokejowych dla danego meczu                                                                      | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*             | INT    | INT     | Klucz obcy, powiązanie z tabelą *matches*                                                                                 | NULL                     |
| OT                     | INT    | {0,1}   | Czy była dogrywka? (0 - nie, 1 - tak)                                                                                     | NULL                     |
| SO                     | INT    | {0,1}   | Czy były rzuty karne (0 - nie, 1 - tak, tylko sezon zasadniczy)                                                           | NULL                     |
| home_team_pp_goals     | INT    | >= 0    | Liczba bramek zdobytych w przewadze przez drużynę gospodarzy                                                              | NULL                     |
| away_team_pp_goals     | INT    | >= 0    | Liczba bramek zdobytych w przewadze przez drużynę gości                                                                   | NULL                     |
| home_team_sh_goals     | INT    | >= 0    | Liczba bramek zdobytych w osłabieniu przez drużynę gospodarzy                                                             | NULL                     |
| away_team_sh_goals     | INT    | >= 0    | Liczba bramek zdobytych w osłabieniu przez drużynę gości                                                                  | NULL                     |
| home_team_shots_acc    | FLOAT  | [0,100] | Skuteczność strzałów drużyny gospodarzy liczona jako liczba bramek dzielona na liczbę strzałów celnych                    | NULL                     |
| away_team_shots_acc    | FLOAT  | [0,100] | Skuteczność strzałów drużyny gości liczona jako liczba bramek dzielona na liczbę strzałów celnych                         | NULL                     |
| home_team_saves        | INT    | >= 0    | Liczba strzałów obronionych przez gospodarzy                                                                              | NULL                     |
| away_team_saves        | INT    | >= 0    | Liczba strzałów obronionych przez gości                                                                                   | NULL                     |
| home_team_saves_acc    | FLOAT  | [0,100] | Skuteczność obron drużyny gospodarzy liczona jako liczba obron dzielona na liczbę strzałów celnych                        | NULL                     |
| away_team_saves_acc    | FLOAT  | [0,100] | Skuteczność obron drużyny gości liczona jako liczba obron dzielona na liczbę strzałów celnych                             | NULL                     |
| home_team_pp_acc       | FLOAT  | [0,100] | Skuteczność gier w przewadze drużyny gospodarzy liczona jako liczba strzelonych bramek w przewadze przez liczbę przewag   | NULL                     |
| away_team_pp_acc       | FLOAT  | [0,100] | Skuteczność gier w przewadze drużyny gości liczona jako liczba strzelonych bramek w przewadze przez liczbę przewag        | NULL                     |
| home_team_pk_acc       | FLOAT  | [0,100] | Skuteczność gier w osłabieniu drużyny gospodarzy liczona jako liczba straconych bramek w osłabieniu przez liczbę osłabień | NULL                     |
| away_team_pk_acc       | FLOAT  | [0,100] | Skuteczność gier w osłabieniu drużyny gości liczona jako liczba straconych bramek w osłabieniu przez liczbę osłabień      | NULL                     |
| home_team_faceoffs     | INT    | >= 0    | Liczba wygranych wznowień przez gospodarzy                                                                                | NULL                     |
| away_team_faceoffs     | INT    | >= 0    | Liczba wygranych wznowień przez gości                                                                                     | NULL                     |
| home_team_faceoffs_acc | FLOAT  | [0,100] | Skuteczność wygranych wznowień przez gospodarzy                                                                           | NULL                     |
| away_team_faceoffs_acc | FLOAT  | [0,100] | Skuteczność wygranych wznowień przez gości                                                                                | NULL                     |
| home_team_hits         | INT    | >= 0    | Liczba uderzeń wykonanych przez gospodarzy                                                                                | NULL                     |
| away_team_hits         | INT    | >= 0    | Liczba uderzeń wykonanych przez gości                                                                                     | NULL                     |
| home_team_to           | INT    | >= 0    | Liczba strat popełnionych przez gospodarzy                                                                                | NULL                     |
| away_team_to           | INT    | >= 0    | Liczba strat popełnionych przez gości                                                                                     | NULL                     |
| home_team_en           | INT    | >= 0    | Liczba goli zdobytych na pustą bramkę (en - empty net) przez gospodarzy                                                   | NULL                     |
| away_team_en           | INT    | >= 0    | Liczba goli zdobytych na pustą bramkę (en - empty net) przez gości                                                        | NULL                     |
| OTwinner               | INT    | {1,2,3} | Wynik dogrywki (1 - gospodarz wygrał, 2 - gość wygrał, 3 - rozstrzygnięcie dopiero w karnych)                             | NULL                     |
| SOwinner               | INT    | {0,1,2} | Wynik karnych (0 - brak karnych, 1 - gospdoarz wygrał, 2 - gość wygrał)                                                   | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są bezpośrednio przy pomocy modułu **nhl_all_scraper.py**

---

### HOCKEY_ROSTERS

(aktualne składy drużyn hokejowych)


| POLE        | DOMENA     | ZAKRES            | UWAGI                                                                                                                                                                              | WARTOŚC DOMYŚLNA         |
| ----------- | ---------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**      | INT        | INT               | ID przewidywane składu                                                                                                                                                             | AUTOMATYCZNIE GENEROWANY |
| *PLAYER_ID* | INT        | INT               | Klucz obcy, powiązanie z tabelą *players*                                                                                                                                          | NULL                     |
| *TEAM_ID*   | INT        | INT               | Klucz obcy, powiązanie z tabelą *teams*                                                                                                                                            | NULL                     |
| LINE        | INT        | {1,2,3,4}         | Linia, w której gra zawodnik                                                                                                                                                       | NULL                     |
| NUMBER      | INT        | [0, 99]           | Numer na koszulce zawodnika                                                                                                                                                        | NULL                     |
| POSITION    | VARCHAR(5) | {G, D, LW, C, RW} | Pozycja zawodnika na lodzie (G - bramkarz, D - obrońca, LW - lewy skrzydłowy, C - środkowy, RW - prawy skrzydłowy)                                                                 | NULL                     |
| PP          | INT        | {0, 1, 2}         | Czy zawodnik jest przypisany do gry w przewadze? (1 - przypisany do pierwszej linii przewagi (1PP), 2 - przypisany do drugiej linii przewagi (PP2), 0 - nieprzypisany do przewagi) | NULL                     |
| IS_INJURED  | INT        | {0, 1}            | Czy zawodnik jest kontuzjowany? (0 - nie, 1 - tak)                                                                                                                                 | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- **Unikalny indeks:** `PLAYER_ID, TEAM_ID` (zapobiega duplikatom graczy w składzie drużyny)

**Sposób generowania danych do tabeli**:

Dane do tabeli BĘDĄ dodawane nowym modułem o potencjalnej nazwie **get_projected_lineups.py**

---

### LEAGUES

(spis analizowanych lig)


| POLE                | DOMENA      | ZAKRES                | UWAGI                                                                                    | WARTOŚC DOMYŚLNA         |
| ------------------- | ----------- | --------------------- | ---------------------------------------------------------------------------------------- | ------------------------ |
| **ID**              | INT         | INT                   | ID ligi                                                                                  | AUTOMATYCZNIE GENEROWANY |
| *SPORT_ID*          | INT         | INT                   | Klucz obcy, powiązanie z tabelą *sports*                                                 | NULL                     |
| *COUNTRY*           | INT         | INT                   | Klucz obcy, powiązanie z tabelą *countries*                                              | NULL                     |
| *CURRENT_SEASON_ID* | INT         | INT                   | Klucz obcy, powiązanie z tabelą *seasons*                                                | NULL                     |
| NAME                | VARCHAR(45) | STRING                | Nazwa drużyny w języku polskim                                                           | NULL                     |
| LAST_UPDATE         | DATETIME    | DATE                  | Ostatnia aktualizacja danych ligowych (jakichkolwiek, nawet fauli w meczu X)             | NULL                     |
| ACTIVE              | INT         | {0, 1}                | Czy liga aktualnie analizowana przez system? (0 - nie, 1 - tak)                          | NULL                     |
| TIER                | INT         | {1, 2, 100, 101, 102} | Poziom rozgrywky ligi (100 - Liga Mistrzów, 101 - Liczba Europy, 102 - Liga Konferencji) | NULL                     |
| HAS_PLAYER_STATS    | INT         | {0, 1}                | Czy liga posiada statystyki zawodników? (0 - nie, 1 - tak)                                    | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `SPORT_ID` → `sports(ID)`
- Klucz obcy: `COUNTRY` → `countries(ID)`
- Klucz obcy: `CURRENT_SEASON_ID` → `seasons(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### MATCHES

(wszystkie analizowane mecze)


| POLE            | DOMENA     | ZAKRES               | UWAGI                                                                                                                                                                                                                                                                                                                                                                          | WARTOŚC DOMYŚLNA         |
| --------------- | ---------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| **ID**          | INT        | INT                  | ID meczu                                                                                                                                                                                                                                                                                                                                                                       | AUTOMATYCZNIE GENEROWANY |
| *LEAGUE*        | INT        | INT                  | Klucz obcy, powiązanie z tabelą *leagues*                                                                                                                                                                                                                                                                                                                                      | NULL                     |
| *SEASON*        | INT        | INT                  | Klucz obcy, powiązanie z tabelą *seasons*                                                                                                                                                                                                                                                                                                                                      | NULL                     |
| *HOME_TEAM*     | INT        | INT                  | Klucz obcy, powiązanie z tabelą *teams*                                                                                                                                                                                                                                                                                                                                        | NULL                     |
| *AWAY_TEAM*     | INT        | INT                  | Klucz obcy, powiązanie z tabelą *teams*                                                                                                                                                                                                                                                                                                                                        | NULL                     |
| *SPORT_ID*      | INT        | INT                  | Klucz obcy, powiązanie z tabelą *sports*                                                                                                                                                                                                                                                                                                                                       | NULL                     |
| GAME_DATE       | DATETIME   | DATETIME             | Termin rozgrywanego meczu                                                                                                                                                                                                                                                                                                                                                      | NULL                     |
| ROUND           | INT        | [0,100] ^ [900,1000] | Runda, w ramach której rozgegrano mecz. Runda 100 jako runda specjalna dla lig, które nie posiadają jednoznacznego podziału na rundy (NHL, MLS). Rundy od 900 to rundy specjalne zawierające informację o momencie fazy pucharowej, w której mecz został rozegrany (wsparcie dla meczów max 1/32 finału, BO7). Dokładny opis znajduje się w komentarzu do pola w bazie danych. | NULL                     |
| RESULT          | VARCHAR(1) | {'X', '0', '1', '2'} | Wynik spotkania ('0' - brak rezultatu w bazie / jeszcze nie rozegrano, '1' - gospodarz wygrał, '2' - gość wygrał, 'X' - remis )                                                                                                                                                                                                                                                | NULL                     |
| HOME_TEAM_GOALS | INT        | INT                  | Liczba bramek zdobyta przez gospodarza                                                                                                                                                                                                                                                                                                                                         | NULL                     |
| AWAY_TEAM_GOALS | INT        | INT                  | Liczba bramek zdobyta przez gościa                                                                                                                                                                                                                                                                                                                                             | NULL                     |
| HOME_TEAM_XG    | FLOAT      | >=0.00               | Współczynnik expected goals(xG) dla drużyny gospodarza                                                                                                                                                                                                                                                                                                                         | NULL                     |
| AWAY_TEAM_XG    | FLOAT      | >=0.00               | Współczynnik expected goals(xG) dla drużyny gościa                                                                                                                                                                                                                                                                                                                             | NULL                     |
| HOME_TEAM_BP    | INT        | INT                  | Posiadanie piłki gospodarza                                                                                                                                                                                                                                                                                                                                                    | NULL                     |
| AWAY_TEAM_BP    | INT        | INT                  | Posiadanie piłki gościa                                                                                                                                                                                                                                                                                                                                                        | NULL                     |
| HOME_TEAM_SC    | INT        | INT                  | Liczba strzałów (wszystkich) gospodarza                                                                                                                                                                                                                                                                                                                                        | NULL                     |
| AWAY_TEAM_SC    | INT        | INT                  | Liczba strzałów (wszystkich) gościa                                                                                                                                                                                                                                                                                                                                            | NULL                     |
| HOME_TEAM_SOG   | INT        | INT                  | Liczba strzałów NA BRAMKĘ gospodarza                                                                                                                                                                                                                                                                                                                                           | NULL                     |
| AWAY_TEAM_SOG   | INT        | INT                  | Liczba strzałów NA BRAMKĘ gościa                                                                                                                                                                                                                                                                                                                                               | NULL                     |
| HOME_TEAM_FK    | INT        | INT                  | Liczba rzutów wolnych wykonanych przez gospodarza                                                                                                                                                                                                                                                                                                                              | NULL                     |
| AWAY_TEAM_FK    | INT        | INT                  | Liczba rzutów wolnych wykonanych przez gościa                                                                                                                                                                                                                                                                                                                                  | NULL                     |
| HOME_TEAM_CK    | INT        | INT                  | Liczba rzutów rożnych wykonanych przez gospodarza                                                                                                                                                                                                                                                                                                                              | NULL                     |
| AWAY_TEAM_CK    | INT        | INT                  | Liczba rzutów rożnych wykonanych przez gościa                                                                                                                                                                                                                                                                                                                                  | NULL                     |
| HOME_TEAM_OFF   | INT        | INT                  | Liczba spalonych popełnionych przez gospodarza                                                                                                                                                                                                                                                                                                                                 | NULL                     |
| AWAY_TEAM_OFF   | INT        | INT                  | Liczba spalonych popełnionych przez gościa                                                                                                                                                                                                                                                                                                                                     | NULL                     |
| HOME_TEAM_FOULS | INT        | INT                  | Liczba fauli popełnionych przez gospodarza                                                                                                                                                                                                                                                                                                                                     | NULL                     |
| AWAY_TEAM_FOULS | INT        | INT                  | Liczba fauli popełnionych przez gościa                                                                                                                                                                                                                                                                                                                                         | NULL                     |
| HOME_TEAM_YC    | INT        | INT                  | Liczba żółtych kartek gospodarza                                                                                                                                                                                                                                                                                                                                               | NULL                     |
| AWAY_TEAM_YC    | INT        | INT                  | Liczba żółtych kartek gościa                                                                                                                                                                                                                                                                                                                                                   | NULL                     |
| HOME_TEAM_RC    | INT        | INT                  | Liczba czerwonych kartek gospodarza                                                                                                                                                                                                                                                                                                                                            | NULL                     |
| AWAY_TEAM_RC    | INT        | INT                  | Liczba czerwonych kartek gościa                                                                                                                                                                                                                                                                                                                                                | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `LEAGUE` → `leagues(ID)`
- Klucz obcy: `SEASON` → `seasons(ID)`
- Klucz obcy: `HOME_TEAM` → `teams(ID)`
- Klucz obcy: `AWAY_TEAM` → `teams(ID)`
- Klucz obcy: `SPORT_ID` → `sports(ID)`
- **Unikalny indeks:** `(HOME_TEAM, AWAY_TEAM, GAME_DATE)` – nie mogą istnieć dwa różne mecze w tym samym momencie dla
tych samych druzyn

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawwane w ramach wszystkich scrapperów dotyczących meczów (**scrapper.py**, **scrapper_wrapper.py**, **nhl_all_scrapper.py** )

---

### MATCH_MODEL_ASSESSMENTS

(Oceny meczów *po fakcie* z modeli assessment — np. kto zagrał lepiej. Nie mylić z `PREDICTIONS` / `FINAL_PREDICTIONS`, które dotyczą predykcji przyszłych zdarzeń zakładkowych.)


| POLE                             | DOMENA       | ZAKRES  | UWAGI                                                                                                                                                         | WARTOŚC DOMYŚLNA         |
| -------------------------------- | ------------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**                           | INT          | INT     | ID oceny                                                                                                                                                      | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*                       | INT          | INT     | Klucz obcy, powiązanie z tabelą *matches*                                                                                                                     | NOT NULL                 |
| *MODEL_ID*                       | INT          | INT     | Klucz obcy, powiązanie z tabelą *models* (musi być aktywny przy zapisie)                                                                                      | NOT NULL                 |
| MODEL_VERSION                    | VARCHAR(64)  | STRING  | Wersja artefaktu / konfiguracji modelu (np. `1.0.0`)                                                                                                           | NOT NULL                 |
| SPORT_ID                         | INT          | INT     | Sport meczu (denormalizacja z kontekstu modelu; spójność z `matches.sport_id`)                                                                                | NOT NULL                 |
| ASSESSMENT_TYPE                  | VARCHAR(64)  | STRING  | Typ oceny (np. `PLAYED_BETTER`); pozwala rozróżnić kolejne rodziny assessmentów                                                                               | NOT NULL                 |
| HOME_PLAYED_BETTER_PROBABILITY   | FLOAT        | [0, 1]  | Prawdopodobieństwo, że gospodarz zagrał lepiej                                                                                                                | NOT NULL                 |
| DRAW_PROBABILITY                 | FLOAT        | [0, 1]  | Prawdopodobieństwo remisu jakości gry                                                                                                                         | NOT NULL                 |
| AWAY_PLAYED_BETTER_PROBABILITY   | FLOAT        | [0, 1]  | Prawdopodobieństwo, że gość zagrał lepiej                                                                                                                     | NOT NULL                 |
| FINAL_ASSESSMENT                 | VARCHAR(32)  | STRING  | Wybrana etykieta końcowa (`HOME_PLAYED_BETTER` / `DRAW` / `AWAY_PLAYED_BETTER`)                                                                               | NOT NULL                 |
| CONFIDENCE                       | FLOAT        | [0, 1]  | Różnica między najwyższym a drugim prawdopodobieństwem (pewnność decyzji)                                                                                     | NULL                     |
| DOMINANCE_SCORE                  | FLOAT        | FLOAT   | Surowy score dominacji gospodarza z labelera (ważona różnica feature’ów)                                                                                      | NULL                     |
| FEATURE_SNAPSHOT                 | JSON         | JSON    | Snapshot feature’ów użytych przy ocenie (audyt / debug)                                                                                                       | NULL                     |
| ARTIFACT_PATH                    | VARCHAR(255) | STRING  | Ścieżka do katalogu artefaktów modelu użytego przy ocenie                                                                                                     | NULL                     |
| CREATED_AT                       | TIMESTAMP    | DATETIME| Data utworzenia wiersza                                                                                                                                       | CURRENT_TIMESTAMP        |
| UPDATED_AT                       | TIMESTAMP    | DATETIME| Data ostatniej aktualizacji (upsert)                                                                                                                          | CURRENT_TIMESTAMP        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)` (`fk_match_model_assessments_match`)
- Klucz obcy: `MODEL_ID` → `models(ID)` (`fk_match_model_assessments_model`)
- **Unikalny indeks:** `unique_match_model_assessment` (`MATCH_ID`, `MODEL_ID`, `MODEL_VERSION`, `ASSESSMENT_TYPE`) — jeden wiersz na mecz/model/wersję/typ; zapis przez `ON DUPLICATE KEY UPDATE`
- Indeks: `idx_match_model_assessments_match_id` (`MATCH_ID`)
- Indeks: `idx_match_model_assessments_model_id` (`MODEL_ID`)

**Sposób generowania danych do tabeli:**

Dane zapisywane przez pipeline ML (`models/pipeline/persistence/match_assessment_writer.py`) przy komendach `assess-match` / `assess-batch` z flagą `--write-db` (`models/scripts/model_runner.py`).

---

### MODELS

(lista stworzonych modeli predykcyjnych)


| POLE       | DOMENA      | ZAKRES | UWAGI                                                                                                          | WARTOŚC DOMYŚLNA         |
| ---------- | ----------- | ------ | -------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**     | INT         | INT    | Klucz główny, automatycznie generowany                                                                         | AUTOMATYCZNIE GENEROWANE |
| NAME       | VARCHAR(50) | STRING | Nazwa modelu predykcyjnego                                                                                     | NULL                     |
| ACTIVE     | INT         | {0, 1} | Flaga aktywności modelu (0 - nieaktywny, 1 - aktywny). Tylko aktywne modele są używane do generowania zakładów | NULL                     |
| *SPORT_ID* | INT         | INT    | Klucz obcy, powiązanie z tabelą *sports*                                                                       | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Indeks unikalny: `ID_UNIQUE` (`ID`)
- Klucz obcy: `SPORT_ID` → `sports(ID)` (ograniczenie `MODELS_SPORTS`)
- Indeks: `MODELS_SPORTS_idx` (`SPORT_ID`)

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są **ręcznie** w ramach konfiguracji nowych modeli predykcyjnych. Każdy nowy model musi być dodany do tej tabeli przed pierwszym użyciem (seed SQL, np. `sql/migrations/002_seed_football_played_better_v1.sql`, `sql/migrations/003_seed_football_played_better_noxg_v1.sql`). Modele assessment (`FOOTBALL_PLAYED_BETTER_V1`, `FOOTBALL_PLAYED_BETTER_NOXG_V1`) zapisują wyniki do `MATCH_MODEL_ASSESSMENTS`, a nie do `PREDICTIONS`.

---

### MODEL_TRAINING_RUNS

(Opcjonalny audyt przebiegów trenowania i ewaluacji modeli ML — metryki, feature’y, ścieżki artefaktów. Nie przechowuje predykcji ani ocen meczów.)


| POLE                 | DOMENA       | ZAKRES  | UWAGI                                                                                          | WARTOŚC DOMYŚLNA         |
| -------------------- | ------------ | ------- | ---------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**               | INT          | INT     | ID przebiegu                                                                                   | AUTOMATYCZNIE GENEROWANY |
| *MODEL_ID*           | INT          | INT     | Klucz obcy, powiązanie z tabelą *models*                                                       | NOT NULL                 |
| MODEL_VERSION        | VARCHAR(64)  | STRING  | Wersja modelu powiązana z przebiegiem                                                          | NOT NULL                 |
| RUN_TYPE             | VARCHAR(32)  | STRING  | Typ przebiegu (np. `train`, `evaluate`)                                                        | NOT NULL                 |
| ARTIFACT_PATH        | VARCHAR(255) | STRING  | Ścieżka katalogu artefaktów (joblib/JSON)                                                      | NOT NULL                 |
| CONFIG_PATH          | VARCHAR(255) | STRING  | Ścieżka pliku konfiguracji treningu / ewaluacji                                                | NOT NULL                 |
| TRAINING_STARTED_AT  | TIMESTAMP    | DATETIME| Start przebiegu                                                                                | NULL                     |
| TRAINING_FINISHED_AT | TIMESTAMP    | DATETIME| Koniec przebiegu                                                                               | NULL                     |
| METRICS              | JSON         | JSON    | Metryki jakości (accuracy, log-loss, Brier, calibration itd.)                                  | NULL                     |
| FEATURE_COLUMNS      | JSON         | JSON    | Lista kolumn feature’ów użytych w przebiegu                                                    | NOT NULL                 |
| DATA_FILTERS         | JSON         | JSON    | Filtry zbioru danych (np. kohorta xG, `required_columns`, `sport_id`)                          | NULL                     |
| CREATED_AT           | TIMESTAMP    | DATETIME| Data utworzenia wiersza audytu                                                                 | CURRENT_TIMESTAMP        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MODEL_ID` → `models(ID)` (`fk_model_training_runs_model`)
- Indeks: `idx_model_training_runs_model_id` (`MODEL_ID`)

**Sposób generowania danych do tabeli:**

Tabela audytowa utworzona wraz z `MATCH_MODEL_ASSESSMENTS`. Zapis przebiegów jest opcjonalny — pipeline może logować tu wyniki `train` / `evaluate` z `models/scripts/model_runner.py` (metryki + lista feature’ów + filtry danych).

---

### ODDS

(pobrane kursy dla danego meczu dla danego zdrarzenia)


| POLE        | DOMENA | ZAKRES | UWAGI                                                | WARTOŚC DOMYŚLNA         |
| ----------- | ------ | ------ | ---------------------------------------------------- | ------------------------ |
| **ID**      | INT    | INT    | ID dodatkowych statystyk hokejowych dla danego meczu | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*  | INT    | INT    | Klucz obcy, powiązanie z tabelą *matches*            | NULL                     |
| *BOOKMAKER* | INT    | INT    | Klucz obcy, powiązanie z tabelą *bookmakers*         | NULL                     |
| *EVENT*     | INT    | INT    | Klucz obcy, powiązanie z tabelą *events*             | NULL                     |
| ODDS        | FLOAT  | >= 1   | Kurs dla danego wpisu                                | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `BOOKMAKER` → `bookmakers(ID)`
- Klucz obcy: `EVENT` → `events(ID)`
- **Unikalny indeks:** `(MATCH_ID, BOOKMAKER, EVENT)` – gwarantuje unikalność zakładu dla każdego meczu, bukmachera oraz zdarzenia (bez sensu tu byłyby duplikaty)

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są w ramach działania modułu **odds_scrapper.py**

Typer LM odczytuje kursy 1/X/2 Superbet (`bookmaker = 1`, eventy `1/2/3`) z tej tabeli i **nie tworzy kopii** (brak kolumn kursów w tabelach `champions_league_typer_*` i brak krawędzi FK Typer → `odds`; powiązanie logiczne przez `matches.id`). Dla Ligi Mistrzów wiersz `(match_id, bookmaker, event)` jest zapisany jednokrotnie przez proces zewnętrzny, zwykle w dniu meczu.

---

### PARLAY_EVENTS

(Szczegóły kuponów)


| POLE        | DOMENA | ZAKRES | UWAGI                                             | WARTOŚC DOMYŚLNA         |
| ----------- | ------ | ------ | ------------------------------------------------- | ------------------------ |
| **ID**      | INT    | INT    | ID zdarzenia                                      | AUTOMATYCZNIE GENEROWANY |
| *PARLAY_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *gambler_parlays* | NULL                     |
| *BET_ID*    | INT    | INT    | Klucz obcy, powiązanie z tabelą *bets*            | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PARLAY_ID` → `gambler_parlays(ID)`
- Klucz obcy: `BET_ID` → `bets(ID)`
**Sposób generowania danych do tabeli**:

Aktualnie dane do tabeli dodawane są tylko i wyłącznie **ręcznie** (w przyszłości przewidywane jest dodawaniez zdarzeń poprzez moduł "Kupony Graczy")

---

### PLAYER_PROPS_LINES

(linie na zdarzenia dla graczy w poszczególnych sportach)


| POLE           | DOMENA | ZAKRES | UWAGI                                        | WARTOŚC DOMYŚLNA         |
| -------------- | ------ | ------ | -------------------------------------------- | ------------------------ |
| **ID**         | INT    | INT    | ID linii na zdarzenie dla gracza             | AUTOMATYCZNIE GENEROWANY |
| *PLAYER_ID*    | INT    | INT    | Klucz obcy, powiązanie z tabelą *players*    | NULL                     |
| *MATCH_ID*     | INT    | INT    | Klucz obcy, powiązanie z tabelą *matches*    | NULL                     |
| *TEAM_ID*      | INT    | INT    | Klucz obcy, powiązanie z tabelą *teams*      | NULL                     |
| *EVENT_ID*     | INT    | INT    | Klucz obcy, powiązanie z tabelą *events*     | NULL                     |
| *BOOKMAKER_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *bookmakers* | NULL                     |
| LINE           | FLOAT  | FLOAT  | Linia na zdarzenie dla gracza                | NULL                     |
| ODDS           | FLOAT  | >= 1   | Kurs dla danej linii                         | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `EVENT_ID` → `events(ID)`
- Klucz obcy: `BOOKMAKER_ID` → `bookmakers(ID)`
- **Unikalny indeks:** `(PLAYER_ID, MATCH_ID, EVENT_ID, BOOKMAKER_ID)` – gwarantuje unikalność linii dla danego zawodnika, meczu, zdarzenia i bukmachera

**Sposób generowania danych do tabeli**:
TODO - mechanizm

---

### PLAYER_NAME_MAPPINGS

(mapowania nazw zawodników dla różnych bukmacherów)


| POLE                  | DOMENA       | ZAKRES   | UWAGI                                                                                          | WARTOŚC DOMYŚLNA            |
| --------------------- | ------------ | -------- | ---------------------------------------------------------------------------------------------- | --------------------------- |
| **ID**                | INT          | INT      | Klucz główny, automatycznie generowany                                                         | AUTOMATYCZNIE GENEROWANE    |
| *PLAYER_ID*           | INT          | INT      | Klucz obcy, powiązanie z tabelą *players*                                                      | NULL                        |
| *BOOKMAKER_ID*        | INT          | INT      | Klucz obcy, powiązanie z tabelą *bookmakers*                                                   | NULL                        |
| BOOKMAKER_FIRST_NAME  | VARCHAR(45)  | STRING   | Imię zawodnika używane przez bukmachera                                                        | NULL                        |
| BOOKMAKER_LAST_NAME   | VARCHAR(45)  | STRING   | Nazwisko zawodnika używane przez bukmachera                                                    | NULL                        |
| BOOKMAKER_COMMON_NAME | VARCHAR(100) | STRING   | Znormalizowana pełna nazwa zawodnika (imię + nazwisko) używana do wyszukiwania i dopasowywania | NULL                        |
| CREATED_AT            | TIMESTAMP    | DATETIME | Data utworzenia rekordu                                                                        | CURRENT_TIMESTAMP           |
| UPDATED_AT            | TIMESTAMP    | DATETIME | Data ostatniej aktualizacji rekordu                                                            | CURRENT_TIMESTAMP ON UPDATE |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `BOOKMAKER_ID` → `bookmakers(ID)`
- **Unikalny indeks**: `(BOOKMAKER_ID, PLAYER_ID)` (zapobiega duplikatom mapowań tego samego zawodnika dla danego bukmachera)
- **Indeks**: `(BOOKMAKER_ID, BOOKMAKER_COMMON_NAME)` (optymalizacja wyszukiwania zawodników po znormalizowanej nazwie)

**Sposób generowania danych do tabeli**:
Dane do tabeli generowane są **automatycznie** w ramach działania modułu **nhl_player_lines.py** podczas pierwszego dopasowania zawodnika z danymi bukmachera. Tabela służy jako cache mapowań, przyspieszając kolejne wyszukiwania i eliminując konieczność ręcznego dodawania wariantów nazw zawodników dla różnych źródeł danych.

---

### PLAYERS

(lista graczy)


| POLE              | DOMENA      | ZAKRES            | UWAGI                                                                                                                                                     | WARTOŚC DOMYŚLNA         |
| ----------------- | ----------- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**            | INT         | INT               | ID zawodnika                                                                                                                                              | AUTOMATYCZNIE GENEROWANY |
| *CURRENT_CLUB*    | INT         | INT               | Klucz obcy, powiązanie z tabelą *teams*                                                                                                                   | NULL                     |
| *CURRENT_COUNTRY* | INT         | INT               | Klucz obcy, powiązanie z tabelą *countries*                                                                                                               | NULL                     |
| *SPORTS_ID*       | INT         | INT               | Klucz obcy, powiązanie z tabelą *sports*                                                                                                                  | NULL                     |
| FIRST_NAME        | VARCHAR(45) | STRING            | Imię zawodnika                                                                                                                                            | NULL                     |
| LAST_NAME         | VARCHAR(45) | STRING            | Nazwisko zawodnika                                                                                                                                        | NULL                     |
| COMMON_NAME       | VARCHAR(60) | STRING            | Nazwisko +_ Pierwsza litera imienia zawodnika (jeśli są powtórki - istnieją wyjątki, które ciężko umieścić w tabeli - należy sprawdzić samemu w źródłach) | NULL                     |
| POSITION          | VARCHAR(5)  | {G, D, LW, C, RW} | Pozycja zawodnika na lodzie (G - bramkarz, D - obrońca, LW - lewy skrzydłowy, C - środkowy, RW - prawy skrzydłowy)                                        | NULL                     |
| EXTERNAL_ID       | VARCHAR(20) | STRING            | ID zawodnika w NHL API                                                                                                                                    | NULL                     |
| EXTERNAL_FLASH_ID | VARCHAR(20) | STRING            | ID zawodnika na flashscorze                                                                                                                               | NULL                     |
| ACTIVE            | INT         | {0, 1}            | Flaga, czy gracz jest aktywny (0 - nie, 1 - tak)                                                                                                          | 1                        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `CURRENT_CLUB` → `teams(ID)`
- Klucz obcy: `CURRENT_COUNTRY` → `countries(ID)`
- Klucz obcy: `SPORTS_ID` → `sports(ID)`

**Sposób generowania danych do tabeli**:

Dane do tabeli wprowadzane AKTUALNIE jedynie przy pomocy modułu **nhl_get_players.py** (w przyszłości planowane rozszerzenie o inne sporty i inne moduły)

---

### PREDICTIONS

(WSZYSTKIE predykcje dla każdego zdarzenia)


| POLE       | DOMENA | ZAKRES | UWAGI                                     | WARTOŚC DOMYŚLNA         |
| ---------- | ------ | ------ | ----------------------------------------- | ------------------------ |
| **ID**     | INT    | INT>0  | ID zawodnika                              | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID* | INT    | INT>0  | Klucz obcy, powiązanie z tabelą *matches* | NULL                     |
| *EVENT_ID* | INT    | INT>0  | Klucz obcy, powiązanie z tabelą *events*  | NULL                     |
| *MODEL_ID* | INT    | INT>0  | Klucz obcy, powiązanie z tabelą *models*  | NULL                     |
| VALUE      | FLOAT  | [0,100] | Prawdopodobieństwo zdarzenia w procentach (pipeline zapisuje przez `_db_percentage`; API konwertuje do [0,1]) | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `EVENT_ID` → `events(ID)`
- Klucz obcy: `MODEL_ID` → `models(ID)`
- **Unikalny indeks:** `(MATCH_ID, EVENT_ID, MODEL_ID)` – gwarantuje unikalność predykcji dla każdego zdarzenia w danym meczu i modelu

**Sposób generowania danych do tabeli**:

Dane naliczane w ramach modułu **main.py**

---

### SCHEDULE

(Stabilny terminarz sezonu piłkarskiego — źródło listy spotkań dla projekcji
końca sezonu EB-15. Izoluje graf „kto z kim w której kolejce” od operacyjnych
przenosin dat w `MATCHES`. Brak kolumny `game_date`; chronologia w symulacji =
`round` + stały interwał 7 dni.)


| POLE       | DOMENA | ZAKRES | UWAGI                                                                                                                                                                                                 | WARTOŚC DOMYŚLNA         |
| ---------- | ------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**     | INT    | INT    | Klucz główny, automatycznie generowany                                                                                                                                                                | AUTOMATYCZNIE GENEROWANY |
| MATCH_ID   | INT    | INT    | Opcjonalne, **logiczne** powiązanie z `matches(ID)` — **bez FK** i bez `UNIQUE(match_id)`. `NULL` = spotkanie jeszcze nie zlinkowane. Po podpięciu ID jest niezmienne (wynik aktualizuje się w `MATCHES`). | NULL                     |
| LEAGUE     | INT    | INT    | Id ligi — powiązanie **logiczne** z `leagues(ID)`, **bez FK** w DDL                                                                                                                                   | NULL                     |
| SEASON     | INT    | INT    | Id sezonu — powiązanie **logiczne** z `seasons(ID)`, **bez FK** w DDL                                                                                                                                 | NULL                     |
| HOME_TEAM  | INT    | INT    | Id gospodarza — powiązanie **logiczne** z `teams(ID)`, **bez FK** w DDL                                                                                                                               | NULL                     |
| AWAY_TEAM  | INT    | INT    | Id gościa — powiązanie **logiczne** z `teams(ID)`, **bez FK** w DDL                                                                                                                                   | NULL                     |
| ROUND      | INT    | INT    | Numer kolejki. Symulacja i walidacja pomijają `round >= 900` (jak standings). Brak `game_date` w tej tabeli.                                                                                           | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- **Unikalny indeks:** `id_UNIQUE (ID)` (redundantny względem PK — stan DDL)
- **Unikalny indeks:** `match_schedule_UNQ (LEAGUE, SEASON, HOME_TEAM, AWAY_TEAM, ROUND)` — jeden wiersz na uporządkowaną parę w kolejce
- **Brak** FK do `leagues` / `seasons` / `teams` / `matches` (świadomie)
- **Brak** `UNIQUE(MATCH_ID)` — uniknięcie dubli `match_id` to reguła aplikacyjna przy linkowaniu

**Semantyka dla projekcji:**

- Lista fixture’ów = wiersze `SCHEDULE` dla `(league, season)` z `round < 900`,
  posortowane po `(round, id)`.
- v1 waliduje double round-robin: `N*(N-1)` wierszy względem rosteru z
  `MATCHES` (DISTINCT drużyn sezonu, `round < 900`).
- W trybie `from_now`: LEFT JOIN wyniku z `MATCHES` po `match_id` — stały wynik
  tylko gdy `result <> '0'`; brak `match_id`, `result = '0'` lub NULL → losowanie.
- W trybie `from_season_start`: wyniki z `MATCHES` nie są czytane.

**Sposób generowania danych do tabeli:**

DDL i wypełnienie terminarza — **ręcznie** / osobnym procesem operacyjnym
(SZP-80 poza agentem). v1 bez automatycznego scrapera `schedule`.

---

### SEASONS

(Tabela z sezonami)


| POLE   | DOMENA      | ZAKRES | UWAGI                                                                                                                                                  | WARTOŚC DOMYŚLNA         |
| ------ | ----------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| **ID** | INT         | INT    | ID sezonu                                                                                                                                              | AUTOMATYCZNIE GENEROWANY |
| YEARS  | VARCHAR(10) | STRING | Lata sezonu, zawsze w tej samej formie: Rok startu + "/" + dwie ostatnie cyfry następnego roku (wyjątek dla sezonów typu 2099/2100)(przykład: 2024/25) | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### SEASON_PROJECTION_RUNS

(Cache metadanych przebiegu Monte Carlo projekcji końca sezonu. Endpoint
`GET /leagues/{league_id}/season-projection` odczytuje ostatni `SUCCEEDED` dla
`(league_id, season_id, mode)` i porównuje `input_fingerprint` ze świeżym
snapshotem — bez uruchamiania TensorFlow.)


| POLE               | DOMENA      | ZAKRES                                      | UWAGI                                                                                                                         | WARTOŚC DOMYŚLNA         |
| ------------------ | ----------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID**             | INT         | INT                                         | Klucz główny runu                                                                                                             | AUTOMATYCZNIE GENEROWANY |
| *LEAGUE_ID*        | INT         | INT                                         | Klucz obcy → `leagues(ID)`                                                                                                    | NULL                     |
| *SEASON_ID*        | INT         | INT                                         | Klucz obcy → `seasons(ID)`                                                                                                    | NULL                     |
| MODE               | VARCHAR(32) | {'from_now', 'from_season_start'}           | Tryb symulacji (osobne runy per mode)                                                                                         | NULL                     |
| STATUS             | VARCHAR(16) | {'RUNNING', 'SUCCEEDED', 'FAILED'}          | Cykl życia zapisu: wiersze drużyn widoczne dopiero po `SUCCEEDED`                                                             | NULL                     |
| MODEL_NAME         | VARCHAR(128)| STRING                                      | Nazwa artefaktu modelu (np. `FOOTBALL_GOALS_POISSON_V1`)                                                                      | NULL                     |
| MODEL_VERSION      | VARCHAR(64) | STRING                                      | Wersja modelu zapisana przy runie                                                                                             | NULL                     |
| ARTIFACT_HASH      | VARCHAR(64) | STRING                                      | Hash artefaktu użytego w inferencji                                                                                           | NULL                     |
| N_TRIALS           | INT         | [100, 10000]                                | Liczba triali Monte Carlo (domyślnie 2000 w CLI)                                                                              | NULL                     |
| SEED               | INT         | INT                                         | Seed RNG — ten sam seed + fingerprint + model + config + mode daje powtarzalny wynik                                          | NULL                     |
| FIXED_MATCHES      | INT         | >=0                                         | Liczba spotkań ze stałym wynikiem (tryb `from_now`)                                                                           | NULL                     |
| SIMULATED_MATCHES  | INT         | >=0                                         | Liczba spotkań losowanych z Poissona                                                                                          | NULL                     |
| INPUT_FINGERPRINT  | VARCHAR(64) | hex SHA-256                                 | Fingerprint wejścia (schedule + opcjonalne wyniki); zmiana unieważnia świeżość cache                                          | NULL                     |
| STARTED_AT         | TIMESTAMP   | TIMESTAMP                                   | Start runu                                                                                                                    | NULL                     |
| COMPLETED_AT       | TIMESTAMP   | TIMESTAMP                                   | Koniec runu; `NULL` dopóki status `RUNNING`                                                                                   | NULL                     |
| ERROR_MESSAGE      | TEXT        | STRING                                      | Komunikat błędu przy `FAILED` (np. niekompletny terminarz); `NULL` przy sukcesie                                              | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `LEAGUE_ID` → `leagues(ID)`
- Klucz obcy: `SEASON_ID` → `seasons(ID)`
- Indeks: `idx_season_projection_runs_lookup (LEAGUE_ID, SEASON_ID, MODE, STATUS, COMPLETED_AT)` — lookup „latest succeeded”

**Semantyka zapisu:**

- Writer ustawia `RUNNING`, po sukcesie atomowo zapisuje wiersze drużyn i
  przełącza na `SUCCEEDED`; przy błędzie → `FAILED` **bez** częściowych wierszy
  w `SEASON_PROJECTION_TEAM_ROWS`.
- Niekompletny `SCHEDULE` kończy run jako `FAILED`; API nie prezentuje go jako
  gotowej projekcji (brak `SUCCEEDED` → 404).

**Sposób generowania danych do tabeli:**

Zapis wyłącznie offline przez CLI `simulate-season`
(`models/pipeline/persistence/season_projection_writer.py`). DDL wgrane ręcznie
(SZP-86 poza agentem — bez migracji w repo).

---

### SEASON_PROJECTION_TEAM_ROWS

(Statystyki końcowe per drużyna dla udanego runu projekcji. Wiersze powstają
dopiero po transakcyjnym `SUCCEEDED` rodzica.)


| POLE                         | DOMENA | ZAKRES | UWAGI                                                                                                                                      | WARTOŚC DOMYŚLNA |
| ---------------------------- | ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- |
| ***RUN_ID***                 | INT    | INT    | Część PK; FK → `season_projection_runs(ID)` ON DELETE CASCADE                                                                              | NULL             |
| ***TEAM_ID***                | INT    | INT    | Część PK; FK → `teams(ID)`                                                                                                                 | NULL             |
| CURRENT_POSITION             | INT    | >=1    | Pozycja „na teraz”: po commitach stałych w `from_now`; w `from_season_start` start dnia 0                                                  | NULL             |
| CURRENT_POINTS               | INT    | >=0    | Punkty odpowiadające `CURRENT_POSITION`                                                                                                    | NULL             |
| EXPECTED_POSITION            | DOUBLE | >=1    | Średnia końcowa pozycja po trialach                                                                                                        | NULL             |
| MOST_LIKELY_POSITION         | INT    | >=1    | Pozycja o największym prawdopodobieństwie w rozkładzie                                                                                     | NULL             |
| POSITION_MIN                 | INT    | >=1    | Najlepsza (najniższy numer) pozycja w skończonej próbce triali                                                                             | NULL             |
| POSITION_MAX                 | INT    | >=1    | Najgorsza pozycja w skończonej próbce triali                                                                                               | NULL             |
| EXPECTED_POINTS              | DOUBLE | >=0    | Średnia końcowych punktów                                                                                                                  | NULL             |
| POINTS_VARIANCE              | DOUBLE | >=0    | Wariancja punktów                                                                                                                          | NULL             |
| POINTS_STDDEV                | DOUBLE | >=0    | Odchylenie standardowe punktów                                                                                                             | NULL             |
| POINTS_P05                   | DOUBLE | >=0    | Percentyl 5 punktów                                                                                                                        | NULL             |
| POINTS_P50                   | DOUBLE | >=0    | Mediana punktów                                                                                                                            | NULL             |
| POINTS_P95                   | DOUBLE | >=0    | Percentyl 95 punktów                                                                                                                       | NULL             |
| POINTS_MIN                   | DOUBLE | >=0    | Minimum punktów w próbce (ekstremum Monte Carlo — mniej stabilne niż P05–P95)                                                              | NULL             |
| POINTS_MAX                   | DOUBLE | >=0    | Maksimum punktów w próbce                                                                                                                  | NULL             |
| EXPECTED_GOAL_DIFFERENCE     | DOUBLE | DOUBLE | Średnia końcowa różnica bramek                                                                                                             | NULL             |
| POSITION_PROBABILITIES_JSON  | JSON   | JSON   | Rozkład P(pozycja = k) dla `k = 1..N`; suma ≈ 1. Tie-break pozycji w trialu: punkty, GD, stabilne `team_id`                                 | NULL             |


**Ograniczenia/Indeksy:**

- Klucz główny: `(RUN_ID, TEAM_ID)`
- Klucz obcy: `RUN_ID` → `season_projection_runs(ID)` ON DELETE CASCADE
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Indeks: `idx_season_projection_team_rows_team (TEAM_ID)`

**Sposób generowania danych do tabeli:**

Wstawiane atomowo razem z przejściem runu na `SUCCEEDED` przez
`season_projection_writer`. Brak wierszy dla runów `RUNNING` / `FAILED`.

---

### SPECIAL_ROUNDS

(Tabela z nazwami rund specjalnych)


| POLE   | DOMENA      | ZAKRES | UWAGI                                                                                                          | WARTOŚC DOMYŚLNA         |
| ------ | ----------- | ------ | -------------------------------------------------------------------------------------------------------------- | ------------------------ |
| **ID** | INT         | INT    | ID rundy specjalnej                                                                                            | AUTOMATYCZNIE GENEROWANY |
| NAME   | VARCHAR(45) | STRING | Nazwa rundy specjalnej (np. finał, mecz numer 1). Rundy specjalne wspierają wszystkie typy rozgrywek aż do BO5 | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### SPORTS

(Tabela z analizowanymi sportami)


| POLE   | DOMENA      | ZAKRES | UWAGI                   | WARTOŚC DOMYŚLNA         |
| ------ | ----------- | ------ | ----------------------- | ------------------------ |
| **ID** | INT         | INT    | ID sportu               | AUTOMATYCZNIE GENEROWANY |
| NAME   | VARCHAR(45) | STRING | Nazwa zwyczajowa sportu | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:
Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### TEAMS

(Tabela z drużynami)


| POLE       | DOMENA      | ZAKRES | UWAGI                                                                                | WARTOŚC DOMYŚLNA         |
| ---------- | ----------- | ------ | ------------------------------------------------------------------------------------ | ------------------------ |
| **ID**     | INT         | INT    | ID drużyny                                                                           | AUTOMATYCZNIE GENEROWANY |
| *COUNTRY*  | INT         | INT    | Klucz obcy, powiązanie z tabelą *countries*                                          | NULL                     |
| *SPORT_ID* | INT         | INT    | Klucz obcy, powiązanie z tabelą *sports*                                             | NULL                     |
| NAME       | VARCHAR(50) | STRING | Nazwa drużyn                                                                         | NULL                     |
| SHORTCUT   | VARCHAR(5)  | STRING | Skrótowa nazwa drużyny (z reguły nie więcej niż 3 litery, aczkolwiek bywają wyjątki) | NULL                     |
| OPTA_NAME  | VARCHAR(45) | STRING | Nazwa drużyny w serwisie OPTA                                                 | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `COUNTRY` → `countries(ID)`
- Klucz obcy: `SPORT_ID` → `sports(ID)`
- **Unikalny indeks:** `(NAME, COUNTRY)` – gwarantuje, że nie mogą istnieć dwie drużyny o tej samej nazwie w jednym kraju.

**Sposób generowania danych do tabeli:**

Dane do tabeli dodawane ręcznie bądź w ramach pobierania nowych meczów (np. **scrapper.py**)

---

### TRANSFERS

(Zapis transferów zawodników między klubami)


| POLE          | DOMENA | ZAKRES | UWAGI                                     | WARTOŚC DOMYŚLNA         |
| ------------- | ------ | ------ | ----------------------------------------- | ------------------------ |
| **ID**        | INT    | INT    | ID transferu                              | AUTOMATYCZNIE GENEROWANY |
| *PLAYER_ID*   | INT    | INT    | Klucz obcy, powiązanie z tabelą *players* | NULL                     |
| *OLD_TEAM_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *teams*   | NULL                     |
| *NEW_TEAM_ID* | INT    | INT    | Klucz obcy, powiązanie z tabelą *teams*   | NULL                     |
| *SEASON_ID*   | INT    | INT    | Klucz obcy, powiązanie z tabelą *seasons* | NULL                     |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `OLD_TEAM_ID` → `teams(ID)`
- Klucz obcy: `NEW_TEAM_ID` → `teams(ID)`
- Klucz obcy: `SEASON_ID` → `seasons(ID)`

**Sposób generowania danych do tabeli**:  

Dane do tabeli dodawane AKTUALNIE tylko w ramach **nhl_get_players.py** (potencjalne rozszerzenia wkrótce)

---

### USER_FAVORITE_LEAGUES

(Ulubione ligi wybranych użytkowników aplikacji — relacja użytkownik–liga)


| POLE            | DOMENA   | ZAKRES   | UWAGI                                                                 | WARTOŚC DOMYŚLNA  |
| --------------- | -------- | -------- | --------------------------------------------------------------------- | ----------------- |
| ***USER_ID***   | INT      | INT      | Klucz główny (część) i klucz obcy do *users*                          | NULL              |
| ***LEAGUE_ID*** | INT      | INT      | Klucz główny (część) i klucz obcy do *leagues*                        | NULL              |
| CREATED_AT      | DATETIME | DATETIME | Moment dodania ligi do ulubionych                                     | CURRENT_TIMESTAMP |


**Ograniczenia/Indeksy:**

- Klucz główny złożony: (`USER_ID`, `LEAGUE_ID`) — jeden użytkownik nie może mieć tej samej ligi dwa razy
- Klucz obcy: `USER_ID` → `users(ID)` **ON DELETE CASCADE** (usunięcie konta czyści ulubione)
- Klucz obcy: `LEAGUE_ID` → `leagues(ID)` **ON DELETE CASCADE** (fizyczne usunięcie ligi czyści relacje)
- Indeks: `idx_user_favorite_leagues_league` (`LEAGUE_ID`) — wymagany przez FK do `leagues`
- Brak kolumny `sort_order`: kolejność na liście to najpierw ulubione, potem reszta, w ramach grup bez zmian względem katalogu lig

Samo `leagues.active = 0` nie usuwa wiersza; użytkownik może usunąć historyczną relację z panelu.

**Sposób generowania danych do tabeli:**

Wiersze dodaje i usuwa zalogowany użytkownik przez API (`PUT`/`DELETE /users/me/favorite-leagues/{league_id}`).

---

### USER_PREFERENCES

(Skalarne preferencje UI konta — relacja 1:1 z `users`; nie mylić z `USER_FAVORITE_LEAGUES`)


| POLE               | DOMENA   | ZAKRES                    | UWAGI                                                                 | WARTOŚC DOMYŚLNA  |
| ------------------ | -------- | ------------------------- | --------------------------------------------------------------------- | ----------------- |
| ***USER_ID***      | INT      | INT                       | Klucz główny i klucz obcy do *users*                                  | NULL              |
| THEME              | ENUM     | {system, dark, light}     | Preferencja schematu kolorów konta                                    | system            |
| TEAM_NAME_DISPLAY  | VARCHAR(15) | STRING (max 15)           | Preferencja etykiet drużyn w UI ze skrótami; allowlista w API, nie ENUM w DB | full              |
| UPDATED_AT         | DATETIME | DATETIME                  | Moment ostatniego zapisu (last-write-wins per pole)                   | CURRENT_TIMESTAMP |


**Ograniczenia/Indeksy:**

- Klucz główny: `USER_ID` — jeden wiersz na konto
- Klucz obcy: `USER_ID` → `users(ID)` **ON DELETE CASCADE** (usunięcie konta kasuje preferencje)
- Brak wiersza = użytkownik nigdy nie zapisał preferencji na koncie (frontend wtedy wypycha cache localStorage)
- Domyślne `system` / `full` w DDL dotyczą bezpośredniego INSERT-a, nie semantyki „użytkownik wybrał te wartości”
- Istniejące wiersze przy `ADD COLUMN ... DEFAULT 'full'` otrzymują `full`
- Kolumna `TEAM_NAME_DISPLAY` to `VARCHAR(15)`, nie ENUM — dopuszczalne tryby (`full`, `shortcut`, ewentualne przyszłe) waliduje warstwa aplikacji (Pydantic + serwis), nie schemat MySQL
- Kolejne preferencje skalarne (np. `odds_format`) dodaje się **kolumną z DEFAULT**, bez nowej tabeli i bez JSON blob
- Aplikacja **nie** wykonuje DDL. Kolumnę wgrać ręcznie **przed** backendem, który ją odczytuje:

```sql
ALTER TABLE user_preferences
  ADD COLUMN team_name_display VARCHAR(15)
  NOT NULL DEFAULT 'full'
  COMMENT 'Preferred team label in abbreviation-capable UI'
  AFTER theme;
```

Po wdrożeniu: `SHOW CREATE TABLE user_preferences` oraz agregacja po `team_name_display`.

**Sposób generowania danych do tabeli:**

Wiersz tworzy i aktualizuje zalogowany użytkownik przez API (`GET`/`PUT /users/me/preferences`).
`GET` zwraca `{ "theme", "team_name_display" }`. `PUT` scala tylko podane pola
(`{ "theme" }` nie zmienia nazw, `{ "team_name_display" }` nie zmienia motywu).
Pusty body albo niedozwolona wartość daje 422.

---

### USERS

(Konta użytkowników aplikacji EkstraBet — logowanie do UI/API; nie mylić z `GAMBLERS`)


| POLE            | DOMENA       | ZAKRES  | UWAGI                                                                 | WARTOŚC DOMYŚLNA         |
| --------------- | ------------ | ------- | --------------------------------------------------------------------- | ------------------------ |
| **ID**          | INT          | INT     | Wewnętrzny klucz główny (zestawienia, admin) — nieeksponowany w API   | AUTOMATYCZNIE GENEROWANY |
| UUID            | CHAR(36)     | STRING  | Publiczny identyfikator (JWT `sub`, odpowiedzi API) — UNIQUE NOT NULL | NULL                     |
| USERNAME        | VARCHAR(50)  | STRING  | Login                                                                 | NULL                     |
| PASSWORD_HASH   | VARCHAR(255) | STRING  | Hash bcrypt hasła                                                     | NULL                     |
| DISPLAY_NAME    | VARCHAR(100) | STRING  | Nazwa wyświetlana w UI                                                | NULL                     |
| IS_ACTIVE       | TINYINT      | INT     | 1 = konto aktywne, 0 = zablokowane                                    | 1                        |
| IS_ADMIN        | TINYINT      | {0,1}   | 1 = administrator Typera LM (publikacja meczów, odczyt cudzego audytu typów); 0 = zwykły użytkownik | 0                        |
| FIRST_LOGIN     | TINYINT      | {0,1}   | 1 = należy ustawić hasło, username i display_name po 1. logowaniu     | 0                        |
| CREATED_AT      | DATETIME     | DATETIME| Data utworzenia konta                                                 | CURRENT_TIMESTAMP        |
| UPDATED_AT      | DATETIME     | DATETIME| Data ostatniej aktualizacji                                           | CURRENT_TIMESTAMP        |


**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- **Unikalny indeks:** `USERNAME`
- **Unikalny indeks:** `UUID` (kontrakt publiczny — JWT `sub` i API zawsze używają UUID, nigdy wewnętrznego `ID`)

**Sposób generowania danych do tabeli:**

Konta dodawane ręcznie (INSERT). Hash hasła: `python scripts/hash_password.py <haslo>`.
UUID przy INSERT: `UUID()` (MySQL) albo `uuid4` w seedzie.
Dla kont z hasłem tymczasowym ustaw `first_login = 1` przy INSERT
(wymusza zmianę hasła, nazwy użytkownika i wyświetlanej nazwy po pierwszym logowaniu).
Istniejące konta bez wymuszenia zostają przy `DEFAULT 0`.
Wyrównanie schematu (jeśli baza odbiega): `sql/align_users_auth_contract.sql`.