# Docelowa struktura repozytorium EkstraBet (EB-1)

Dokument opisuje cztery główne foldery aplikacyjnych (`api/`, `backend/`,
`frontend/`, `models/`) oraz zasady importów między warstwami.

## Przepływ danych

```
Browser -> frontend/ (Next.js) -> api/ (FastAPI) -> backend/ (domena, SQL) -> MySQL
models/ (batch ML) -> MySQL
```

## Docelowa struktura plików

```
EkstraBet/
├── api/                          # Warstwa HTTP (FastAPI)
│   ├── main.py                   # Start aplikacji, CORS, rejestracja routerów
│   ├── routers/                  # Endpointy HTTP per domena
│   │   ├── teams.py
│   │   ├── matches.py
│   │   ├── odds.py
│   │   ├── predictions.py
│   │   ├── models.py             # Metadane modeli z bazy (nie pipeline ML)
│   │   ├── leagues.py
│   │   ├── standings.py
│   │   ├── bets.py
│   │   ├── analytics.py
│   │   └── players.py
│   ├── schemas/                  # Pydantic — kontrakty odpowiedzi HTTP
│   ├── dependencies/             # Zależności FastAPI (np. widoczność danych)
│   └── tests/
│
├── backend/                      # Logika domenowa wspólna dla API i batch
│   ├── config.py                 # Ustawienia z .env 
│   ├── database.py               # Connection manager
│   ├── repositories/             # Zapytania SQL
│   ├── services/                 # Obliczenia biznesowe
│   ├── sports/
│   │   ├── football/
│   │   ├── hockey/
│   │   └── basketball/
│   ├── policies/                 # Reguły widoczności danych
│   └── tests/
│
├── frontend/                     # Aplikacja Next.js/React
│   ├── src/
│   │   ├── app/                  # Routing (App Router)
│   │   ├── components/
│   │   ├── lib/api.ts
│   │   └── types/
│   └── public/
│
├── models/                       # Pipeline ML i artefakty
│   ├── pipeline/                 # Kod trenowania i predykcji
│   ├── configs/                  # Konfiguracje treningu/predykcji
│   ├── artifacts/                # Wagi .h5, configi release
│   └── scripts/                  # Skrypty batchowe
│
├── web_code/                     # LEGACY — Streamlit (do wygaszenia w EB-16)
├── model_code/                   # LEGACY — poprzednia lokalizacja pipeline ML (EB-13)
├── db_funcs/                     # LEGACY — skrypty batchowe DB (poza zakresem migracji UI)
├── graphics_code/                # LEGACY — generowanie wykresów (rozdzielenie w EB-14)
├── db_documentation/             # Dokumentacja schematu bazy
```

## Zasady importów

### Dozwolone zależności

```
frontend -> (tylko HTTP) -> api
api -> backend
backend -> (stdlib, biblioteki, MySQL - bez importu z api/ i frontend/)
models -> backend.config, backend.database  (wyłącznie batch, nie HTTP)
models -> MySQL bezpośrednio tylko tam, gdzie batch już tak działa - docelowo przez backend
```

### Zakazy

| Warstwa | Nie importuje z |
|---------|-----------------|
| `frontend/` | `backend/`, `models/` |
| `api/` | `web_code/`, `model_code/`, `frontend/` |
| `backend/` | `api/`, `frontend/` |
| `models/` | `api/`, `frontend/` |

### Rozróżnienie `api/routers/models.py` vs `models/`

- `api/routers/models.py` - endpointy HTTP zwracające metadane modeli z tabeli
  `MODELS` w bazie danych.
- `models/` (katalog główny) - pipeline uczenia, predykcji batchowej i pliki
  `.h5`. Brak współdzielenia nazw modułów Pythona między tymi warstwami.

### Konfiguracja i baza danych

- Jedno źródło konfiguracji: `backend/config.py`
- Jeden connection manager: `backend/database.py`

### Widoczność danych

- Reguły w `backend/policies/data_visibility.py`.
- Redakcja w `backend/services/redaction_service.py`.
- Wstrzykiwanie profilu w `api/dependencies/visibility.py`.
- Cache musi uwzględniać tryb `DATA_VISIBILITY_MODE`.
