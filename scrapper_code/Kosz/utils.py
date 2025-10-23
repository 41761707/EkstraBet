import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
from dataclasses import dataclass
from typing import Any
import pandas as pd


@dataclass
class BasketballMatchData:
    """Klasa reprezentująca podstawowe dane meczu koszykarskiego.
    
    Attributes:
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        home_team (int): ID drużyny gospodarzy.
        away_team (int): ID drużyny gości.
        match_date (str): Data i czas meczu w formacie 'YYYY-MM-DD HH:MM'.
        home_team_score (int): Punkty drużyny gospodarzy.
        away_team_score (int): Punkty drużyny gości.
        round (int): Numer rundy (100 dla sezonu regularnego, 900+ dla playoff).
        result (int): Wynik meczu (1 - wygrana gospodarzy, 0 - remis, 2 - wygrana gości).
        sport_id (int): ID sportu (domyślnie 2 dla koszykówki).
    """
    league: int
    season: int
    home_team: int
    away_team: int
    game_date: str
    home_team_goals: int = 0
    away_team_goals: int = 0
    round: int = 100
    result: int = 0
    sport_id: int = 3


@dataclass
class BasketballMatchStatsAdd:
    """Klasa reprezentująca dodatkowe statystyki meczu koszykarskiego.
    
    Attributes odpowiadające tabeli BASKETBALL_MATCHES_ADD:
        match_id (int): ID meczu w bazie danych.
        
        Rzuty z gry:
        home_team_field_goals_attempts (int): Liczba oddanych rzutów z gry przez drużynę gospodarzy.
        away_team_field_goals_attempts (int): Liczba oddanych rzutów z gry przez drużynę gości.
        home_team_field_goals_made (int): Liczba trafionych rzutów z gry przez drużynę gospodarzy.
        away_team_field_goals_made (int): Liczba trafionych rzutów z gry przez drużynę gości.
        home_team_field_goals_acc (float): Skuteczność rzutów z gry drużyny gospodarzy.
        away_team_field_goals_acc (float): Skuteczność rzutów z gry drużyny gości.
        
        Rzuty za 2 punkty:
        home_team_2_p_field_goals_attempts (int): Liczba oddanych rzutów za 2 punkty przez drużynę gospodarzy.
        away_team_2_p_field_goals_attempts (int): Liczba oddanych rzutów za 2 punkty przez drużynę gości.
        home_team_2_p_field_goals_made (int): Liczba trafionych rzutów za 2 punkty przez drużynę gospodarzy.
        away_team_2_p_field_goals_made (int): Liczba trafionych rzutów za 2 punkty przez drużynę gości.
        home_team_2_p_acc (float): Skuteczność rzutów za 2 punkty drużyny gospodarzy.
        away_team_2_p_acc (float): Skuteczność rzutów za 2 punkty drużyny gości.
        
        Rzuty za 3 punkty:
        home_team_3_p_field_goals_attempts (int): Liczba oddanych rzutów za 3 punkty przez drużynę gospodarzy.
        away_team_3_p_field_goals_attempts (int): Liczba oddanych rzutów za 3 punkty przez drużynę gości.
        home_team_3_p_field_goals_made (int): Liczba trafionych rzutów za 3 punkty przez drużynę gospodarzy.
        away_team_3_p_field_goals_made (int): Liczba trafionych rzutów za 3 punkty przez drużynę gości.
        home_team_3_p_acc (float): Skuteczność rzutów za 3 punkty drużyny gospodarzy.
        away_team_3_p_acc (float): Skuteczność rzutów za 3 punkty drużyny gości.
        
        Rzuty wolne:
        home_team_ft_attempts (int): Liczba oddanych rzutów wolnych przez drużynę gospodarzy.
        away_team_ft_attempts (int): Liczba oddanych rzutów wolnych przez drużynę gości.
        home_team_ft_made (int): Liczba trafionych rzutów wolnych przez drużynę gospodarzy.
        away_team_ft_made (int): Liczba trafionych rzutów wolnych przez drużynę gości.
        home_team_ft_acc (float): Skuteczność rzutów wolnych drużyny gospodarzy.
        away_team_ft_acc (float): Skuteczność rzutów wolnych drużyny gości.
        
        Zbiórki:
        home_team_off_rebounds (int): Liczba ofensywnych zbiórek drużyny gospodarzy.
        away_team_off_rebounds (int): Liczba ofensywnych zbiórek drużyny gości.
        home_team_def_rebounds (int): Liczba defensywnych zbiórek drużyny gospodarzy.
        away_team_def_rebounds (int): Liczba defensywnych zbiórek drużyny gości.
        home_team_rebounds_total (int): Łączna liczba zbiórek drużyny gospodarzy.
        away_team_rebounds_total (int): Łączna liczba zbiórek drużyny gości.
        
        Pozostałe statystyki:
        home_team_assists (int): Liczba asyst drużyny gospodarzy.
        away_team_assists (int): Liczba asyst drużyny gości.
        home_team_blocks (int): Liczba bloków drużyny gospodarzy.
        away_team_blocks (int): Liczba bloków drużyny gości.
        home_team_turnovers (int): Liczba strat drużyny gospodarzy.
        away_team_turnovers (int): Liczba strat drużyny gości.
        home_team_steals (int): Liczba przechwytów drużyny gospodarzy.
        away_team_steals (int): Liczba przechwytów drużyny gości.
        home_team_personal_fouls (int): Liczba przewinień osobistych drużyny gospodarzy.
        away_team_personal_fouls (int): Liczba przewinień osobistych drużyny gości.
        home_team_technical_fouls (int): Liczba przewinień technicznych drużyny gospodarzy.
        away_team_technical_fouls (int): Liczba przewinień technicznych drużyny gości.
    """
    match_id: int = 0
    home_team_field_goals_attempts: int = -1
    away_team_field_goals_attempts: int = -1
    home_team_field_goals_made: int = -1
    away_team_field_goals_made: int = -1
    home_team_field_goals_acc: float = -1.0
    away_team_field_goals_acc: float = -1.0
    home_team_2_p_field_goals_attempts: int = -1
    away_team_2_p_field_goals_attempts: int = -1
    home_team_2_p_field_goals_made: int = -1
    away_team_2_p_field_goals_made: int = -1
    home_team_2_p_acc: float = -1.0
    away_team_2_p_acc: float = -1.0
    home_team_3_p_field_goals_attempts: int = -1
    away_team_3_p_field_goals_attempts: int = -1
    home_team_3_p_field_goals_made: int = -1
    away_team_3_p_field_goals_made: int = -1
    home_team_3_p_acc: float = -1.0
    away_team_3_p_acc: float = -1.0
    home_team_ft_attempts: int = -1
    away_team_ft_attempts: int = -1
    home_team_ft_made: int = -1
    away_team_ft_made: int = -1
    home_team_ft_acc: float = -1.0
    away_team_ft_acc: float = -1.0
    home_team_off_rebounds: int = -1
    away_team_off_rebounds: int = -1
    home_team_def_rebounds: int = -1
    away_team_def_rebounds: int = -1
    home_team_rebounds_total: int = -1
    away_team_rebounds_total: int = -1
    home_team_assists: int = -1
    away_team_assists: int = -1
    home_team_blocks: int = -1
    away_team_blocks: int = -1
    home_team_turnovers: int = -1
    away_team_turnovers: int = -1
    home_team_steals: int = -1
    away_team_steals: int = -1
    home_team_personal_fouls: int = -1
    away_team_personal_fouls: int = -1
    home_team_technical_fouls: int = -1
    away_team_technical_fouls: int = -1


@dataclass
class BasketballPlayerStats:
    """Klasa reprezentująca statystyki zawodnika w meczu koszykarskim.
    
    Attributes odpowiadające tabeli BASKETBALL_MATCH_PLAYER_STATS:
        match_id (int): ID meczu w bazie danych.
        team_id (int): ID drużyny zawodnika.
        player_id (int): ID zawodnika.
        points (int): Liczba punktów zdobytych przez zawodnika.
        rebounds (int): Liczba zbiórek zdobytych przez zawodnika.
        assists (int): Liczba asyst wykonanych przez zawodnika.
        time_played (str): Czas gry zawodnika w formacie 'MM:SS'.
        field_goals_made (int): Liczba trafionych rzutów z gry.
        field_goals_attempts (int): Liczba oddanych rzutów z gry.
        two_p_field_goals_made (int): Liczba trafionych rzutów za 2 punkty.
        two_p_field_goals_attempts (int): Liczba oddanych rzutów za 2 punkty.
        three_p_field_goals_made (int): Liczba trafionych rzutów za 3 punkty.
        three_p_field_goals_attempts (int): Liczba oddanych rzutów za 3 punkty.
        ft_made (int): Liczba trafionych rzutów wolnych.
        ft_attempts (int): Liczba oddanych rzutów wolnych.
        plus_minus (int): Wskaźnik plus/minus zawodnika.
        off_rebounds (int): Liczba ofensywnych zbiórek.
        def_rebounds (int): Liczba defensywnych zbiórek.
        personal_fouls (int): Liczba przewinień osobistych.
        steals (int): Liczba przechwytów.
        turnovers (int): Liczba strat.
        blocked_shots (int): Liczba zablokowanych rzutów.
        blocks_against (int): Liczba zablokowanych rzutów przeciwko zawodnikowi.
        technical_fouls (int): Liczba przewinień technicznych.
    """
    match_id: int = 0
    team_id: int = 0
    player_id: int = 0
    points: int = -1
    rebounds: int = -1
    assists: int = -1
    time_played: str = '00:00'
    field_goals_made: int = -1
    field_goals_attempts: int = -1
    two_p_field_goals_made: int = -1
    two_p_field_goals_attempts: int = -1
    three_p_field_goals_made: int = -1
    three_p_field_goals_attempts: int = -1
    ft_made: int = -1
    ft_attempts: int = -1
    plus_minus: int = -1
    off_rebounds: int = -1
    def_rebounds: int = -1
    personal_fouls: int = -1
    steals: int = -1
    turnovers: int = -1
    blocked_shots: int = -1
    blocks_against: int = -1
    technical_fouls: int = -1


@dataclass
class BasketballMatchRoster:
    """Klasa reprezentująca skład drużyny w meczu koszykarskim.
    
    Attributes odpowiadające tabeli BASKETBALL_MATCH_ROSTERS:
        match_id (int): ID meczu w bazie danych.
        team_id (int): ID drużyny.
        player_id (int): ID zawodnika.
        number (int): Numer zawodnika w meczu.
        starter (int): Flaga czy zawodnik był w pierwszej piątce (1 - tak, 0 - nie).
    """
    match_id: int = 0
    team_id: int = 0
    player_id: int = 0
    number: int = -1
    starter: int = 0


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


def parse_match_date(match_date: str) -> str:
    """Konwertuje datę meczu z formatu FlashScore na format bazy danych.
    
    Args:
        match_date (str): Data w formacie "dd.mm.yyyy HH:MM"
        
    Returns:
        str: Data w formacie "yyyy-mm-dd HH:MM" gotowa do wstawienia do bazy danych
    """
    date_object = datetime.strptime(match_date, "%d.%m.%Y %H:%M")
    date_formatted = date_object.strftime("%Y-%m-%d %H:%M")
    return date_formatted


def get_match_links(games: str, driver) -> list[str]:
    """Pobiera linki do wszystkich meczów koszykarskich z strony wyników FlashScore.
    
    Args:
        games (str): URL strony z wynikami meczów na FlashScore
        driver: WebDriver Selenium
        
    Returns:
        list[str]: Lista linków do szczegółów poszczególnych meczów w formacie z ?mid=
    """
    links = []
    driver.get(games)
    time.sleep(5)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    
    for element in game_divs:
        try:
            link_element = element.find_element(By.TAG_NAME, "a")
            href = link_element.get_attribute('href')
            if href and 'flashscore.pl/mecz/' in href and '?mid=' in href:
                links.append(href)
            else:
                print(f"UWAGA: Nie znaleziono linku w nowym formacie dla elementu {element.get_attribute('id')}")
        except Exception as e:
            print(f"BŁĄD: Nie można pobrać linku dla elementu {element.get_attribute('id')}: {e}")
    
    print(f"Znaleziono {len(links)} linków do meczów koszykarskich")
    return links


def check_if_in_db(home_team: int, away_team: int, match_date: str = None, round_num: int = None, season_id: int = None, conn=None) -> int:
    """Sprawdza, czy mecz koszykarski jest już w bazie danych.
    
    Funkcja umożliwia wyszukiwanie meczu na dwa sposoby:
    1. Według daty meczu (parametr match_date)
    2. Według kolejki i sezonu (parametry round_num i season_id)
    
    Args:
        home_team (int): ID drużyny gospodarzy.
        away_team (int): ID drużyny gości.
        match_date (str, opcjonalny): Data meczu w formacie 'YYYY-MM-DD HH:MM'. Wymagana, jeśli nie podano round_num i season_id.
        round_num (int, opcjonalny): Numer kolejki. Wymagana, jeśli nie podano match_date.
        season_id (int, opcjonalny): ID sezonu. Wymagany wraz z round_num.
        conn: Połączenie do bazy danych.
        
    Returns:
        int: ID meczu, jeśli istnieje, -1 w przeciwnym razie.
    """
    cursor = conn.cursor()
    try:
        if match_date is not None:
            # Wyszukiwanie według daty
            query = """
                SELECT m.id 
                FROM matches m 
                WHERE m.home_team = %s AND m.away_team = %s AND m.game_date = %s
                """
            cursor.execute(query, (home_team, away_team, match_date))
        else:
            # Wyszukiwanie według kolejki i sezonu
            query = """
                SELECT m.id 
                FROM matches m 
                WHERE m.home_team = %s AND m.away_team = %s AND m.round = %s AND m.season = %s
                """
            cursor.execute(query, (home_team, away_team, round_num, season_id))
        
        result = cursor.fetchone()
        return result[0] if result else -1
    except Exception as e:
        print(f"Błąd podczas sprawdzania meczu w bazie danych: {e}")
        return -1
    finally:
        cursor.close()


def parse_score(score_str: str) -> tuple[int, int]:
    """Parsuje wynik meczu koszykarskiego z tekstu.
    
    Args:
        score_str (str): Tekst zawierający wynik meczu
        
    Returns:
        tuple[int, int]: Krotka zawierająca punkty drużyny gospodarzy i gości
    """
    score = score_str.split('\n')
    home_score = int(score[0])
    away_score = int(score[2])
    return home_score, away_score


def calculate_result(home_score: int, away_score: int) -> int:
    """Oblicza wynik meczu na podstawie punktów.
    
    Args:
        home_score (int): Punkty drużyny gospodarzy
        away_score (int): Punkty drużyny gości
        
    Returns:
        int: 1 - wygrana gospodarzy, 2 - wygrana gości, 0 - remis (bardzo rzadko w koszykówce)
    """
    if home_score > away_score:
        return 1
    elif away_score > home_score:
        return 2
    else:
        return 0  # Remis - bardzo rzadko w koszykówce


def build_basketball_url(base_link: str, path: str) -> str:
    """Buduje URL do konkretnej sekcji meczu koszykarskiego na FlashScore.
    
    Args:
        base_link (str): Podstawowy link do meczu z ?mid=
        path (str): Ścieżka do konkretnej sekcji
        
    Returns:
        str: Pełny URL do żądanej sekcji
    """
    path_mapping = {
        "statystyki/0": "statystyki/0",
        "sklady": "sklady", 
        "statystyki-gracza": "statystyki-gracza"
    }
    
    parts = base_link.split('?mid=')
    base_url = parts[0].rstrip('/')
    mapped_path = path_mapping.get(path, path)
    return f"{base_url}/szczegoly/{mapped_path}/?mid={parts[1]}"


def safe_int(text: str, default: int = 0) -> int:
    """Bezpieczna konwersja tekstu na liczbę całkowitą z obsługą pustych wartości.
    
    Args:
        text (str): Tekst do konwersji
        default (int): Wartość domyślna zwracana w przypadku błędu lub pustego tekstu
        
    Returns:
        int: Skonwertowana liczba lub wartość domyślna
    """
    try:
        if text == '-' or text == '' or text is None:
            return default
        return int(text.strip())
    except (ValueError, AttributeError):
        return default


def safe_plus_minus(text: str, default: int = 0) -> int:
    """Bezpieczna konwersja tekstu wskaźnika plus/minus na liczbę całkowitą.
    
    Obsługuje formaty: '+15', '-7', '0', '-'
    
    Args:
        text (str): Tekst do konwersji (np. '+15', '-7')
        default (int): Wartość domyślna zwracana w przypadku błędu lub pustego tekstu
        
    Returns:
        int: Skonwertowany wskaźnik plus/minus lub wartość domyślna
    """
    try:
        if text == '-' or text == '' or text is None:
            return default
        text = text.strip()
        if text.startswith('+'):
            return int(text[1:])
        return int(text)
    except (ValueError, AttributeError):
        return default


def update_db(queries: list, conn) -> bool:
    """Wykonuje listę zapytań SQL w transakcji dla koszykówki.
    
    Args:
        queries (list): Lista zapytań SQL do wykonania.
        conn: Połączenie do bazy danych.
    
    Returns:
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
        print(f"Błąd bazy danych koszykówki: {error}, cofnięto całe wgranie zmian.") 
        return False
    finally:
        cursor.close()