# EkstraBet API

Modularny system API do zarządzania danymi systemu EkstraBet, zbudowany z wykorzystaniem FastAPI.

## Architektura

API składa się z modułów:
- **Teams** (`api_teams.py`) - Zarządzanie drużynami
- **Główny** (`start_api.py`) - Inicjalizacja i orkiestracja wszystkich modułów

W przyszłości planowane są moduły:
- **Leagues** - Zarządzanie ligami
- **Matches** - Zarządzanie meczami  
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

**Przykład zapytania**:
```bash
curl "http://localhost:8000/teams/15/stats"
```

**Przykład odpowiedzi**:
```json
{
  "team_id": 15,
  "team_name": "Warta Poznań",
  "total_matches": 236,
  "home_matches": 119,
  "away_matches": 117,
  "wins": 81,
  "draws": 53,
  "losses": 102,
  "goals_scored": 246,
  "goals_conceded": 282
}
```

### 4. GET `/teams/countries`
**Opis**: Pobiera listę wszystkich krajów w systemie z liczbą drużyn.

**Przykład zapytania**:
```bash
curl "http://localhost:8000/teams/countries"
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

### 5. GET `/teams/sports`
**Opis**: Pobiera listę wszystkich sportów w systemie z liczbą drużyn.

**Przykład zapytania**:
```bash
curl "http://localhost:8000/teams/sports"
```

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

## Kontakt

W przypadku problemów z API, skontaktuj się z autorem projektu.
