import time
import sys
import pandas as pd
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta

import db_module

def parse_match_date(match_date):
    date_object = datetime.strptime(match_date, "%d.%m.%Y %H:%M")

    date_formatted = date_object.strftime("%Y-%m-%d %H:%M")

    return date_formatted

def get_match_id(link, driver, matches_df, league_id, season_id, round_to_d, team_id):
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
    # Znajdź wszystkie divy o klasie '_row_18zuy_8'
    stat_divs = driver.find_elements(By.CLASS_NAME, "wcl-row_OFViZ")
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
    match_data['home_team'] = team_id[match_info[1]] #nazwa gospodarzy
    match_data['away_team'] = team_id[match_info[3]]
    match_data['game_date'] = parse_match_date(match_info[0])
    if league_id != 25:
        if int(round) != round_to_d:
            return -1
    record = matches_df.loc[(matches_df['home_team'] == match_data['home_team']) & (matches_df['away_team'] == match_data['away_team'])]
    id = record.iloc[0]['id']
    if id == -1:
        print("Nie udalo sie znalezc meczu!")
    return id

def get_1x2_odds(id, link, driver):
    # 1 - zwyciestwo gospodarza
    # 2 - remis
    # 3 - zwyciestwo gosci
    inserts = []
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
        inserts.append(text_1)
        inserts.append(text_2)
        inserts.append(text_3)
    return inserts
        
def get_over_under_odds(id, link, driver):
    # 8 - o2,5
    # 12 - u2,5
    inserts = []
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
            inserts.append(text_1)
            inserts.append(text_2)
    return inserts

def get_btts_odds(id, link, driver):
    # 6 - btts
    # 172 - no btts
    inserts = []
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
        inserts.append(text_1)
        inserts.append(text_2)
    return inserts

def get_handi_odds(id, link, driver):
    pass

def get_double_chance_odds(id, link, driver):
    pass

def get_correct_score_odds(id, link, driver):
    pass

def update_db(queries, conn):
    for query in queries:
        cursor = conn.cursor() #DO POPRAWKI NATYCHMIAST
        cursor.execute(query)
        conn.commit()

def get_data(games, driver, matches_df, league_id, season_id, round_to_d, team_id, conn, to_automate):
    driver.get(games)
    time.sleep(5)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    links = []
    for element in game_divs:
        id = element.get_attribute('id').split('_')[2]
        links.append('https://www.flashscore.pl/mecz/{}'.format(id))
    for link in links[:len(matches_df)]:
        match_id = get_match_id(link, driver, matches_df, league_id, season_id, round_to_d, team_id)
        if match_id == -1:
            break
        result_inserts = get_1x2_odds(match_id, "{}{}".format(link,'#/zestawienie-kursow/kursy-1x2/koniec-meczu'), driver)
        ou_inserts = get_over_under_odds(match_id, "{}{}".format(link,'/#/zestawienie-kursow/powyzej-ponizej/koniec-meczu'), driver)
        btts_inserts = get_btts_odds(match_id, "{}{}".format(link,'#/zestawienie-kursow/obie-druzyny-strzela/koniec-meczu'), driver)
        if to_automate:
            print("HALKO")
            update_db(result_inserts, conn)
            update_db(ou_inserts, conn)
            update_db(btts_inserts, conn)
        #get_handi_odds(match_id, 'https://www.flashscore.pl/mecz/{}/#/zestawienie-kursow/handicap-azjat/koniec-meczu'.format(id), driver)
        #get_double_chance_odds(match_id, 'https://www.flashscore.pl/mecz/{}/#/zestawienie-kursow/podwojna-szansa/koniec-meczu'.format(id), driver)
        #get_correct_score_odds(match_id,'https://www.flashscore.pl/mecz/KGgchU8S/#/zestawienie-kursow/correct-score/koniec-meczu'.format(id), driver)


def odds_to_automate(league_id, season_id, games):
    #WYWOŁANIE
    to_automate = 1
    conn = db_module.db_connect()
    query = "select round from matches where league = {} and season = {} and cast(game_date as date) = current_date order by game_date limit 1".format(league_id, season_id)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    round_to_d = results[0][0]
    print("RUNDA: ", round_to_d)
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    print(team_id)
    #current_date = datetime.today().strftime('%Y-%m-%d')+1
    query = "SELECT * FROM matches where league = {} and season = {} and result = '0' and cast(game_date as date) = current_date".format(league_id, season_id, round_to_d)
    matches_df = pd.read_sql(query, conn)
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    get_data(games, driver, matches_df, league_id, season_id, round_to_d, team_id, conn, to_automate)
    conn.close()

def main():
    #WYWOŁANIE
    to_automate = 0
    conn = db_module.db_connect()
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    round_to_d = int(sys.argv[4])
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    print(team_id)
    #current_date = datetime.today().strftime('%Y-%m-%d')+1
    query = "SELECT * FROM matches where league = {} and season = {} and result = '0' and cast(game_date as date) = current_date".format(league_id, season_id, round_to_d)
    matches_df = pd.read_sql(query, conn)
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    #Link do strony z wynikami
    #games = 'https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2023-2024/wyniki/'
    games = sys.argv[3]
    #games = 'https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2023-2024/wyniki/'
    get_data(games, driver, matches_df, league_id, season_id, round_to_d, team_id, conn, to_automate)
    conn.close()
if __name__ == '__main__':
    main()