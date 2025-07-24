import time
import sys
import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import db_module
from utils import parse_match_date, get_match_links, update_db
                

def update_match_data(driver, league_id, season_id, link, match_id, team_id):
    stats = []
    match_info = []
    match_data = {
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
        'result' : 0,
        'id' : 0}
    # duelParticipant__startTime - czas rozegrania meczu (timestamp)
    # participant__participantName - drużyny biorące udział w meczu
    # detailScore__wrapper - wynik meczu
    driver.get(link)
    time.sleep(2) # Let the user actually see something!
    # Znajdź wszystkie divy o klasie '_row_18zuy_8'
    stat_divs = driver.find_elements(By.CLASS_NAME, "wcl-row_OFViZ")
    # Znajdź wszystkie divy o klasie 'duelParticipant__startTime'
    time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
    score_divs = driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")

    # Dodaj zawartość divów do listy danych
    for div in stat_divs:
        stats.append(div.text.strip())
    for div in time_divs:
        match_info.append(div.text.strip())
    for div in team_divs:
        match_info.append(div.text.strip())
    for div in score_divs:
        match_info.append(div.text.strip())

    match_data['game_date'] = parse_match_date(match_info[0])
    score = match_info[5].split('\n')
    home_goals = int(score[0])
    away_goals = int(score[2])
    match_data['id'] = match_id
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

def get_match_id(link, driver, matches_df, league_id, season_id, team_id):
    id = -1
    driver.get(link)
    time.sleep(2)
    match_info = []
    match_data = {
        'league': 0,
        'season': 0,
        'home_team' : 0,
        'away_team' : 0,
        'game_date' : 0}
    # Znajdź wszystkie divy o klasie 'wcl-row_OFViZ'
    stat_divs = driver.find_elements(By.CLASS_NAME, "wcl-row_OFViZ")
    # Znajdź wszystkie divy o klasie 'duelParticipant__startTime'
    time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
    # Dodaj zawartość divów do listy danych
    for div in time_divs:
        match_info.append(div.text.strip())
    for div in team_divs:
        match_info.append(div.text.strip())

    #print(match_info)
    match_data['league'] = league_id #id ligi
    match_data['season'] = season_id #id sezonu
    match_data['home_team'] = team_id[match_info[1]] #nazwa gospodarzy
    match_data['away_team'] = team_id[match_info[3]]
    match_data['game_date'] = parse_match_date(match_info[0])
    record = matches_df.loc[(matches_df['home_team'] == match_data['home_team']) & (matches_df['away_team'] == match_data['away_team']) & (matches_df['game_date'] == match_data['game_date'])]
    if not record.empty:
        id = record.iloc[0]['id']
    else:
        id = -1
        print("#Nie udalo sie znalezc meczu!")
    return id

def to_automate(league_id, season_id, games, one_link = 0):
    conn = db_module.db_connect()
    query = "select round from matches where league = {} and season = {} and cast(game_date as date) <= DATE_SUB(CURDATE(), INTERVAL 1 DAY) order by game_date limit 1".format(league_id, season_id)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    if len(results) == 0:
        print("BRAK SPOTKAŃ")
        return
    round_to_d = results[0][0]
    print("RUNDA: ",round_to_d)
    query = "SELECT * FROM matches where league = {} and season = {} and result = '0' and cast(game_date as date) <= DATE_SUB(CURDATE(), INTERVAL 1 DAY) ".format(league_id, season_id, round_to_d)
    matches_df = pd.read_sql(query, conn)
    if len(matches_df) == 0:
        print("BRAK SPOTKAŃ")
        return
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    print(team_id)
    if one_link == 1:
        links = [games]
    else:
        links = get_match_links(games, driver)
    inserts = []
    no_matches = len(matches_df)
    for link in links[:]:
        match_id = get_match_id(link, driver, matches_df, league_id, season_id, team_id)
        match_data = update_match_data(driver, league_id, season_id, link, match_id, team_id)
        if match_data['id'] != -1:
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
    update_db(inserts, conn)
    conn.close()    

def main():
    #WYWOŁANIE
    #python scrapper.py <id_ligi> <id_sezonu> <link do strony z wynikami na flashscorze> <czy pobrac tylko jeden mecz z linka>
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    games = sys.argv[3]
    one_link = int(sys.argv[4])
    to_automate(league_id, season_id, games, one_link)

if __name__ == '__main__':
    main()