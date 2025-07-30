# Dokumentacja Modułów Scrapperów - EkstraBet

## Przegląd systemu scrapowania

System scrapowania EkstraBet składa się z modularnych narzędzi do pobierania danych piłkarskich z serwisu Flashscore.pl oraz generowania hipotetycznych zakładów bukmacherskich na podstawie wygenerowanych predykcji.

---

## 🏗️ Architektura systemu

### Moduły wspólne
- **`utils.py`** - Wspólne funkcje i struktury danych używane przez wszystkie scrappery
- **`scrapper_wrapper.py`** - Wrapper do grupowego uruchamiania scrapperów

### Główne moduły scrapowania
1. **`scrapper.py`** - Pobieranie kompletnych danych meczowych z wynikami i statystykami
2. **`upcoming_scrapper.py`** - Pobieranie nadchodzących meczów
3. **`update_scraper.py`** - Aktualizacja istniejących meczów o wyniki i statystyki
4. **`odds_scrapper.py`** - Pobieranie kursów bukmacherskich
5. **`bet_all.py`** - Generowanie zakładów na podstawie predykcji modeli

---

## 📋 Szczegółowy opis modułów

### 1. scrapper.py - Scrapper Główny
**Przeznaczenie**: Pobieranie kompletnych danych historycznych meczów wraz ze statystykami

**Funkcjonalności**:
- Pobieranie wyników meczów z pełnymi statystykami
- Parsowanie danych drużyn, dat, rezultatów
- Obsługa pojedynczych meczów i list meczów
- Automatyczny zapis do bazy danych lub tryb testowy

**Sposób wywołania**:
```bash
python scrapper.py <league_id> <season_id> <link> [--match] [--automate]
```

**Parametry**:
- `league_id` (int): ID ligi w bazie danych
- `season_id` (int): ID sezonu w bazie danych  
- `link` (str): Link do strony z wynikami lub link do konkretnego meczu
- `--match` (opcjonalna): Tryb pojedynczego meczu
- `--automate` (opcjonalna): Automatyczny zapis do bazy (domyślnie tryb testowy)

**Przykłady użycia**:
```bash
# Tryb testowy - pobieranie wszystkich meczów bez zapisu
python scrapper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/wyniki/"

# Tryb produkcyjny - zapis do bazy danych
python scrapper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/wyniki/" --automate

# Pojedynczy mecz
python scrapper.py 1 12 "https://www.flashscore.pl/mecz/xyz/" --match --automate
```

**Pobierane dane**:
- Podstawowe informacje o meczu (data, drużyny, wynik)
- Statystyki ofensywne (strzały, celne strzały, xG)
- Statystyki defensywne (faule, kartki, spalonki)
- Statystyki posiadania piłki i rzutów rożnych

---

### 2. upcoming_scrapper.py - Scrapper Nadchodzących Meczów
**Przeznaczenie**: Pobieranie informacji o nadchodzących meczach (maksymalnie 7 dni w przód)

**Funkcjonalności**:
- Pobieranie terminów przyszłych meczów
- Automatyczne blokowanie meczów odległych w czasie
- Parsowanie dat i drużyn
- Integracja z systemem drużyn w bazie

**Sposób wywołania**:
```bash
python upcoming_scrapper.py <league_id> <season_id> <link> [--match] [--automate]
```

**Parametry**:
- `league_id` (int): ID ligi w bazie danych
- `season_id` (int): ID sezonu w bazie danych
- `link` (str): Link do strony z meczami lub link do konkretnego meczu
- `--match` (opcjonalna): Tryb pojedynczego meczu
- `--automate` (opcjonalna): Automatyczny zapis do bazy (domyślnie tryb testowy)

**Przykłady użycia**:
```bash
# Pobieranie nadchodzących meczów bez zapisu
python upcoming_scrapper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/mecze/"

# Zapis nadchodzących meczów do bazy
python upcoming_scrapper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/mecze/" --automate

# Pojedynczy nadchodzący mecz
python upcoming_scrapper.py 1 12 "https://www.flashscore.pl/mecz/xyz/" --match --automate
```

**Pobierane dane**:
- Data i godzina meczu
- Drużyny gospodarze i goście
- Runda rozgrywek
- Status meczu (zaplanowany/przełożony)

---

### 3. update_scraper.py - Scrapper Aktualizacyjny
**Przeznaczenie**: Aktualizacja istniejących w bazie meczów o wyniki i statystyki

**Funkcjonalności**:
- Identyfikacja meczów wymagających aktualizacji
- Aktualizacja wyników i statystyk dla rozegranych meczów
- Inteligentne dopasowywanie meczów na podstawie drużyn i dat
- Obsługa pojedynczych aktualizacji

**Sposób wywołania**:
```bash
python update_scraper.py <league_id> <season_id> <link> [--match] [--automate]
```

**Parametry**:
- `league_id` (int): ID ligi w bazie danych
- `season_id` (int): ID sezonu w bazie danych
- `link` (str): Link do strony z wynikami lub link do konkretnego meczu
- `--match` (opcjonalna): Tryb pojedynczego meczu
- `--automate` (opcjonalna): Automatyczny zapis do bazy (domyślnie tryb testowy)

**Przykłady użycia**:
```bash
# Aktualizacja wszystkich meczów - tryb testowy
python update_scraper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/wyniki/"

# Aktualizacja z zapisem do bazy
python update_scraper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/wyniki/" --automate

# Aktualizacja pojedynczego meczu
python update_scraper.py 1 12 "https://www.flashscore.pl/mecz/xyz/" --match --automate
```

**Aktualizowane dane**:
- Wynik końcowy meczu
- Wszystkie statystyki meczowe
- Status rezultatu (zmiana z '0' na '1')
- Data i godzina faktycznego rozpoczęcia

---

### 4. odds_scrapper.py - Scrapper Kursów Bukmacherskich
**Przeznaczenie**: Pobieranie kursów bukmacherskich dla różnych typów zakładów

**Funkcjonalności**:
- Pobieranie kursów od różnych bukmacherów
- Obsługa trzech trybów: daily, historical, match
- Automatyczne parsowanie różnych typów zakładów
- Integracja z systemem bukmacherów w bazie
- Tryb testowy i produkcyjny z kontrolą zapisu

**Sposób wywołania**:
```bash
python odds_scrapper.py <league_id> <season_id> <link> <mode> [--skip <liczba>] [--automate]
```

**Parametry**:
- `league_id` (int): ID ligi w bazie danych
- `season_id` (int): ID sezonu w bazie danych
- `link` (str): Link do meczu/meczów na Flashscore
- `mode` (str): Tryb działania ('daily', 'historical', 'match')
- `--skip` (int, opcjonalna): Liczba meczów do pominięcia (tylko tryb historical)
- `--automate` (opcjonalna): Automatyczny zapis kursów do bazy (domyślnie tryb testowy)

**Tryby działania**:
- **daily**: Pobiera kursy dla meczów z bieżącego dnia
- **historical**: Pobiera kursy dla meczów historycznych
- **match**: Pobiera kursy dla konkretnego meczu

**Przykłady użycia**:
```bash
# Kursy dzienne - tryb testowy
python odds_scrapper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/" daily

# Kursy dzienne z zapisem do bazy
python odds_scrapper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/" daily --automate

# Kursy historyczne z pominięciem 5 najstarszych meczów
python odds_scrapper.py 1 12 "https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/wyniki/" historical --skip 5 --automate

# Kursy dla konkretnego meczu
python odds_scrapper.py 1 12 "https://www.flashscore.pl/mecz/xyz/" match --automate
```

**Pobierane kursy**:
- Wygrana gospodarzy/remis/wygrana gości (1X2)
- Obie drużyny strzelą gol (BTTS)
- Powyżej/Poniżej 2.5 gola (O/U 2.5)
- Różne warianty handicapów i specjalnych zakładów

---

### 5. bet_all.py - Generator Zakładów
**Przeznaczenie**: Generowanie zakładów na podstawie predykcji modeli i kursów bukmacherskich

**Funkcjonalności**:
- Obliczanie wartości oczekiwanej (EV) dla zakładów
- Wybór najlepszych kursów spośród bukmacherów
- Cztery tryby generowania zakładów
- Automatyczna analiza predykcji vs kursy

**Sposób wywołania**:
```bash
python bet_all.py <mode> <league_id> <season_id> [opcje specyficzne dla trybu]
```

**Parametry główne**:
- `mode` (str): Tryb generowania ('today', 'round', 'date_range', 'match')
- `league_id` (int): ID ligi w bazie danych
- `season_id` (int): ID sezonu w bazie danych

**Tryby i ich parametry**:

1. **today** - Zakłady na dzisiejsze mecze:
   ```bash
   python bet_all.py today 1 12
   ```

2. **round** - Zakłady dla konkretnej rundy:
   ```bash
   python bet_all.py round 1 12 --round_num 15
   ```

3. **date_range** - Zakłady dla przedziału czasowego:
   ```bash
   python bet_all.py date_range 1 12 --date_from 2024-07-01 --date_to 2024-07-20
   ```

4. **match** - Zakład dla konkretnego meczu:
   ```bash
   python bet_all.py match 1 12 --match 12345
   ```

**Generowane typy zakładów**:
- Rezultat meczu (1X2) - wybierany najwyższy % spośród trzech opcji
- BTTS (Both Teams To Score) - TAK/NIE
- Over/Under 2.5 gola - wybierany wyższy %

**Obliczane metryki**:
- EV (Expected Value) - wartość oczekiwana zakładu
- Najlepszy kurs spośród dostępnych bukmacherów
- Identyfikacja najbardziej opłacalnego bukmachera

---

### 6. scrapper_wrapper.py - Wrapper Grupowy
**Przeznaczenie**: Uruchamianie scrapperów dla wielu lig jednocześnie w trybie produkcyjnym

**Funkcjonalności**:
- Automatyczne przetwarzanie listy lig
- Pięć trybów działania
- Konfiguracja poprzez wewnętrzną listę linków
- Automatyzacja codziennych procesów
- Wszystkie operacje wykonywane w trybie produkcyjnym (automate=True)

**Sposób wywołania**:
```bash
python scrapper_wrapper.py <mode>
```

**Dostępne tryby**:
- **update**: Aktualizuje wszystkie mecze do dzisiejszej daty (update_scraper.py)
- **upcoming**: Pobiera nadchodzące mecze (upcoming_scrapper.py)
- **odds**: Pobiera kursy bukmacherskie w trybie daily (odds_scrapper.py)
- **historic**: Pobiera historyczne wyniki (scrapper.py)
- **bet**: Generuje zakłady (bet_all.py)

**Przykłady użycia**:
```bash
# Aktualizacja wszystkich lig
python scrapper_wrapper.py update

# Pobieranie nadchodzących meczów
python scrapper_wrapper.py upcoming

# Pobieranie kursów bukmacherskich
python scrapper_wrapper.py odds

# Generowanie zakładów dla aktywnych lig
python scrapper_wrapper.py bet
```

**Wywołania modułów**:
- **update**: `update_scraper.to_automate(league_id, season_id, link, single_match=False, automate=True)`
- **upcoming**: `upcoming_scrapper.to_automate(league_id, season_id, link, single_match=False, automate=True)`
- **odds**: `odds_scrapper.odds_to_automate(league_id, season_id, link, 'daily', skip=0, automate=True)`
- **historic**: `scrapper.to_automate(league_id, season_id, link, single_match=False, automate=True)`
- **bet**: `bet_all.bet_to_automate('today', league_id, season_id)`

**Konfiguracja lig**:
Lista lig jest skonfigurowana wewnątrz pliku w formacie:
```python
'league_id season_id https://flashscore_link'
```

---

## 🛠️ Moduł utils.py - Funkcje Wspólne

### Struktury danych
- **`MatchData`**: Dataclass przechowująca kompletne dane meczu
- **`TeamMapping`**: Słownik mapowania nazw drużyn na ID

### Funkcje wspólne
- **`setup_chrome_driver()`**: Konfiguracja ChromeDriver z optymalnymi ustawieniami
- **`get_teams_dict()`**: Pobieranie mapowania drużyn z bazy danych
- **`fetch_match_elements()`**: Pobieranie elementów DOM meczu
- **`parse_stats()`**: Parsowanie statystyk meczowych
- **`generate_insert_sql()`**: Generowanie zapytań INSERT dla bazy danych
- **`update_db()`**: Bezpieczny zapis zmian do bazy danych

---

## 🔧 Konfiguracja i wymagania

### Wymagania systemowe
- Python 3.8+
- Chrome/Chromium browser
- ChromeDriver
- MySQL database

### Wymagane pakiety Python
```
selenium
pandas
mysql-connector-python
numpy
beautifulsoup4
argparse
```

### Konfiguracja bazy danych
Wszystkie moduły wymagają skonfigurowanego połączenia MySQL poprzez `db_module.py` z tabelami:
- `matches` - dane meczów
- `teams` - dane drużyn
- `leagues` - dane lig
- `seasons` - dane sezonów
- `odds` - kursy bukmacherskie
- `predictions` - predykcje modeli
- `bets` - wygenerowane zakłady

---

## 🚀 Workflow typowego użycia

### Proces codzienny
1. **Aktualizacja wyników**: `python scrapper_wrapper.py update`
2. **Pobieranie nowych meczów**: `python scrapper_wrapper.py upcoming`
3. **Aktualizacja kursów**: `python scrapper_wrapper.py odds`
4. **Generowanie zakładów**: `python scrapper_wrapper.py bet`

### Dodawanie nowej ligi
1. Dodanie ligi do bazy danych
2. Pobranie historycznych danych: `python scrapper.py <league_id> <season_id> <link> --automate`
3. Pobranie kursów historycznych: `python odds_scrapper.py <league_id> <season_id> <link> historical`
4. Dodanie do listy w `scrapper_wrapper.py`

### Testowanie i debug
Wszystkie moduły domyślnie działają w trybie testowym (bez zapisu do bazy). Do zapisania zmian wymagana jest flaga `--automate` lub odpowiedni parametr.

---

## ⚠️ Bezpieczeństwo i najlepsze praktyki

### Flagi bezpieczeństwa
- Domyślny tryb testowy zapobiega przypadkowym zapisom
- Verbose komunikaty informują o trybie działania
- Walidacja parametrów przed uruchomieniem

### Obsługa błędów
- Automatyczne zamykanie połączeń z bazą danych
- Obsługa błędów Selenium i timeoutów
- Logowanie błędów parsowania

### Monitoring wydajności
- Automatyczne zarządzanie sesją przeglądarki
- Optymalizacja zapytań do bazy danych
- Minimalizacja czasu ładowania stron

---

## 📞 Wsparcie i rozwiązywanie problemów

### Typowe problemy
1. **ChromeDriver compatibility**: Sprawdzenie wersji Chrome vs ChromeDriver
2. **Timeout errors**: Zwiększenie timeout w ustawieniach Selenium
3. **Database connection**: Weryfikacja parametrów połączenia w `db_module.py`
4. **Parsing errors**: Sprawdzenie czy struktura strony Flashscore się nie zmieniła

### Debugging
- Użycie trybu testowego (`bez --automate`) do sprawdzenia parsowania
- Sprawdzenie logów w terminalu
- Weryfikacja poprawności linków Flashscore
- Kontrola dostępności bazy danych

---

*Dokumentacja wygenerowana dla systemu scrapowania EkstraBet v2.0*  
*Ostatnia aktualizacja: 26 lipca 2025*
