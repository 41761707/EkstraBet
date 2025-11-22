import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime

from sklearn import base
from utils import update_db, parse_match_date
import argparse

from db_module import db_connect


def check_odds_in_db(match_id: int, conn) -> bool:
    """
    Sprawdza, czy kursy dla danego meczu już istnieją w bazie danych.
    Args:
        match_id (int): ID meczu.
        conn: Połączenie z bazą danych.
    Returns:
        bool: True, jeśli kursy istnieją, False w przeciwnym razie.
    """
    cursor = conn.cursor()
    match_id = int(match_id)
    query = "SELECT COUNT(*) FROM odds WHERE match_id = %s"
    cursor.execute(query, (match_id,))
    result = cursor.fetchone()[0]
    cursor.close()
    return result > 0


def get_match_id(link: str, driver, matches_df: pd.DataFrame, league_id: int, season_id: int, team_id: dict) -> int:
    """    Pobiera ID meczu na podstawie linku do meczu.
    Args:
        link (str): Link do meczu.
        driver: Sterownik Selenium.
        matches_df (DataFrame): DataFrame z danymi meczów.
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        team_id (dict): Słownik z ID drużyn.
    Returns:
        int: ID meczu, jeśli znaleziono, -1 w przeciwnym razie.
    """
    id = -1
    driver.get(link)
    time.sleep(2)
    match_info = []
    match_data = {
        'league': 0,
        'season': 0,
        'home_team': 0,
        'away_team': 0,
        'game_date': 0
    }
    # Znajdź wszystkie divy o klasie 'duelParticipant__startTime'
    time_divs = driver.find_elements(
        By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(
        By.CLASS_NAME, "participant__participantName")
    # Dodaj zawartość divów do listy danych
    for div in time_divs:
        match_info.append(div.text.strip())
    for div in team_divs:
        match_info.append(div.text.strip())

    match_data['league'] = league_id  # id ligi
    match_data['season'] = season_id  # id sezonu
    match_data['home_team'] = team_id.get(
        match_info[1], None)  # nazwa gospodarzy
    match_data['away_team'] = team_id.get(match_info[3], None)
    try:
        match_data['game_date'] = parse_match_date(match_info[0])
    except Exception as e:
        print(f"Błąd parsowania daty meczu: {e}")
        return -1

    # Sprawdź, czy wszystkie dane są dostępne
    if None in [match_data['home_team'], match_data['away_team'], match_data['game_date']]:
        print("Brak wymaganych danych meczu (gospodarz, goście lub data).")
        return -1
    record = matches_df.loc[(matches_df['home_team'] == match_data['home_team']) &
                            (matches_df['away_team'] == match_data['away_team']) &
                            (matches_df['game_date'] == match_data['game_date'])]
    if record.empty:
        return -1

    try:
        id = record.iloc[0]['id']
    except Exception as e:
        print(f"Brak meczu, błąd: {e}")
        return
    return id

def get_odds(id: int, link: str, driver, bookie_dict: dict, type: str) -> list:
    """Pobiera kursy bukmacherskie dla danego meczu.
    Args:
        id (int): ID meczu.
        link (str): Link do strony z kursami.
        driver: Sterownik Selenium.
        bookie_dict (dict): Słownik ID : Nazwa bukmacherów.
        type (str): Typ kursów (np. "result", "over_under", "btts").
    Returns:
        list: Lista zapytań SQL do wstawienia kursów bukmacherskich.
    """
    driver.get(link)
    time.sleep(2)
    book_divs = driver.find_elements(By.CLASS_NAME, "ui-table__row")
    bookies = []
    for book in book_divs:
        try:
            # Szukamy tagu img wewnątrz obecnego diva
            img_tag = book.find_element(By.TAG_NAME, "img")
            # Pobieramy wartość atrybutu title z tagu img
            title = img_tag.get_attribute("title").strip("'")
            # Dodajemy tytuł do listy
            bookies.append(title)
        except:
            # Obsługujemy przypadek, gdy tag img lub atrybut title nie jest obecny
            bookies.append(None)
    if type == "result":
        return get_1x2_odds(id, book_divs, bookies, bookie_dict)
    elif type == "ou":
        return get_over_under_odds(id, book_divs, bookies, bookie_dict)
    elif type == "btts":
        return get_btts_odds(id, book_divs, bookies, bookie_dict)


def get_1x2_odds(id: int, book_divs: list, bookies: list, bookie_dict: dict) -> list:
    """Pobiera kursy 1X2 dla danego meczu.
    Args:
        id (int): ID meczu.
        book_divs (list): Lista divów z kursami.
        bookies (list): Lista bukmacherów.
        bookie_dict (dict): Słownik ID : Nazwa bukmacherów.
    Returns:
        list: Lista zapytań SQL do wstawienia kursów 1X2.
    """
    # 1 - zwyciestwo gospodarza
    # 2 - remis
    # 3 - zwyciestwo gosci
    inserts = []
    for i in range(len(book_divs)):
        text = book_divs[i].text.strip()
        text_tab = text.split('\n')
        if len(text_tab) >= 3 and all(x != '-' for x in text_tab):
            text_1 = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                id, bookie_dict[bookies[i]], 1, text_tab[0])
            text_2 = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                id, bookie_dict[bookies[i]], 2, text_tab[1])
            text_3 = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                id, bookie_dict[bookies[i]], 3, text_tab[2])
            print(text_1)
            print(text_2)
            print(text_3)
            inserts.append(text_1)
            inserts.append(text_2)
            inserts.append(text_3)
        else:
            # Dodajemy tylko te kursy, które nie są "-"
            for idx, event in enumerate([1, 2, 3]):
                if len(text_tab) > idx and text_tab[idx] != '-':
                    text_sql = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                        id, bookie_dict.get(bookies[i]), event, text_tab[idx])
                    print(text_sql)
                    inserts.append(text_sql)
    return inserts


def get_over_under_odds(id: int, book_divs: list, bookies: list, bookie_dict: dict) -> list:
    """Pobiera kursy over/under dla danego meczu.
    Args:
        id (int): ID meczu.
        book_divs (list): Lista divów z kursami.
        bookies (list): Lista bukmacherów.
        bookie_dict (dict): Słownik ID : Nazwa bukmacherów.
    Returns:
        list: Lista zapytań SQL do wstawienia kursów over/under."""
    # 8 - o2,5
    # 12 - u2,5
    inserts = []
    for i in range(len(book_divs)):
        text = book_divs[i].text.strip()
        text_tab = text.split('\n')
        # print(text_tab)
        if len(text_tab) >= 3 and text_tab[0] == '2.5':
            # Sprawdzamy czy kursy są dostępne
            if text_tab[1] != '-':
                text_1 = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                    id, bookie_dict.get(bookies[i]), 8, text_tab[1])
                print(text_1)
                inserts.append(text_1)
            if text_tab[2] != '-':
                text_2 = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                    id, bookie_dict.get(bookies[i]), 12, text_tab[2])
                print(text_2)
                inserts.append(text_2)
    return inserts


def get_btts_odds(id: int, book_divs: list, bookies: list, bookie_dict: dict) -> list:
    """Pobiera kursy BTTS dla danego meczu.
    Args:
        id (int): ID meczu.
        book_divs (list): Lista divów z kursami.
        bookies (list): Lista bukmacherów.
        bookie_dict (dict): Słownik ID : Nazwa bukmacherów.
    Returns:
        list: Lista zapytań SQL do wstawienia kursów BTTS.
    """
    # 6 - btts
    # 172 - no btts
    inserts = []
    for i in range(len(book_divs)):
        text = book_divs[i].text.strip()
        text_tab = text.split('\n')
        if len(text_tab) >= 2:
            if text_tab[0] != '-':
                text_1 = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                    id, bookie_dict.get(bookies[i]), 6, text_tab[0])
                print(text_1)
                inserts.append(text_1)
            if text_tab[1] != '-':
                text_2 = "INSERT INTO odds(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(
                    id, bookie_dict.get(bookies[i]), 172, text_tab[1])
                print(text_2)
                inserts.append(text_2)
    return inserts


def get_links(game_divs) -> list:
    """Pobiera linki do meczów z divów.
    Args:
        game_divs: Lista divów z meczami.
    Returns:
        list: Lista linków do meczów.
    """
    links = []
    for element in game_divs:
        # znajdź pierwszy <a> w danym divie
        a_tag = element.find_element(By.TAG_NAME, "a")
        href = a_tag.get_attribute("href")
        if href:
            links.append(href)
    return links


def get_data(games, driver, matches_df, league_id, season_id, team_id, conn, mode, automate, skip=0) -> None:
    """Pobiera dane o kursach bukmacherskich dla meczów.
    Args:
        games: Lista gier do przetworzenia.
        driver: Sterownik Selenium.
        matches_df: DataFrame z danymi meczów.
        league_id: ID ligi.
        season_id: ID sezonu.
        team_id: ID drużyny.
        conn: Połączenie z bazą danych.
        mode: Tryb działania (daily, historical, match).
        automate: Czy automatycznie zapisywać kursy do bazy danych.
        skip: Liczba meczów do pominięcia.
    """
    #Nie pobieraj meczow jesli mam go podanego doslownie jako jedyny link
    if mode != 'match':
        driver.get(games)
        time.sleep(5)
        game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
        links = get_links(game_divs)
    else:
        links = [games]
    for link in links[skip:len(matches_df)]:
        match_id = get_match_id(link, driver, matches_df,
                                league_id, season_id, team_id)
        if check_odds_in_db(match_id, conn):
            print(f"Kursy już istnieją dla meczu o id: {match_id}, wychodzę...")
            return
        if match_id == -1:
            print(f"Brak meczu w bazie danych, pomijam")
            continue
        bookie_dict = {
            'STS.pl': 4,
            'eFortuna.pl': 3,
            'Betclic.pl': 2,
            'BETFAN': 6,
            'Etoto': 7,
            'LV BET': 5,
            'Superbet.pl': 1,
            'Fuksiarz.pl': 8
        }
        base_link, query = link.split("?", 1)  # oddzielamy część przed ? i parametry (?mid=...)
        base_link = base_link.replace("szczegoly/", "")
        print(base_link)
        result_inserts = get_odds(
            match_id,
            f"{base_link}kursy/kursy-1x2/koniec-meczu/?{query}",
            driver,
            bookie_dict,
            "result"
        )

        ou_inserts = get_odds(
            match_id,
            f"{base_link}kursy/powyzej-ponizej/koniec-meczu/?{query}",
            driver,
            bookie_dict,
            "ou"
        )

        btts_inserts = get_odds(
            match_id,
            f"{base_link}kursy/obie-druzyny-strzela/koniec-meczu/?{query}",
            driver,
            bookie_dict,
            "btts"
        )
        if automate:
            update_db(result_inserts, conn)
            update_db(ou_inserts, conn)
            update_db(btts_inserts, conn)


def odds_to_automate(league_id: int, season_id: int, games: str, mode: str, skip: int = 0, automate: bool = False) -> None:
    """Automatyzuje proces pobierania kursów bukmacherskich dla wybranej ligi i sezonu.

    Funkcja łączy się z bazą danych, inicjalizuje przeglądarkę i pobiera kursy w zależności od wybranego trybu.

    Args:
        league_id (int): ID ligi w bazie danych
        season_id (int): ID sezonu w bazie danych
        games (str): Link do strony z meczami na Flashscore
        mode (str): Tryb działania ('daily', 'historical', 'match')
        skip (int, optional): Liczba najwcześniejszych meczów do pominięcia. Defaults to 0.
        automate (bool): Czy automatycznie zapisywać kursy do bazy danych (True) czy tylko wyświetlać (False).

    Note:
        Tryby działania:
        - 'daily': pobiera kursy dla meczów z bieżącego dnia
        - 'historical': pobiera kursy dla meczów historycznych
        - 'match': pobiera kursy dla konkretnego meczu
    """
    # Inicjalizacja parametrów i połączenia z bazą danych
    conn = db_connect()

    try:
        # Pobranie danych o meczach dla danej ligi i sezonu
        matches_df = pd.read_sql(
            f"SELECT * FROM matches where league = {league_id} and season = {season_id}", conn)

        # Pobranie kraju dla danej ligi
        country_df = pd.read_sql(
            f"select country from leagues where id = {league_id}", conn)
        country = country_df.values.flatten()

        # Pobranie słownika z ID drużyn dla danego kraju
        teams_df = pd.read_sql(
            f"select name, id from teams where country = {country[0]}", conn)
        team_id = teams_df.set_index('name')['id'].to_dict()
        # Konfiguracja i inicjalizacja przeglądarki Chrome
        options = webdriver.ChromeOptions()
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        driver = webdriver.Chrome(options=options)
        # Wybór odpowiedniej funkcji w zależności od trybu
        if mode == 'daily':
            matches_df = matches_df[matches_df['game_date'].dt.date == datetime.today(
            ).date()]
            if matches_df.empty:
                print("Brak meczów na dziś")
                return
            get_data(games, driver, matches_df, league_id,
                     season_id, team_id, conn, mode, automate)
        elif mode == 'historical':
            if matches_df.empty:
                print("Brak meczów w bazie danych")
                return
            # Pomijanie najwcześniejszych meczów
            if skip >= len(matches_df):
                print("Liczba do pominięcia przekracza liczbę meczów")
                return
            get_data(games, driver, matches_df, league_id,
                     season_id, team_id, conn, mode, automate, skip)
        elif mode == 'match':
            match_id = get_match_id(
                games, driver, matches_df, league_id, season_id, team_id)
            if match_id == -1:
                print("Brak meczu w bazie danych")
                return
            matches_df = matches_df[matches_df['id'] == match_id]
            get_data(games, driver, matches_df, league_id,
                     season_id, team_id, conn, mode, automate)
    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania kursów: {str(e)}")
    finally:
        conn.close()
        driver.quit()


def main() -> None:
    """Główna funkcja do uruchomienia skryptu do pobierania kursów bukmacherskich."""

    parser = argparse.ArgumentParser(
        description="""Skrypt do pobierania kursów bukmacherskich z Flashscore.
        Przykłady użycia:
        - Dla kursów dziennych (tryb testowy):
          python odds_scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/ daily
        - Dla kursów dziennych z zapisem do bazy:
          python odds_scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/ daily --automate
        - Dla kursów historycznych:
          python odds_scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/wyniki historical --skip 5 --automate
        - Dla konkretnego meczu:
          python odds_scrapper.py 19 11 https://www.flashscore.pl/mecz/pilka-nozna/W4853zVH/ match --automate""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('league_id', type=int, help='ID ligi')
    parser.add_argument('season_id', type=int, help='ID sezonu')
    parser.add_argument('games', help='Link do meczu/meczów na Flashscore')
    parser.add_argument('mode', choices=['daily', 'historical', 'match'],
                        help='Tryb działania: daily (mecze dzisiejsze), historical (mecze historyczne), match (konkretny mecz)')
    parser.add_argument('--skip', type=int, default=0,
                        help='Liczba najwcześniejszych meczów do pominięcia (działa tylko w trybie historical)')
    parser.add_argument('--automate', action='store_true',
                        help='Automatyczny zapis kursów do bazy danych (domyślnie tryb testowy)')
    args = parser.parse_args()
    # Sprawdzenie czy parametr skip jest używany tylko w trybie historical
    if args.skip != 0 and args.mode != 'historical':
        parser.error(
            "Parametr --skip może być używany tylko w trybie historical")
    
    # Informowanie o trybie działania
    if args.automate:
        print("Tryb produkcyjny - kursy będą zapisywane do bazy danych.")
    else:
        print("Tryb testowy - kursy będą tylko wyświetlane.")
    
    odds_to_automate(args.league_id, args.season_id,
                     args.games, args.mode, args.skip, args.automate)


if __name__ == '__main__':
    main()
