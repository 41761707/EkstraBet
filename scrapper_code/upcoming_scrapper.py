from selenium import webdriver
from datetime import date, datetime, timedelta
import db_module
from utils import (
    MatchData, setup_chrome_driver, get_teams_dict,
    fetch_match_elements, parse_round, parse_match_info,
    parse_match_date, get_match_links, update_db, generate_insert_sql
)
from dataclasses import asdict
import argparse

def get_match_data(
    driver: webdriver.Chrome,
    league_id: int,
    season_id: int,
    link: str,
    round_to_d: int,
    team_id: dict[str, int]
) -> dict | int:
    """Pobiera dane nadchodzącego meczu z podanego linku.
    
    Args:
        driver (webdriver.Chrome): Instancja przeglądarki Selenium.
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        link (str): Link do strony z danymi meczu.
        round_to_d (int): Docelowa runda do pobrania (0 = automatyczne).
        team_id (dict[str, int]): Słownik z nazwami drużyn i ich ID.
        
    Returns:
        dict | int: Słownik z danymi meczu lub -1, jeśli mecz nie spełnia kryteriów.
    """
    stat_divs, time_divs, team_divs, score_divs, round_divs = fetch_match_elements(driver, link)
    round_val = parse_round(round_divs)
    match_info = parse_match_info(time_divs, team_divs, score_divs)
    
    try:
        home_team = team_id[match_info[1]]
        away_team = team_id[match_info[3]]
        game_date = parse_match_date(match_info[0])
    except (IndexError, KeyError):
        return -1
    
    # Logika sprawdzania rundz
    if round_to_d == 0:
        try:
            round_to_d = int(round_val)
            max_date = date.today()
        except ValueError as e:
            print(f"Błąd w pobieraniu rundy: {e}")
    
    # Specjalna logika dla ligi 25
    if league_id != 25:
        if int(round_val) != int(round_to_d):
            return -1
    else:
        round_val = 100
        today = date.today()
        max_date = today + timedelta(days=4)
        game_date_obj = datetime.strptime(game_date, "%Y-%m-%d %H:%M").date()
        if game_date_obj > max_date:
            return -1
    
    # Tworzenie obiektu MatchData
    match_data = MatchData(
        league=league_id,
        season=season_id,
        home_team=home_team,
        away_team=away_team,
        game_date=game_date,
        round=round_val
    )
    
    return asdict(match_data)

def to_automate(league_id: int, season_id: int, games: str, round_to_d: int, single_match: bool = False, automate: bool = False) -> None:
    """Automatyzuje pobieranie nadchodzących meczów.
    
    Args:
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        games (str): Link do strony z meczami lub bezpośredni link do meczu.
        round_to_d (int): Numer rundy do pobrania (0 = automatycznie).
        single_match (bool): Czy pobierać tylko jeden mecz (True) czy wszystkie z listy (False).
        automate (bool): Czy automatycznie zapisywać zmiany do bazy danych (True) czy tylko wyświetlać (False).
    """
    conn = db_module.db_connect()
    
    # Sprawdzenie czy istnieją już przyszłe mecze w bazie (tylko gdy nie jest to pojedynczy mecz)
    if not single_match:
        query = """
            SELECT id FROM matches 
            WHERE league = %s AND season = %s 
            AND CAST(game_date AS DATE) >= CURRENT_DATE 
            ORDER BY game_date LIMIT 1
        """
        cursor = conn.cursor()
        cursor.execute(query, (league_id, season_id))
        results = cursor.fetchall()
        cursor.close()
        
        if len(results) > 0:
            print("BLOKADA DODAWANIA NOWYCH SPOTKAŃ GDY W BAZIE ZNAJDUJĄ SIĘ MECZE Z DATĄ PÓŹNIEJSZĄ NIŻ DATA URUCHOMIENIA SKRYPTU")
            conn.close()
            return
    
    driver = setup_chrome_driver()
    
    try:
        team_id = get_teams_dict(league_id, conn)
        print(f"Znalezione drużyny: {team_id}")
        
        # Wybór trybu pobierania linków
        if single_match:
            links = [games]
        else:
            links = get_match_links(games, driver)
        
        inserts = []
        
        for link in links:
            match_data = get_match_data(driver, league_id, season_id, link, round_to_d, team_id)
            if match_data == -1:
                    break
            if round_to_d == 0:
                round_to_d = match_data['round']
            
            sql = generate_insert_sql(MatchData(**match_data))
            inserts.append(sql)
            print(sql)
        
        if inserts:
            if automate:
                update_db(inserts, conn)
        else:
            print("Brak danych do zapisania.")
        
    except ValueError as e:
        print(f"Błąd: {e}")
    finally:
        driver.quit()
        conn.close()

def main() -> None:
    parser = argparse.ArgumentParser(
        description="""Skrypt do scrapowania nadchodzących meczów z Flashscore.

Przykłady użycia:
- Pobieranie nadchodzących meczów (tryb testowy):
  python upcoming_scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/

- Pobieranie nadchodzących meczów z automatycznym zapisem do bazy:
  python upcoming_scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/ --automate

- Pobieranie pojedynczego nadchodzącego meczu:
  python upcoming_scrapper.py 33 11 https://www.flashscore.pl/mecz/pilka-nozna/4GPWXVlS/ --match --automate --round 5

Parametry:
  <id_ligi>         ID ligi w bazie danych
  <id_sezonu>       ID sezonu w bazie danych
  <link>            Link do strony z meczami lub do konkretnego meczu na Flashscore

Uwaga: Bez flagi --automate dane będą tylko wyświetlane, ale nie zapisywane do bazy.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('league_id', type=int, help='ID ligi')
    parser.add_argument('season_id', type=int, help='ID sezonu')
    parser.add_argument('games', help='Link do strony z meczami lub do konkretnego meczu na Flashscore')
    parser.add_argument('--match', action='store_true', 
                       help='Tryb pojedynczego meczu - parametr "games" powinien zawierać bezpośredni link do meczu')
    parser.add_argument('--automate', action='store_true',
                       help='Automatycznie zapisuj zmiany do bazy danych (bez tej flagi dane będą tylko wyświetlane)')
    parser.add_argument('--round', type=int, default=0,
                       help='Numer rundy do pobrania (0 = automatycznie)')
    args = parser.parse_args()
    to_automate(args.league_id, args.season_id, args.games, args.round, args.match, args.automate)
    
if __name__ == '__main__':
    main()