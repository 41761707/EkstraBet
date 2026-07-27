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

## Odświeżanie statystyk (`refresh-statistics`)

Idempotentny cykl batchowy: generuje/aktualizuje automatyczne `bets` dla
rynków z kursami, potem rozlicza `final_predictions.outcome` (wszystkie
rodziny) oraz `bets.outcome` (tylko rynki kursowe).

### Co robi cykl

| Etap | Zakres | Efekt |
|------|--------|--------|
| Generowanie zakładów | Finalne predykcje + najlepszy kurs z `odds` | Upsert `bets` (kurs, EV); bez resetu istniejącego `outcome` |
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
opróżnia wszystkie oczekujące FP i zakłady rynków kursowych.

```bash
# Dry-run (bezpieczny podgląd raportu JSON na stdout)
python models/scripts/model_runner.py refresh-statistics

# Dry-run z filtrem generowania zakładów
python models/scripts/model_runner.py refresh-statistics --match-id 120084
python models/scripts/model_runner.py refresh-statistics --league-id 1 --date-from 2026-07-27 --date-to 2026-07-28

# Zapis (po migracji indeksu — patrz niżej)
python models/scripts/model_runner.py refresh-statistics --write-db
```

Sukces: exit code `0` + raport JSON. Błąd bazy/transakcji: log na stderr,
exit code `1`, rollback partii.

### Windows Task Scheduler

Wrapper przekazuje argumenty i kod wyjścia:

```bat
models\scripts\run_model_statistics.bat --write-db
```

### Smoke test (idempotencja)

1. Dry-run dla zakończonego meczu (`result` w `1/X/2`) i przyszłego — sprawdź raport.
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
