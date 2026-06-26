EkstraBet — przewidywanie zdarzeń w meczach piłkarskich w przystępnej, przejrzystej formie.

## Struktura repozytorium (FastAPI + Next.js)

| Katalog | Rola |
|---------|------|
| [`api/`](api/) | Warstwa HTTP (FastAPI) |
| [`backend/`](backend/) | Logika domenowa, SQL, serwisy |
| [`frontend/`](frontend/) | Aplikacja Next.js/React |
| [`models/`](models/) | Pipeline ML i artefakty |

Mapa migracji i zasady importów:
[docs/repository-structure.md](docs/repository-structure.md).