import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import pandas as pd
import re

import db_module

class Game:
    #driver, league_id, season_id, link, team_id
    def __init__(self, driver, league_id, season_id, shortcuts, conn):
        self.driver = driver 
        self.league_id = league_id
        self.season_id = season_id
        self.conn = conn
        self.shortcuts = shortcuts

    def check_if_in_db(self, home_team, away_team, game_date):
        cursor = self.conn.cursor()
        query = """
            SELECT m.id 
            FROM matches m 
            WHERE m.home_team = %s AND m.away_team = %s AND m.game_date = %s
        """

        cursor.execute(query, (home_team, away_team, game_date))
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else -1
        
        
    def extract_round(self, round_div, game_div):
        round_str = ""
        for div in round_div:
            round_info = div.text.strip()
            round_str = round_info.split(" - ")[-1].strip()
        if round_str == 'USA: NHL':
            return 100
        if round_str == 'All Stars' or round_str == 'Przedsezonowy':
            return -1
        for div in game_div:
            game_info = div.text.strip()
            game_str = "0"
            match = re.search(r"(\d+\s+runda)", game_info)
            if match:
                game_str = match.group(1)
            round_str = round_str + ", " + game_str
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
        time.sleep(30) #Dla hokeja trzeba troche poczekac
        game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
        for element in game_divs:
            id = element.get_attribute('id').split('_')[2]
            links.append('https://www.flashscore.pl/mecz/{}/#/szczegoly-meczu/'.format(id))
        return links

    def get_match_info(self, link, team_id, match_data):
        match_info = []
        ot_flag = 0
        ot_winner = 0 #0 - brak dogrywki, 1- gospo win, 2 - goście win
        self.driver.get(link)
        time.sleep(2)
        round_div = self.driver.find_elements(By.CLASS_NAME, "tournamentHeader__country")
        game_div = self.driver.find_elements(By.CLASS_NAME, "infoBox__info")
        match_data['round'] = self.extract_round(round_div, game_div)
        if match_data['round'] == -1:
            return -1, -1
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
            extra_time = div.text.strip()
            if extra_time == 'PO DOGRYWCE':
                ot_flag = 1
            if extra_time == 'PO RZUTACH KARNYCH':
                ot_flag = 2
            match_info.append(extra_time)
        #print(match_info)
        match_data['league'] = self.league_id #id ligi
        match_data['season'] = self.season_id #id sezonu
        match_data['home_team'] = team_id[match_info[1]] #nazwa gospodarzy
        match_data['away_team'] = team_id[match_info[3]]
        match_data['game_date'] = self.parse_match_date(match_info[0])
        check_id = self.check_if_in_db(match_data['home_team'], match_data['away_team'], match_data['game_date'])
        if check_id != -1:
            print(f"#Ten mecz znajduje się już w bazie danych!, ID:{check_id}")
            return -1, -1
        score = match_info[5].split('\n')
        home_goals = int(score[0])
        away_goals = int(score[2])
        if ot_flag:
            #TUTAJ WYNIK W SCORE BEDZIE PO DOGRYWCE!
            score_regular = match_info[6].split('\n')
            match_data['home_team_goals'] = int(score_regular[1])
            match_data['away_team_goals'] = int(score_regular[3])
            match_data['result'] = 'X'
            if home_goals > away_goals:
                ot_winner = 1
            else:
                ot_winner = 2
        else:
            match_data['home_team_goals'] = home_goals
            match_data['away_team_goals'] = away_goals
        if match_data['result'] == 0:
            if home_goals > away_goals:
                match_data['result'] = '1'
            else:
                match_data['result'] = '2'
        return ot_flag, ot_winner

    def get_event_id(self, event):
        #Na razie mapowanie na sztywno, raczej nie poprawiam
        event_mapping = {
            'hockeyGoal-ico': 181,
            'penalty-2-min': 183,
            'whistle-ico': 184,
            'penalty-5-min': 185,
            'penalty-10-min-misconduct': 186,
            'warning' : 187,
            'substitution' : 188,
            'penalty-10-min' : 189, 
        }
        return event_mapping.get(event, 0)  # Domyślna wartość to 0, jeśli event nie istnieje

    
    def get_player_id(self, common_name, flash_id = None): 
        player_id = -1
        cursor = self.conn.cursor()
        try:
            # 1. Sprawdź ilu jest graczy z podanym common_name
            query_count = "SELECT COUNT(*) FROM players WHERE common_name = %s"
            cursor.execute(query_count, (common_name,))
            count = cursor.fetchone()[0]
            if count == 0:
                flash_player_id = "SELECT id FROM players where external_flash_id = %s"
                cursor.execute(flash_player_id, (flash_id,))
                result = cursor.fetchone()
                if result:
                    player_id = result[0]
                else:
                    print(f'BRAK GRACZA O PODANYM COMMON_NAME. Common name: {common_name}, flash_id: {flash_id}')
            elif count == 1:
                # 2. Jeśli jest dokładnie jeden gracz, pobierz jego id
                query_single = "SELECT id FROM players WHERE common_name = %s"
                cursor.execute(query_single, (common_name,))
                result = cursor.fetchone()
                if result:
                    player_id = result[0]
            else:
                # 3. Jeśli jest więcej niż jeden gracz, użyj flash_id do znalezienia właściwego
                query_by_flash_id = """
                    SELECT id FROM players 
                    WHERE common_name = %s AND external_flash_id = %s 
                """
                cursor.execute(query_by_flash_id, (common_name, flash_id))
                result = cursor.fetchone()
                if result:
                    player_id = result[0]
                else:
                    print(f'BRAK GRACZA O PODANYM external_flash_id. Common name: {common_name}, flash_id: {flash_id}')
        except Exception as e:
            print(f"Wystąpił błąd: {e}")
        finally:
            cursor.close()
        return player_id
    
    def insert_match(self):
        pass

    def get_player_team_id(self, shortcut):
        #TLUMACZENIA Z FLASHSCORE
        if shortcut == 'NAS':
            shortcut = 'NSH'
        if shortcut == 'WIN':
            shortcut = 'WPG'
        if shortcut == 'LOS':
            shortcut = 'LAK'
        if shortcut == 'MON':
            shortcut = 'MTL'
        
        return self.shortcuts[shortcut]

    def get_match_events(self, link, match_id, home_team, away_team):
        self.driver.get(link)
        time.sleep(2)
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
                match_events['match_id'] = match_id
                description_str = ""
                match_events['period'] = current_period
                if "smv__homeParticipant" in div.get_attribute("class"):
                    match_events['team_id'] = home_team
                elif "smv__awayParticipant" in div.get_attribute("class"):
                    match_events['team_id'] = away_team
                incident = div.find_element(By.CLASS_NAME, "smv__incident")
                time_box = incident.find_element(By.CLASS_NAME, "smv__timeBox")
                match_events['event_time'] = time_box.text
                try:
                    main_player = incident.find_element(By.TAG_NAME, "a")
                    flash_id_link = main_player.get_attribute('href')
                    flash_id = flash_id_link.split('/')[-2]
                    match_events['player_id'] = self.get_player_id(main_player.text, flash_id)
                except:
                    match_events['player_id'] = 0
                try:
                    sub_players = incident.find_element(By.CLASS_NAME, "smv__assist")
                    description_str = description_str + "{}".format(sub_players.text)
                except:
                    pass
                try:
                    sub_incident = incident.find_element(By.CLASS_NAME, "smv__subIncident").text.strip().strip("()")
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
                try:
                    svg_element = incident.find_element(By.TAG_NAME, "svg")
                    svg_class = svg_element.get_attribute("class")
                    match_events['event_id'] = self.get_event_id(svg_class.strip())
                except:
                    pass
                match_events['description'] = description_str
                if match_events['player_id'] == 0 and (match_events['event_id'] == 183 or match_events['event_id'] == 186):
                    match_events['player_id'] = 2002 #Definicja gracza w bazie
                match_events_lists.append(match_events)
        return match_events_lists

    def get_match_stats_add(self, link, match_data, match_stats_add, ot_flag, ot_winner):
        stats = []
        self.driver.get(link)
        #print("MATCH_STATS_ADD")
        time.sleep(2)
        if ot_flag == 1:
            match_stats_add["OT"] = 1
            match_stats_add["OTwinner"] = ot_winner
        if ot_flag == 2:
            match_stats_add["OT"] = 1
            match_stats_add["SO"] = 1
            match_stats_add["OTwinner"] = 3
            match_stats_add["SOwinner"] = ot_winner
        stat_divs = self.driver.find_elements(By.CLASS_NAME, "wcl-row_OFViZ")
        for div in stat_divs:
            stats.append(div.text.strip())
        for element in stats:
            stat = element.split('\n')
            ### SEKCJA MATCH_DATA
            if(stat[1] == 'Strzały na bramkę'):
                match_data['home_team_sog'] = stat[0]
                match_data['away_team_sog'] = stat[2]
            if(stat[1] == "Strzały niecelne"):
                match_data['home_team_sc'] = str(int(match_data['home_team_sog']) + int(stat[0]))
                match_data['away_team_sc'] = str(int(match_data['away_team_sog']) + int(stat[2]))
            if(stat[1] == "Suma kar"):
                match_data["home_team_fk"] = stat[0]
                match_data["away_team_fk"] = stat[2]
            if(stat[1] == "Kary"):
                match_data["home_team_fouls"] = stat[0]
                match_data["away_team_fouls"] = stat[2]
            if(stat[1] == "Skuteczność %"):
                match_stats_add["home_team_shots_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_shots_acc"] = stat[2].split("%")[0]
            if(stat[1] == "Strzały obronione"):
                match_stats_add["home_team_saves"] = stat[0]
                match_stats_add["away_team_saves"] = stat[2]
            if(stat[1] == "Strzały obr. %"):
                match_stats_add["home_team_saves_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_saves_acc"] = stat[2].split("%")[0]  
            if(stat[1] == "Gole w przewadze"):
                match_stats_add["home_team_pp_goals"] = stat[0]             
                match_stats_add["away_team_pp_goals"] = stat[2] 
            if(stat[1] == "Gole w osłabieniu"):
                match_stats_add["home_team_sh_goals"] = stat[0]
                match_stats_add["away_team_sh_goals"] = stat[2]
            if(stat[1] == "Gole w przewadze %"):
                match_stats_add["home_team_pp_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_pp_acc"] = stat[2].split("%")[0]
            if(stat[1] == "Obr. w osłabieniu %"):
                match_stats_add["home_team_pk_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_pk_acc"] = stat[2].split("%")[0]
            if(stat[1] == "Gra ciałem"):
                match_stats_add["home_team_hits"] = stat[0]
                match_stats_add["away_team_hits"] = stat[2]
            if(stat[1] == "Wznowienia wygrane"):
                match_stats_add["home_team_faceoffs"] = stat[0]
                match_stats_add["away_team_faceoffs"] = stat[2]
            if(stat[1] == "Wznowienia %"):
                match_stats_add["home_team_faceoffs_acc"] = stat[0].split("%")[0]  
                match_stats_add["away_team_faceoffs_acc"] = stat[2].split("%")[0]  
            if(stat[1] == "Straty"):
                match_stats_add["home_team_to"] = stat[0]
                match_stats_add["away_team_to"] = stat[2]
            if(stat[1] == "Gole do p. bramki"):
                match_stats_add["home_team_en"] = stat[0]
                match_stats_add["away_team_en"] = stat[2]
        if match_data['home_team_sc'] == 0:
            match_data['home_team_sc'] = match_data['home_team_sog']
        if match_data['away_team_sc'] == 0:
            match_data['away_team_sc'] = match_data['away_team_sog']        

    def get_match_boxscore(self, link, match_id):
        boxscore = []
        self.driver.get(link)
        time.sleep(2)
        #ui-table playerStatsTable
        columns_player = [
            'match_id',
            'player_id',
            'team_id',
            'goals',
            'assists',
            'points',
            'plus_minus',
            'penalty_minutes',
            'sog',
            'hits',
            'blocked',
            'turnovers',
            'steals',
            'faceoff',
            'faceoff_won',
            'faceoff_acc',
            'toi',
            'shots_acc'
        ]
        columns_goaltender = [
            'match_id',
            'player_id',
            'team_id',
            'points',
            'penalty_minutes',
            'toi',
            'shots_saved',
            'saves_acc',
            'shots_against',
        ]
        player_divs = self.driver.find_elements(By.CLASS_NAME, "playerStatsTable__row") 
        for player in player_divs:
            #Tu trochę magii, można spróbowac lepiej bo potem nic nie zrozumiem
            current_column = 0
            current_player_info = []
            current_player_info.append(match_id) #MATCH_ID
            divs = player.find_elements(By.XPATH, "./*")
            for div in divs:
                stat = div.text.strip().replace('%','')
                if current_column == 0: #COMMON NAME GRACZA
                    flash_id_div = player.find_element(By.TAG_NAME, 'a')
                    flash_id_link = flash_id_div.get_attribute('href')
                    flash_id = flash_id_link.split('/')[-2]
                    current_player_info.append(self.get_player_id(stat, flash_id))
                elif current_column == 1: #KLUB
                    current_player_info.append(self.get_player_team_id(stat))
                else:
                    #print(stat)
                    stat = "0" if stat == "-" else stat
                    current_player_info.append(stat)
                current_column = current_column + 1
                #print(current_player_info)
            #Drobna poprawka dla strzałów
        
            if len(current_player_info) == 8:
                saves_stat = current_player_info[6].split('-')
                current_player_info[6] = saves_stat[0]
                current_player_info.append(saves_stat[1])
                player_stats = dict(zip(columns_goaltender, current_player_info))
            #Tragiczny kod, ale to tylko dla starych meczow, potem usuwam
            #Obejscie dla zawodnikow dla starych danych (brak wzowien)
            elif len(current_player_info) == 15:
                current_player_info.insert(-2, 0)
                current_player_info.insert(-2, 0)
                player_stats = dict(zip(columns_player, current_player_info))
            #Obejscie dla bramkarzy dla starych danych (info o obronach w even i pp/pk)
            elif len(current_player_info) == 7:
                saves_stat = current_player_info[5].split('-')
                current_player_info[5] = saves_stat[0]
                current_player_info.append(saves_stat[1])
                goaltender_stats = [current_player_info[0], 
                                    current_player_info[1], 
                                    current_player_info[2], 
                                    current_player_info[3], 
                                    current_player_info[4], 
                                    '60:00', 
                                    current_player_info[5],
                                    current_player_info[6],
                                    current_player_info[7]]
                player_stats = dict(zip(columns_goaltender, goaltender_stats))  
            elif len(current_player_info) == 9:
                saves_stat = current_player_info[7].split('-')
                current_player_info[7] = saves_stat[0]
                current_player_info.append(saves_stat[1])
                goaltender_stats = [current_player_info[0], 
                                    current_player_info[1], 
                                    current_player_info[2], 
                                    current_player_info[3], 
                                    current_player_info[4], 
                                    '00:60:00', 
                                    current_player_info[7],
                                    current_player_info[8],
                                    current_player_info[9]]
                player_stats = dict(zip(columns_goaltender, goaltender_stats))  
            elif len(current_player_info) == 10:
                saves_stat = current_player_info[8].split('-')
                current_player_info[8] = saves_stat[0]
                current_player_info.append(saves_stat[1])
                goaltender_stats = [current_player_info[0], 
                                    current_player_info[1], 
                                    current_player_info[2], 
                                    current_player_info[3], 
                                    current_player_info[4], 
                                    '00:60:00', 
                                    current_player_info[8],
                                    current_player_info[9],
                                    current_player_info[10]]
                player_stats = dict(zip(columns_goaltender, goaltender_stats))                
            elif len(current_player_info) == 11:
                saves_stat = current_player_info[9].split('-')
                current_player_info[9] = saves_stat[0]
                current_player_info.append(saves_stat[1])
                goaltender_stats = [current_player_info[0], 
                                    current_player_info[1], 
                                    current_player_info[2], 
                                    current_player_info[3], 
                                    current_player_info[4], 
                                    current_player_info[5], 
                                    current_player_info[9],
                                    current_player_info[10],
                                    current_player_info[11]]
                player_stats = dict(zip(columns_goaltender, goaltender_stats))
            else:
                player_stats = dict(zip(columns_player, current_player_info))
            boxscore.append(player_stats)
        return boxscore
    
    def get_match_roster(self, link, match_id, home_team, away_team):
        self.driver.get(link)
        time.sleep(2)
        columns_roster = [
            'match_id',
            'player_id',
            'team_id',
            'position',
            'line',
            'number'
        ]
        match_roster = []
        current_index = -1
        current_line = 1
        positions = ['D', 'D', 'RW', 'C', 'LW']
        lineup_div = self.driver.find_element(By.CLASS_NAME, 'lf__lineUp')
        sections = lineup_div.find_elements(By.CLASS_NAME, 'section')[:4]
        for section in sections:
            current_player_info = []
            sides = section.find_elements(By.CLASS_NAME, 'lf__side')  
            #home_team = [player.text for player in sides[0].find_elements(By.CLASS_NAME, 'lf__participantNew') if player.text.strip()]
            #away_team = [player.text for player in sides[1].find_elements(By.CLASS_NAME, 'lf__participantNew') if player.text.strip()]  
            for player in sides[0].find_elements(By.CLASS_NAME, 'lf__participantNew'):
                player_info = player.text.strip().split('\n')
                flash_id_div = player.find_element(By.TAG_NAME, 'a')
                flash_id_link = flash_id_div.get_attribute('href')
                flash_id = flash_id_link.split('/')[-1]
                player_id = self.get_player_id(player_info[1], flash_id)
                position = []
                if current_index < 0:
                    position = 'G'
                else:
                    position = positions[current_index]
                current_player_info = [match_id, player_id, home_team, position, current_line, player_info[0]]
                current_index = current_index + 1
                match_roster.append(dict(zip(columns_roster, current_player_info)))

            current_index = -1 if current_line == 1 else 0

            for player in sides[1].find_elements(By.CLASS_NAME, 'lf__participantNew'):
                player_info = player.text.strip().split('\n')
                flash_id_div = player.find_element(By.TAG_NAME, 'a')
                flash_id_link = flash_id_div.get_attribute('href')
                flash_id = flash_id_link.split('/')[-1]
                player_id = self.get_player_id(player_info[1], flash_id)
                position = []
                if current_index < 0:
                    position = 'G'
                else:
                    position = positions[current_index]
                current_player_info = [match_id, player_id, away_team, position, current_line, player_info[0]]
                current_index = current_index + 1
                match_roster.append(dict(zip(columns_roster, current_player_info)))
            current_index = 0
            current_line = current_line + 1
        
        return match_roster

    def human_print(self, match_data, match_stats_add, match_events, match_boxscore, match_rosters):
        #Pretty print do logów, na razie jako słowniki, potem jako inserty
        print("GŁÓWNE DANE MECZOWE")
        for key,value in match_data.items():
            print("{} : {}".format(key, value)) 
        print("DODATKOWE STATYSTYKI MECZOWE") 
        for key,value in match_stats_add.items():
            print("{} : {}".format(key, value))   
        print("ZDARZENIA MECZOWE")
        for element in match_events:
            for key,value in element.items():
                print("{} : {}".format(key, value))  
        print("BOXSCORE")
        for element in match_boxscore:
            for key,value in element.items():
                print("{} : {}".format(key, value))
        print("SKŁADY")      
        for element in match_rosters:
            for key,value in element.items():
                print("{} : {}".format(key, value))

    def get_match_data(self, link, team_id):
        #1. Wczytac mecz standardowo do struktury matches
        #2. Zaczytac statystyki istotne dla hokeja do tabeli hockey_matches_add
        #3. Zaczytac zdarzenia meczowe do tabeli hockey_match_events
        #4. Zaczytac boxscore do tabeli hockey_match_player_stats
        #5. Zaczytac składy do tabeli hockey_match_roster
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
            'result' : 0,
            'sport_id' : 2}
        match_stats_add = {
            'match_id' : 0,
            'OT': 0,
            'SO' : 0,
            'home_team_pp_goals' : 0,
            'away_team_pp_goals' : 0,
            'home_team_sh_goals' : 0,
            'away_team_sh_goals' : 0,
            'home_team_shots_acc' : 0,
            'away_team_shots_acc' : 0,
            'home_team_saves' : 0,
            'away_team_saves' : 0,
            'home_team_saves_acc' : 0,
            'away_team_saves_acc' : 0,
            'home_team_pp_acc' : 0,
            'away_team_pp_acc' : 0,
            'home_team_pk_acc' : 0,
            'away_team_pk_acc' : 0,
            'home_team_faceoffs' : 0,
            'away_team_faceoffs' : 0,
            'home_team_faceoffs_acc' : 0,
            'away_team_faceoffs_acc' : 0,
            'home_team_hits' : 0,
            'away_team_hits' : 0,
            'home_team_to' : 0,
            'away_team_to' : 0,
            'home_team_en' : 0,
            'away_team_en' : 0,            
            'OTwinner' : 0,
            'SOwinner' : 0,
        }
        match_events = []
        match_boxscore = []
        match_rosters = []
        #1. 
        #TUTAJ MATCH_DATA BEZ STATYSTYK, SAM OPIS KTO Z KIM KIEDY
        ot_flag, ot_winner = self.get_match_info("{}szczegoly-meczu".format(link), team_id, match_data)
        if ot_flag == -1 and ot_winner == -1:
            return -1, -1, -1, -1, -1
        #2. 
        self.get_match_stats_add("{}statystyki-meczu/0".format(link), match_data, match_stats_add, ot_flag, ot_winner)
        match_stats_add['match_id'] = self.insert_match_data(match_data)
        print(f"#AKTUALNE ID MECZU: {match_stats_add['match_id']}")
        self.insert_procedure(match_stats_add, "hockey_matches_add")

        #3. 
        match_events = self.get_match_events("{}szczegoly-meczu".format(link), match_stats_add['match_id'], match_data['home_team'], match_data['away_team'])

        #4. 
        match_boxscore = self.get_match_boxscore("{}player-statistics/0".format(link), match_stats_add['match_id'])

        #5. 
        match_rosters = self.get_match_roster("{}sklady/0".format(link), match_stats_add['match_id'], match_data['home_team'], match_data['away_team'])
        self.insert_match_details(match_events, match_boxscore, match_rosters)

        #self.human_print(match_data, match_stats_add, match_events, match_boxscore, match_rosters)
        print(f"#Import meczu o ID {match_stats_add['match_id']} zakończony sukcesem")
        return match_data, match_stats_add, match_events, match_boxscore, match_rosters

    def insert_match_details(self, match_events, match_boxscore, match_rosters):
        for element in match_events:
            self.insert_procedure(element, "hockey_match_events")
        for element in match_boxscore:
            self.insert_procedure(element, "hockey_match_player_stats")
        for element in match_rosters:
            self.insert_procedure(element, "hockey_match_rosters")

    def insert_procedure(self, data, tablename):
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data)) 
        values = ', '.join([str(f"'{value}'") for value in data.values()])    
        query = f"INSERT INTO {tablename} ({columns}) VALUES ({placeholders});"
        #print(query)
        debug_query = f"INSERT INTO {tablename} ({columns}) VALUES ({values});"
        print(debug_query)
        cursor = self.conn.cursor()
        cursor.execute(query, tuple(data.values()))
        self.conn.commit()
        cursor.close()

    #FUNKCJE DO INSERTOWANIA
    def insert_match_data(self, match_data):
        self.insert_procedure(match_data, "matches")
        cursor = self.conn.cursor()
        cursor.execute("SELECT LAST_INSERT_ID();")
        match_id = cursor.fetchone()[0]
        cursor.close()
        return match_id

def get_shortcuts(conn, country):
    query = "select shortcut, id from teams where country = {} and sport_id = 2".format(country)
    teams_df = pd.read_sql(query, conn)
    shortcuts = teams_df.set_index('shortcut')['id'].to_dict()
    return shortcuts

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
    skip = int(sys.argv[5])
    no_to_download = int(sys.argv[6])
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query,conn)
    country = country_df.values.flatten() 
    query = "select name, id from teams where country = {} and sport_id = 2".format(country[0])
    teams_df = pd.read_sql(query, conn)
    team_id = teams_df.set_index('name')['id'].to_dict()
    shortcuts = get_shortcuts(conn, country[0])
    game_data = Game(driver, league_id, season_id, shortcuts, conn)
    if one_link == '-1':
        links = game_data.get_match_links(games, driver)
        if no_to_download == '-1':
            no_to_download = len(links)
        for link in links[skip:no_to_download]:
            match_data, _, _, _, _ = game_data.get_match_data(link, team_id)
            if match_data == -1:
                print("# ALL STAR ALBO PRZEDSEZONOWA - POMIJAMY")
            #break
    else:
        game_data.get_match_data(one_link, team_id)
    conn.close() 
if __name__ == '__main__':
    main()