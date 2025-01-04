# OFICJALNA DOKUMENTACJA BAZODANOWA
###### Ostatnia data modyfikacji: 09.12.2024

## Opis struktury bazy 

## Wszystkie tabele w bazie danych
- bets (Wszystkie możliwe do zrealizowania zakłady)
- bookmakers (Wszyscy bukmacherzy brani pod uwagę w ramach badania)
- countries (Kraje, z których pochodzą analizowane ligi)
- events (Typy zakładów)
- events_parlays (Szczegóły kuponów)
- final_predictions (Końcowe predyckje, dla każdego meczu, dla każdego zdarzenia)
- football_special_round_add (rundy specjalne w piłce - dodatkowe informacje (głównie chodzi o puchary))
- gambler_parlays (kupony graczy)
- gamblers (zadeklarowani gracze)
- hockey_match_events (zdarzenia występujące w danym meczu hokejowym)
- hockey_match_player_stats (statystyki każdego gracza w danym meczu)
- hockey_matches_add (dodatkowe statystyki specyficzne dla meczu hokejowego)
- hockey_rosters (składy drużyn hokejowych)
- leagues (spis analizowanych lig)
- matches (wszystkie analizowane mecze)
- odds (pobrane kursy dla danego meczu dla danego zdrarzenia)
- players (lista graczy)
- predictions (WSZYSTKIE predykcje dla każdego zdarzenia)
- seasons (Tabela z sezonami)
- sports (Tabela z analizowanymi sportami)
- teams (Tabela z drużynami)
- transfers (Zapis transferów zawodników między klubami)

## Opisy poszczególnych tabel
- BETS (Wszystkie możliwe do zrealizowania zakłady)

| POLE          | DOMENA        | ZAKRES    | UWAGI             |
| :---:         |  :---:        | :---:     | :---:             |
| **ID**        | INT           | INT       | Klucz główny, automatycznie generowany            |
| *MATCH_ID*    | INT           | INT       | Klucz obcy, powiązanie z tabelą *matches* |
| *EVENT_ID*    | INT           | INT       | Klucz obcy, powiązanie z tabelą *events* |
| ODDS          | FLOAT         | ODDS >= 1 | Kurs danego zdarzenia |
| EV            | FLOAT         |           |                       |
| *BOOKMAKER*   | INT           | INT       | Klucz obcy, powiązanie z tabelą *bookmakers* |
| OUTCOME       | INT           | {0, 1}    | 1 jeśli zakład wygrany, 0 jeśli przegrany |

- BOOKMAKERS


## UWAGA: SPRAWA NHL
W tabeli MATCHES dla hokeja mamy takie dane:
- 

- league - liga
- season - sezon
- home_team - ID gospodarza
- away_team - ID gościa
- game_date - data meczu
- home_team_goals - liczba bramek gospodarza (REGULARNY CZAS)
- away_team-goals - liczba bramek gościa (REGULARNY CZAS)
- home_team_sc - strzały gospodarza (WSZYSTKIE, WŁĄCZNIE Z DOGRYWKĄ)
- away_team_sc - strzały gościa (WSZYSTKIE, WŁĄCZNIE Z DOGRYWKĄ)
- home_team_sog - strzały na bramkę oddane przez gospodarza (WŁĄCZNIE Z DOGRYWKĄ)
- away_team_sog - strzały na bramkę oddane przez gościa (WŁĄCZNIE Z DOGRYWKĄ)
- home_team_fk - czas wszystkich kar gospodarza
- away_team_fk - czas wszystkich kar gościa
- home_team_fouls - liczba wszystkich kar gospodarza
- away_team-fouls - liczba wszystkich kar gościa
- round - runda, w której odbył się mecz (JAK TO DZIAŁA - OPIS JEST W BAZIE)
- result - rezultat spotkania (OPIS W BAZIE)