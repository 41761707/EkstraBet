# backend/

Wspólna warstwa domenowa, serwisowa i dostępu do danych. Używana przez `api/`
(requesty HTTP) oraz potencjalnie przez zadania batchowe w `models/`.

## Odpowiedzialność

- Konfiguracja aplikacji i połączenia z bazą (`config.py`, `database.py`).
- Zapytania SQL (`repositories/`).
- Obliczenia biznesowe: tabele ligowe, forma drużyny, EV zakładów (`services/`).
- Logika sport-specific (`sports/football`, `sports/hockey`, `sports/basketball`).
- Polityka widoczności danych publicznych vs prywatnych (`policies/`).

## Struktura (docelowa)

```
backend/
├── config.py
├── database.py
├── repositories/
├── services/
├── sports/
│   ├── football/
│   ├── hockey/
│   └── basketball/
├── policies/
└── tests/
```

## Zasady importów

**Może importować:** biblioteki Pythona, moduły wewnątrz `backend/`.

**Nie importuje:** `api/`, `frontend/`.

**Używany przez:** `api/` (serwisy i repozytoria), opcjonalnie `models/` (config, DB w batch).

Pełna mapa: [docs/repository-structure.md](../docs/repository-structure.md).
