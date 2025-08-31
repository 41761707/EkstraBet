from selenium import webdriver
from db_module import db_connect
from utils import (
    MatchData, setup_chrome_driver, get_teams_dict, 
    fetch_match_elements, parse_round, parse_match_info, 
    parse_score, parse_stats, generate_insert_sql,
    check_if_in_db, parse_match_date, get_match_links, update_db
)
from dataclasses import asdict
import argparse


def get_match_data(
    driver: webdriver.Chrome,
    league_id: int,
    season_id: int,
    link: str,
    team_id: dict[str, int],
    conn
) -> dict[str, int] | int:
    """Pobiera dane meczu z podanego linku.
    
    Args:
        driver (webdriver.Chrome): Instancja przeglądarki Selenium.
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        link (str): Link do strony z danymi meczu.
        team_id (dict[str, int]): Słownik z nazwami drużyn i ich ID.
        conn: Połączenie do bazy danych.
        
    Returns:
        dict[str, int]: Słownik z danymi meczu lub -1,
        jeśli mecz już istnieje w bazie danych.
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
    
    match_data = MatchData(
        league=league_id,
        season=season_id,
        home_team=home_team,
        away_team=away_team,
        game_date=game_date,
        round=round_val
    )
    
    match_id = check_if_in_db(match_data.home_team, match_data.away_team, game_date=match_data.game_date, conn=conn)
    #if match_id != -1:
    #    return -1
    
    score_str = match_info[5] if len(match_info) > 5 else ''
    home_goals, away_goals = parse_score(score_str)
    match_data.home_team_goals = home_goals
    match_data.away_team_goals = away_goals
    
    if home_goals > away_goals:
        match_data.result = '1'
    elif home_goals == away_goals:
        match_data.result = 'X'
    else:
        match_data.result = '2'
    
    stats = [div.text.strip() for div in stat_divs]
    match_data = parse_stats(stats, match_data)
    
    return asdict(match_data)


def to_automate(league_id: int, season_id: int, games: str, single_match: bool = False, automate: bool = False) -> None:
    """Automatyzuje scrapowanie wyników meczów.
    
    Args:
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        games (str): Link do strony z wynikami na flashscorze lub bezpośredni link do meczu.
        single_match (bool): Czy pobierać tylko jeden mecz (True) czy wszystkie z listy (False).
        automate (bool): Czy automatycznie zapisywać zmiany do bazy danych (True) czy tylko wyświetlać (False).
    """
    conn = db_connect()
    driver = setup_chrome_driver()
    
    try:
        team_id = get_teams_dict(league_id, conn)
        print(f"Znalezione drużyny: {team_id}")
        inserts = []
        # Wybór trybu pobierania linków
        if single_match:
            links = [games]
        else:
            links = get_match_links(games, driver)
        
        for link in links:
            match_data = get_match_data(driver, league_id, season_id, link, team_id, conn)
            if match_data == -1:
                print("Mecz już istnieje w bazie danych lub wystąpił błąd parsowania.")
                driver.quit()
                conn.close()
                return
            
            sql = generate_insert_sql(MatchData(**match_data))
            inserts.append(sql)
            print(sql)
        
        if inserts:
            if automate:
                update_db(inserts, conn)
                print("Pomyślnie zapisano dane do bazy.")
        else:
            print("Brak danych do zapisania.")
        
    except ValueError as e:
        print(f"Błąd: {e}")
    finally:
        driver.quit()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="""Skrypt do scrapowania wyników meczów z Flashscore.

Przykłady użycia:
- Pobieranie wszystkich meczów ligi i sezonu (tryb testowy):
  python scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/

- Pobieranie wszystkich meczów z automatycznym zapisem do bazy:
  python scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/ --automate

- Pobieranie pojedynczego meczu z zapisem do bazy:
  python scrapper.py 33 11 https://www.flashscore.pl/mecz/pilka-nozna/4GPWXVlS/#/szczegoly-meczu/statystyki-meczu/0 --match --automate

Parametry:
  <id_ligi>         ID ligi w bazie danych
  <id_sezonu>       ID sezonu w bazie danych
  <link>            Link do strony z wynikami lub do konkretnego meczu na Flashscore

Uwaga: Bez flagi --automate dane będą tylko wyświetlane, ale nie zapisywane do bazy.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('league_id', type=int, help='ID ligi')
    parser.add_argument('season_id', type=int, help='ID sezonu')
    parser.add_argument('games', help='Link do strony z wynikami lub do konkretnego meczu na Flashscore')
    parser.add_argument('--match', action='store_true', 
                       help='Tryb pojedynczego meczu - parametr "games" powinien zawierać bezpośredni link do meczu')
    parser.add_argument('--automate', action='store_true',
                       help='Automatycznie zapisuj zmiany do bazy danych (bez tej flagi dane będą tylko wyświetlane)')
    args = parser.parse_args()
    to_automate(args.league_id, args.season_id, args.games, args.match, args.automate)


if __name__ == '__main__':
    main()
