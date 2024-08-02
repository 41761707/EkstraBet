# EkstraBet

## Wersja polska
Rozszerzenie pracy magisterskiej, przewidywanie zdarzeń w meczach piłkarskich z wykorzystaniem sztucznej inteligencji

## Aktualnie obsługiwane zdarzenia
1. 1X2
2. BTTS
3. Dokładna liczba bramek
4. (NOWE) Rozkład prawdopodobieństwa bramek + Over / Under 2.5

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
15. (NOWE) Chance liga + Dywizja 2 (Czechy)
16. (NOWE) Bundesliga + 2. Liga (Austria)

## Planowane rozszerzenia
1. Serie A i Serie B (Brazylia)
2. Liga Profesional (Argentyna)
3. Premiership i 1 Dywizja (Szkocja)
4. TBD


## Opis przebiegu generowania predykcji oraz zakładów
1. Uruchom moduł <i> upcoming_scrapper.py </i> z odpowiednimi parametrami. Zostaną pobrane wszystkie mecze danego sezonu dla danej ligi w trakcie trwania podanej rundy.
2. Po wprowadzeniu meczów do bazy danych (upcoming_scrapper generuje wpisy do bazy danych w formie tekstu, nie robi bezpośrednich wpisów!) wygeneruj predykcje korzystając z modułu <i> main.py </i> uruchamiając go z odpowiednimi parametrami.
3. Pobierz kursy od wybranych bukmacherów korzystając z modułu <i> odds_scraper.py </i>. Pamiętaj o tym, aby nie pobierać kursów ze znacznym wyprzedzeniem
4. Po wprowadzeniu kursów do bazy danych wygeneruj predykcje oraz zakłady korzystając z modułu <i> bet_module.py </i>
5. Po wykonaniu powyższych kroków pod zakładką "Terminarz" dla wybranej kolejki powinny ukazać się predykcje wraz z proponowanymi zakładami

## Opis przebiegu aktualizowania meczów
1. Uruchom moduł <i> update_scrapper.py </i> z odpowiednimi parametrami. Wyniki procesu wprowadź do bazy danych
2. Przeliczyć wyniki przy pomocy moduły <i> recalc_outcome.py</i>
2. Dla wskazanego meczu w zakładce "Terminarz" pojawi się dodatkowa informacja o zrealizowanych predykcjach, zakładach oraz ich poprawności


### Change-log
21.07.2024 - Wykrycie błędu w trakcie testowania modelu goals_ppb, wprowadzenie istotnych poprawek

22.07.2024 - Poprawki w modelu do 1x2

30.07.2024 - Poprawki w generowaniu okna oraz obliczaniu rankingów. Zmiany obejmują istotne mechaniki działania wszystkich modeli

