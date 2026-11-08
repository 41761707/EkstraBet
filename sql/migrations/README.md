# Migracje schematu

Runner czyta tylko pliki `V###__nazwa.sql` z tego katalogu. `README.md`
i inne pliki pomija.

## Nazwa

`V002__krotka_nazwa.sql`: trzy cyfry, opis małymi literami i podkreśleniami.
Wzorzec: `V` + trzy cyfry + `__` + `[a-z0-9_]+` + `.sql`.

`V001__baseline.sql` jest zrzutem schematu. Nie edytuj go.

## Od V002

Jeden plik to jedna zmiana schematu. Może zawierać kilka statementów DDL.
Każdy statement to jedna linia albo wiele linii domkniętych średnikiem
na końcu ostatniej linii. Średnik w środku linii runner odrzuca.

W pliku jest tylko struktura: `CREATE`, `ALTER`, `DROP`, kolumny,
`NULL` / `NOT NULL`, `DEFAULT` potrzebny do zapisu, klucze i indeksy.
Bez `CHECK` i bez `ENUM`.

Bez wierszy. W migracji nie ma `INSERT`, `UPDATE`, `DELETE`, `REPLACE`
ani innego DML. Dotyczy to też pierwszej ligi i każdego kolejnego sezonu.
Wiersze wchodzą na bazę matkę poza runnerem, a na test i produkcję przez
backup + restore albo `scripts/sync/sync_local_to_prod.py`.

Kolumna dokładana do tabeli z danymi: najpierw `NULL` albo `NOT NULL`
z `DEFAULT`.

Zaaplikowanego pliku nie wolno edytować. Poprawka jest następnym numerem.

## Która komenda

`baseline` tylko dla pierwszego oznaczenia istniejącej bazy (matka, test,
produkcja z danymi). Nie wykonuje treści `V001`.

`apply` dla pustej bazy i dla każdego następnego pliku `V00N`.

Na trzech istniejących bazach nie uruchamiaj `V001` przez `apply`.

Komendy operatorskie: [docs/deployment-vps.md](../../docs/deployment-vps.md),
sekcja 9.6.

## Po migracji

Gdy API ma pisać do nowej tabeli, w tym samym zadaniu dopisz `GRANT`
w sekcji 9.3 runbooku. Runner grantów nie nadaje. Sam `SELECT` na
`ekstrabet.*` już obejmuje nową tabelę.

Sync wierszy dopiero po `apply` na produkcji. Nowa tabela słownikowa
dostaje `TableSpec` w `scripts/sync/sync_local_to_prod.py`, rodzic FK
przed dzieckiem. Runner synca nie uruchamia.
