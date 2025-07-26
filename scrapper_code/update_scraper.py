from math import sin
import pandas as pd
from selenium import webdriver
import db_module
from utils import (
    MatchData, setup_chrome_driver, get_teams_dict,
    fetch_match_elements, parse_round, parse_match_info,
    parse_score, parse_stats, parse_match_date,
    get_match_links, update_db
)
from dataclasses import asdict
import argparse


def update_match_data(
    driver: webdriver.Chrome,
    league_id: int,
    season_id: int,
    link: str,
    match_id: int,
    team_id: dict[str, int]
) -> dict:
    """Aktualizuje dane meczu na podstawie linku do meczu.

    Args:
        driver (webdriver.Chrome): Instancja przeglądarki Selenium.
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        link (str): Link do strony z danymi meczu.
        match_id (int): ID meczu w bazie danych.
        team_id (dict[str, int]): Słownik z nazwami drużyn i ich ID.

    Returns:
        dict: Słownik z zaktualizowanymi danymi meczu.
    """
    stat_divs, time_divs, team_divs, score_divs, _ = fetch_match_elements(
        driver, link)
    match_info = parse_match_info(time_divs, team_divs, score_divs)

    # Przygotowanie podstawowych danych meczu
    match_data = MatchData(
        league=league_id,
        season=season_id,
        home_team=team_id[match_info[1]],
        away_team=team_id[match_info[3]],
        game_date=parse_match_date(match_info[0])
    )

    # Parsowanie wyniku meczu
    score_str = match_info[5] if len(match_info) > 5 else ''
    home_goals, away_goals = parse_score(score_str)
    match_data.home_team_goals = home_goals
    match_data.away_team_goals = away_goals

    # Określenie wyniku
    if home_goals > away_goals:
        match_data.result = '1'
    elif home_goals == away_goals:
        match_data.result = 'X'
    else:
        match_data.result = '2'

    # Parsowanie statystyk
    stats = [div.text.strip() for div in stat_divs]
    match_data = parse_stats(stats, match_data)

    # Dodanie ID meczu do słownika
    match_dict = asdict(match_data)
    match_dict['id'] = match_id

    return match_dict


def get_match_id(
    link: str,
    driver: webdriver.Chrome,
    matches_df: pd.DataFrame,
    team_id: dict[str, int]
) -> int:
    """Pobiera ID meczu z bazy danych na podstawie linku.

    Args:
        link (str): Link do strony z meczem.
        driver (webdriver.Chrome): Instancja przeglądarki Selenium.
        matches_df (pd.DataFrame): DataFrame z meczami z bazy danych.
        team_id (dict[str, int]): Słownik z nazwami drużyn i ich ID.

    Returns:
        int: ID meczu z bazy danych lub -1, jeśli nie znaleziono.
    """
    _, time_divs, team_divs, score_divs, _ = fetch_match_elements(
        driver, link)
    match_info = parse_match_info(time_divs, team_divs, score_divs)

    try:
        home_team = team_id[match_info[1]]
        away_team = team_id[match_info[3]]
        game_date = parse_match_date(match_info[0])
    except (IndexError, KeyError):
        print("#Nie udało się sparsować danych meczu!")
        return -1

    # Wyszukanie meczu w DataFrame
    record = matches_df.loc[
        (matches_df['home_team'] == home_team) &
        (matches_df['away_team'] == away_team) &
        (matches_df['game_date'] == game_date)
    ]

    if not record.empty:
        return record.iloc[0]['id']
    else:
        print("#Nie udało się znaleźć meczu!")
        return -1


def to_automate(league_id: int, season_id: int, games: str, single_match: bool = False, automate: bool = False) -> None:
    """Automatyzuje aktualizację danych meczów w bazie danych.

    Args:
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        games (str): Link do strony z meczami lub pojedynczy link do meczu.
        single_match (bool): Czy aktualizować tylko jeden mecz (True) czy wszystkie z listy (False).
        automate (bool): Czy automatycznie zapisywać zmiany do bazy danych (True) czy tylko wyświetlać (False).
    """
    conn = db_module.db_connect()
    # Pobranie meczów do aktualizacji
    query = """
        SELECT * FROM matches 
        WHERE league = %s AND season = %s AND result = '0' 
    """
    if not single_match:
        query += "AND CAST(game_date AS DATE) <= DATE_SUB(CURDATE(), INTERVAL 1 DAY)"
    matches_df = pd.read_sql(query, conn, params=(league_id, season_id))
    if matches_df.empty and not single_match:
        print("BRAK SPOTKAŃ")
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
        no_matches = len(matches_df)

        for link in links:
            match_id = get_match_id(
                link, driver, matches_df, team_id)
            if match_id == -1:
                continue
            match_data = update_match_data(
                driver, league_id, season_id, link, match_id, team_id)
            sql = '''UPDATE `ekstrabet`.`matches` SET  `game_date` = '{game_date}', \
`home_team_goals` = '{home_team_goals}', \
`away_team_goals` = '{away_team_goals}', \
`home_team_xg` = '{home_team_xg}', \
`away_team_xg` = '{away_team_xg}', \
`home_team_bp` = '{home_team_bp}', \
`away_team_bp` = '{away_team_bp}', \
`home_team_sc` = '{home_team_sc}', \
`away_team_sc` = '{away_team_sc}', \
`home_team_sog` = '{home_team_sog}', \
`away_team_sog` = '{away_team_sog}', \
`home_team_fk` = '{home_team_fk}', \
`away_team_fk` = '{away_team_fk}', \
`home_team_ck` = '{home_team_ck}', \
`away_team_ck` = '{away_team_ck}', \
`home_team_off` = '{home_team_off}', \
`away_team_off` = '{away_team_off}', \
`home_team_fouls` = '{home_team_fouls}', \
`away_team_fouls` = '{away_team_fouls}', \
`home_team_yc` = '{home_team_yc}', \
`away_team_yc` = '{away_team_yc}', \
`home_team_rc` = '{home_team_rc}', \
`away_team_rc` = '{away_team_rc}', \
`result` = '{result}' \
WHERE (`id` = '{id}');'''.format(**match_data)
            print(sql)
            inserts.append(sql)
            no_matches = no_matches - 1
            if no_matches == 0:
                break
        if inserts:
            if automate:
                update_db(inserts, conn)
        else:
            print("Brak danych do aktualizacji.")

    except ValueError as e:
        print(f"Błąd: {e}")
    finally:
        driver.quit()
        conn.close()


def main() -> None:
    """Główna funkcja uruchamiająca skrypt."""
    parser = argparse.ArgumentParser(
        description="""Skrypt do aktualizacji danych meczów w bazie na podstawie danych z Flashscore.

Przykłady użycia:
- Aktualizacja meczów (tryb testowy):
  python update_scraper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/wyniki/

- Aktualizacja meczów z automatycznym zapisem do bazy:
  python update_scraper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/wyniki/ --automate

- Aktualizacja pojedynczego meczu:
  python update_scraper.py 33 11 https://www.flashscore.pl/mecz/pilka-nozna/4GPWXVlS/#/szczegoly-meczu/statystyki-meczu/0 --match --automate

Parametry:
  <id_ligi>         ID ligi w bazie danych
  <id_sezonu>       ID sezonu w bazie danych
  <link>            Link do strony z wynikami lub do konkretnego meczu na Flashscore

Uwaga: Bez flagi --automate dane będą tylko wyświetlane, ale nie zapisywane do bazy.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('league_id', type=int, help='ID ligi')
    parser.add_argument('season_id', type=int, help='ID sezonu')
    parser.add_argument(
        'games', help='Link do strony z wynikami lub do konkretnego meczu na Flashscore')
    parser.add_argument('--match', action='store_true',
                        help='Tryb pojedynczego meczu - parametr "games" powinien zawierać bezpośredni link do meczu')
    parser.add_argument('--automate', action='store_true',
                        help='Automatycznie zapisuj zmiany do bazy danych (bez tej flagi dane będą tylko wyświetlane)')
    args = parser.parse_args()
    to_automate(args.league_id, args.season_id,
                args.games, args.match, args.automate)


if __name__ == '__main__':
    main()
