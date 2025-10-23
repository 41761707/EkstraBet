# Scraper Koszykówki - Dokumentacja

## Opis modułu

Moduł `nba_all_scrapper.py` jest odpowiedzialny za pobieranie danych meczów koszykarskich z serwisu FlashScore. Bazuje na strukturze modułu hokejowego (`nhl_all_scraper.py`) i jest dostosowany do specyfiki danych koszykarskich. **Wykorzystuje dataclass'y zamiast słowników** dla lepszej organizacji kodu.

## Struktury danych (dataclass'y)

Moduł wykorzystuje następujące dataclass'y zdefiniowane w `utils.py`:

### 1. BasketballMatchData
Podstawowe dane meczu odpowiadające tabeli MATCHES:
- `league_id`, `season_id` - identyfikatory ligi i sezonu
- `home_team`, `away_team` - ID drużyn
- `match_date` - data meczu w formacie 'YYYY-MM-DD HH:MM'
- `home_team_score`, `away_team_score` - punkty drużyn
- `round` - numer rundy (100 dla sezonu regularnego)
- `result` - wynik (1=gospodarze, 2=goście, 0=remis)
- `status` - status meczu ('FT' = zakończony)

### 2. BasketballMatchStatsAdd
Dodatkowe statystyki meczowe (tabela BASKETBALL_MATCHES_ADD):
- Rzuty z gry: `*_field_goals_attempts/made/acc`
- Rzuty za 2 pkt: `*_2_p_field_goals_attempts/made/acc`
- Rzuty za 3 pkt: `*_3_p_field_goals_attempts/made/acc`
- Rzuty wolne: `*_ft_attempts/made/acc`
- Zbiórki: `*_off/def/total_rebounds`
- Pozostałe: `*_assists/blocks/steals/turnovers/fouls`

### 3. BasketballPlayerStats
Statystyki indywidualne zawodników (tabela BASKETBALL_MATCH_PLAYER_STATS):
- Podstawowe: `points`, `rebounds`, `assists`, `time_played`
- Rzuty: `field_goals_*`, `two_p_field_goals_*`, `three_p_field_goals_*`, `ft_*`
- Zaawansowane: `plus_minus`, `off/def_rebounds`, `steals`, `turnovers`, `blocked_shots`

### 4. BasketballMatchRoster
Składy drużyn (tabela BASKETBALL_MATCH_ROSTERS):
- `match_id`, `team_id`, `player_id`
- `number` - numer zawodnika
- `starter` - czy w pierwszej piątce (1=tak, 0=nie)

## Workflow pobierania danych

1. **Pobranie linków meczowych** - `get_match_links()` z głównej strony wyników ligi
2. **Dane podstawowe** - `get_match_info()` → `BasketballMatchData`
3. **Statystyki meczowe** - `get_match_stats_add()` → `BasketballMatchStatsAdd`  
4. **Statystyki zawodników** - `get_match_player_stats()` → `list[BasketballPlayerStats]`
5. **Składy drużyn** - `get_match_rosters()` → `list[BasketballMatchRoster]`

## Przykłady URL-ów

### Główna strona meczu:
```
https://www.flashscore.pl/mecz/koszykowka/indiana-pacers-YPohMUTt/oklahoma-city-thunder-0fHFHEWD/?mid=YasLoKTi
```

### Statystyki meczowe:
```
https://www.flashscore.pl/mecz/koszykowka/indiana-pacers-YPohMUTt/oklahoma-city-thunder-0fHFHEWD/szczegoly/statystyki/0/?mid=YasLoKTi
```

### Statystyki zawodników:
```
https://www.flashscore.pl/mecz/koszykowka/indiana-pacers-YPohMUTt/oklahoma-city-thunder-0fHFHEWD/szczegoly/statystyki-gracza/?mid=YasLoKTi
```

### Składy:
```
https://www.flashscore.pl/mecz/koszykowka/indiana-pacers-YPohMUTt/oklahoma-city-thunder-0fHFHEWD/szczegoly/sklady/?mid=YasLoKTi
```

## Użycie skryptu

### Tryb testowy (bez zapisu do bazy):
```bash
python nba_all_scrapper.py 1 1 "https://www.flashscore.pl/koszykowka/usa/nba-2023-2024/wyniki/"
```

### Tryb produkcyjny (z zapisem do bazy):
```bash
python nba_all_scrapper.py 1 1 "https://www.flashscore.pl/koszykowka/usa/nba-2023-2024/wyniki/" --automate
```

### Pobranie konkretnego meczu:
```bash
python nba_all_scrapper.py 1 1 "link_do_ligi" --one_link "https://www.flashscore.pl/mecz/koszykowka/..."
```

## Funkcje pomocnicze w utils.py

### Sprawdzanie w bazie danych:
- `check_if_in_db()` - sprawdza czy mecz już istnieje w bazie

### Parsowanie danych:
- `parse_match_date()` - konwersja daty z FlashScore
- `parse_score()` - parsowanie wyniku meczu
- `calculate_result()` - obliczanie wyniku (1/2/0)

### Budowanie URL-ów:
- `build_basketball_url()` - generuje URL-e do sekcji FlashScore

### Operacje na bazie:
- `get_teams_dict()` - pobiera mapowanie drużyn
- `update_db()` - wykonuje transakcje SQL

## Status implementacji

### ✅ Gotowe:
- **Pełna struktura dataclass'ów** zgodna z bazą danych
- **Zrefaktorowana metoda `get_match_data()`** używająca dataclass'ów
- **Wszystkie metody pobierania danych** z prawidłowymi typami
- **Funkcje pomocnicze w utils.py** wraz z `check_if_in_db()`
- **Argumenty wiersza poleceń i workflow**

### 🔄 Do implementacji:
- Konkretne selektory CSS dla elementów FlashScore
- Rzeczywiste parsowanie danych z HTML
- Implementacja `insert_match_data()` i `insert_procedure()`
- Funkcje pomocnicze (`get_country`, `get_teams_ids`, `get_shortcuts`)
- Testowanie na rzeczywistych danych

## Zalety refaktoryzacji na dataclass'y

1. **Bezpieczeństwo typów** - IDE może sprawdzać typy pól
2. **Czytelność kodu** - jasne definicje struktur danych
3. **Łatwość utrzymania** - jedna zmiana w dataclass propaguje się wszędzie
4. **Dokumentacja** - pola są udokumentowane w definicji klasy
5. **Zgodność z bazą danych** - nazwy pól odpowiadają kolumnom w tabelach

## Przykład użycia dataclass'ów

```python
# Tworzenie obiektu z danymi meczu
match_data = BasketballMatchData(
    league_id=1,
    season_id=1,
    home_team=10,
    away_team=15,
    match_date='2024-01-15 20:00'
)

# Dostęp do pól
print(f"Mecz: {match_data.home_team} vs {match_data.away_team}")
match_data.home_team_score = 110
match_data.away_team_score = 105
match_data.result = calculate_result(match_data.home_team_score, match_data.away_team_score)
```

Kod jest teraz bardziej czytelny, bezpieczny typowo i łatwiejszy w utrzymaniu!