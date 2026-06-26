# Docelowa struktura warstwy API

Katalog `api/` jest jedyną warstwą HTTP dla frontendu i integracji zewnętrznych.
Operacyjna dokumentacja endpointów: [README.md](README.md).

## Odpowiedzialność

- Kontrakt HTTP (JSON), walidacja parametrów, kody błędów.
- Rejestracja routerów, CORS, `/health`, OpenAPI (`/docs`, `/redoc`).
- Mapowanie odpowiedzi na schematy Pydantic w `schemas/`.
- Brak logiki SQL i obliczeń domenowych — delegacja do `backend/`.

## Struktura docelowa

```
api/
├── main.py                 
├── routers/
│   ├── teams.py            # z api_teams.py
│   ├── matches.py          # z api_matches.py
│   ├── odds.py
│   ├── predictions.py
│   ├── models.py           # metadane MODELS z DB — nie folder models/
│   ├── leagues.py          
│   ├── standings.py        
│   ├── bets.py             
│   ├── analytics.py        
│   └── players.py          
├── schemas/
├── dependencies/           # np. visibility
└── tests/
```
## Zasady importów

**Może importować:** `backend.repositories`, `backend.services`, `backend.config`,
`api.schemas`, `api.dependencies`.

**Używany przez:** `frontend/` (HTTP), testy w `api/tests/`.

Pełna mapa: [docs/repository-structure.md](../docs/repository-structure.md).
