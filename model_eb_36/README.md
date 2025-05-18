# MODEL MODULE

## Uruchomienie skryptu
1. Zdefniuj odpowiednie parametry uruchomienia w pliku <b> main.py </b>:
- Id lig, dla których ma się uruchomić skrypt (pozostawienie tablicy pustej skutkuje uruchomieniem skryptu dla wszystkich lig)
- Id krajów, dla których ma się uruchomić skrypt (pozostawienie country = -1 skutkuje uruchomieniem skryptu dla wszystkich krajów)
- Rozmiar okna <b>(window_size)</b> - informacja o tym ile meczów wstecz należy wziąć pod uwagę w analizie
- Nazwy kolumn, których dane mają wziąć udział w treningu <b> (feature_columns) </b>
- Typy rankingów (<b>rating_types</b>) 
- Definicje kolumn, na podstawie których liczone są rankingi 

2. Uruchom skrypt <b> main.py </b> z odpowiednimi parametrami 
```
[model_type] [model_mode] [load_weights]
```
- model_type defniuje typ modelu (aktualnie wspierane: winner / btts / goals / exact)
- model_mode definiuje tryb, w którym uruchamiany jest skrypt (aktualnie wspierane: train / predict)
- load_weights definiuje potrzebę załadowania wag z wcześniej utworzonych modelów (aktualnie wspierane: 0 (nie ładuj) / 1 (załaduj))

## Opis mechanizmu trenowania modelu
TO-DO: Opis