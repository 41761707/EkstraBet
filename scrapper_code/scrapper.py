import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import pandas as pd
import numpy as np
import db_module

def check_if_in_db(home_team, away_team, game_date, conn):
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

def parse_match_date(match_date):
    date_object = datetime.strptime(match_date, "%d.%m.%Y %H:%M")

    date_formatted = date_object.strftime("%Y-%m-%d %H:%M")

    return date_formatted

def get_match_links(games, driver):
    links = []
    driver.get(games)
    time.sleep(15)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    for element in game_divs:
        id = element.get_attribute('id').split('_')[2]
        links.append('https://www.flashscore.pl/mecz/{}/#/szczegoly-meczu/statystyki-meczu/0'.format(id))
    return links
                

def get_match_data(driver, league_id, season_id, link, team_id, conn):
    stats = []
    match_info = []
    match_data = {
        'league': 0,
        'season': 0,
        'home_team' : 0,
        'away_team' : 0,
        'game_date' : 0,
        'home_team_goals' : 0,
        'away_team_goals' : 0,
        'home_team_xg' : 0,
        'away_team_xg' : 0,
        'home_team_bp' : 0,
        'away_team_bp' : 0,
        'home_team_sc' : 0,
        'away_team_sc' : 0,
        'home_team_sog' : 0,
        'away_team_sog' : 0,
        'home_team_fk' : 0,
        'away_team_fk': 0,
        'home_team_ck' : 0,
        'away_team_ck' : 0,
        'home_team_off' : 0,
        'away_team_off' : 0,
        'home_team_fouls' : 0,
        'away_team_fouls' : 0,
        'home_team_yc' : 0,
        'away_team_yc' : 0,
        'home_team_rc' : 0,
        'away_team_rc' : 0,
        'round' : 0,
        'result' : 0,
        'sport_id' : 1}
    # _row_n1rcj_9 - klasa zawierająca informacje o statystykach meczowych
    # duelParticipant__startTime - czas rozegrania meczu (timestamp)
    # participant__participantName - drużyny biorące udział w meczu
    # detailScore__wrapper - wynik meczu
    driver.get(link)
    time.sleep(3) # Let the user actually see something!
    # Znajdź wszystkie divy o klasie '_row_18zuy_8'
    stat_divs = driver.find_elements(By.CLASS_NAME, "wcl-row_OFViZ")
    # Znajdź wszystkie divy o klasie 'duelParticipant__startTime'
    time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
    score_divs = driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")
    round_divs = driver.find_elements(By.CLASS_NAME, "wcl-scores-overline-03_0pkdl")
    round = 0
    for div in round_divs:
        round_info = div.text.strip()
        round = round_info.split(" ")[-1]

    # Dodaj zawartość divów do listy danych
    for div in stat_divs:
        stats.append(div.text.strip())
    for div in time_divs:
        match_info.append(div.text.strip())
    for div in team_divs:
        match_info.append(div.text.strip())
    for div in score_divs:
        match_info.append(div.text.strip())

    #print(match_info)
    match_data['league'] = league_id #id ligi
    match_data['season'] = season_id #id sezonu
    match_data['home_team'] = team_id[match_info[1]] #nazwa gospodarzy
    match_data['away_team'] = team_id[match_info[3]]
    match_data['game_date'] = parse_match_date(match_info[0])
    match_data['round'] = round
    check_id = check_if_in_db(match_data['home_team'], match_data['away_team'], match_data['game_date'], conn)
    if check_id != -1:
        print(f"#Ten mecz znajduje się już w bazie danych!, ID:{check_id}")
        return check_id
    score = match_info[5].split('\n')
    home_goals = int(score[0])
    away_goals = int(score[2])
    match_data['home_team_goals'] = home_goals
    match_data['away_team_goals'] = away_goals
    if home_goals > away_goals:
        match_data['result'] = '1'
    elif home_goals == away_goals:
        match_data['result'] = 'X'
    else:
        match_data['result'] = '2'
    for element in stats:
        stat = element.split('\n')
        if(stat[1] == 'Oczekiwane gole (xG)'):
            match_data['home_team_xg'] = stat[0]
            match_data['away_team_xg'] = stat[2]
        elif(stat[1] == 'Posiadanie piłki'):
            match_data['home_team_bp'] = int(stat[0][:-1])
            match_data['away_team_bp'] = int(stat[2][:-1])
        elif(stat[1] == 'Strzały łącznie'):
            match_data['home_team_sc'] = int(stat[0])
            match_data['away_team_sc'] = int(stat[2])
        elif(stat[1] == 'Strzały na bramkę'):
            match_data['home_team_sog'] = int(stat[0])
            match_data['away_team_sog'] = int(stat[2])
        elif(stat[1] == 'Rzuty wolne'):
            match_data['home_team_fk'] = int(stat[0])
            match_data['away_team_fk'] = int(stat[2])
        elif(stat[1] == 'Rzuty rożne'):
            match_data['home_team_ck'] = int(stat[0])
            match_data['away_team_ck'] = int(stat[2])
        elif(stat[1] == 'Spalone'):
            match_data['home_team_off'] = int(stat[0])
            match_data['away_team_off'] = int(stat[2])
        elif(stat[1] == 'Faule'):
            match_data['home_team_fouls'] = int(stat[0])
            match_data['away_team_fouls'] = int(stat[2])
        elif(stat[1] == 'Żółte kartki'):
            match_data['home_team_yc'] = int(stat[0])
            match_data['away_team_yc'] = int(stat[2])
        elif(stat[1] == 'Czerwone kartki'):
            match_data['home_team_rc'] = int(stat[0])
            match_data['away_team_rc'] = int(stat[2])
    return match_data

def main():
    #WYWOŁANIE
    #python scrapper.py <id_ligi> <id_sezonu> <link do strony z wynikami na flashscorze>
    options = webdriver.ChromeOptions()
    conn = db_module.db_connect()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    #Link do strony z wynikami
    #games = 'https://www.flashscore.pl/pilka-nozna/francja/ligue-1-2016-2017/wyniki/'
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    games = sys.argv[3]
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    print(team_id)
    links = get_match_links(games, driver)
    for link in links[:]:
        match_data = get_match_data(driver, league_id, season_id, link, team_id, conn)
        if match_data == -1:
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
        print(sql)
if __name__ == '__main__':
    main()