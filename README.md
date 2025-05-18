# EkstraBet

## Wersja polska
Rozszerzenie pracy magisterskiej, przewidywanie zdarzeń w meczach piłkarskich z wykorzystaniem sztucznej inteligencji

## Wykorzystane technologie
1. Silnik bazodanowy: <b>MySQL</b>
2. Frontend: Framework <b> streamlit (Python)</b> pozwalajacy na ładne oraz schludne prezentowanie danych analitycznych
3. Backend: <b> Python </b>

## Zawartość strony
1. Graficzne przedstawienie przewidywań modelów nauczania głębokiego odnośnie rozpatrywanych zdarzeń (lista zdarzeń poniżej)
2. Graficzne przedstawienie zaawansowanych statystyk zespołów (zwycięstwa / porażki / remisy / zdobyte i stracone bramki itd.)
3. Tabele ligowe z podziałem na dom i wyjazd zgodnie z analizowanymi zdarzeniami
4. Graficzne przedstawienie osiągnięć modelu w zakładach z podziałem na procent poprawnych predykcji oraz zysk (bądź stratę) względem bukmacherów
5. Przedstawienie charakterystyk ligowych pomagających w analizie przyszłych spotkań
4. (NOWE) Informacje o osiągnięciach poszczególnych zawodników w lidze NHL + pełen game log oraz boxscore

## Aktualnie obsługiwane zdarzenia
1. 1X2
2. BTTS
3. Dokładna liczba bramek
4. (NOWE) Rozkład prawdopodobieństwa bramek, na podstawie którego generowany jest Over / Under 2.5

## Aktualnie obsługiwane ligi
1. Ekstraklasa + 1. Liga (Polska)
2. Premier League + Championship (Anglia)
3. Serie A + Serie B (Włochy)
4. Ligue 1 + Ligue 2 (Francja)
5. LaLiga + LaLiga2 (Hiszpania)
6. Bundesliga + 2. Bundesliga (Niemcy)
7. K League 1 + K League 2 (Korea Południowa)
8. MLS (USA)
9. J1 League + J2 League (Japonia)
10. Jupiler League + Challenger Pro League (Belgia)
11. Swiss Super League + Challenge League (Szwajcaria)
12. Super Lig + 1.Lig (Turcja)
13. Liga Portugal + Liga Portugal 2 (Portugalia)
14. Eredivisie + Eerste Divisie (Holandia)
15. Chance liga + Dywizja 2 (Czechy)
16. Bundesliga + 2. Liga (Austria)
17. (NOWE) A-League (Australia)
18. (NOWE) Serie A + Serie B (Brazylia)
19. (NOWE) Torneo Betano (Argentyna)
20. (NOWE) NHL (Hokej, NA)

## Planowane rozszerzenia
3. Premiership i 1 Dywizja (Szkocja)
4. NBA (Koszykówka, NA)

## Jak poprawnie definiować linki w modułach do pobierania meczów
W pliku <i> scrapper_wrapper.py </i> w liście <i> links </i> zdefiniuj ligi, dla których chcesz pobrać mecze. Ligi definiujemy poprzez podanie stringa o następującej formule \
```[id ligi] [id sezonu] [link do strony z meczami] [tryb działania]```

## Opis przebiegu pobierania przyszłych meczów
Umieść odpowiednie linki w tablicy oraz uruchom skrypt zgodnie z poniższym wzorcem: \
```[id ligi] [id sezonu] [link do strony z meczami] [upcoming]``` \
Upcoming jest wymaganym parametrem przekazującym informację do skrytpu o potrzebie pobrania nadchodzących meczów
Istotnym jest, że skrypt pobiera tylko mecze NADCHODZĄCEJ KOLEJKI - aktualnie pobieranie i przewidywanie więcej niż jednego meczu wprzód jest niewspierane

## Opis przebieg pobierania przeszłych meczów
Umieść odpowiednie linki w tablicy oraz uruchom skrypt zgodnie z poniższym wzorcem: \
```[id ligi] [id sezonu] [link do strony z meczami] [historic]``` \
Historic jest wymaganym parametrem informującym skrypt o pobraniu spotkań, które już się odbyły oraz które nie mają swoich wpisów w bazie danych. Skrypt kończy działanie gdy natrafi na spotkanie, które już znajduje się w bazie danych.

## Opis przebiegu aktualizowania spotkań
Umieść odpowiednie linki w tablicy oraz uruchom skrypt zgodnie z poniższym wzorcem: \
```[id ligi] [id sezonu] [link do strony z meczami] update``` \
Skrypt aktualizuje spotkania, które odbyły się wcześniej niż data uruchomienia skryptu. (Np. gdy skrypt uruchomiono 22.10.2025 to zaktualizowane zostaną mecze rozegrane 21.10.2025 i wcześniej). Skrypt kończy działanie dopiero, gdy zaktualizuje wszystkie mecze

## Opis przebiegu generowania predykcji oraz zakładów
TO-DO (opis po poprawkach)

## Opis przebiegu trenowania modelów
TO-DO (opis po poprawkach)

