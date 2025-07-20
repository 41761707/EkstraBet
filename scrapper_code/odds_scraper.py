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

def check_odds_in_db(match_id, conn):
    print
    """
    Check if odds exist for given match_id in the database
    Returns True if odds exist, False otherwise
    """
    cursor = conn.cursor()
    match_id = int(match_id)
    query = "SELECT COUNT(*) FROM odds WHERE match_id = %s"
    cursor.execute(query, (match_id,))
    result = cursor.fetchone()[0]
    cursor.close()
    return result > 0

def get_match_id(link, driver, matches_df, league_id, season_id, team_id):
    id = -1
    driver.get(link)
    time.sleep(2)
    match_info = []
    match_data = {
        'league': 0,
        'season': 0,
        'home_team': 0,
        'away_team': 0,
        'game_date': 0
    }
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

    match_data['league'] = league_id  # id ligi
    match_data['season'] = season_id  # id sezonu
    match_data['home_team'] = team_id.get(match_info[1], None)  # nazwa gospodarzy
    match_data['away_team'] = team_id.get(match_info[3], None)
    try:
        match_data['game_date'] = parse_match_date(match_info[0])
    except Exception as e:
        print(f"Błąd parsowania daty meczu: {e}")
        return -1

    # Sprawdź, czy wszystkie dane są dostępne
    if None in [match_data['home_team'], match_data['away_team'], match_data['game_date']]:
        print("Brak wymaganych danych meczu (gospodarz, goście lub data).")
        return -1
    record = matches_df.loc[(matches_df['home_team'] == match_data['home_team']) &
        (matches_df['away_team'] == match_data['away_team']) &
        (matches_df['game_date'] == match_data['game_date'])]
    if record.empty:
        return -1

    try:
        id = record.iloc[0]['id']
    except Exception as e:
        print(f"Błąd pobierania ID meczu: {e}")
        return
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
        if len(text_tab) >= 3 and all (x != '-' for x in text_tab):
            text_1 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict[bookies[i]], 1, text_tab[0])
            text_2 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict[bookies[i]], 2, text_tab[1])
            text_3 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict[bookies[i]], 3, text_tab[2])
            print(text_1)
            print(text_2)
            print(text_3)
            inserts.append(text_1)
            inserts.append(text_2)
            inserts.append(text_3)
        else:
            # Dodajemy tylko te kursy, które nie są "-"
            for idx, event in enumerate([1, 2, 3]):
                if len(text_tab) > idx and text_tab[idx] != '-':
                    text_sql = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict.get(bookies[i]), event, text_tab[idx])
                    print(text_sql)
                    inserts.append(text_sql)
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
    for i in range(len(book_divs)):
        text = book_divs[i].text.strip()
        text_tab = text.split('\n')
        #print(text_tab)
        if len(text_tab) >= 3 and text_tab[0] == '2.5':
            # Sprawdzamy czy kursy są dostępne
            if text_tab[1] != '-':
                text_1 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict.get(bookies[i]), 8, text_tab[1])
                print(text_1)
                inserts.append(text_1)
            if text_tab[2] != '-':
                text_2 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict.get(bookies[i]), 12, text_tab[2])
                print(text_2)
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
        if len(text_tab) >= 2:
            if text_tab[0] != '-':
                text_1 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict.get(bookies[i]), 6, text_tab[0])
                print(text_1)
                inserts.append(text_1)
            if text_tab[1] != '-':
                text_2 = "INSERT INTO ODDS(match_id, bookmaker, event, odds) VALUES({}, {}, {}, {}) AS new ON DUPLICATE KEY UPDATE odds = new.odds;".format(id, bookie_dict.get(bookies[i]), 172, text_tab[1])
                print(text_2)
                inserts.append(text_2)
    return inserts

def update_db(queries, conn):
    for query in queries:
        cursor = conn.cursor() #DO POPRAWKI NATYCHMIAST
        cursor.execute(query)
        conn.commit()

def get_data(games, driver, matches_df, league_id, season_id, team_id, conn, to_automate, skip = 0):
    driver.get(games)
    time.sleep(5)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    links = []
    for element in game_divs:
        id = element.get_attribute('id').split('_')[2]
        links.append('https://www.flashscore.pl/mecz/{}'.format(id))
    for link in links[skip:len(matches_df)]:
        match_id = get_match_id(link, driver, matches_df, league_id, season_id, team_id)
        # Check if odds already exist for this match
        if check_odds_in_db(match_id, conn):
            print(f"Kursy już istnieją dla meczu o id: {match_id}, pomijam...")
            continue
        if match_id == -1:
            print(f"Brak meczu w bazie danych, pomijam")
            continue
        result_inserts = get_1x2_odds(match_id, "{}{}".format(link,'#/zestawienie-kursow/kursy-1x2/koniec-meczu'), driver)
        ou_inserts = get_over_under_odds(match_id, "{}{}".format(link,'/#/zestawienie-kursow/powyzej-ponizej/koniec-meczu'), driver)
        btts_inserts = get_btts_odds(match_id, "{}{}".format(link,'#/zestawienie-kursow/obie-druzyny-strzela/koniec-meczu'), driver)
        if to_automate:
            print("HALKO")
            update_db(result_inserts, conn)
            update_db(ou_inserts, conn)
            update_db(btts_inserts, conn)

def get_daily_odds(conn, driver, matches_df, league_id, season_id, games, team_id, to_automate):
    #TO-DO: Dokładny test tego komponentu
    matches_df = matches_df[matches_df['game_date'].dt.date == datetime.today().date()]
    if matches_df.empty:
        print("Brak meczów na dzisiaj")
        return
    get_data(games, driver, matches_df, league_id, season_id, team_id, conn, to_automate)

def get_historical_odds(conn, driver, matches_df, league_id, season_id, games, team_id, to_automate, skip):
    get_data(games, driver, matches_df, league_id, season_id, team_id, conn, to_automate, skip) 

def get_given_match_odds(conn, driver, matches_df, league_id, season_id, games, team_id, to_automate):
    match_id = get_match_id(games, driver, matches_df, league_id, season_id, team_id)
    if match_id == -1:
        print("Brak meczu w bazie danych")
        return 
    result_inserts = get_1x2_odds(match_id, "{}{}".format(games,'#/zestawienie-kursow/kursy-1x2/koniec-meczu'), driver)
    ou_inserts = get_over_under_odds(match_id, "{}{}".format(games,'/#/zestawienie-kursow/powyzej-ponizej/koniec-meczu'), driver)
    btts_inserts = get_btts_odds(match_id, "{}{}".format(games,'#/zestawienie-kursow/obie-druzyny-strzela/koniec-meczu'), driver)
    if to_automate:
        print("HALKO")
        update_db(result_inserts, conn)
        update_db(ou_inserts, conn)
        update_db(btts_inserts, conn)

def odds_to_automate(league_id, season_id, games, mode, skip = 0):
    #Inicjalizacja parametrów
    to_automate = 1
    conn = db_module.db_connect()
    query = f"SELECT * FROM matches where league = {league_id} and season = {season_id}"
    matches_df = pd.read_sql(query, conn)
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    print(team_id)
    if mode == 'historical':
        get_historical_odds(conn, driver, matches_df, league_id, season_id, games, team_id, to_automate, skip)
    elif mode == 'match':
        get_given_match_odds(conn, driver, matches_df, league_id, season_id, games, team_id, to_automate)
    elif mode == 'daily':
        get_daily_odds(conn, driver, matches_df, league_id, season_id, games, team_id, to_automate)
    else:
        print("Nieobsługiwany typ wywołania procedury (mode: historical / match / daily)")
    conn.close()
    driver.quit()

def main():
    #Przykłady wywołania
    # python odds_scraper.py <id ligi> <id sezonu> <link do meczu/meczów> <typ: daily/historical/match> <liczba meczow do pominiecia (dla historical)
    # python .\odds_scraper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/ daily
    # python .\odds_scraper.py 4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/wyniki historical
    # python .\odds_scraper.py 19 11 https://www.flashscore.pl/mecz/pilka-nozna/W4853zVH/  match
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    games = sys.argv[3]
    mode = sys.argv[4]
    skip = 0  # wartość domyślna
    if len(sys.argv) > 5:
        try:
            skip = int(sys.argv[5])
        except (ValueError, IndexError):
            skip = 0 
            print("Ostrzeżenie: Nieprawidłowa wartość skip, ustawiam 0")
    odds_to_automate(league_id, season_id, games, mode, skip)


if __name__ == '__main__':
    main()