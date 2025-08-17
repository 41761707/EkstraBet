# EkstraBet — system analityczny do predykcji zdarzeń sportowych

## Wersja polska
EkstraBet to modularny projekt Pythonowy łączący scraping, analizę danych, modele predykcyjne oraz wygodną warstwę prezentacji. Projekt powstał jako rozszerzenie pracy magisterskiej i jest rozwijany pod kątem analizy meczów, generowania predykcji i symulacji zakładów bukmacherskich.

## Główne funkcjonalności
- Pobieranie i aktualizacja danych meczowych (historyczne i nadchodzące) — moduły scrapperów ([scrapper_code/README_scrappers.md](scrapper_code/README_scrappers.md)).
- Pobieranie kursów bukmacherskich i powiązanie ich z predykcjami (odds).
- Pipeline trenowania i predykcji modeli (winner / btts / goals / exact) z możliwością zapisu/ładowania wag — moduł modelowy ([model_code/main.py](model_code/main.py)).
- Generowanie propozycji zakładów i ocena Value (EV) — narzędzia typu `bet_all`.
- Interfejs webowy oparty o Streamlit do eksploracji wyników, wizualizacji i nawigacji po ligach ([web_code/Home.py](web_code/Home.py), [`Base.set_config`](web_code/base_site_module.py)).
- Lekki REST API z dokumentacją Swagger/Redoc do integracji zewnętrznej ([api_code/start_api.py](api_code/start_api.py), [api_code/README.md](api_code/README.md)).
- Kompleksowa dokumentacja schematu bazy danych ([db_documentation/db_documentation.md](db_documentation/db_documentation.md)).

## Struktura repozytorium (logiczne części)
- api_code/ — serwer API i moduły FastAPI (teams, helper, matches, models, itp.). Zajrzyj do [api_code/README.md](api_code/README.md).
- web_code/ — aplikacja Streamlit i moduły UI/wykresów/tabel. Punkt wejścia: [web_code/Home.py](web_code/Home.py).
- scrapper_code/ — moduły do pobierania danych z serwisów (Flashscore, NHL API itd.), konfiguracja scrapperów i wrapper do batchowania.
- model_code/ — pipeline treningu i predykcji, przygotowanie danych, mapowanie kalkulatorów ratingów ([model_code/main.py](model_code/main.py), [model_code/README.md](model_code/README.md)).
- db_funcs/ — funkcje pomocnicze związane z bazą (skrypty i migracje).
- db_documentation/ — pełna dokumentacja schematu bazy danych i opis tabel ([db_documentation/db_documentation.md](db_documentation/db_documentation.md)).
- graphics_code/ — narzędzia i zasoby graficzne używane w UI.
- models/ oraz latest_backup/ — katalogi z wytrenowanymi wagami i backupami.
- .github/, .devcontainer/ — konfiguracje CI / devcontainer / instrukcje Copilot itp.

## Szybki start
- Aplikacja Streamlit:
  - Przejdź do katalogu `web_code/`.
  - Uruchom: `streamlit run Home.py`
  - Interfejs wykorzystuje lokalne połączenie do bazy danych za pomocą `db_module`.

- API:
  - Skonfiguruj `.env` w `api_code/` kopiując `.env.example`.
  - Uruchom: `python start_api.py` lub `uvicorn start_api:app --reload`.
  - Sprawdź dokumentację: /docs i /redoc (np. http://localhost:8000/redoc).

- Modele:
  - Instrukcje w [model_code/README.md](model_code/README.md).
  - Typowy przykład: `python main.py winner train 0 alpha_0_0_result` (uruchamiane z katalogu `model_code/`).

- Scrappery:
  - Przykłady i tryby działania w [scrapper_code/README_scrappers.md](scrapper_code/README_scrappers.md).
  - Tryb testowy (bez --automate) domyślnie nie zapisuje do bazy.

## Aktualnie obsługiwane zdarzenia
1. 1X2
2. BTTS
3. Dokładna liczba bramek
4. Rozkład prawdopodobieństwa bramek, na podstawie którego generowany jest Over / Under 2.5

## Aktualnie obsługiwane ligi
1. Ekstraklasa + 1. Liga (Polska)
2. Premier League + Championship (Anglia)
3. Serie A + Serie B (Włochy)
4. Ligue 1 + Ligue 2 (Francja)
5. LaLiga + LaLiga2 (Hiszpania)
6. Bundesliga + 2. Bundesliga (Niemcy)
7. K League 1 + K League 2 (Korea Południowa)
8. MLS (USA)
9. J1 League + J2 League (Japonia)
10. Jupiler League + Challenger Pro League (Belgia)
11. Swiss Super League + Challenge League (Szwajcaria)
12. Super Lig + 1.Lig (Turcja)
13. Liga Portugal + Liga Portugal 2 (Portugalia)
14. Eredivisie + Eerste Divisie (Holandia)
15. Chance liga + Dywizja 2 (Czechy)
16. Bundesliga + 2. Liga (Austria)
17. (NOWE) A-League (Australia)
18. (NOWE) Serie A + Serie B (Brazylia)
19. (NOWE) Torneo Betano (Argentyna)
20. (NOWE) NHL (Hokej, NA)

## Planowane rozszerzenia
1. Premiership i 1 Dywizja (Szkocja)
2. NBA (Koszykówka, NA)
3. Dane z OPTY o zawodnikach

## Dokumentacja techniczna
- Schemat bazy i opisy tabel: [db_documentation/db_documentation.md](db_documentation/db_documentation.md).
- Dokumentacja API: [api_code/README.md](api_code/README.md).
- Instrukcje scrapperów: [scrapper_code/README_scrappers.md](scrapper_code/README_scrappers.md).
- Instrukcje modeli: [model_code/README.md](model_code/README.md).