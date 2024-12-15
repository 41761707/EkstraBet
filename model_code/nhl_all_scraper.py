import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import pandas as pd

import db_module

class Game:
    #driver, league_id, season_id, link, team_id
    def __init__(self, driver, league_id, season_id, conn):
        self.driver = driver 
        self.league_id = league_id
        self.season_id = season_id
        self.conn = conn
        
    def extract_round(self, round_div, game_div):
        round_str = ""
        for div in round_div:
            round_info = div.text.strip()
            round_str = round_info.split("-")[-1].strip()
        if round_str == 'USA: NHL':
            return 100
        for div in game_div:
            game_info = div.text.strip()
            game_str = game_info.split(".")[0]
            print(game_str)
            round_str = round_str + ", " + game_str
        print(round_str)
        return self.get_special_round(round_str)
    

    def get_special_round(self, round_str):
        special_round_names = {
            '1/64-FINAŁU, 1 runda': 900,
            '1/64-FINAŁU, 2 runda': 901,
            '1/64-FINAŁU, 3 runda': 902,
            '1/64-FINAŁU, 4 runda': 903,
            '1/64-FINAŁU, 5 runda': 904,
            '1/64-FINAŁU, 6 runda': 905,
            '1/64-FINAŁU, 7 runda': 906,
            '1/32-FINAŁU, 1 runda': 910,
            '1/32-FINAŁU, 2 runda': 911,
            '1/32-FINAŁU, 3 runda': 912,
            '1/32-FINAŁU, 4 runda': 913,
            '1/32-FINAŁU, 5 runda': 914,
            '1/32-FINAŁU, 6 runda': 915,
            '1/32-FINAŁU, 7 runda': 916,
            '1/16-FINAŁU, 1 runda': 920,
            '1/16-FINAŁU, 2 runda': 921,
            '1/16-FINAŁU, 3 runda': 922,
            '1/16-FINAŁU, 4 runda': 923,
            '1/16-FINAŁU, 5 runda': 924,
            '1/16-FINAŁU, 6 runda': 925,
            '1/16-FINAŁU, 7 runda': 926,
            '1/8-FINAŁU, 1 runda': 930,
            '1/8-FINAŁU, 2 runda': 931,
            '1/8-FINAŁU, 3 runda': 932,
            '1/8-FINAŁU, 4 runda': 933,
            '1/8-FINAŁU, 5 runda': 934,
            '1/8-FINAŁU, 6 runda': 935,
            '1/8-FINAŁU, 7 runda': 936,
            'ĆWIERĆFINAŁ, 1 runda': 940,
            'ĆWIERĆFINAŁ, 2 runda': 941,
            'ĆWIERĆFINAŁ, 3 runda': 942,
            'ĆWIERĆFINAŁ, 4 runda': 943,
            'ĆWIERĆFINAŁ, 5 runda': 944,
            'ĆWIERĆFINAŁ, 6 runda': 945,
            'ĆWIERĆFINAŁ, 7 runda': 946,
            'PÓŁFINAŁ, 1 runda': 950,
            'PÓŁFINAŁ, 2 runda': 951,
            'PÓŁFINAŁ, 3 runda': 952,
            'PÓŁFINAŁ, 4 runda': 953,
            'PÓŁFINAŁ, 5 runda': 954,
            'PÓŁFINAŁ, 6 runda': 955,
            'PÓŁFINAŁ, 7 runda': 956,
            'FINAŁ, 1 runda': 960,
            'FINAŁ, 2 runda': 961,
            'FINAŁ, 3 runda': 962,
            'FINAŁ, 4 runda': 963,
            'FINAŁ, 5 runda': 964,
            'FINAŁ, 6 runda': 965,
            'FINAŁ, 7 runda': 966
        }
        return special_round_names.get(round_str)


    def parse_match_date(self, match_date):
        date_object = datetime.strptime(match_date, "%d.%m.%Y %H:%M")

        date_formatted = date_object.strftime("%Y-%m-%d %H:%M")

        return date_formatted

    def get_match_links(self, games, driver):
        links = []
        driver.get(games)
        time.sleep(2) #Dla hokeja trzeba troche poczekac
        game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
        for element in game_divs:
            id = element.get_attribute('id').split('_')[2]
            links.append('https://www.flashscore.pl/mecz/{}/#/szczegoly-meczu/'.format(id))
        return links

    def get_match_info(self, link, team_id):
        match_info = []
        match_data = {
        'league': 0,
        'season': 0,
        'home_team' : 0,
        'away_team' : 0,
        'game_date' : 0,
        'home_team_goals' : 0,
        'away_team_goals' : 0,
        'home_team_sc' : 0,
        'away_team_sc' : 0,
        'home_team_sog' : 0,
        'away_team_sog' : 0,
        'home_team_fk' : 0,
        'away_team_fk': 0,
        'home_team_fouls' : 0,
        'away_team_fouls' : 0,
        'round' : 0,
        'result' : 0}
        ot_flag = 0
        self.driver.get(link)
        time.sleep(2)
        round_div = self.driver.find_elements(By.CLASS_NAME, "tournamentHeader__country")
        game_div = self.driver.find_elements(By.CLASS_NAME, "infoBox__info")
        match_data['round'] = self.extract_round(round_div, game_div)
        time_divs = self.driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
        team_divs = self.driver.find_elements(By.CLASS_NAME, "participant__participantName")
        score_divs = self.driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")
        full_time_divs = self.driver.find_elements(By.CLASS_NAME, "detailScore__fullTime")
        extra_time_divs = self.driver.find_elements(By.CLASS_NAME, "detailScore__status")
        for div in time_divs:
            match_info.append(div.text.strip())
        for div in team_divs:
            match_info.append(div.text.strip())
        for div in score_divs:
            match_info.append(div.text.strip())
        for div in full_time_divs:
            ot_flag = 1
            match_info.append(div.text.strip())
        for div in extra_time_divs:
            match_info.append(div.text.strip())
        print(match_info)
        match_data['league'] = self.league_id #id ligi
        match_data['season'] = self.season_id #id sezonu
        match_data['home_team'] = team_id[match_info[1]] #nazwa gospodarzy
        match_data['away_team'] = team_id[match_info[3]]
        match_data['game_date'] = self.parse_match_date(match_info[0])
        score = match_info[5].split('\n')
        home_goals = int(score[0])
        away_goals = int(score[2])
        if ot_flag:
            #TUTAJ WYNIK W SCORE BEDZIE PO DOGRYWCE!
            score_regular = match_info[6].split('\n')
            match_data['home_team_goals'] = int(score_regular[1])
            match_data['away_team_goals'] = int(score_regular[3])
            match_data['result'] = 'X'
        else:
            match_data['home_team_goals'] = home_goals
            match_data['away_team_goals'] = away_goals
        if match_data['result'] == 0:
            if home_goals > away_goals:
                match_data['result'] = '1'
            else:
                match_data['result'] = '2'
        return match_data

    def get_event_id(self):
        pass

    def get_player_id(self, common_name):
        player_id = -1
        query = "SELECT id FROM players WHERE common_name = %s"
        cursor = self.conn.cursor()
        cursor.execute(query, (common_name,))
        result = cursor.fetchone()
        if result:
            player_id = result[0]
        else:
            print('BRAK GRACZA')
        cursor.close()
        return player_id
    def get_match_id(self):
        pass

    def get_match_events(self, home_team, away_team):
        match_events_lists = []
        game_log = self.driver.find_element(By.CLASS_NAME, "smv__verticalSections.section")
        game_events_divs = game_log.find_elements(By.XPATH, "./*")
        current_period = 0
        for div in game_events_divs:
            if "smv__incidentsHeader section__title" in div.get_attribute("class"):
                # Jeśli napotkamy nowy nagłówek, zapisujemy aktualny licznik i resetujemy
                #PERIOD 4 = DOGRYWKA
                #PERIOD 5 = KARNE
                current_period = current_period + 1
            elif "smv__participantRow" in div.get_attribute("class"):
                match_events = {
                    'event_id' : 0,
                    'match_id' : 0,
                    'team_id' : 0,
                    'player_id' : 0,
                    'period' : 0,
                    'event_time': 0,
                    'pp_flag' : 0,
                    'en_flag' : 0,
                    'description' : 0
                }
                description_str = ""
                match_events['period'] = current_period
                if "smv__homeParticipant" in div.get_attribute("class"):
                    match_events['team_id'] = home_team
                elif "smv__awayParticipant" in div.get_attribute("class"):
                    match_events['team_id'] = away_team
                incident = div.find_element(By.CLASS_NAME, "smv__incident")
                time_box = incident.find_element(By.CLASS_NAME, "smv__timeBox")
                match_events['event_time'] = time_box.text
                main_player = incident.find_element(By.TAG_NAME, "a")
                match_events['player_id'] = self.get_player_id(main_player.text)
                try:
                    sub_players = incident.find_element(By.CLASS_NAME, "smv__assist")
                    description_str = description_str + "{}".format(sub_players.text)
                except:
                    pass
                try:
                    sub_incident = incident.find_element(By.CLASS_NAME, "smv__subIncident").text.strip().strip("()")
                    print(sub_incident)
                    if sub_incident == 'W przewadze':
                        match_events['pp_flag'] = 1
                    elif sub_incident == 'Do pustej bramki':
                        match_events['en_flag'] = 1
                    else:
                        pass
                    if description_str == "":
                        description_str = description_str + "{}".format(sub_incident)
                    else:
                        if sub_incident == "Rzut karny":
                            description_str = description_str + "Karny trafiony"
                        description_str = description_str + ", {}".format(sub_incident)
                except:
                    pass
                print(description_str)
                match_events['description'] = description_str
                
                match_events_lists.append(match_events)
        for event in match_events_lists:
            print(event)

    def get_match_stats_add(self, link):
        print(link)
        self.driver.get(link)
        time.sleep(3)


                

    def get_match_data(self, link, team_id):
        #1. Wczytac mecz standardowo do struktury matches
        #2. Zaczytac statystyki istotne dla hokeja do tabeli hockey_matches_add
        #3. Zaczytac zdarzenia meczowe do tabeli hockey_match_events
        #4. Zaczytac boxscore do tabeli hockey_match_player_stats
        match_data = {}
        match_events = {}
        match_stats_add = {}
        #1. 
        #TUTAJ MATCH_DATA BEZ STATYSTYK, SAM OPIS KTO Z KIM KIEDY
        #PAMIETAC O UZUPELNIENIU PRZY REALIZACJI PUNKTU 2
        match_data = self.get_match_info("{}szczegoly-meczu".format(link), team_id)
        #3. TA SAMA PODSTRONA TO IDZIEMY ZA CIOSEM
        match_events = self.get_match_events(match_data['home_team'], match_data['away_team'])

        #2. 
        match_stats_add = self.get_match_stats_add("{}statystyki-meczu/0".format(link))

    def update_db(self, queries, conn):
        print("HALKO")
        for query in queries:
            cursor = conn.cursor() #DO POPRAWKI NATYCHMIAST
            cursor.execute(query)
            conn.commit()

def main():
    #WYWOŁANIE
    #python scrapper.py <id_ligi> <id_sezonu> <link do strony z wynikami na flashscorze>
    conn = db_module.db_connect()
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    #Link do strony z wynikami
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    games = sys.argv[3]
    one_link = sys.argv[4]
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {}".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    inserts = []
    game_data = Game(driver, league_id, season_id, conn)
    if one_link == '-1':
        links = Game.get_match_links(games, driver)
        for link in links:
            game_data.get_match_data(link, team_id)
            #inserts.append(sql)
            break
    else:
        game_data.get_match_data(one_link, team_id)
    #update_db(inserts, conn)
    conn.close() 
if __name__ == '__main__':
    main()