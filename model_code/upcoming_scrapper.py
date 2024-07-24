import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import pandas as pd
import numpy as np
import db_module

'''def get_team_id(team_name):
    team_ids = {
		'Real Salt Lake' : 358,
		'Minnesota' : 359,
		'Los Angeles Galaxy' : 360,
		'Los Angeles FC' : 361,
		'Austin FC' : 362,
		'Colorado Rapids' : 363,
		'Vancouver Whitecaps' : 364,
		'Houston Dynamo' : 365,
		'Seattle Sounders' : 366,
		'Portland Timbers' : 367,
		'St. Louis City' : 368,
		'FC Dallas' : 369,
		'San Jose Earthquakes' : 370,
		'Sporting Kansas City' : 371,
		'Inter Miami' : 372,
		'Cincinnati' : 373,
		'New York City' : 374,
		'Columbus Crew' : 375,
		'New York Red Bulls' : 376,
		'Toronto FC' : 377,
		'Charlotte' : 378,
		'Philadelphia Union' : 379,
		'DC United' : 380,
		'Orlando City' : 381,
		'Nashville SC' : 382,
		'Atlanta Utd' : 383,
		'CF Montreal' : 384,
		'Chicago Fire' : 385,
		'New England Revolution' : 386
	}
    return team_ids[team_name]'''

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
                

def get_match_data(driver, league_id, season_id, link, round_to_d, team_id):
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
        'result' : 0}
    # _row_n1rcj_9 - klasa zawierająca informacje o statystykach meczowych
    # duelParticipant__startTime - czas rozegrania meczu (timestamp)
    # participant__participantName - drużyny biorące udział w meczu
    # detailScore__wrapper - wynik meczu
    driver.get(link)
    time.sleep(3) # Let the user actually see something!
    # Znajdź wszystkie divy o klasie '_row_1nw75_8'
    stat_divs = driver.find_elements(By.CLASS_NAME, "_row_1nw75_8")
    # Znajdź wszystkie divy o klasie 'duelParticipant__startTime'
    time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
    score_divs = driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")
    round_divs = driver.find_elements(By.CLASS_NAME, "tournamentHeader__country")
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
    if int(round) != round_to_d:
        return -1
    match_data['round'] = round
    return match_data

def main():
    #WYWOŁANIE
    #python scrapper.py <id_ligi> <id_sezonu> <link do strony z wynikami na flashscorze> <numer rundy>
    conn = db_module.db_connect()
    #Link do strony z wynikami
    #games = 'https://www.flashscore.pl/pilka-nozna/francja/ligue-1-2016-2017/wyniki/'
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    round_to_d = int(sys.argv[4])
    games = sys.argv[3]
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    print(team_id)
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    links = get_match_links(games, driver)
    conn.close()
    for link in links:
        match_data = get_match_data(driver, league_id, season_id, link, round_to_d, team_id)
        if match_data == -1:
            break
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
result)  \
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
'{result}');'''.format(**match_data)
        print(sql)
if __name__ == '__main__':
    main()