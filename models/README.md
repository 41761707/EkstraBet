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
