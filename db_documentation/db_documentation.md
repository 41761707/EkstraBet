# OFICJALNA DOKUMENTACJA BAZODANOWA
###### Ostatnia data modyfikacji: 31.08.2025

## Opis struktury bazy 

## Wszystkie tabele w bazie danych
- [BASKETBALL_CURRENT_ROSTER](#basketball_current_roster) (Aktualne składy drużyn koszykarskich)
- [BASKETBALL_MATCH_PLAYER_STATS](#basketball_match_player_stats) (Statystyki graczy w meczu koszykarskim)
- [BASKETBALL_MATCHES_ADD](#basketball_matches_add) (Dodatkowe statystyki meczów koszykarskich)
- [BASKETBALL_MATCH_ROSTERS](#basketball_match_rosters) (Składy drużyn koszykarskich w danym spotkaniu)
- [BETS](#bets) (Wszystkie możliwe do zrealizowania zakłady)
- [BOOKMAKERS](#bookmakers) (Wszyscy bukmacherzy brani pod uwagę w ramach badania)
- [CONFERENCE_DIVISIONS](#conference_divisions) (Dywizje przypisane do konferencji (dotyczy lig północnoamerykańskich))
- [CONFERENCES](#conferences) (Podział lig (głównie północnoamerykańskich) na konferencje)
- [COUNTRIES](#countries) (Kraje, z których pochodzą analizowane ligi)
- [DIVISION_TEAMS](#division_teams) (Przydział drużyn do dywizji)
- [DIVISIONS](#divisions) (Dywizje w ligach północnoamerykańskich)
- [EVENT_FAMILIES](#event_families) (Rodziny typów zdarzeń w systemie)
- [EVENT_FAMILY_MAPPINGS](#event_family_mappings) (Mapowania zdarzeń do rodzin zdarzeń)
- [EVENT_MODEL_FAMILIES](#event_model_families) (Powiązania modeli z rodzinami zdarzeń)
- [EVENTS](#events) (Typy zakładów)
- [EVENTS_PARLAY](#events_parlay) (Szczegóły kuponów)
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
- [MODELS](#models) (lista stworzonych modeli predykcyjnych)
- [ODDS](#odds) (pobrane kursy dla danego meczu dla danego zdrarzenia)
- [PLAYERS](#players) (lista graczy)
- [PREDICTIONS](#predictions) (WSZYSTKIE predykcje dla każdego zdarzenia)
- [SEASONS](#seasons) (Tabela z sezonami)
- [SPECIAL_ROUNDS](#special_rounds) (Tabela z nazwami rund specjalnych)
- [SPORTS](#sports) (Tabela z analizowanymi sportami)
- [TEAMS](#teams) (Tabela z drużynami)
- [TRANSFERS](#transfers) (Zapis transferów zawodników między klubami)

## Legenda

- Pole **pogrubione** oznacza KLUCZ GŁÓWNY w tabeli
- Pole *kursywą* oznacza KLUCZ OBCY w tabeli
- Wartości domyslne **-1** w miejscach, gdzie zbiór wartości to [0, +inf) oznaczają "brak danych"

## Opisy poszczególnych tabel

### BASKETBALL_CURRENT_ROSTER
(Tabela z aktualnymi składami drużyn koszykarskich)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        | INT           | INT      | Klucz główny, automatycznie generowany            | AUTOMATYCZNIE GENEROWANE |
| *TEAM_ID*    | INT           | INT       | Klucz obcy, powiązanie z tabelą *teams* | NULL |
| *PLAYER_ID*    | INT           | INT       | Klucz obcy, powiązanie z tabelą *players* | NULL |
| NUMBER         | INT         | INT | Numer zawodnika w drużynie | NULL |
| STARTER | INT | {0,1} | Flaga, czy zawodnik jest podstawowym zawodnikiem drużyny (1 - tak, 0 - nie) | 0 |
| IS_INJURED | INT | {0,1} | Flaga, czy zawodnik jest kontuzjowany (1 - tak, 0 - nie) | 0 |

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

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:            |
| **ID**        |  INT          | INT       | ID przypisania    | AUTOMATYCZNIE GENEROWANY            |
| *MATCH_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *matches* | NULL |
| *TEAM_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *teams* | NULL |
| *PLAYER_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *players* | NULL |
| POINTS | INT          | INT       | Liczba punktów zdobytych przez zawodnika w meczu | -1            |
| REBOUNDS | INT          | INT       | Liczba zbiórek zdobytych przez zawodnika w meczu | -1            |
| ASSISTS | INT          | INT       | Liczba asyst wykonanych przez zawodnika w meczu | -1            |
| TIME_PLAYED | VARCHAR(9)         | 00:00:00 - 99:59:59       | Czas gry zawodnika w meczu (w minutach) | -1            |
| FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów z gry przez zawodnika w meczu | -1            |
| FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów z gry przez zawodnika w meczu | -1            |
| 2_P_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów za 2 punkty przez zawodnika w meczu | -1            |
| 2_P_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów za 2 punkty przez zawodnika w meczu | -1            |
| 3_P_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów za 3 punkty przez zawodnika w meczu | -1            |
| 3_P_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów za 3 punkty przez zawodnika w meczu | -1            |
| FT_MADE | INT          | INT       | Liczba trafionych rzutów wolnych przez zawodnika w meczu | -1            |
| FT_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów wolnych przez zawodnika w meczu | -1            |
| PLUS_MINUS | INT          | INT       | Wskaźnik plus/minus zawodnika w meczu | -1            |
| OFF_REBOUNDS | INT          | INT       | Liczba ofensywnych zbiórek zdobytych przez zawodnika w meczu | -1            |
| DEF_REBOUNDS | INT          | INT       | Liczba defensywnych zbiórek zdobytych przez zawodnika w meczu | -1            |
| PERSONAL_FOULS | INT          | INT       | Liczba przewinień osobistych popełnionych przez zawodnika w meczu | -1            |
| STEALS | INT          | INT       | Liczba przechwytów dokonanych przez zawodnika w meczu | -1            |
| TURNOVERS | INT          | INT       | Liczba strat popełnionych przez zawodnika w meczu | -1            |
| BLOCKED_SHOTS | INT          | INT       | Liczba zablokowanych rzutów dokonanych przez zawodnika w meczu | -1            |
| BLOCKS_AGAINST | INT          | INT       | Liczba zablokowanych rzutów przeciwko zawodnikowi w meczu | -1            |
| TECHNICAL_FOULS | INT          | INT       | Liczba przewinień technicznych popełnionych przez zawodnika w meczu | -1            |

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

**Sposób generowania danych do tabeli**:
Dane do tabeli generowane są w ramach działania modułu **basketball_scrapper.py**
---

### BASKETBALL_MATCH_ROSTERS
(Składy drużyn koszykarskich w danym spotkaniu)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:            |
| **ID**        |  INT          | INT       | ID przypisania    | AUTOMATYCZNIE GENEROWANY            |
| *MATCH_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *matches* | NULL |
| *TEAM_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *teams* | NULL |
| *PLAYER_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *players* | NULL |
| NUMBER | INT          | INT       | Numer zawodnika w meczu | -1            |
| STARTER | INT          | {0,1}       | Flaga, czy zawodnik był podstawowym zawodnikiem drużyny w meczu (1 - tak, 0 - nie) | 0            |

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
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:            |
| **ID**        |  INT          | INT       | ID przypisania    | AUTOMATYCZNIE GENEROWANY            |
| *MATCH_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *matches* | NULL |
| HOME_TEAM_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów z gry przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów z gry przez drużynę gości w meczu | -1            |
| HOME_TEAM_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów z gry przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów z gry przez drużynę gości w meczu | -1            |
| HOME_TEAM_FIELD_GOALS_ACC | FLOAT          | FLOAT       | Skuteczność rzutów z gry drużyny gospodarzy w meczu | -1            |
| AWAY_TEAM_FIELD_GOALS_ACC | FLOAT          | FLOAT       | Skuteczność rzutów z gry drużyny gości w meczu | -1            |
| HOME_TEAM_2_P_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów za 2 punkty przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_2_P_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów za 2 punkty przez drużynę gości w meczu | -1            |
| HOME_TEAM_2_P_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów za 2 punkty przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_2_P_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów za 2 punkty przez drużynę gości w meczu | -1            |
| HOME_TEAM_2_P_ACC | FLOAT          | FLOAT       | Skuteczność rzutów za 2 punkty drużyny gospodarzy w meczu | -1            |
| AWAY_TEAM_2_P_ACC | FLOAT          | FLOAT       | Skuteczność rzutów za 2 punkty drużyny gości w meczu | -1            |
| HOME_TEAM_3_P_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów za 3 punkty przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_3_P_FIELD_GOALS_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów za 3 punkty przez drużynę gości w meczu | -1            |
| HOME_TEAM_3_P_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów za 3 punkty przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_3_P_FIELD_GOALS_MADE | INT          | INT       | Liczba trafionych rzutów za 3 punkty przez drużynę gości w meczu | -1            |
| HOME_TEAM_3_P_ACC | FLOAT          | FLOAT       | Skuteczność rzutów za 3 punkty drużyny gospodarzy w meczu | -1            |
| AWAY_TEAM_3_P_ACC | FLOAT          | FLOAT       | Skuteczność rzutów za 3 punkty drużyny gości w meczu | -1            |
| HOME_TEAM_FT_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów wolnych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_FT_ATTEMPTS | INT          | INT       | Liczba oddanych rzutów wolnych przez drużynę gości w meczu | -1            |
| HOME_TEAM_FT_MADE | INT          | INT       | Liczba trafionych rzutów wolnych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_FT_MADE | INT          | INT       | Liczba trafionych rzutów wolnych przez drużynę gości w meczu | -1            |
| HOME_TEAM_FT_ACC | FLOAT          | FLOAT       | Skuteczność rzutów wolnych drużyny gospodarzy w meczu | -1            |
| AWAY_TEAM_FT_ACC | FLOAT          | FLOAT       | Skuteczność rzutów wolnych drużyny gości w meczu | -1            |
| HOME_TEAM_OFF_REBOUNDS | INT          | INT       | Liczba ofensywnych zbiórek zdobytych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_OFF_REBOUNDS | INT          | INT       | Liczba ofensywnych zbiórek zdobytych przez drużynę gości w meczu | -1            |
| HOME_TEAM_DEF_REBOUNDS | INT          | INT       | Liczba defensywnych zbiórek zdobytych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_DEF_REBOUNDS | INT          | INT       | Liczba defensywnych zbiórek zdobytych przez drużynę gości w meczu | -1            |
| HOME_TEAM_REBOUNDS_TOTAL | INT          | INT       | Łączna liczba zbiórek zdobytych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_REBOUNDS_TOTAL | INT          | INT       | Łączna liczba zbiórek zdobytych przez drużynę gości w meczu | -1            |
| HOME_TEAM_ASSISTS | INT          | INT       | Liczba asyst wykonanych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_ASSISTS | INT          | INT       | Liczba asyst wykonanych przez drużynę gości w meczu | -1            |
| HOME_TEAM_BLOCKS | INT          | INT       | Liczba zablokowanych rzutów dokonanych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_BLOCKS | INT          | INT       | Liczba zablokowanych rzutów dokonanych przez drużynę gości w meczu | -1            |
| HOME_TEAM_TURNOVERS | INT          | INT       | Liczba strat popełnionych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_TURNOVERS | INT          | INT       | Liczba strat popełnionych przez drużynę gości w meczu | -1            |
| HOME_TEAM_STEALS | INT          | INT       | Liczba przechwytów dokonanych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_STEALS | INT          | INT       | Liczba przechwytów dokonanych przez drużynę gości w meczu | -1            |
| HOME_TEAM_PERSONAL_FOULS | INT          | INT       | Liczba przewinień osobistych popełnionych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_PERSONAL_FOULS | INT          | INT       | Liczba przewinień osobistych popełnionych przez drużynę gości w meczu | -1            |
| HOME_TEAM_TECHNICAL_FOULS | INT          | INT       | Liczba przewinień technicznych popełnionych przez drużynę gospodarzy w meczu | -1            |
| AWAY_TEAM_TECHNICAL_FOULS | INT          | INT       | Liczba przewinień technicznych popełnionych przez drużynę gości w meczu | -1            |

**Ograniczenia/Indeksy:**
- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- **Unikalny indeks**: `MATCH_ID` (zapobiega duplikatom dodatkowych statystyk dla tego samego meczu)

**Sposób generowania danych do tabeli**:
Dane do tabeli generowane są w ramach działania modułu **basketball_scrapper.py**
---

### BETS 
(Wszystkie możliwe do zrealizowania zakłady)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        | INT           | INT      | Klucz główny, automatycznie generowany            | AUTOMATYCZNIE GENEROWANE |
| *MATCH_ID*    | INT           | INT       | Klucz obcy, powiązanie z tabelą *matches* | NULL |
| *EVENT_ID*    | INT           | INT       | Klucz obcy, powiązanie z tabelą *events* | NULL |
| ODDS          | FLOAT         | >= 1.0 | Kurs danego zdarzenia | NULL |
| EV            | FLOAT         | Teoretycznie (-inf, +inf), ale z reguły sensownie wartości są do [-1, 1]          | Sposób obliczania:  ustalone prawdopodobieństwo zdarzenia * maksymalny kurs od bukmacherów - 1. Wartości > 0 uznawane są jako "Interesujące" z perspektywy gracza                   | NULL |
| *BOOKMAKER*   | INT           | INT       | Klucz obcy, powiązanie z tabelą *bookmakers* | NULL |
| OUTCOME       | INT           | {0, 1}    | 1 jeśli zakład wygrany, 0 jeśli przegrany | NULL (to istotne) |
| CUSTOM_BET       | INT           | {0, 1}    | 0 jeśli zakład wygenerowany przez model, 1 jeśli zakład dodany ręcznie przez użytkownika | 0 |
| *MODEL_ID* | INT | INT  | Klucz obcy, powiązanie z tabelą *models* | NULL | 

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `EVENT_ID` → `events(ID)`
- Klucz obcy: `BOOKMAKER` → `bookmakers(ID)`
- Klucz obcy: `MODEL_ID` → `models(ID)`
- **Unikalny indeks**: `MATCH_ID`, `EVENT_ID`, `BOOKMAKER`, `ODDS` (zapobiega duplikatom zakładów dla tego samego meczu, zdarzenia i bukmachera)

**Sposób generowania danych do tabeli**:

Dane do tabeli naliczane są w funkcji **bet_all.py**

---

### BOOKMAKERS 
(Wszyscy bukmacherzy brani pod uwagę w ramach badania)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID bukmachera            | AUTOMATYCZNIE GENEROWANY            |
| NAZWA         |  VARCHAR(45)       | STRING    |   Nazwa bukmachera         | NULL             |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### CONFERENCE_DIVISIONS
(Dywizje przypisane do konferencji (dotyczy lig północnoamerykańskich))
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:            |
| **ID**        |  INT          | INT       | ID przypisania    | AUTOMATYCZNIE GENEROWANY            |
| *CONFERENCE_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *conferences* | NULL |
| *DIVISION_ID* | INT           | INT       | Klucz obcy, powiązanie z tabelą *divisions* | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `CONFERENCE_ID` → `conferences(ID)`
- Klucz obcy: `DIVISION_ID` → `divisions(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### CONFERENCES
(Podział lig (głównie północnoamerykańskich) na konferencje)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:            |
| **ID**        |  INT          | INT       | ID przypisania    | AUTOMATYCZNIE GENEROWANY            |
| *LEAGUE_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *leagues* | NULL |
| NAME | VARCHAR(45)          | STRING       | Nazwa konferencji| NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `LEAGUE_ID` → `leagues(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### COUNTRIES 
(Kraje, z których pochodzą analizowane ligi)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID kraju           | AUTOMATYCZNIE GENEROWANY            |
| NAME | VARCHAR(45) | STRING | Nazwa kraju (PL) | NULL |
| SHORT | VARCHAR(3) |  STRING | Skrót kraju (max 3 litery) | NULL |
| EMOJI | VARCHAR(45) | STRING | Napis, który reprezentuje flagę kraju w postaci emotki | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### DIVISION_TEAMS
(Przydział drużyn do dywizji)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:            |
| **ID**        |  INT          | INT       | ID przypisania    | AUTOMATYCZNIE GENEROWANY            |
| *TEAM_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *teams* | NULL |
| *DIVISION_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *divisions* | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `TEAM_ID` → `teams(ID)`
- Klucz obcy: `DIVISION_ID` → `divisions(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### DIVISIONS
(Dywizje w ligach północnoamerykańskich)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:            |
| **ID**        |  INT          | INT       | ID przypisania    | AUTOMATYCZNIE GENEROWANY            |
| *LEAGUE_ID* | INT         | INT       | Klucz obcy, powiązanie z tabelą *leagues* | NULL |
| NAME | VARCHAR(45)          | STRING       | Nazwa dywizji| NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `LEAGUE_ID` → `leagues(ID)`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### EVENT_FAMILIES
(Rodziny typów zdarzeń w systemie)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID rodziny zdarzeń           | AUTOMATYCZNIE GENEROWANY            |
| *SPORT_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *sports* | NULL |
| NAME | VARCHAR(45) | STRING | Nazwa rodziny zdarzeń (np. REZULTAT, OU, BTTS, EXACT) | NULL |
| DESCRIPTION | VARCHAR(200) | STRING | Opis rodziny zdarzeń | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `SPORT_ID` → `sports(ID)`
- **Unikalny indeks**: `SPORT_ID`, `NAME` (zapobiega duplikatom nazw rodzin w ramach tego samego sportu)

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### EVENT_FAMILY_MAPPINGS
(Mapowania zdarzeń do rodzin zdarzeń)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID mapowania           | AUTOMATYCZNIE GENEROWANY            |
| *EVENT_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *events* | NULL |
| *EVENT_FAMILY_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *event_families* | NULL |

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

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID powiązania           | AUTOMATYCZNIE GENEROWANY            |
| *MODEL_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *models* | NULL |
| *EVENT_FAMILY_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *event_families* | NULL |

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

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID zdarzenia           | AUTOMATYCZNIE GENEROWANY            |
| NAME | VARCHAR(45) | STRING | Nazwa zdarzenia | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### EVENTS_PARLAY 
(Szczegóły kuponów)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID zdarzenia           | AUTOMATYCZNIE GENEROWANY            |
| *PARLAY_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *gambler_parlays* | NULL |
| *BET_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *bets*  | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PARLAY_ID` → `gambler_parlays(ID)`
- Klucz obcy: `BET_ID` → `bets(ID)`
**Sposób generowania danych do tabeli**:

Aktualnie dane do tabeli dodawane są tylko i wyłącznie **ręcznie** (w przyszłości przewidywane jest dodawaniez zdarzeń poprzez moduł "Kupony Graczy")

---

### FINAL_PREDICTIONS
(Wskaźniki predykcji ostatecznych)

| POLE            | DOMENA   | ZAKRES   | UWAGI                                                      | WARTOŚĆ DOMYŚLNA |
| :---:           | :---:    | :---:    | :---:                                                      | :---:            |
| **ID**          | INT      | INT>0    | Klucz główny, automatycznie generowany                     | AUTOMATYCZNIE GENEROWANY |
| *PREDICTIONS_ID*| INT      | INT>0    | Klucz obcy, powiązanie z tabelą *predictions*              | NULL             |
| CREATED_AT      | TIMESTAMP| TIMESTAMP| Data utworzenia wpisu (timestamp generowany automatycznie) | CURRENT_TIMESTAMP |
| OUTCOME       | INT           | {0, 1} | Wynik predykcji (0 - predykcja niepoprawna, 1 - predykcja poprawna) | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PREDICTIONS_ID` → `predictions(ID)`
- **Unikalny indeks:** `PREDICTIONS_ID` (zapobiega duplikatom predykcji)

**Sposób generowania danych do tabeli**:

Dane do tabeli generowane są w ramach działania modułu **prediction_module.py**

---

### FOOTBALL_PLAYER_STATS
(Boxscore meczowy w piłce nożnej)

| POLE            | DOMENA   | ZAKRES   | UWAGI                                                          | WARTOŚĆ DOMYŚLNA |
| :---:           | :---:    | :---:    | :---:                                                          | :---:            |
| **ID**          | INT      | INT>0    | Klucz główny, automatycznie generowany                         | AUTOMATYCZNIE GENEROWANY |
| *MATCH_ID*      | INT      | INT>0    | Klucz obcy, powiązanie z tabelą *matches*                      | NULL             |
| *PLAYER_ID*     | INT      | INT>0    | Klucz obcy, powiązanie z tabelą *players*                      | NULL             |
| *TEAM_ID*       | INT      | INT>0    | Klucz obcy, powiązanie z tabelą *teams*                        | NULL             |
| GOALS           | INT      | INT>0    | Liczba goli strzelonych przez zawodnika w meczu                | -1               |
| ASSISTS         | INT      | INT>0    | Liczba asyst wykonanych przez zawodnika w meczu                | -1               |
| RED_CARDS       | INT      | {0,1}    | Liczba czerwonych kartek otrzymanych przez zawodnika w meczu   | -1               |
| YELLOW_CARDS    | INT      | {0,1,2}  | Liczba żółtych kartek otrzymanych przez zawodnika w meczu      | -1               |
| CORNERS_WON     | INT      | INT>0    | Liczba rzutów rożnych wygranych przez zawodnika                | -1               |
| SHOTS           | INT      | INT>0    | Liczba strzałów oddanych przez zawodnika                       | -1               |
| SHOTS_ON_TARGET | INT      | INT>0    | Liczba strzałów na bramkę oddanych przez zawodnika             | -1               |
| BLOCKED_SHOTS   | INT      | INT>0    | Liczba zablokowanych strzałów przez zawodnika                  | -1               |
| PASSES          | INT      | INT>0    | Liczba wszystkich podań wykonanych przez zawodnika             | -1               |
| CROSSES         | INT      | INT>0    | Liczba wrzutek wykonanych przez zawodnika                      | -1               |
| TACKLES         | INT      | INT>0    | Liczba wślizgów wykonanych przez zawodnika                     | -1               |
| OFFSIDES        | INT      | INT>0    | Liczba sytuacji, w których zawodnik znalazł się na pozycji spalonej  | -1               |
| FOULS_CONCEDED  | INT      | INT>0    | Liczba poprzełnionych fauli przez zawodnika                    | -1               |
| FOULS_WON       | INT      | INT>0    | Liczba fauli popełnionych na zawodniku                         | -1               |
| SAVES           | INT      | INT>0    | Liczba obronionych strzałów (dotyczy jedynie bramkarzy)        | -1               |


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

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID dodatkowych danych meczowych w piłce          | AUTOMATYCZNIE GENEROWANY            |
| *MATCH_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *matches* | NULL | 
| OT | INT | {0,1} | Flaga, czy w meczu odbyła się dogrywka (teoretycznie z aktualną strukturą bazy to flaga zawsze będzie równa 1, jednak w przyszłości może się to zmienić!) | 1 |
| PEN | INT | {0,1} | Flaga, czy w meczu odbyła się seria jedynastek | 0 |
| home_team_goals_after_ot | INT | INT | Liczba bramek strzelona przez drużynę gospodarzy podczas regularnego czasu gry + podczas dogrywki | NULL |
| away_team_goals_after_ot | INT | INT | Liczba bramek strzelona przez drużynę gości podczas regularnego czasu gry + podczas dogrywki | NULL | 
| home_team_pen_score | INT | INT | Liczba trafionych karnych przez gospodarzy w ramach konkursu jedynastek | NULL |
| away_team_pen_score | INT | INT | Liczba trafionych karnych przez gości w ramach konkursu jedynastek | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`

**Sposób generowania danych do tabeli**:

Dane do tabeli **BĘDĄ** (jeszcze aktualnie nie są) naliczane w ramach scrapperów (głównie **scrapper.py** oraz **update_scrapper.py**)

---

### GAMBLER_PARLAYS
(kupony graczy)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID kuponu         | AUTOMATYCZNIE GENEROWANY        |
| *GAMBLER_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *gamblers* | NULL |
| PARLAY_ODDS | FLOAT | > 1 | Kurs całego kuponu (mnożenie kursów wszystkich zdarzeń) | NULL |
| STAKE | FLOAT | > 0 | Wkład gracza (ile pieniędzy postawił w ramach kuponu), w unitach | 1 |
| SETTLED | INT | {0,1} | Czy kupon rozliczony (0 - nie, 1 - tak) | 0 |
| PARLAY_OUTCOME | INT | {0,1} | Wynik kuponu (0 - przegrany, 1 - wygrany) | 0 |
| PROFIT | FLOAT | {-stake, parlay_odds * stake - stake} | Zysk / Strata gracza w zależności od tego, czy kupon został wygrany czy przegrany. Jeśli kupon wygrany, profitem nazywamy iloczyn stawki oraz kursu kuponu pomniejszonego o jedną stawkę (wkład początkowy nie jest w żadnym wypadku profitem z zakładu). Jeśli kupon przegrany, gracz traci poświęconą stawkę | 0 |
| CREATION_DATE | TIMESTAMP | TIMESTAMP | Data utworzenia kuponu | CURRENT_TIMESTAMP |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `GAMBLER_ID` → `gamblers(ID)`

**Sposób generowania danych do tabeli**:

Aktualnie dane do tabeli dodawane są tylko i wyłącznie **ręcznie** (w przyszłości przewidywane jest dodawaniez zdarzeń poprzez moduł "Kupony Graczy"). Dane aktualizowane są w ramach modułu **recalc_parlay.py** 

---

### GAMBLERS 
(zadeklarowani gracze) 

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID kuponu         | AUTOMATYCZNIE GENEROWANY        |
| GAMBLER_NAME | VARCHAR(30) | STRING | Nazwa typera | NULL |
| PARLAYS_PLAYED | INT | >= 0 | Liczba kuponów zagranych przez typera | 0 |
| PARLAYS_WON | INT | >= 0 | Liczba kuponów wygranych przez typera | 0 |
| BALANCE | FLOAT | FLOAT | Aktualny stan konta typera | 0 |
| ACTIVE | INT | {0, 1} | Flaga, czy gracz jest aktywny (0 - nie, 1 - tak) | 1 |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są **ręcznie** (Możliwe rozszerzenie na tworzenie nowych typerów przez innych ludzi (np. tworzenie kont w serwisie), jednak jest to BARDZO przyszłościowe rozszerzenie)

---

### HOCKEY_MATCH_EVENTS 
(zdarzenia występujące w danym meczu hokejowym)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID kuponu         | AUTOMATYCZNIE GENEROWANY        |
| *EVENT_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *events*  | NULL |
| *MATCH_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *matches*  | NULL |
| *TEAM_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| *PLAYER_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *players*  | NULL |
| PERIOD | INT | {1,2,3,4,5} | Tercja, w której zdarzenie miało miejsce. Jeśli PERIOD = 4 to zdarzenie miało miejsce w dogrywce, jeśli 5 - w rzutach karnych| NULL |
| EVENT_TIME| VARCHAR(9) | <20:00:00 | Czas w tercji, w którym zdarzenie miało miejsce. W karnych rundy konwertowane są na czas w następujący sposób: 1 runda karnych -> 00:00:01, 2 runda karnych -> 00:00:02, etc. | NULL |
| PP_FLAG | INT | {0,1} | Czy gol padł w przewadze? (1 - tak, 0 - nie) | NULL |
| EN_FLAG | INT | {0,1} | Czy gol padł do pustej bramki? (1 - tak, 0 - nie) | NULL |
| DESCRPTION | VARCHAR(100) | STRING | Opis zdarzenia (np. kto asystował) | NULL |

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
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID statystyk danego zawodnika w danym meczu hokejowym         | AUTOMATYCZNIE GENEROWANY        |
| *MATCH_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *matches*  | NULL |
| *PLAYER_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *players*  | NULL |
| *TEAM_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| GOALS | INT | >=0 | Liczba bramek strzelona przez hokeistę | NULL |
| ASSISTS | INT | >=0 | Liczba asysty zdobyta przez hokeistę  | NULL |
| POINTS | INT | >=0 | Liczba punktów kanadyjskich (GOALS + ASSISTS) | NULL |
| PLUS_MINUS | INT | INT | Indywidualna statystyka w hokeju na lodzie, która stanowi punktację liczoną za przebywanie na lodzie w momencie zdobycia (+) i straty gola (-) przez drużynę zawodnika | NULL |
| PENALTY_MINUTES | INT | >=0 | Liczba minut spędzonych na ławce kar przez zawodnika | NULL |
| SOG | INT | >=0 | Liczba CELNYCH strzałów na bramkę | NULL |
| BLOCKED | INT | >=0 | Liczba zablokowanych strzałów (zawodnik z pola) | NULL |
| SHOTS_ACC | FLOAT | [0,100]"%" | Celność strzałów | NULL |
| TURNOVERS | INT | >=0 | Liczba straconych "posiadań" przez zawodnika (utraty krążka wynikające z błędu własnego) | NULL |
| STEALS | INT | >=0 | Liczba przechwytów | NULL |
| FACEOFF | INT | >=0 | Liczba wznowień, w których zawodnik brał udział | NULL |
| FACEOFF_WON | INT | >=0 | Liczba wznowień wygranych przez zawodnika | NULL |
| FACEOFF_ACC | FLOAT | [0,100]"%" | Skuteczność wznowień | NULL |
| HITS | INT | >=0 | Liczba legalnych uderzeń wykonanych przez gracza | NULL |
| TOI | VARCHAR(9) |  >=0 | Czas spędzony przez gracza na lodzie (TOI = Time On Ice) | NULL |
| SHOTS_AGAINST | INT | >=0 | Liczba strzałów oddanych przez przeciwników na bramkę danego zawodnika  (TYLKO BRAMKARZE) | NULL |
| SHOTS_SAVED | INT | >=0 |  Liczba obronionych strzałów (TYLKO BRAMKARZE) | NULL |
| SAVES_ACC | INT | >=0 | Skuteczność obron (TYLKO BRAMKARZE) | NULL |
| TOI_STR | VARCHAR(10) | STRING | Prezentacja TOI w formie stringa (były problemy z formtowaniem więc załatwiłem to przez dodatkową kolumnę, nieoptymalnie, ale na razie niech będzie) | NULL |

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
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID dodatkowych statystyk hokejowych dla danego meczu         | AUTOMATYCZNIE GENEROWANY        |
| *MATCH_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *matches*  | NULL |
| *PLAYER_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *players*  | NULL |
| *TEAM_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| POSITION | VARCHAR(5) | {G, D, LW, C, RW} | Pozycja zawodnika na lodzie (G - bramkarz, D - obrońca, LW - lewy skrzydłowy, C - środkowy, RW - prawy skrzydłowy) | NULL |
| LINE | INT | {1,2,3,4} | Linia, w której gra zawodnik | NULL |
| NUMBER | INT | [0, 99] | Numer na koszulce zawodnika | NULL |

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
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID dodatkowych statystyk hokejowych dla danego meczu         | AUTOMATYCZNIE GENEROWANY        |
| *MATCH_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *matches*  | NULL |
| OT | INT | {0,1} | Czy była dogrywka? (0 - nie, 1 - tak) | NULL |
| SO | INT | {0,1} | Czy były rzuty karne (0 - nie, 1 - tak, tylko sezon zasadniczy) | NULL |
| home_team_pp_goals | INT | >= 0 | Liczba bramek zdobytych w przewadze przez drużynę gospodarzy | NULL |
| away_team_pp_goals | INT | >= 0 | Liczba bramek zdobytych w przewadze przez drużynę gości | NULL |
| home_team_sh_goals | INT | >= 0 | Liczba bramek zdobytych w osłabieniu przez drużynę gospodarzy | NULL |
| away_team_sh_goals | INT | >= 0 | Liczba bramek zdobytych w osłabieniu przez drużynę gości | NULL |
| home_team_shots_acc | FLOAT | [0,100] | Skuteczność strzałów drużyny gospodarzy liczona jako liczba bramek dzielona na liczbę strzałów celnych | NULL |
| away_team_shots_acc | FLOAT | [0,100] | Skuteczność strzałów drużyny gości liczona jako liczba bramek dzielona na liczbę strzałów celnych | NULL |
| home_team_saves | INT | >= 0 | Liczba strzałów obronionych przez gospodarzy | NULL |
| away_team_saves | INT | >= 0 | Liczba strzałów obronionych przez gości | NULL |
| home_team_saves_acc| FLOAT | [0,100] | Skuteczność obron drużyny gospodarzy liczona jako liczba obron dzielona na liczbę strzałów celnych | NULL |
| away_team_saves_acc | FLOAT | [0,100] | Skuteczność obron drużyny gości liczona jako liczba obron dzielona na liczbę strzałów celnych | NULL |
| home_team_pp_acc | FLOAT | [0,100] | Skuteczność gier w przewadze drużyny gospodarzy liczona jako liczba strzelonych bramek w przewadze przez liczbę przewag | NULL |
| away_team_pp_acc | FLOAT | [0,100] | Skuteczność gier w przewadze drużyny gości liczona jako liczba strzelonych bramek w przewadze przez liczbę przewag | NULL |
| home_team_pk_acc | FLOAT | [0,100] | Skuteczność gier w osłabieniu drużyny gospodarzy liczona jako liczba straconych bramek w osłabieniu przez liczbę osłabień | NULL |
| away_team_pk_acc | FLOAT | [0,100]| Skuteczność gier w osłabieniu drużyny gości liczona jako liczba straconych bramek w osłabieniu przez liczbę osłabień | NULL |
| home_team_faceoffs | INT | >= 0 | Liczba wygranych wznowień przez gospodarzy | NULL |
| away_team_faceoffs | INT | >= 0 | Liczba wygranych wznowień przez gości | NULL |
| home_team_faceoffs_acc | FLOAT | [0,100] | Skuteczność wygranych wznowień przez gospodarzy | NULL |
| away_team_faceoffs_acc | FLOAT | [0,100]| Skuteczność wygranych wznowień przez gości | NULL |
| home_team_hits | INT | >= 0 | Liczba uderzeń wykonanych przez gospodarzy | NULL |
| away_team_hits | INT | >= 0 | Liczba uderzeń wykonanych przez gości | NULL |
| home_team_to | INT | >= 0 | Liczba strat popełnionych przez gospodarzy | NULL |
| away_team_to | INT | >= 0 | Liczba strat popełnionych przez gości | NULL |
| home_team_en | INT | >= 0 | Liczba goli zdobytych na pustą bramkę (en - empty net) przez gospodarzy | NULL |
| away_team_en | INT | >= 0 | Liczba goli zdobytych na pustą bramkę (en - empty net) przez gości | NULL |
| OTwinner | INT | {1,2,3} | Wynik dogrywki (1 - gospodarz wygrał, 2 - gość wygrał, 3 - rozstrzygnięcie dopiero w karnych) | NULL |
| SO winner | INT | {0,1,2} | Wynik karnych (0 - brak karnych, 1 - gospdoarz wygrał, 2 - gość wygrał) | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są bezpośrednio przy pomocy modułu **nhl_all_scraper.py**

---

### HOCKEY_ROSTERS
(aktualne składy drużyn hokejowych)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID przewidywane składu         | AUTOMATYCZNIE GENEROWANY        |
| *PLAYER_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *players*  | NULL |
| *TEAM_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| LINE | INT | {1,2,3,4} | Linia, w której gra zawodnik | NULL |
| NUMBER | INT | [0, 99] | Numer na koszulce zawodnika | NULL |
| POSITION | VARCHAR(5) | {G, D, LW, C, RW} | Pozycja zawodnika na lodzie (G - bramkarz, D - obrońca, LW - lewy skrzydłowy, C - środkowy, RW - prawy skrzydłowy) | NULL |
| PP | INT | {0, 1, 2} | Czy zawodnik jest przypisany do gry w przewadze? (1 - przypisany do pierwszej linii przewagi (1PP), 2 - przypisany do drugiej linii przewagi (PP2), 0 - nieprzypisany do przewagi) | NULL | 
|IS_INJURED| INT | {0, 1} | Czy zawodnik jest kontuzjowany? (0 - nie, 1 - tak) | NULL |

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
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID ligi         | AUTOMATYCZNIE GENEROWANY        |
| *SPORT_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *sports*  | NULL |
| *COUNTRY* | INT | INT | Klucz obcy, powiązanie z tabelą *countries* | NULL |
| *CURRENT_SEASON_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *seasons*  | NULL |
| NAME | VARCHAR(45) | STRING | Nazwa drużyny w języku polskim | NULL |
| LAST_UPDATE | DATETIME | DATE | Ostatnia aktualizacja danych ligowych (jakichkolwiek, nawet fauli w meczu X) | NULL |
| ACTIVE | INT | {0, 1} | Czy liga aktualnie analizowana przez system? (0 - nie, 1 - tak) | NULL |
| TIER | INT | {1, 2, 100, 101, 102} | Poziom rozgrywky ligi (100 - Liga Mistrzów, 101 - Liczba Europy, 102 - Liga Konferencji) | NULL |

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
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID meczu         | AUTOMATYCZNIE GENEROWANY        |
| *LEAGUE* | INT | INT | Klucz obcy, powiązanie z tabelą *leagues* | NULL |
| *SEASON* | INT | INT | Klucz obcy, powiązanie z tabelą *seasons*  | NULL |
| *HOME_TEAM* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| *AWAY_TEAM* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| *SPORT_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *sports* | NULL
| GAME_DATE | DATETIME | DATETIME | Termin rozgrywanego meczu | NULL |
| ROUND | INT | [0,100] ^ [900,1000] | Runda, w ramach której rozgegrano mecz. Runda 100 jako runda specjalna dla lig, które nie posiadają jednoznacznego podziału na rundy (NHL, MLS). Rundy od 900 to rundy specjalne zawierające informację o momencie fazy pucharowej, w której mecz został rozegrany (wsparcie dla meczów max 1/32 finału, BO7). Dokładny opis znajduje się w komentarzu do pola w bazie danych. | NULL |
| RESULT | VARCHAR(1) | {'X', '0', '1', '2'} | Wynik spotkania ('0' - brak rezultatu w bazie / jeszcze nie rozegrano, '1' - gospodarz wygrał, '2' - gość wygrał, 'X' - remis ) | NULL |
| HOME_TEAM_GOALS | INT | INT | Liczba bramek zdobyta przez gospodarza | NULL |
| AWAY_TEAM_GOALS | INT | INT | Liczba bramek zdobyta przez gościa | NULL |
| HOME_TEAM_XG | FLOAT | >=0.00 | Współczynnik expected goals(xG) dla drużyny gospodarza| NULL |
| AWAY_TEAM_XG | FLOAT | >=0.00 | Współczynnik expected goals(xG) dla drużyny gościa | NULL |
| HOME_TEAM_BP | INT | INT | Posiadanie piłki gospodarza | NULL |
| AWAY_TEAM_BP | INT | INT | Posiadanie piłki gościa | NULL |
| HOME_TEAM_SC | INT | INT | Liczba strzałów (wszystkich) gospodarza | NULL |
| AWAY_TEAM_SC | INT | INT | Liczba strzałów (wszystkich) gościa | NULL |
| HOME_TEAM_SOG | INT | INT | Liczba strzałów NA BRAMKĘ gospodarza | NULL |
| AWAY_TEAM_SOG | INT | INT | Liczba strzałów NA BRAMKĘ gościa | NULL |
| HOME_TEAM_FK | INT | INT | Liczba rzutów wolnych wykonanych przez gospodarza | NULL |
| AWAY_TEAM_FK | INT | INT | Liczba rzutów wolnych wykonanych przez gościa | NULL |
| HOME_TEAM_CK | INT | INT | Liczba rzutów rożnych wykonanych przez gospodarza | NULL |
| AWAY_TEAM_CK | INT | INT | Liczba rzutów rożnych wykonanych przez gościa | NULL |
| HOME_TEAM_OFF | INT | INT | Liczba spalonych popełnionych przez gospodarza | NULL |
| AWAY_TEAM_OFF | INT | INT | Liczba spalonych popełnionych przez gościa | NULL |
| HOME_TEAM_FOULS | INT | INT | Liczba fauli popełnionych przez gospodarza | NULL |
| AWAY_TEAM_FOULS | INT | INT | Liczba fauli popełnionych przez gościa | NULL |
| HOME_TEAM_YC | INT | INT | Liczba żółtych kartek gospodarza | NULL |
| AWAY_TEAM_YC | INT | INT | Liczba żółtych kartek gościa | NULL |
| HOME_TEAM_RC | INT | INT | Liczba czerwonych kartek gospodarza | NULL |
| AWAY_TEAM_RC | INT | INT | Liczba czerwonych kartek gościa | NULL |

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

### MODELS
(lista stworzonych modeli predykcyjnych)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        | INT           | INT       | Klucz główny, automatycznie generowany | AUTOMATYCZNIE GENEROWANE |
| NAME          | VARCHAR(50)   | STRING    | Nazwa modelu predykcyjnego | NULL |
| ACTIVE        | INT           | {0, 1}    | Flaga aktywności modelu (0 - nieaktywny, 1 - aktywny). Tylko aktywne modele są używane do generowania zakładów | NULL |
| *SPORT_ID*    | INT           | INT       | Klucz obcy, powiązanie z tabelą *sports* | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Indeks unikalny: `ID_UNIQUE` (`ID`)
- Klucz obcy: `SPORT_ID` → `sports(ID)` (ograniczenie `MODELS_SPORTS`)
- Indeks: `MODELS_SPORTS_idx` (`SPORT_ID`)

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są **ręcznie** w ramach konfiguracji nowych modeli predykcyjnych. Każdy nowy model musi być dodany do tej tabeli przed pierwszym użyciem.

---

### ODDS 
(pobrane kursy dla danego meczu dla danego zdrarzenia)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID dodatkowych statystyk hokejowych dla danego meczu         | AUTOMATYCZNIE GENEROWANY        |
| *MATCH_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *matches*  | NULL |
| *BOOKMAKER* | INT | INT | Klucz obcy, powiązanie z tabelą *bookmakers* | NULL |
| *EVENT* | INT | INT | Klucz obcy, powiązanie z tabelą *events*  | NULL |
| ODDS | FLOAT | >= 1 | Kurs dla danego wpisu | NULL | 

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `BOOKMAKER` → `bookmakers(ID)`
- Klucz obcy: `EVENT` → `events(ID)`
- **Unikalny indeks:** `(MATCH_ID, BOOKMAKER, EVENT)` – gwarantuje unikalność zakładu dla każdego meczu, bukmachera oraz zdarzenia (bez sensu tu byłyby duplikaty)

**Sposób generowania danych do tabeli**:

Dane do tabeli dodawane są w ramach działania modułu **odds_scrapper.py**

---

### PLAYERS
(lista graczy)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID zawodnika         | AUTOMATYCZNIE GENEROWANY        |
| *CURRENT_CLUB* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| *CURRENT_COUNTRY* | INT | INT | Klucz obcy, powiązanie z tabelą *countries* | NULL |
| *SPORTS_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *sports* | NULL |
| FIRST_NAME | VARCHAR(45) | STRING | Imię zawodnika | NULL |
| LAST_NAME | VARCHAR(45) | STRING | Nazwisko zawodnika | NULL |
| COMMON_NAME | VARCHAR(60) | STRING | Nazwisko +_ Pierwsza litera imienia zawodnika (jeśli są powtórki - istnieją wyjątki, które ciężko umieścić w tabeli - należy sprawdzić samemu w źródłach) | NULL |
| POSITION | VARCHAR(5) | {G, D, LW, C, RW} | Pozycja zawodnika na lodzie (G - bramkarz, D - obrońca, LW - lewy skrzydłowy, C - środkowy, RW - prawy skrzydłowy) | NULL |
| EXTERNAL_ID | VARCHAR(20) | STRING | ID zawodnika w NHL API | NULL |
| EXTERNAL_FLASH_ID | VARCHAR(20) | STRING | ID zawodnika na flashscorze | NULL |
| ACTIVE | INT | {0, 1} | Flaga, czy gracz jest aktywny (0 - nie, 1 - tak) | 1 |

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

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT>0          | ID zawodnika        | AUTOMATYCZNIE GENEROWANY        |
| *MATCH_ID*    | INT           | INT>0       | Klucz obcy, powiązanie z tabelą *matches* | NULL |
| *EVENT_ID*    | INT           | INT>0       | Klucz obcy, powiązanie z tabelą *events* | NULL |
| *MODEL_ID*    | INT           | INT>0       | Klucz obcy, powiązanie z tabelą *models* | NULL |
| VALUE         | FLOAT         | [0,1] | Prawdopodobieństwo danego zdarzenia | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `MATCH_ID` → `matches(ID)`
- Klucz obcy: `EVENT_ID` → `events(ID)`
- Klucz obcy: `MODEL_ID` → `models(ID)`
- **Unikalny indeks:** `(MATCH_ID, EVENT_ID, MODEL_ID)` – gwarantuje unikalność predykcji dla każdego zdarzenia w danym meczu i modelu

**Sposób generowania danych do tabeli**:

Dane naliczane w ramach modułu **main.py**

---

### SEASONS 
(Tabela z sezonami)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID sezonu       | AUTOMATYCZNIE GENEROWANY        |
| YEARS | VARCHAR(10) | STRING | Lata sezonu, zawsze w tej samej formie: Rok startu + "/" + dwie ostatnie cyfry następnego roku (wyjątek dla sezonów typu 2099/2100)(przykład: 2024/25) | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### SPECIAL_ROUNDS
(Tabela z nazwami rund specjalnych)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID rundy specjalnej      | AUTOMATYCZNIE GENEROWANY        |
| NAME | VARCHAR(45) | STRING | Nazwa rundy specjalnej (np. finał, mecz numer 1). Rundy specjalne wspierają wszystkie typy rozgrywek aż do BO5 | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:

Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### SPORTS 
(Tabela z analizowanymi sportami)

| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID sportu       | AUTOMATYCZNIE GENEROWANY        |
| NAME | VARCHAR(45) | STRING | Nazwa zwyczajowa sportu | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`

**Sposób generowania danych do tabeli**:
Aktualne dane do tabeli zostały dodane **ręcznie** w ramach jednorazowego wgrania predefiniowanego skryptu

---

### TEAMS 
(Tabela z drużynami)
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID drużyny      | AUTOMATYCZNIE GENEROWANY        |
| *COUNTRY* | INT | INT | Klucz obcy, powiązanie z tabelą *countries* | NULL |
| *SPORT_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *sports* | NULL |
| NAME | VARCHAR(50) | STRING | Nazwa drużyn | NULL |
| SHORTCUT | VARCHAR(5) | STRING | Skrótowa nazwa drużyny (z reguły nie więcej niż 3 litery, aczkolwiek bywają wyjątki) | NULL |

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
| POLE          | DOMENA        | ZAKRES    | UWAGI             | WARTOŚC DOMYŚLNA |
| :---:         |  :---:        | :---:     | :---:             | :---:             |
| **ID**        |  INT       | INT    | ID transferu      | AUTOMATYCZNIE GENEROWANY        |
| *PLAYER_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *players*  | NULL |
| *OLD_TEAM_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| *NEW_TEAM_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *teams*  | NULL |
| *SEASON_ID* | INT | INT | Klucz obcy, powiązanie z tabelą *seasons*  | NULL |

**Ograniczenia/Indeksy:**

- Klucz główny: `ID`
- Klucz obcy: `PLAYER_ID` → `players(ID)`
- Klucz obcy: `OLD_TEAM_ID` → `teams(ID)`
- Klucz obcy: `NEW_TEAM_ID` → `teams(ID)`
- Klucz obcy: `SEASON_ID` → `seasons(ID)`

**Sposób generowania danych do tabeli**:  

Dane do tabeli dodawane AKTUALNIE tylko w ramach **nhl_get_players.py** (potencjalne rozszerzenia wkrótce)
















