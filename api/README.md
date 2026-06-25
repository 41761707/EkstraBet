# EkstraBet API

Modularny system API do zarządzania danymi systemu EkstraBet, zbudowany z wykorzystaniem FastAPI.

## Architektura

API składa się z modułów:
- **Teams** (`api_teams.py`) - Zarządzanie drużynami
- **Helper** (`api_helper.py`) - Dane pomocnicze (kraje, sporty, sezony)
- **Matches** (`api_matches.py`) - Zarządzanie meczami
- **Odds** (`api_odds.py`) - Kursy bukmacherskie
- **Predictions** (`api_predictions.py`) - Predykcje modeli
- **Główny** (`start_api.py`) - Inicjalizacja i orkiestracja wszystkich modułów

W przyszłości planowane są moduły:
- **Leagues** - Zarządzanie ligami
- **Predictions** - System predykcji  
- **Predictions** - System predykcji
itd.

## Instalacja i uruchomienie

### Wymagania
- Python 3.8+
- MySQL 8.0+
- Dostęp do bazy danych EkstraBet

### Instalacja zależności
```bash
pip install -r requirements.txt
```

### Konfiguracja środowiska
```bash
# 1. Skopiuj plik przykładowy
cp .env.example .env

# 2. Edytuj plik .env i ustaw swoje wartości
# WYMAGANE zmienne:
# - DB_PASSWORD (hasło do bazy danych)
# - SECRET_KEY (klucz do uwierzytelniania)

# 3. Wygeneruj bezpieczny SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### Uruchomienie serwera
```bash
python start_api.py
```

Alternatywnie z wykorzystaniem uvicorn:
```bash
uvicorn start_api:app --host 0.0.0.0 --port 8000 --reload
```

## Dokumentacja API

Po uruchomieniu serwera dostępne są automatycznie generowane dokumentacje:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Endpointy systemowe

### GET `/`
**Opis**: Informacje o całym API i dostępnych modułach.

### GET `/health`
**Opis**: Sprawdzenie stanu aplikacji i połączenia z bazą danych.

### GET `/teams/`
**Opis**: Informacje o module zarządzania drużynami.

## Moduł Helper - Endpointy pomocnicze

### 1. GET `/helper/countries`
**Opis**: Pobiera listę wszystkich krajów w systemie z liczbą drużyn.

**Przykład zapytania**:
```bash
curl "http://localhost:8000/helper/countries"
```

**Przykład odpowiedzi**:
```json
{
  "countries": [
    {
      "id": 2,
      "name": "Anglia",
      "short_name": "ENG",
      "emoji": "🇬🇧",
      "teams_count": 56
    }
  ],
  "total_countries": 15
}
```

### 2. GET `/helper/sports`
**Opis**: Pobiera listę wszystkich sportów w systemie z liczbą drużyn.

**Przykład zapytania**:
```bash
curl "http://localhost:8000/helper/sports"
```

**Przykład odpowiedzi**:
```json
{
  "sports": [
    {
      "id": 2,
      "name": "Hokej na lodzie",
      "teams_count": 34
    },
    {
      "id": 3,
      "name": "Koszykówka",
      "teams_count": 30
    },
    {
      "id": 1,
      "name": "Piłka nożna",
      "teams_count": 863
    }
  ],
  "total_sports": 3
}
```

### 3. GET `/helper/seasons`
**Opis**: Pobiera listę wszystkich sezonów w systemie z liczbą meczów.

**Przykład zapytania**:
```bash
curl "http://localhost:8000/helper/seasons"
```

**Przykład odpowiedzi**:
```json
{
  "seasons": [
    {
      "id": 5,
      "years": "2024/25",
      "matches_count": 1245
    },
    {
      "id": 4,
      "years": "2023/24",
      "matches_count": 2156
    }
  ],
  "total_seasons": 8
}
```

## Moduł Teams - Endpointy

### 1. GET `/teams/all`
**Opis**: Pobiera wszystkie drużyny z bazy danych z obsługą paginacji.

**Parametry**:
- `page` (int, opcjonalny): Numer strony (domyślnie 1)
- `page_size` (int, opcjonalny): Rozmiar strony (domyślnie 50, max 500)

**Przykład zapytania**:
```bash
curl "http://localhost:8000/teams/all?page=1&page_size=20"
```

**Przykład odpowiedzi**:
```json
{
  "teams": [
    {
      "id": 1,
      "name": "Śląsk Wrocław",
      "shortcut": "ŚLĄ",
      "country_id": 1,
      "country_name": "Polska",
      "country_emoji": "🇵🇱",
      "sport_id": 1,
      "sport_name": "Piłka nożna"
    }
  ],
  "total_count": 150,
  "page": 1,
  "page_size": 20
}
```

### 2. GET `/teams/search`
**Opis**: Wyszukuje drużyny na podstawie różnych filtrów.

**Parametry**:
- `country_id` (int, opcjonalny): ID kraju
- `country_name` (str, opcjonalny): Nazwa kraju (częściowe dopasowanie)
- `sport_id` (int, opcjonalny): ID sportu
- `sport_name` (str, opcjonalny): Nazwa sportu (częściowe dopasowanie)
- `team_name` (str, opcjonalny): Nazwa drużyny (częściowe dopasowanie)
- `team_shortcut` (str, opcjonalny): Skrót drużyny (dokładne dopasowanie)
- `page` (int, opcjonalny): Numer strony
- `page_size` (int, opcjonalny): Rozmiar strony

**Przykłady zapytań**:
```bash
# Wyszukaj drużyny z Polski
curl "http://localhost:8000/teams/search?country_name=Polska"

# Wyszukaj drużyny hokejowe
curl "http://localhost:8000/teams/search?sport_name=hokej"

# Wyszukaj drużyny zawierające "United" w nazwie
curl "http://localhost:8000/teams/search?team_name=United"

# Kombinacja filtrów
curl "http://localhost:8000/teams/search?country_id=2&sport_id=1&team_name=Arsenal"
```

### 3. GET `/teams/{team_id}/stats`
**Opis**: Pobiera szczegółowe statystyki meczowe dla konkretnej drużyny.

**Parametry**:
- `team_id` (int): ID drużyny
- `season_id` (int, opcjonalny): ID sezonu do filtrowania
- `last_n_matches` (int, opcjonalny): Ostatnie N meczów (1-100)

**Przykłady zapytań**:
```bash
# Podstawowe statystyki
curl "http://localhost:8000/teams/15/stats"

# Statystyki w konkretnym sezonie
curl "http://localhost:8000/teams/15/stats?season_id=3"

# Ostatnie 5 meczów
curl "http://localhost:8000/teams/15/stats?last_n_matches=5"

# Ostatnie 3 mecze w konkretnym sezonie
curl "http://localhost:8000/teams/15/stats?season_id=3&last_n_matches=3"
```

**Przykład odpowiedzi**:
```json
{
  "team_id": 15,
  "team_name": "Warta Poznań",
  "season_id": 3,
  "season_years": "2023/24",
  "last_n_matches": 5,
  "total_matches": 5,
  "home_matches": 3,
  "away_matches": 2,
  "wins": 2,
  "draws": 1,
  "losses": 2,
  "goals_scored": 8,
  "goals_conceded": 7
}
```

### 4. GET `/teams/{team_id}/btts`
**Opis**: Pobiera statystyki BTTS (Both Teams To Score) dla konkretnej drużyny.

**Parametry**:
- `team_id` (int): ID drużyny
- `season_id` (int, opcjonalny): ID sezonu do filtrowania
- `last_n_matches` (int, opcjonalny): Ostatnie N meczów (1-100)

**Przykłady zapytań**:
```bash
# Podstawowe statystyki BTTS
curl "http://localhost:8000/teams/15/btts"

# BTTS dla ostatnich 10 meczów
curl "http://localhost:8000/teams/15/btts?last_n_matches=10"

# BTTS w konkretnym sezonie
curl "http://localhost:8000/teams/15/btts?season_id=3"
```

**Przykład odpowiedzi**:
```json
{
  "team_id": 15,
  "team_name": "Warta Poznań",
  "season_id": null,
  "season_years": null,
  "last_n_matches": null,
  "total_matches": 236,
  "btts_yes": 142,
  "btts_no": 94,
  "btts_yes_percentage": 60.17,
  "btts_no_percentage": 39.83
}
```

## Najnowsze rozszerzenia API (2025)

### Zaawansowane filtrowanie statystyk
API zostało rozszerzone o zaawansowane możliwości filtrowania statystyk drużyn:

#### Filtr sezonu
Wszystkie endpointy statystyk (`/stats` i `/btts`) obsługują filtrowanie według konkretnego sezonu:
- Parametr `season_id` pozwala analizować wyniki tylko z określonego sezonu
- W odpowiedzi zwracane są informacje o sezonie (ID i lata)

#### Filtr ostatnich N meczów  
Możliwość ograniczenia analizy do ostatnich N spotkań drużyny:
- Parametr `last_n_matches` (zakres: 1-100) 
- Przydatne do analizy aktualnej formy drużyny
- Mecze sortowane według daty malejąco

#### Kombinowanie filtrów
Filtry można łączyć dla precyzyjnej analizy:
- Najpierw filtrowanie według sezonu
- Następnie ograniczenie do ostatnich N meczów z tego sezonu
- Przykład: ostatnie 5 meczów z sezonu 2023/24

### Statystyki BTTS (Both Teams To Score)
Nowy typ analizy meczów pod kątem strzelania bramek przez obie drużyny:
- Liczba meczów BTTS Tak/Nie
- Procentowe wskaźniki skuteczności
- Obsługa wszystkich filtrów (sezon, ostatnie N meczów)
- Szczególnie przydatne dla analiz zakładowych

### Rozszerzone modele danych
Modele odpowiedzi zostały wzbogacone o nowe pola:
- `season_id`, `season_years` - informacje o filtrowanym sezonie
- `last_n_matches` - liczba ostatnich meczów w analizie
- Nowy model `TeamBTTSResponse` dla statystyk BTTS

### Walidacja parametrów
Implementacja solidnej walidacji wejścia:
- `last_n_matches`: zakres 1-100 z walidacją FastAPI
- `season_id`: weryfikacja istnienia w bazie danych  
- `team_id`: sprawdzanie dostępności drużyny
- Odpowiednie kody błędów HTTP (422, 404)

## Kody statusów HTTP

- **200 OK**: Żądanie wykonane pomyślnie
- **404 Not Found**: Zasób nie został znaleziony (np. drużyna o podanym ID)
- **422 Unprocessable Entity**: Błędne parametry zapytania
- **500 Internal Server Error**: Błąd serwera lub bazy danych

## Bezpieczeństwo

### Zmienne środowiskowe
API wykorzystuje zmienne środowiskowe dla wrażliwych danych:

- **DB_PASSWORD** (wymagane) - hasło do bazy danych
- **SECRET_KEY** (wymagane) - klucz do uwierzytelniania
- **DB_HOST**, **DB_USER**, **DB_NAME**, **DB_PORT** (opcjonalne)

### Najlepsze praktyki

```bash
# Generowanie bezpiecznego SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Sprawdzenie konfiguracji
python test_setup.py
```

### ⚠️ Ważne ostrzeżenia

- **NIE commituj pliku `.env`** do repozytorium
- Używaj silnych haseł w produkcji
- Regularnie rotuj klucze dostępowe
- Ograniczaj dostęp do bazy danych przez firewall

### Pliki bezpieczeństwa

- `.env.example` - szablon konfiguracji (bezpieczny do commitu)
- `.env` - twoja lokalna konfiguracja (**NIE commituj!**)
- `.gitignore` - ignoruje wrażliwe pliki

## Bezpieczeństwo

API aktualnie nie implementuje mechanizmów uwierzytelniania. W przyszłości planowane jest dodanie:
- Tokenów API
- Rate limitingu
- CORS policy
- Logowania żądań

## Struktura odpowiedzi

Wszystkie endpointy zwracają dane w formacie JSON. Struktury odpowiedzi są zdefiniowane przy użyciu modeli Pydantic, co zapewnia:
- Walidację typów danych
- Automatyczne generowanie dokumentacji
- Lepsze podpowiedzi w IDE

## Obsługa błędów

API implementuje kompleksową obsługę błędów:
- Automatyczne łapanie błędów bazy danych
- Walidacja parametrów wejściowych
- Szczegółowe logowanie błędów
- Przyjazne komunikaty dla użytkowników

## Monitoring i logowanie

API zapisuje logi ze szczegółowymi informacjami o:
- Błędach połączenia z bazą danych
- Błędnych zapytaniach SQL
- Nieoczekiwanych wyjątkach
- Dostępach do endpointów

## Wydajność

API zostało zoptymalizowane pod kątem wydajności:
- Paginacja dla dużych zestawów danych
- Efektywne zapytania JOIN
- Context manager dla połączeń z bazą
- Automatyczne zamykanie połączeń

## Rozszerzenia

Planowane rozszerzenia API:
- Endpoints dla meczów
- Endpoints dla statystyk
- Endpoints dla predykcji
- System uwierzytelniania
- Cache'owanie wyników
- Rate limiting

## Testowanie API

### Uruchamianie testów
```bash
# Uruchom kompletny zestaw testów
python test_api.py

# Lub uruchom testy w trybie verbose
python -v test_api.py
```

### Zakres testów
Testy pokrywają wszystkie funkcjonalności API:

#### Testy systemowe
- Podstawowe połączenie z API
- Health check i status aplikacji
- Informacje o modułach

#### Testy funkcjonalne podstawowe
- Pobieranie wszystkich drużyn z paginacją
- Wyszukiwanie drużyn z różnymi filtrami
- Endpointy pomocnicze (kraje, sporty, sezony)

#### Testy funkcjonalności zaawansowanych
- **Statystyki drużyn** - podstawowe i z filtrami
- **Statystyki BTTS** - wszystkie warianty filtrowania
- **Filtrowanie sezonowe** - kombinacje parametrów
- **Ostatnie N meczów** - walidacja i funkcjonalność

#### Testy przypadków brzegowych
- Walidacja parametrów (wartości nieprawidłowe, graniczne)
- Obsługa nieistniejących zasobów (404)
- Nieprawidłowe typy danych (422)
- Kombinacje nieprawidłowych parametrów

#### Testy wydajnościowe
- Pomiar czasu odpowiedzi endpointów
- Test wszystkich głównych funkcjonalności
- Monitorowanie performance

### Przykład uruchomienia testów
```bash
🚀 Rozpoczynam testy API EkstraBet
============================================================
✅ Połączenie z API działa
✅ Status aplikacji: healthy
✅ Pobrano 50 drużyn
✅ Statystyki dla Śląsk Wrocław: 236 meczów
✅ Statystyki BTTS: 142 tak (60.17%), 94 nie (39.83%)
✅ Test ostatnich 5 meczów: 5 meczów
✅ Test filtrowania według sezonu 2023/24
✅ Test przypadków brzegowych: wszystkie prawidłowe
⚡ Wydajność: średni czas odpowiedzi 45ms
============================================================
✅ Wszystkie testy zakończone
```

## Moduł Matches - Endpointy

### 1. GET `/matches/seasons/{league_id}`
**Opis**: Pobiera wszystkie sezony dla danej ligi.

**Parametry**:
- `league_id` (int, wymagany): ID ligi

**Przykład zapytania**:
```bash
curl "http://localhost:8000/matches/seasons/1"
```

**Przykład odpowiedzi**:
```json
{
  "seasons": [
    {
      "season_id": 8,
      "years": "2023/24"
    },
    {
      "season_id": 7,
      "years": "2022/23"
    },
    {
      "season_id": 6,
      "years": "2021/22"
    }
  ],
  "total_count": 3
}
```

### 2. GET `/matches/rounds/{league_id}/{season_id}`
**Opis**: Pobiera wszystkie rundy dla danego sezonu w lidze.

**Parametry**:
- `league_id` (int, wymagany): ID ligi
- `season_id` (int, wymagany): ID sezonu

**Przykład zapytania**:
```bash
curl "http://localhost:8000/matches/rounds/1/8"
```

**Przykład odpowiedzi**:
```json
{
  "rounds": [
    {
      "round_number": 34,
      "game_date": "2024-05-25"
    },
    {
      "round_number": 33,
      "game_date": "2024-05-18"
    },
    {
      "round_number": 32,
      "game_date": "2024-05-11"
    }
  ],
  "total_count": 34
}
```

### 3. GET `/matches/`
**Opis**: Informacje o module matches.

**Przykład zapytania**:
```bash
curl "http://localhost:8000/matches/"
```

**Przykład odpowiedzi**:
```json
{
  "module": "EkstraBet Matches API",
  "version": "1.0.0",
  "description": "API do zarządzania danymi meczów",
  "endpoints": [
    "/matches/seasons/{league_id} - Sezony dla danej ligi",
    "/matches/rounds/{league_id}/{season_id} - Rundy dla danego sezonu w lidze"
  ]
}
```

---

## Moduł Odds

Moduł do zarządzania kursami bukmacherskimi.

### Dostępne endpointy:

### 1. GET `/odds/match/{match_id}`

Pobiera wszystkie kursy dla określonego meczu.

**Parametry:**
- `match_id` (int) - ID meczu

**Przykład użycia:**
```bash
curl "http://localhost:8000/odds/match/1"
```

**Odpowiedź:**
```json
{
  "odds": [
    {
      "bookmaker": "Fortuna",
      "event": "Winner",
      "odds": 2.15
    },
    {
      "bookmaker": "Fortuna", 
      "event": "Over 2.5",
      "odds": 1.85
    }
  ],
  "total_count": 2,
  "match_id": 1
}
```

### 2. GET `/odds/`

Informacje o module odds.

**Odpowiedź:**
```json
{
  "module": "EkstraBet Odds API",
  "version": "1.0.0",
  "description": "Moduł API do obsługi kursów bukmacherskich",
  "endpoints": [
    "/odds/match/{match_id} - Wszystkie kursy dla danego meczu"
  ]
}
```

---

## Moduł Predictions

Moduł do zarządzania predykcjami modeli.

### Dostępne endpointy:

### 1. GET `/predictions/search`

Wyszukuje predykcje z opcjonalnymi filtrami. Wszystkie filtry są opcjonalne.

**Parametry query:**
- `match_id` (int, opcjonalny) - ID meczu
- `event_id` (int, opcjonalny) - ID zdarzenia
- `model_ids` (string, opcjonalny) - Lista ID modeli oddzielona przecinkami (np. "1,2,3")
- `page` (int, domyślnie 1) - Numer strony
- `page_size` (int, domyślnie 50, max 500) - Rozmiar strony

**Przykłady użycia:**

```bash
# Wszystkie predykcje (pierwsza strona)
curl "http://localhost:8000/predictions/search"

# Predykcje dla meczu o ID 1
curl "http://localhost:8000/predictions/search?match_id=1"

# Predykcje dla zdarzenia o ID 2
curl "http://localhost:8000/predictions/search?event_id=2"

# Predykcje dla modeli 1 i 3
curl "http://localhost:8000/predictions/search?model_ids=1,3"

# Kombinacja filtrów - mecz 1, zdarzenie 2, modele 1,2,3
curl "http://localhost:8000/predictions/search?match_id=1&event_id=2&model_ids=1,2,3"

# Z paginacją - strona 2, 20 wyników na stronę
curl "http://localhost:8000/predictions/search?page=2&page_size=20"
```

**Odpowiedź:**
```json
{
  "predictions": [
    {
      "id": 1,
      "match_id": 1,
      "event_id": 2,
      "event_name": "Winner",
      "model_id": 1,
      "value": 0.75
    },
    {
      "id": 2,
      "match_id": 1,
      "event_id": 2,
      "event_name": "Winner",
      "model_id": 2,
      "value": 0.68
    }
  ],
  "total_count": 2,
  "filters_applied": {
    "match_id": 1,
    "event_id": 2,
    "model_ids": [1, 2],
    "page": 1,
    "page_size": 50
  }
}
```

### 2. GET `/predictions/team/{team_id}/{season_id}`

Pobiera predykcje dla określonej drużyny w danym sezonie, wraz z wynikami (poprawne/niepoprawne).

**Parametry:**
- `team_id` (int) - ID drużyny
- `season_id` (int) - ID sezonu

**Przykład użycia:**
```bash
curl "http://localhost:8000/predictions/team/1/8"
```

**Odpowiedź:**
```json
{
  "team_predictions": [
    {
      "event_id": 1,
      "outcome": 1
    },
    {
      "event_id": 2,
      "outcome": null
    }
  ],
  "total_count": 2,
  "team_id": 1,
  "season_id": 8
}
```

### 3. GET `/predictions/match/{match_id}`

Pobiera końcowe predykcje dla pojedynczego meczu wraz z wynikami (poprawne/niepoprawne).

**Parametry:**
- `match_id` (int) - ID meczu

**Przykład użycia:**
```bash
curl "http://localhost:8000/predictions/match/106538"
```

**Odpowiedź:**
```json
{
  "match_predictions": [
    {
      "event_id": 1,
      "name": "Winner",
      "outcome": 1,
      "model_id": 1
    },
    {
      "event_id": 2,
      "name": "Over 2.5",
      "outcome": null,
      "model_id": 1
    }
  ],
  "total_count": 2,
  "match_id": 106538
}
```

### 4. GET `/predictions/`

Informacje o module predictions.

**Odpowiedź:**
```json
{
  "module": "EkstraBet Predictions API",
  "version": "1.0.0",
  "description": "Moduł API do obsługi predykcji modeli",
  "endpoints": [
    "/predictions/search - Wyszukiwanie predykcji z opcjonalnymi filtrami",
    "/predictions/team/{team_id}/{season_id} - Predykcje dla drużyny w danym sezonie",
    "/predictions/match/{match_id} - Końcowe predykcje dla pojedynczego meczu"
  ]
}
```

## Kontakt

W przypadku problemów z API, skontaktuj się z autorem projektu.
