import time
from selenium.webdriver.common.by import By
from datetime import datetime

def check_if_in_db(home_team: str, away_team: str, game_date: str, conn) -> int:
    """Sprawdza, czy mecz jest już w bazie danych.
    Args:
        home_team (str): Nazwa drużyny gospodarzy.
        away_team (str): Nazwa drużyny gości.
        game_date (str): Data meczu.
    Returns:
        int: ID meczu, jeśli istnieje, -1 w przeciwnym razie.
    """
    cursor = conn.cursor()
    query = """
        SELECT m.id 
        FROM matches m 
        WHERE m.home_team = %s AND m.away_team = %s AND m.game_date = %s
        """
    cursor.execute(query, (home_team, away_team, game_date))
    result = cursor.fetchone()
    cursor.close()
    return result[0] if result else -1

def update_db(queries: list, conn) -> bool:
    """Wykonuje listę zapytań SQL w transakcji. Zatwierdza zmiany tylko, jeśli wszystkie zapytania się powiodą.
    
    Argumenty:
        queries (list): Lista zapytań SQL do wykonania.
        conn: Połączenie do bazy danych.
    
    Zwraca:
        bool: True, jeśli wszystkie zapytania wykonano pomyślnie, False w przeciwnym przypadku.
    """
    cursor = conn.cursor()
    try:
        for query in queries:
            cursor.execute(query)
        conn.commit() 
        return True
    except Exception as error:
        conn.rollback()
        print(f"Błąd bazy danych: {error}, cofnięto całe wgranie zmian.") 
        return False
    finally:
        cursor.close() 

def parse_match_date(match_date : str) -> str:
    """ Konwertuje datę meczu w formacie 'dd.mm.yyyy HH:MM' na format 'YYYY-MM-DD HH:MM'
    Args:
        match_date (str): Data meczu w formacie 'dd.mm.yyyy HH:MM'.
    Returns:
        str: Data meczu w formacie 'YYYY-MM-DD HH:MM'.
    """
    date_object = datetime.strptime(match_date, "%d.%m.%Y %H:%M")

    date_formatted = date_object.strftime("%Y-%m-%d %H:%M")

    return date_formatted

def get_match_links(games: str, driver) -> list[str]:
    """Pobiera linki do meczów z podanej strony.
    Args:
        games (str): URL strony z meczami.
        driver: Instancja sterownika Selenium.
    Returns:
        list[str]: Lista linków do meczów.
    """
    links = []
    driver.get(games)
    time.sleep(15)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    for element in game_divs:
        id = element.get_attribute('id').split('_')[2]
        links.append('https://www.flashscore.pl/mecz/{}/#/szczegoly-meczu/statystyki-meczu/0'.format(id))
    return links
