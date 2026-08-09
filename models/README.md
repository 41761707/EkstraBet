# models/

Pipeline uczenia maszynowego, konfiguracje trenowania/predykcji, wagi modeli
i skrypty batchowe. Oddzielony od `api/routers/models.py`, który zwraca
**metadane modeli z bazy** (tabela `MODELS`), a nie pliki artefaktów.

## Odpowiedzialność

- Trenowanie, ewaluacja i batchowa ocena meczów (zapis do
  `match_model_assessments` dla modeli assessment; `PREDICTIONS` /
  `FINAL_PREDICTIONS` pozostają dla predykcji przyszłych zdarzeń).
- Artefakty: joblib/JSON (i legacy `.h5`), configi training/prediction.
- Skrypty uruchamiane poza requestami HTTP (`models/scripts/model_runner.py`).

## Struktura

```
models/
├── pipeline/           # wspólny runner + feature/label/train/predict
├── configs/
│   ├── training/
│   └── prediction/
├── artifacts/
│   ├── dev/
│   └── release/
├── scripts/            # model_runner.py + bat wrappery
└── tests/
```

## Uruchomienie

```bash
python models/scripts/model_runner.py train --config models/configs/training/football_played_better_v1.json
python models/scripts/model_runner.py evaluate --config models/configs/training/football_played_better_v1.json
python models/scripts/model_runner.py assess-match --config models/configs/prediction/football_played_better_v1.json --match-id 12345 --write-db
python models/scripts/model_runner.py assess-batch --config models/configs/prediction/football_played_better_v1.json --season-id 12 --write-db
```

## Projekcja końca sezonu (`simulate-season`)

Monte Carlo nad tabelą `schedule` (nie `matches`). Wynik trafia do cache
`season_projection_runs` / `season_projection_team_rows`. Endpoint HTTP tylko
odczytuje cache — bez TensorFlow w request path.

### Tryby

| Mode | Zachowanie |
|------|------------|
| `from_now` | Podpięte `match_id` z `result <> '0'` = wynik stały; reszta losowana |
| `from_season_start` | Ignoruje `match_id`; wszystkie mecze losowane |

Oba tryby startują standings od dnia 0 sezonu; cechy/ratingi mają warm-start
z historii `game_date < season_anchor`.

### CLI

```bash
python models/scripts/model_runner.py simulate-season \
  --goals-config models/configs/prediction/football_goals_poisson_v1.json \
  --league-id 1 --season-id 13 --mode from_now --trials 2000 --seed 42

# wrapper Windows (wstrzykuje goals-config)
models\scripts\run_future_events.bat simulate-season --league-id 1 --season-id 13 --mode from_now --trials 2000 --seed 42
```

Wymagania: kompletny `schedule` (`N*(N-1)` dla double RR, `round < 900`),
liga piłkarska, artefakt Poissona. Niekompletny terminarz → run `FAILED`,
API bez gotowej projekcji (404).

Fingerprint wejścia unieważnia cache przy zmianie `schedule` lub korekcie
wyniku w `matches` (sama `game_date` nie wpływa). API zwraca wtedy ostatni
`SUCCEEDED` z `is_stale=true`.

### Budżet wydajności (SZP-89)

Referencja: liga 1 / sezon 13 (N=18, 306 fixture’ów), `n_trials=2000`,
seed 42, model `FOOTBALL_GOALS_POISSON_V1` — zmierzony wall ~**3079 s
(~51 min)** (`season_projection_runs.id=5`).

| Limit | Wartość | Status |
|-------|---------|--------|
| Wall (scheduler) | **≤ 6158 s (2× pomiar)** | zatwierdzony (`APPROVED_WALL_SECONDS_LIMIT`) |
| Peak RSS | **≤ 4096 MiB** | **niepomierzony** interim ceiling (`PEAK_RSS_LIMIT_IS_MEASURED=false`); run id=5 nie zapisał RSS |
| Soft budget mock | ≤ 180 s / ≤ 2048 MiB @ 100 triali | pomiar ~77 s / ~144 MiB |

Stałe: `models/pipeline/simulation/perf_budget.py`.

Aby zatwierdzić RSS: uruchom `simulate-season` (CLI zwraca `wall_seconds`
i `peak_rss_mb`), wpisz pomiar do `REFERENCE_PEAK_RSS_MB`, ustaw
`PEAK_RSS_LIMIT_IS_MEASURED=true` i limit (np. 2× pomiar).

Opt-in harness (mock predictor, pełna liga + porównanie trybów):

```bash
# domyślny pytest pomija ten plik
set EKSTRABET_SEASON_PERF=1
set EKSTRABET_SEASON_PERF_TRIALS=100
python -m pytest models/tests/test_season_simulation_performance.py -s
```

Porównanie trybów w harnessie: N=8 z early rounds `is_fixed=True` —
`FROM_NOW` ma `fixed_matches > 0` i mniej wierszy inferencji niż
`FROM_SEASON_START`. Na produkcji sensowny A/B wymaga zlinkowanych
`schedule.match_id`.
### Odbiór ręczny (UI)

1. `/leagues/{leagueId}` — ekspander projekcji **pod** „Tabele ligowe”.
2. Przed otwarciem: brak requestu projekcji (Network).
3. Pierwsze otwarcie: loading → tabela (`expected_position`, xPts, SD, P05–P95).
4. Brak runu: stan empty/404; błąd sieci: error; `is_stale`: banner świeżości.
5. Istniejące standings i preview meczu bez regresji.

## Odświeżanie statystyk (`refresh-statistics`)

Idempotentny cykl batchowy: generuje/aktualizuje automatyczne `bets` dla
rynków z kursami, potem rozlicza `final_predictions.outcome` (wszystkie
rodziny) oraz `bets.outcome` (tylko rynki kursowe).

### Co robi cykl

| Etap | Zakres | Efekt |
|------|--------|--------|
| Generowanie zakładów | Nieskończone mecze + FP + najlepszy kurs z `odds` | Upsert `bets` (kurs, EV); bez resetu `outcome` |
| Backfill zakładów (`--backfill` + scope) | Zakończone mecze w zakresie ligi/sezonu/dat | Upsert historycznych `bets` dla statystyk |
| Settlement FP | Wszystkie obsługiwane rodziny (1X2, BTTS, O/U, GOALS, EXACT) | Ustawia `final_predictions.outcome` gdy `NULL` |
| Settlement bets | Tylko event_id **1, 2, 3, 6, 8, 12, 172** | Ustawia `bets.outcome` gdy `NULL` |

GOALS / EXACT: tylko `final_predictions.outcome`. Brak kursu = brak wiersza
w `bets` (oczekiwane, bez ostrzeżenia).

### Semantyka i EV

- `outcome`: `NULL` oczekujący, `0` nietrafiony, `1` trafiony.
- `predictions.value` w skali **0–100**.
- EV: `round((value / 100) * odds - 1, 4)` — ten sam wzór co backend.
- Najlepszy kurs: `odds DESC`, potem `odds.id ASC`.
- Idempotencja: zapis tylko przy `outcome IS NULL`, upsert zakładów, indeks
  `unique_model_bet(match_id, event_id, model_id)`.

### Dry-run vs zapis

Domyślnie **dry-run** (żadnych zapisów). Zapis wymaga `--write-db`.

Flagi zakresu (`--league-id`, `--season-id`, `--match-id`, `--date-from`,
`--date-to`) filtrują **tylko generowanie zakładów**. Settlement zawsze
opróżnia wszystkie oczekujące FP i zakłady rynków kursowych — **chyba że**
użyjesz `--preview` (wtedy te same filtry obejmują też settlement).

```bash
# Dry-run (bezpieczny podgląd raportu JSON na stdout)
python models/scripts/model_runner.py refresh-statistics

# Dry-run z filtrem generowania zakładów
python models/scripts/model_runner.py refresh-statistics --match-id 120084
python models/scripts/model_runner.py refresh-statistics --league-id 1 --date-from 2026-07-27 --date-to 2026-07-28

# Preview: próbka planowanych zapisów (before/after); scope obejmuje settlement
python models/scripts/model_runner.py refresh-statistics --match-id 120084 --preview
python models/scripts/model_runner.py refresh-statistics --match-id 120084 --preview --preview-limit 20

# Zapis (bieżące, nieskończone mecze)
python models/scripts/model_runner.py refresh-statistics --write-db

# Backfill historycznych bets w zakresie dat (wymaga scope + --backfill)
python models/scripts/model_runner.py refresh-statistics --write-db --backfill --date-from 2026-07-01 --date-to 2026-07-27
python models/scripts/model_runner.py refresh-statistics --write-db --backfill --season-id 12 --league-id 1
```

Domyślnie generowanie zakładów **pomija mecze zakończone** (`result` w
`1/X/2`). Flaga `--backfill` zdejmuje ten filtr, ale wymaga co najmniej
jednego filtra zakresu (`--league-id`, `--season-id`, `--match-id`,
`--date-from`, `--date-to`).

`--preview` jest wyłącznie trybem podglądu (koliduje z `--write-db`). W JSON
pojawia się `preview` (lista planowanych upsertów/`SET outcome`) oraz
`preview_truncated` gdy próbek było więcej niż limit.

Sukces: exit code `0` + raport JSON. Błąd bazy/transakcji: log na stderr,
exit code `1`, rollback partii.

### Windows Task Scheduler

Wrapper przekazuje argumenty i kod wyjścia:

```bat
models\scripts\run_model_statistics.bat --write-db
```

### Smoke test (idempotencja)

1. `--preview` dla zakończonego meczu (`result` w `1/X/2`) i przyszłego —
   sprawdź `preview` (planowane `outcome` / upserty EV).
2. `--write-db`.
3. Ponowne uruchomienie: `generated` / `settled` / `updated` dla już
   rozliczonych rekordów powinny spaść do zera (brak dodatkowych zmian).

## Uwagi implementacyjne (PLAYED_BETTER)

Dwa komplementarne modele:

| Model | Config | Trening (filtr xG) | Feature'y / label xG |
|---|---|---|---|
| `FOOTBALL_PLAYED_BETTER_V1` | `football_played_better_v1` | `require_positive_xg=true` | tak |
| `FOOTBALL_PLAYED_BETTER_NOXG_V1` | `football_played_better_noxg_v1` | `exclude_positive_xg=true` | nie |

- **Filtr xG w repository:** tylko przy `train` / `evaluate` (dobór danych
  uczących). Sterowany `require_positive_xg` / `exclude_positive_xg`.
  `xG <= 0` traktowane jako brak danych (NaN).
- **Assess:** bez filtra xG — ten sam mecz można odpalić na V1 i NOXG
  (porównanie wpływu xG). NOXG po prostu ignoruje kolumny xG w features.
  V1 nadal wymaga dodatnich xG w feature builderze (`required_columns`).
- **Soft targets:** labeler liczy soft probabilities; `SklearnTrainer` mapuje
  je na hard label + `sample_weight` (sklearn nie uczy się bezpośrednio na
  soft `y`).
- **Evaluate:** metryki obejmują m.in. Brier score per klasa i uproszczony
  reliability summary (`calibration_reliability`).

## Zasady importów

**Może importować:** `backend.config`, `backend.database`, moduły w `models/pipeline/`.

**Nie importuje:** `api/`, `frontend/`

**Nie jest importowany przez:** `api/` (poza metadanymi z DB), `frontend/`.

**Wyjątek (tylko lokalnie):** endpoint `POST /predictions/preview` może
załadować `models.pipeline` przez
`backend/services/prediction_preview_service.py`, wyłącznie gdy
`EKSTRABET_ML_PREVIEW=1`. Ścieżki `artifact_dir` w configach JSON są
względne względem roota repozytorium (`REPO_ROOT`), nie względem CWD procesu.

Pełna mapa: [docs/repository-structure.md](../docs/repository-structure.md).
