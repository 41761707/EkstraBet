import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
from dataclasses import dataclass
from typing import Any
import pandas as pd


@dataclass
class MatchData:
    """Klasa reprezentująca dane meczu piłkarskiego.
    
    Attributes:
        league (int): ID ligi.
        season (int): ID sezonu.
        home_team (int): ID drużyny gospodarzy.
        away_team (int): ID drużyny gości.
        game_date (str): Data i czas meczu w formacie 'YYYY-MM-DD HH:MM'.
        home_team_goals (int): Liczba goli drużyny gospodarzy.
        away_team_goals (int): Liczba goli drużyny gości.
        home_team_xg (float): Expected Goals drużyny gospodarzy.
        away_team_xg (float): Expected Goals drużyny gości.
        home_team_bp (int): Posiadanie piłki drużyny gospodarzy (%).
        away_team_bp (int): Posiadanie piłki drużyny gości (%).
        home_team_sc (int): Strzały łącznie drużyny gospodarzy.
        away_team_sc (int): Strzały łącznie drużyny gości.
        home_team_sog (int): Strzały na bramkę drużyny gospodarzy.
        away_team_sog (int): Strzały na bramkę drużyny gości.
        home_team_fk (int): Rzuty wolne drużyny gospodarzy.
        away_team_fk (int): Rzuty wolne drużyny gości.
        home_team_ck (int): Rzuty rożne drużyny gospodarzy.
        away_team_ck (int): Rzuty rożne drużyny gości.
        home_team_off (int): Spalone drużyny gospodarzy.
        away_team_off (int): Spalone drużyny gości.
        home_team_fouls (int): Faule drużyny gospodarzy.
        away_team_fouls (int): Faule drużyny gości.
        home_team_yc (int): Żółte kartki drużyny gospodarzy.
        away_team_yc (int): Żółte kartki drużyny gości.
        home_team_rc (int): Czerwone kartki drużyny gospodarzy.
        away_team_rc (int): Czerwone kartki drużyny gości.
        round (Any): Numer rundy.
        result (str): Wynik meczu ('1' - wygrana gospodarzy, 'X' - remis, '2' - wygrana gości, '0' - nie rozegrany).
        sport_id (int): ID sportu (domyślnie 1 dla piłki nożnej).
    """
    league: int
    season: int
    home_team: int
    away_team: int
    game_date: str
    home_team_goals: int = 0
    away_team_goals: int = 0
    home_team_xg: float = 0
    away_team_xg: float = 0
    home_team_bp: int = 0
    away_team_bp: int = 0
    home_team_sc: int = 0
    away_team_sc: int = 0
    home_team_sog: int = 0
    away_team_sog: int = 0
    home_team_fk: int = 0
    away_team_fk: int = 0
    home_team_ck: int = 0
    away_team_ck: int = 0
    home_team_off: int = 0
    away_team_off: int = 0
    home_team_fouls: int = 0
    away_team_fouls: int = 0
    home_team_yc: int = 0
    away_team_yc: int = 0
    home_team_rc: int = 0
    away_team_rc: int = 0
    round: Any = 0
    result: str = '0'
    sport_id: int = 1


def setup_chrome_driver() -> webdriver.Chrome:
    """Konfiguruje i zwraca instancję przeglądarki Chrome z odpowiednimi opcjami.
    
    Returns:
        webdriver.Chrome: Skonfigurowana instancja przeglądarki Chrome.
    """
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(options=options)


def get_teams_dict(league_id: int, conn) -> dict[str, int]:
    """Pobiera słownik drużyn dla danej ligi z bazy danych.
    
    Args:
        league_id (int): ID ligi.
        conn: Połączenie do bazy danych.
        
    Returns:
        dict[str, int]: Słownik gdzie kluczem jest nazwa drużyny, a wartością ID drużyny.
        
    Raises:
        ValueError: Jeśli nie znaleziono kraju dla podanej ligi lub brak drużyn dla kraju.
    """
    query = f"SELECT country FROM leagues WHERE id = {league_id}"
    country_df = pd.read_sql(query, conn)
    if country_df.empty:
        raise ValueError(f"Nie znaleziono kraju dla ligi ID: {league_id}")
    
    country = country_df.values.flatten()[0]
    query = f"SELECT name, id FROM teams WHERE country = '{country}'"
    teams_df = pd.read_sql(query, conn)
    if teams_df.empty:
        raise ValueError(f"Brak drużyn dla kraju: {country}")
    
    return teams_df.set_index('name')['id'].to_dict()


def fetch_match_elements(driver: webdriver.Chrome, link: str) -> tuple[list, list, list, list, list]:
    """Pobiera elementy meczu z podanego linku.
    
    Args:
        driver (webdriver.Chrome): Instancja przeglądarki Selenium.
        link (str): Link do strony z danymi meczu.
        
    Returns:
        tuple: Krotka zawierająca elementy statystyk, czasu, drużyn, wyniku i rundy.
    """
    driver.get(link)
    time.sleep(3)
    stat_divs = driver.find_elements(By.CLASS_NAME, "wcl-row_2oCpS")
    time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
    score_divs = driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")
    round_divs = driver.find_elements(By.CLASS_NAME, "wcl-scores-overline-03_KIU9F")
    return stat_divs, time_divs, team_divs, score_divs, round_divs


def parse_round(round_divs: list) -> str | int:
    """Parsuje informacje o rundzie z elementów strony.
    
    Args:
        round_divs (list): Lista elementów HTML zawierających informacje o rundzie.
        
    Returns:
        str | int: Zwraca numer rundy jako string lub 0, jeśli nie znaleziono.
    """
    round_val = 0
    for div in round_divs:
        round_info = div.text.strip()
        round_val = round_info.split(" ")[-1]
    return round_val


def parse_match_info(time_divs: list, team_divs: list, score_divs: list) -> list[str]:
    """Parsuje informacje o meczu z elementów strony.
    
    Args:
        time_divs (list): Lista elementów HTML zawierających czas meczu.
        team_divs (list): Lista elementów HTML zawierających nazwy drużyn.
        score_divs (list): Lista elementów HTML zawierających wyniki meczu.
        
    Returns:
        list: Lista zawierająca informacje o meczu, takie jak czas, drużyny i wynik.
    """
    match_info = []
    for div in time_divs:
        match_info.append(div.text.strip())
    for div in team_divs:
        match_info.append(div.text.strip())
    for div in score_divs:
        match_info.append(div.text.strip())
    return match_info


def parse_score(score_str: str) -> tuple[int, int]:
    """Parsuje wynik meczu z tekstu.
    
    Args:
        score_str (str): Tekst zawierający wynik meczu.
        
    Returns:
        tuple[int, int]: Krotka zawierająca liczbę goli drużyny gospodarzy i gości.
    """
    score = score_str.split('\n')
    home_goals = int(score[0])
    away_goals = int(score[2])
    return home_goals, away_goals


def parse_stats(stats: list[str], match_data: MatchData) -> MatchData:
    """Parsuje statystyki meczu z listy elementów i aktualizuje MatchData.
    
    Args:
        stats (list[str]): Lista stringów zawierających statystyki meczu.
        match_data (MatchData): Obiekt z danymi meczu do aktualizacji.
        
    Returns:
        MatchData: Zaktualizowany obiekt z danymi meczu.
    """
    stat_map = {
        'Oczekiwane gole (xG)': ('home_team_xg', 'away_team_xg', float),
        'Posiadanie piłki': ('home_team_bp', 'away_team_bp', lambda x: int(x[:-1])),
        'Strzały łącznie': ('home_team_sc', 'away_team_sc', int),
        'Strzały na bramkę': ('home_team_sog', 'away_team_sog', int),
        'Rzuty wolne': ('home_team_fk', 'away_team_fk', int),
        'Rzuty rożne': ('home_team_ck', 'away_team_ck', int),
        'Spalone': ('home_team_off', 'away_team_off', int),
        'Faule': ('home_team_fouls', 'away_team_fouls', int),
        'Żółte kartki': ('home_team_yc', 'away_team_yc', int),
        'Czerwone kartki': ('home_team_rc', 'away_team_rc', int),
    }
    
    for element in stats:
        stat = element.split('\n')
        if len(stat) < 3:
            continue
        key = stat[1]
        if key in stat_map:
            home_key, away_key, conv = stat_map[key]
            try:
                setattr(match_data, home_key, conv(stat[0]))
                setattr(match_data, away_key, conv(stat[2]))
            except Exception:
                continue
    return match_data


def generate_insert_sql(match_data: MatchData) -> str:
    """Generuje zapytanie SQL INSERT dla danych meczu.
    
    Args:
        match_data (MatchData): Obiekt z danymi meczu.
        
    Returns:
        str: Zapytanie SQL INSERT.
    """
    return (
        f"INSERT INTO matches (league, season, home_team, away_team, game_date, "
        f"home_team_goals, away_team_goals, home_team_xg, away_team_xg, home_team_bp, away_team_bp, "
        f"home_team_sc, away_team_sc, home_team_sog, away_team_sog, home_team_fk, away_team_fk, "
        f"home_team_ck, away_team_ck, home_team_off, away_team_off, home_team_fouls, away_team_fouls, "
        f"home_team_yc, away_team_yc, home_team_rc, away_team_rc, round, result, sport_id) VALUES ("
        f"{match_data.league}, {match_data.season}, {match_data.home_team}, {match_data.away_team}, "
        f"'{match_data.game_date}', {match_data.home_team_goals}, {match_data.away_team_goals}, "
        f"{match_data.home_team_xg}, {match_data.away_team_xg}, {match_data.home_team_bp}, {match_data.away_team_bp}, "
        f"{match_data.home_team_sc}, {match_data.away_team_sc}, {match_data.home_team_sog}, {match_data.away_team_sog}, "
        f"{match_data.home_team_fk}, {match_data.away_team_fk}, {match_data.home_team_ck}, {match_data.away_team_ck}, "
        f"{match_data.home_team_off}, {match_data.away_team_off}, {match_data.home_team_fouls}, {match_data.away_team_fouls}, "
        f"{match_data.home_team_yc}, {match_data.away_team_yc}, {match_data.home_team_rc}, {match_data.away_team_rc}, "
        f"{match_data.round}, '{match_data.result}', {match_data.sport_id});"
    )


def check_if_in_db(home_team: str, away_team: str, game_date: str = None, round_num: str = None, season: int = None, conn=None) -> int:
    """Sprawdza, czy mecz jest już w bazie danych.
    
    Funkcja umożliwia wyszukiwanie meczu na dwa sposoby:
    1. Według daty meczu (parametr game_date)
    2. Według kolejki i sezonu (parametry round_num i season)
    
    Args:
        home_team (str): Nazwa drużyny gospodarzy.
        away_team (str): Nazwa drużyny gości.
        game_date (str, opcjonalny): Data meczu. Wymagana, jeśli nie podano round_num i season.
        round_num (str, opcjonalny): Numer kolejki. Wymagana, jeśli nie podano game_date.
        season (int, opcjonalny): ID sezonu. Wymagany wraz z round_num.
        conn: Połączenie do bazy danych.
        
    Returns:
        int: ID meczu, jeśli istnieje, -1 w przeciwnym razie.
    """
    cursor = conn.cursor()
    try:
        if game_date is not None:
            # Wyszukiwanie według daty
            query = """
                SELECT m.id 
                FROM matches m 
                WHERE m.home_team = %s AND m.away_team = %s AND m.game_date = %s
                """
            cursor.execute(query, (home_team, away_team, game_date))
        else:
            # Wyszukiwanie według kolejki i sezonu
            # game_date może być None więc nie wiem czemu to jest wyszarzone?
            query = """ SELECT m.id 
                FROM matches m 
                WHERE m.home_team = %s AND m.away_team = %s AND m.round = %s AND m.season = %s
                """
            cursor.execute(query, (home_team, away_team, round_num, season))
        
        result = cursor.fetchone()
        return result[0] if result else -1
    finally:
        cursor.close()

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
        list[str]: Lista linków do meczów ze statystykami.
    """
    links = []
    driver.get(games)
    time.sleep(15)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    for element in game_divs:
        # Pobierz link bezpośrednio z elementu <a>
        a_tag = element.find_element(By.TAG_NAME, "a")
        href = a_tag.get_attribute("href")
        if href:
            # Przekształć link na format ze statystykami
            if "?" in href:
                base_link, query = href.split("?", 1)
                stats_link = f"{base_link}szczegoly/statystyki/0/?{query}"
            else:
                stats_link = f"{href}szczegoly/statystyki/0/"
            links.append(stats_link)
    return links

def get_special_rounds_dict(conn) -> dict[int, str]:
    """Pobiera słownik rund specjalnych z bazy danych.
    
    Args:
        conn: Połączenie do bazy danych.
        
    Returns:
        dict[int, str]: Słownik gdzie kluczem jest ID rundy, a wartością nazwa rundy.
    """
    query = "SELECT id, name FROM special_rounds"
    special_rounds_df = pd.read_sql(query, conn)
    return special_rounds_df.set_index('id')['name'].to_dict()
