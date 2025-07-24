import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import db_module
from utils import check_if_in_db, parse_match_date, get_match_links
from dataclasses import dataclass, asdict
from typing import Any
import argparse

@dataclass
class MatchData:
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
    stat_divs = driver.find_elements(By.CLASS_NAME, "wcl-row_OFViZ")
    time_divs = driver.find_elements(
        By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(
        By.CLASS_NAME, "participant__participantName")
    score_divs = driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")
    round_divs = driver.find_elements(
        By.CLASS_NAME, "wcl-scores-overline-03_0pkdl")
    return stat_divs, time_divs, team_divs, score_divs, round_divs


def parse_round(round_divs: list) -> str | int:
    """Parsuje informacje o rundzie z elementów strony.
    Args:
        round_divs (list): Lista elementów HTML zawierających informacje o rundzie.
    Returns:
        str | int: Zwraca numer rundy jako string lub 0, jeśli nie znaleziono.
    """
    round = 0
    for div in round_divs:
        round_info = div.text.strip()
        round = round_info.split(" ")[-1]
    return round


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
    """Parsuje statystyki meczu z listy elementów i aktualizuje MatchData."""
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
    stat_divs, time_divs, team_divs, score_divs, round_divs = fetch_match_elements(
        driver, link)
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
    match_id = check_if_in_db(match_data.home_team,
                              match_data.away_team, match_data.game_date, conn)
    #if match_id != -1:
    #    print(f"#Ten mecz znajduje się już w bazie danych!, ID:{match_id}")
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


def to_automate(league_id: int, season_id: int, games: str) -> None:
    """Automatyzuje scrapowanie wyników meczów.
    Args:
        league_id (int): ID ligi.
        season_id (int): ID sezonu.
        games (str): Link do strony z wynikami na flashscorze.
    """
    options = webdriver.ChromeOptions()
    conn = db_module.db_connect()
    options.add_experimental_option(
        'excludeSwitches', ['enable-logging'])  # Here
    driver = webdriver.Chrome(options=options)
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query, conn)
    country = country_df.values.flatten()
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    print(team_id)
    inserts = []
    links = get_match_links(games, driver)
    for link in links[:]:
        match_data = get_match_data(
            driver, league_id, season_id, link, team_id, conn)
        if match_data == -1:
            # update_db(inserts, conn)
            return
        sql = '''INSERT INTO matches (league, \
season, \
home_team, \
away_team, \
game_date, \
home_team_goals, \
away_team_goals, \
home_team_xg, \
away_team_xg, \
home_team_bp, \
away_team_bp, \
home_team_sc, \
away_team_sc, \
home_team_sog, \
away_team_sog, \
home_team_fk, \
away_team_fk, \
home_team_ck, \
away_team_ck, \
home_team_off, \
away_team_off, \
home_team_fouls, \
away_team_fouls, \
home_team_yc, \
away_team_yc, \
home_team_rc, \
away_team_rc, \
round, \
result, \
sport_id)  \
VALUES ({league}, \
{season}, \
{home_team}, \
{away_team}, \
'{game_date}', \
{home_team_goals}, \
{away_team_goals}, \
{home_team_xg}, \
{away_team_xg}, \
{home_team_bp}, \
{away_team_bp}, \
{home_team_sc}, \
{away_team_sc}, \
{home_team_sog}, \
{away_team_sog}, \
{home_team_fk}, \
{away_team_fk}, \
{home_team_ck}, \
{away_team_ck}, \
{home_team_off}, \
{away_team_off}, \
{home_team_fouls}, \
{away_team_fouls}, \
{home_team_yc}, \
{away_team_yc}, \
{home_team_rc}, \
{away_team_rc}, \
{round}, \
'{result}', \
{sport_id});'''.format(**match_data)
        #inserts.append(sql)
        print(sql)
    # update_db(inserts, conn)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="""Skrypt do scrapowania wyników meczów z Flashscore.\n\nPrzykłady użycia:\n- Pobieranie wszystkich meczów ligi i sezonu:\n  python scrapper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/\n\nParametry:\n  <id_ligi>         ID ligi w bazie danych\n  <id_sezonu>       ID sezonu w bazie danych\n  <link>            Link do strony z wynikami na Flashscore\n""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('league_id', type=int, help='ID ligi')
    parser.add_argument('season_id', type=int, help='ID sezonu')
    parser.add_argument(
        'games', help='Link do strony z wynikami na Flashscore')
    args = parser.parse_args()
    to_automate(args.league_id, args.season_id, args.games)


if __name__ == '__main__':
    main()
