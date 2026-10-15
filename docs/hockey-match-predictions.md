# Predykcje zdarzeń meczowych NHL

Moduł liczy jedną predykcję na mecz z aktualnego składu w `hockey_rosters`.
Liga NHL ma `league_id` 45.

## Skład, z którego liczymy

Źródłem jest wyłącznie `hockey_rosters`. Dostawca NHL sygnalizuje tam
aktualizację, więc wiersz w tabeli jest składem na najbliższy mecz klubu.

Do siły składu i do propsów wchodzą tylko zawodnicy, którzy wychodzą na lód:

- napastnicy (`LW`, `C`, `RW`) z linii 1–4,
- obrońcy (`D`) z linii 1–3,
- bramkarz z linii 1 — jedyny bramkarz w modelu (procent obron i GSAA).

Bramkarz z linii 2 jest rezerwowym. Widać go w składzie, ale nie wchodzi
do lambdy ani do propsów. Linia 0 oraz `is_injured = 1` zostają poza
składem. Puste miejsce na linii nie jest uzupełniane innym zawodnikiem.

Brak rosteru albo brak bramkarza z linii 1 nie pomija meczu. Ta strona
dostaje średnią siłę drużyny i średni procent obron.

## Które mecze wchodzą do przebiegu

Bez `--match-ids` skrypt bierze najbliższy mecz każdego klubu, który da
się przewidzieć. Jutrzejszy mecz back-to-back nie jest liczony na
dzisiejszym rosterze: po pierwszym meczu skład może się zmienić.

`--match-ids` ogranicza przebieg do podanych meczów. Identyfikatory spoza
wyboru są pomijane i wracają w `ignored_match_ids`.

## Jak uruchomić

Z katalogu głównego repozytorium, przy działającej bazie z `.env`:

```bat
models\scripts\run_hockey_predictions.bat
```

Skrypt wykonuje po kolei:

1. `predict-hockey --league-id 45 --write-db --select-finals` — rynki
   drużynowe (zwycięzca, suma goli, obie strzelą i pozostałe rodziny
   z konfiguracji modelu).
2. `predict-hockey-props --league-id 45 --write-db` — beta statystyk
   zawodników (gole, asysty, punkty, strzały). Bez kursów i bez
   rozliczania.
3. `refresh-statistics --write-db` — odświeżenie statystyk modeli.

Samodzielny przebieg na sucho, bez zapisu:

```bat
python models\scripts\model_runner.py predict-hockey --league-id 45
python models\scripts\model_runner.py predict-hockey-props --league-id 45
```

`--write-db` zapisuje wiersze. `--select-finals` przy rynkach drużynowych
wskazuje faworyta rodziny. Przed wstawieniem nowego faworyta skrypt
usuwa poprzedni finał tej rodziny i nierozliczony zakład, w jednej
transakcji. Powtórzenie skryptu po update rosteru zastępuje zmieniony
wynik.

## Co widać w aplikacji

Karta meczu przed pierwszym gwizdkiem bierze skład z `hockey_rosters`,
nie z ostatniego box score. Bramkarz linii 1 jest podpisany jako
starter, bramkarz linii 2 jako rezerwowy. Strona drużyny układa linie
tylko według `hockey_rosters.line`. Ostatni mecz podaje numer na
koszulce i informację, czy zawodnik wtedy wyszedł.

Tabele `hockey_probable_lineups` i `hockey_prediction_runs` zostają
w bazie, ale ten moduł ich nie zapisuje i nie czyta.
