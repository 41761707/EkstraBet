# Migracje schematu

Runner czyta tylko pliki `V###__nazwa.sql` z tego katalogu. `README.md`
i inne pliki pomija.

## Nazwa

`V002__krotka_nazwa.sql`: trzy cyfry, opis małymi literami i podkreśleniami.
Wzorzec: `V` + trzy cyfry + `__` + `[a-z0-9_]+` + `.sql`.

`V001__baseline.sql` jest zrzutem schematu. Nie edytuj go.

## Od V002

Jeden plik to jeden statement: jedna linia albo wiele linii domkniętych
jednym średnikiem na końcu ostatniej linii.

Dozwolone: kolumny, `NULL` / `NOT NULL`, `DEFAULT` potrzebny do zapisu,
klucze i indeksy. Bez `CHECK` i bez `ENUM`.

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
w sekcji 9.3 runbooku. Runner grantów nie nadaje.

Sync wierszy dopiero po `apply` na produkcji.
