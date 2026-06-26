# models/

Pipeline uczenia maszynowego, konfiguracje trenowania/predykcji, wagi modeli
i skrypty batchowe. Oddzielony od `api/routers/models.py`, który zwraca
**metadane modeli z bazy** (tabela `MODELS`), a nie pliki `.h5`.

## Odpowiedzialność

- Trenowanie i predykcja batchowa (zapis do `PREDICTIONS`, `FINAL_PREDICTIONS`).
- Artefakty: pliki `.h5`, configi JSON release/dev.
- Skrypty uruchamiane poza requestami HTTP (np. `run_predictions.bat`).

## Struktura (docelowa)

```
models/
├── pipeline/           moduły ML)
├── configs/
│   ├── training/       
│   └── prediction/     
├── artifacts/
│   ├── dev/            
│   └── release/        
└── scripts/            
```

## Zasady importów

**Może importować:** `backend.config`, `backend.database`, moduły w `models/pipeline/`.

**Nie importuje:** `api/`, `frontend/`

**Nie jest importowany przez:** `api/` (poza metadanymi z DB), `frontend/`.

**Uwaga:** nie mylić pakietu Python `models` z routerem `api/routers/models.py`.

Pełna mapa: [docs/repository-structure.md](../docs/repository-structure.md).
