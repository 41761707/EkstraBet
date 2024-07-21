import time
import sys
import pandas as pd
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta

import db_module
def get_team_id(team_name):
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
    return team_ids[team_name]

def parse_match_date(match_date):
    date_object = datetime.strptime(match_date, "%d.%m.%Y %H:%M")

    date_formatted = date_object.strftime("%Y-%m-%d %H:%M")

    return date_formatted

def get_match_id(link, driver, matches_df, league_id, season_id, round_to_d):
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
    # Znajdź wszystkie divy o klasie '_row_1csk6_9'
    stat_divs = driver.find_elements(By.CLASS_NAME, "_row_1csk6_9")
    # Znajdź wszystkie divy o klasie 'duelParticipant__startTime'
    time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
    team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
    round_divs = driver.find_elements(By.CLASS_NAME, "tournamentHeader__country")
    for div in round_divs:
        round_info = div.text.strip()
        round = round_info.split(" ")[-1]
    # Dodaj zawartość divów do listy danych
    for div in time_divs:
        match_info.append(div.text.strip())
    for div in team_divs:
        match_info.append(div.text.strip())

    #print(match_info)
    match_data['league'] = league_id #id ligi
    match_data['season'] = season_id #id sezonu
    match_data['home_team'] = get_team_id(match_info[1]) #nazwa gospodarzy
    match_data['away_team'] = get_team_id(match_info[3])
    match_data['game_date'] = parse_match_date(match_info[0])
    #if int(round) != round_to_d:
    #    return -1
    record = matches_df.loc[(matches_df['home_team'] == match_data['home_team']) & (matches_df['away_team'] == match_data['away_team'])]
    id = record.iloc[0]['id']
    if id == -1:
        print("Nie udalo sie znalezc meczu!")
    return id
def get_1x2_odds(id, link, driver):
    # 1 - zwyciestwo gospodarza
    # 2 - remis
    # 3 - zwyciestwo gosci
    driver.get(link)
    time.sleep(2)
    book_divs = driver.find_elements(By.CLASS_NAME, "ui-table__row")
    bookie_dict = {
        'STS.pl' : 4,
        'eFortuna.pl': 3,
        'Betclic.pl' : 2,
        'BETFAN' : 6,
        'Etoto' : 7,
        'LV BET': 5,
        'Superbet.pl' : 1,
        'Fuksiarz.pl' : 8
    }
    bookies = []
    for book in book_divs:
        try:
            # Szukamy tagu img wewnątrz obecnego diva
            img_tag = book.find_element(By.TAG_NAME, "img")
            # Pobieramy wartość atrybutu title z tagu img
            title = img_tag.get_attribute("title").strip("'")
            # Dodajemy tytuł do listy
            bookies.append(title)
        except:
            # Obsługujemy przypadek, gdy tag img lub atrybut title nie jest obecny
            bookies.append(None)
    for i in range(len(book_divs)):
        text = book_divs[i].text.strip()
        text_tab = text.split('\n')
        text_1 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {});".format(id, bookie_dict[bookies[i]], 1, text_tab[0])
        text_2 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {});".format(id, bookie_dict[bookies[i]], 2, text_tab[1])
        text_3 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {});".format(id, bookie_dict[bookies[i]], 3, text_tab[2])
        print(text_1)
        print(text_2)
        print(text_3)
        
def get_over_under_odds(id, link, driver):
    # 8 - o2,5
    # 12 - u2,5
    driver.get(link)
    time.sleep(2)
    book_divs = driver.find_elements(By.CLASS_NAME, "ui-table__row")
    bookie_dict = {
        'STS.pl' : 4,
        'eFortuna.pl': 3,
        'Betclic.pl' : 2,
        'BETFAN' : 6,
        'Etoto' : 7,
        'LV BET': 5,
        'Superbet.pl' : 1,
        'Fuksiarz.pl' : 8
    }
    bookies = []
    for book in book_divs:
        try:
            # Szukamy tagu img wewnątrz obecnego diva
            img_tag = book.find_element(By.TAG_NAME, "img")
            # Pobieramy wartość atrybutu title z tagu img
            title = img_tag.get_attribute("title").strip("'")
            # Dodajemy tytuł do listy
            bookies.append(title)
        except:
            # Obsługujemy przypadek, gdy tag img lub atrybut title nie jest obecny
            bookies.append(None)
    iter = 1
    for i in range(len(book_divs)):
        text = book_divs[i].text.strip()
        text_tab = text.split('\n')
        #print(text_tab)
        if text_tab[0] == '2.5':
            text_1 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {});".format(id, bookie_dict[bookies[i]], 8, text_tab[1])
            text_2 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {});".format(id, bookie_dict[bookies[i]], 12, text_tab[2])
            print(text_1)
            print(text_2)
        #print(text_3)

def get_btts_odds(id, link, driver):
    # 6 - btts
    # 172 - no btts
    driver.get(link)
    time.sleep(2)
    book_divs = driver.find_elements(By.CLASS_NAME, "ui-table__row")
    bookie_dict = {
        'STS.pl' : 4,
        'eFortuna.pl': 3,
        'Betclic.pl' : 2,
        'BETFAN' : 6,
        'Etoto' : 7,
        'LV BET': 5,
        'Superbet.pl' : 1,
        'Fuksiarz.pl' : 8
    }
    bookies = []
    for book in book_divs:
        try:
            # Szukamy tagu img wewnątrz obecnego diva
            img_tag = book.find_element(By.TAG_NAME, "img")
            # Pobieramy wartość atrybutu title z tagu img
            title = img_tag.get_attribute("title").strip("'")
            # Dodajemy tytuł do listy
            bookies.append(title)
        except:
            # Obsługujemy przypadek, gdy tag img lub atrybut title nie jest obecny
            bookies.append(None)
    for i in range(len(book_divs)):
        text = book_divs[i].text.strip()
        text_tab = text.split('\n')
        #print(text_tab)
        text_1 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {});".format(id, bookie_dict[bookies[i]], 6, text_tab[0])
        text_2 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {});".format(id, bookie_dict[bookies[i]], 172, text_tab[1])
        print(text_1)
        print(text_2)

def get_handi_odds(id, link, driver):
    pass

def get_double_chance_odds(id, link, driver):
    pass

def get_correct_score_odds(id, link, driver):
    pass

def get_data(games, driver, matches_df, league_id, season_id, round_to_d):
    driver.get(games)
    time.sleep(15)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    links = []
    for element in game_divs:
        id = element.get_attribute('id').split('_')[2]
        links.append('https://www.flashscore.pl/mecz/{}'.format(id))
    for link in links:
        match_id = get_match_id(link, driver, matches_df, league_id, season_id, round_to_d)
        if match_id == -1:
            break
        get_1x2_odds(match_id, "{}{}".format(link,'#/zestawienie-kursow/kursy-1x2/koniec-meczu'), driver)
        get_over_under_odds(match_id, "{}{}".format(link,'/#/zestawienie-kursow/powyzej-ponizej/koniec-meczu'), driver)
        get_btts_odds(match_id, "{}{}".format(link,'#/zestawienie-kursow/obie-druzyny-strzela/koniec-meczu'), driver)
        #get_handi_odds(match_id, 'https://www.flashscore.pl/mecz/{}/#/zestawienie-kursow/handicap-azjat/koniec-meczu'.format(id), driver)
        #get_double_chance_odds(match_id, 'https://www.flashscore.pl/mecz/{}/#/zestawienie-kursow/podwojna-szansa/koniec-meczu'.format(id), driver)
        #get_correct_score_odds(match_id,'https://www.flashscore.pl/mecz/KGgchU8S/#/zestawienie-kursow/correct-score/koniec-meczu'.format(id), driver)

def main():
    #WYWOŁANIE
    conn = db_module.db_connect()
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    round_to_d = int(sys.argv[4])
    #current_date = datetime.today().strftime('%Y-%m-%d')+1
    query = "SELECT * FROM matches where league = {} and season = {} and round = {} and result = '0'".format(league_id, season_id, round_to_d)
    #query = "SELECT * FROM matches where league = {} and season = {} and cast(game_date as date) = {}".format(league_id, season_id, current_date)
    matches_df = pd.read_sql(query, conn)
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    #Link do strony z wynikami
    #games = 'https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2023-2024/wyniki/'
    games = sys.argv[3]
    #games = 'https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2023-2024/wyniki/'
    get_data(games, driver, matches_df, league_id, season_id, round_to_d)
    conn.close()
if __name__ == '__main__':
    main()