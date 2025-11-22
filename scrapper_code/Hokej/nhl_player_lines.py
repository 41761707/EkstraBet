import time
from selenium.webdriver.common.by import By
import re
import unicodedata
from utils import setup_chrome_driver
import db_module

@staticmethod
def normalize(text):
    """
    Normalizuje tekst usuwając znaki diakrytyczne i specjalne.
    Args:
        text (str): Tekst do normalizacji
    Returns:
        str: Znormalizowany tekst
    """
    SPECIAL_MAPPINGS = {
        'ü': 'ue',
        'ö': 'oe', 
        'ä': 'ae',
        'ß': 'ss',
        'ø': 'o',
        'å': 'a',
        'æ': 'ae'
    }
    if not text:
        return ""
    text = text.lower().strip()
    # Zamiana specjalnych znaków niemieckich/skandynawskich
    for char, replacement in SPECIAL_MAPPINGS.items():
        text = text.replace(char, replacement)
    # Usunięcie znaków diakrytycznych
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('ASCII')
    # Usunięcie nawiasów i ich zawartości (np. "Sebastian (CAR)" -> "Sebastian")
    text = re.sub(r'\([^)]*\)', '', text).strip()
    # Usunięcie wielokrotnych spacji
    text = re.sub(r'\s+', ' ', text)
    return text

@staticmethod
def create_normalized_full_name(first_name, last_name):
    """
    Tworzy pełną znormalizowaną nazwę.
    Args:
        first_name (str): Imię zawodnika
        last_name (str): Nazwisko zawodnika
        
    Returns:
        str: Znormalizowana pełna nazwa
    """
    norm_first = normalize(first_name)
    norm_last = normalize(last_name)
    return f"{norm_first} {norm_last}"

def open_at_player_props(url):
    url_parts = url.rsplit('=', 1)
    return url_parts[0] + '=46' #hardcodowana wartosc dla zawodnikow na superbecie

def get_team_ids(teams, conn):
    """
    Pobiera ID drużyn z bazy danych, zachowując kolejność: teams[0] = gospodarz, teams[1] = gość.
    Args:
        teams (list): Lista nazw drużyn [gospodarz, gość]
        conn: Połączenie z bazą danych
    Returns:
        list: Lista ID drużyn [home_team_id, away_team_id]
    """
    cursor = conn.cursor()
    # Pobierz ID gospodarza
    query_home = "SELECT id FROM teams WHERE name = %s"
    cursor.execute(query_home, (teams[0],))
    home_result = cursor.fetchone()
    # Pobierz ID gościa
    query_away = "SELECT id FROM teams WHERE name = %s"
    cursor.execute(query_away, (teams[1],))
    away_result = cursor.fetchone()
    cursor.close()
    if not home_result or not away_result:
        return []
    return [home_result[0], away_result[0]]

def get_match_id_from_teams(teams_dict, conn):
    cursor = conn.cursor()
    query = """
    SELECT id FROM matches 
    WHERE home_team = %s AND away_team = %s
    ORDER BY game_date DESC LIMIT 1"""
    cursor.execute(query, (teams_dict[0], teams_dict[1]))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def get_match_info(driver):
    teams = []
    match_info_text = driver.find_elements(By.CLASS_NAME, 'teams-container')[0].text
    teams = [element for element in match_info_text.split('\n')]
    
    # Zabezpieczenie dla Washington - zmiana na pełną nazwę
    for i in range(len(teams)):
        if teams[i] == 'Washington':
            teams[i] = 'Washington Capitals'
    
    return teams

def find_player_id_by_name(first_name, last_name, team_ids, conn):
    """
    Wyszukuje ID zawodnika na podstawie imienia i nazwiska.
    Wykorzystuje tabelę mapowań oraz normalizację nazw.
    Args:
        first_name (str): Imię zawodnika z Superbet
        last_name (str): Nazwisko zawodnika z Superbet
        team_ids (list): Lista ID drużyn biorących udział w meczu
        conn: Połączenie z bazą danych
    Returns:
        int: ID zawodnika lub None jeśli nie znaleziono
    """
    BOOKMAKER_ID = 1  # Superbet
    cursor = conn.cursor()
    normalized_search = create_normalized_full_name(first_name, last_name)
    # Krok 1: Sprawdzenie w tabeli mapowań
    query_mapping = """
    SELECT player_id FROM player_name_mappings 
    WHERE bookmaker_id = %s AND bookmaker_common_name = %s
    LIMIT 1"""
    cursor.execute(query_mapping, (BOOKMAKER_ID, normalized_search))
    result = cursor.fetchone()
    if result:
        cursor.close()
        return result[0]
    # Krok 2: Wyszukiwanie po znormalizowanych nazwach w tabeli players
    query_players = """
    SELECT p.id, p.first_name, p.last_name 
    FROM players p
    WHERE p.current_club IN (%s, %s)"""
    cursor.execute(query_players, (team_ids[0], team_ids[1]))
    players = cursor.fetchall()
    for player_id, db_first, db_last in players:
        normalized_db = create_normalized_full_name(db_first, db_last)
        if normalized_db == normalized_search:
            # Krok 3: Automatyczne dodanie mapowania
            insert_mapping = """
            INSERT INTO player_name_mappings 
            (player_id, bookmaker_id, bookmaker_first_name, bookmaker_last_name, bookmaker_common_name)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP"""
            cursor.execute(insert_mapping, (player_id, BOOKMAKER_ID, first_name, last_name, normalized_search))
            conn.commit()
            cursor.close()
            return player_id
    cursor.close()
    print(f"Nie znaleziono zawodnika: {first_name} {last_name} (znormalizowane: {normalized_search})")
    return None

def insert_player_prop_line(player_id, match_id, team_id, event_id, line, odds, conn):
    BOOKMAKER_ID = 1
    cursor = conn.cursor()
    query = """
    INSERT INTO player_props_lines (player_id, match_id, team_id, event_id, bookmaker_id, line, odds)
    VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    cursor.execute(query, (player_id, match_id, team_id, event_id, BOOKMAKER_ID, line, odds))
    cursor.close()

def process_player_props(player_props_list, match_id, team_ids, event_id_over, event_id_under, conn):
    # Stała krotka: (player_name - direction line, odds) (dlatego i+=2)
    for i in range(1, len(player_props_list), 2):
        if i + 1 >= len(player_props_list):
            break
        prop_info = player_props_list[i]
        odds = player_props_list[i + 1]
        # Rozdziel nazwisko, imię i linię
        parts = prop_info.split(' - ')
        if len(parts) != 2:
            continue
        name_part = parts[0]
        prop_part = parts[1]
        # Rozdziel imię i nazwisko
        name_parts = name_part.split(', ')
        if len(name_parts) != 2:
            continue
        last_name = name_parts[0]
        first_name = name_parts[1]
        #TMP obsluga Stutzla i Aho
        if last_name == 'Stuetzle':
            last_name = 'Stützle'
        if first_name == 'Sebastian (CAR)':
            first_name = 'Sebastian'
        prop_details = prop_part.split(' ')
        if len(prop_details) != 2:
            continue
        direction = prop_details[0]
        line = float(prop_details[1])
        event_id = event_id_under if direction == 'poniżej' else event_id_over
        player_id = find_player_id_by_name(first_name, last_name, team_ids, conn)
        if not player_id:
            continue
        cursor = conn.cursor()
        cursor.execute("SELECT current_club FROM players WHERE id = %s", (player_id,))
        result = cursor.fetchone()
        cursor.close()
        team_id = result[0] if result else None
        if not team_id:
            continue
        
        insert_player_prop_line(player_id, match_id, team_id, event_id, line, odds, conn)

def process_player_goals_only_over(player_goals_list, match_id, team_ids, conn):
    EVENT_ID_GOALS_OVER = 196
    GOALS_LINE = 0.5
    # Stała krotka: (player_name, goals_odds) (dlatego i+=2)
    for i in range(1, len(player_goals_list), 2):
        if i + 1 >= len(player_goals_list):
            break
        player_name = player_goals_list[i]
        odds = player_goals_list[i + 1]
        name_parts = player_name.split(', ')
        if len(name_parts) != 2:
            continue
        last_name = name_parts[0]
        first_name = name_parts[1]
        player_id = find_player_id_by_name(first_name, last_name, team_ids, conn)
        if not player_id:
            continue
        cursor = conn.cursor()
        cursor.execute("SELECT current_club FROM players WHERE id = %s", (player_id,))
        result = cursor.fetchone()
        cursor.close()
        team_id = result[0] if result else None
        if not team_id:
            continue
        insert_player_prop_line(player_id, match_id, team_id, EVENT_ID_GOALS_OVER, GOALS_LINE, odds, conn)

def process_player_sog_table_format(player_sog_list, match_id, team_ids, conn):
    EVENT_ID_SOG_OVER = 190
    EVENT_ID_SOG_UNDER = 191
    i = 4
    #Stała krotka: (player_name, line_under, odds_under, line_over, odds_over) (dlatego i+=5)
    while i < len(player_sog_list):
        if player_sog_list[i] == 'POKAŻ MNIEJ':
            break
        if i + 4 >= len(player_sog_list):
            break
        player_name = player_sog_list[i]
        line_under = float(player_sog_list[i + 1])
        odds_under = player_sog_list[i + 2]
        line_over = float(player_sog_list[i + 3])
        odds_over = player_sog_list[i + 4]
        name_parts = player_name.split(' ')
        if len(name_parts) < 2:
            i += 5
            continue
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:])
        player_id = find_player_id_by_name(first_name, last_name, team_ids, conn)
        if not player_id:
            i += 5
            continue
        cursor = conn.cursor()
        cursor.execute("SELECT current_club FROM players WHERE id = %s", (player_id,))
        result = cursor.fetchone()
        cursor.close()
        team_id = result[0] if result else None
        if not team_id:
            i += 5
            continue
        insert_player_prop_line(player_id, match_id, team_id, EVENT_ID_SOG_UNDER, line_under, odds_under, conn)
        insert_player_prop_line(player_id, match_id, team_id, EVENT_ID_SOG_OVER, line_over, odds_over, conn)
        i += 5

def get_player_points(driver, match_id, team_ids, conn):
    EVENT_ID_POINTS_OVER = 192
    EVENT_ID_POINTS_UNDER = 193
    
    player_points = driver.find_elements(By.CSS_SELECTOR, "div[data-id='Zawodnik - liczba punktów (z dogrywką) 236265']")[0].text
    player_points = [prop for prop in player_points.split('\n')]
    
    process_player_props(player_points, match_id, team_ids, EVENT_ID_POINTS_OVER, EVENT_ID_POINTS_UNDER, conn)

def get_player_goals(driver, match_id, team_ids, conn):
    player_goals = driver.find_elements(By.CSS_SELECTOR, "div[data-id='Zawodnik - strzeli gola (z dogrywką) 236259']")[0].text
    player_goals = [prop for prop in player_goals.split('\n')]
    
    process_player_goals_only_over(player_goals, match_id, team_ids, conn)

def get_player_assists(driver, match_id, team_ids, conn):
    EVENT_ID_ASSISTS_OVER = 194
    EVENT_ID_ASSISTS_UNDER = 195
    
    player_assists = driver.find_elements(By.CSS_SELECTOR, "div[data-id='Zawodnik - liczba asyst (z dogrywką) 236264']")[0].text
    player_assists = [prop for prop in player_assists.split('\n')]
    process_player_props(player_assists, match_id, team_ids, EVENT_ID_ASSISTS_OVER, EVENT_ID_ASSISTS_UNDER, conn)

def get_player_sog(driver, match_id, team_ids, conn):
    sog_section = driver.find_elements(By.CSS_SELECTOR, "div[data-id='Celne strzały zawodnika (z dogrywką) 230023']")[0]
    # Kliknij przycisk "POKAŻ WIĘCEJ" jeśli istnieje
    try:
        show_more_button = sog_section.find_element(By.XPATH, ".//button[contains(text(), 'POKAŻ WIĘCEJ')]")
        driver.execute_script("arguments[0].click();", show_more_button)
        time.sleep(2)
    except:
        pass
    
    player_sog = sog_section.text
    player_sog = [prop for prop in player_sog.split('\n')]
    
    process_player_sog_table_format(player_sog, match_id, team_ids, conn)

def download_player_lines(driver):
    """
    Pobiera linie zawodników NHL ze strony i zwraca je jako listę słowników.
    Args:
        driver: Obiekt WebDriver do obsługi przeglądarki.
    """
    main_url = "https://superbet.pl/zaklady-bukmacherskie/hokej-na-lodzie/usa/nhl/wszystko?ct=m"
    driver.get(main_url)
    time.sleep(5)
    match_divs = driver.find_elements(By.CSS_SELECTOR, 'div.single-event div.event__header__append a')
    match_urls = [div.get_attribute('href') for div in match_divs]
    #print(match_urls)
    conn = db_module.db_connect()
    for url in match_urls:
        player_url = open_at_player_props(url)
        driver.get(player_url)
        time.sleep(5)
        teams = get_match_info(driver)
        print(teams)
        teams_ids = get_team_ids(teams, conn)
        print(teams_ids)
        match_id = get_match_id_from_teams(teams_ids, conn)
        print(match_id)
        time.sleep(5)
        get_player_points(driver, match_id, teams_ids, conn)
        time.sleep(5)
        get_player_goals(driver, match_id, teams_ids, conn)
        time.sleep(5)
        get_player_assists(driver, match_id, teams_ids, conn)
        time.sleep(10)
        get_player_sog(driver, match_id, teams_ids, conn)
        conn.commit()
    conn.close()

def main():
    driver = setup_chrome_driver()
    download_player_lines(driver)

if __name__ == '__main__':
    main()