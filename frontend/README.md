# frontend/

Aplikacja Next.js/React — interfejs użytkownika EkstraBet. Zastępuje
dynamicznymi trasami (`/leagues/[leagueId]`, `/teams/[teamId]`, `/matches/[matchId]`).

## Odpowiedzialność

- Prezentacja danych pobranych wyłącznie z FastAPI (`api/`).
- Routing, komponenty UI, filtry w URL query params.
- Assety statyczne (np. koszulki drużyn z `web_code/pages/shirts/`).

## Struktura (docelowa)

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                    # Strona główna (Home.py)
│   │   ├── leagues/[leagueId]/page.tsx
│   │   ├── teams/[teamId]/page.tsx
│   │   ├── matches/[matchId]/page.tsx
│   │   ├── bets/page.tsx
│   │   └── stats/page.tsx
│   ├── components/
│   ├── lib/api.ts                      # Klient HTTP do FastAPI
│   └── types/api.ts
├── public/
├── package.json                        # inicjalizacja Next.js
└── tsconfig.json
```

## Zasady importów

**Może:** komponenty wewnętrzne, `src/lib/api.ts`, typy z `src/types/`.

**Nie importuje:** `backend/`, `models/`, bezpośredniego dostępu do MySQL.

**Komunikacja z danymi:** wyłącznie HTTP do `NEXT_PUBLIC_API_BASE_URL` (domyślnie `http://localhost:8000`).

Pełna mapa: [docs/repository-structure.md](../docs/repository-structure.md).
