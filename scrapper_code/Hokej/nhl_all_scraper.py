import time
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime, date, timedelta

import pandas as pd
import re
from utils import check_if_in_db

from db_module import db_connect

class Game:
    
    def __init__(self, driver, league_id, season_id, shortcuts, conn):
        """
        Inicjalizuje obiekt klasy Game.
        
        Args:
            driver: WebDriver Selenium do automatyzacji przeglądarki
            league_id (int): ID ligi w bazie danych
            season_id (int): ID sezonu w bazie danych
            shortcuts (dict): Mapowanie skrótów drużyn na ich ID
            conn: Połączenie z bazą danych
        """
        self.driver = driver 
        self.league_id = league_id
        self.season_id = season_id
        self.conn = conn
        self.shortcuts = shortcuts
        
        
    def extract_round(self, round_div, game_div):
        """
        Ekstraktuje informacje o rundzie/fazie rozgrywek z elementów strony.
        Metoda analizuje tekst z elementów HTML zawierających informacje o rundzie
        i mapuje je na odpowiednie numery rund używane w bazie danych.
        Args:
            round_div: Lista elementów HTML zawierających informacje o rundzie
            game_div: Lista elementów HTML zawierających dodatkowe informacje o grze
        Returns:
            int: Numer rundy (100 dla regularnego sezonu NHL, -1 dla meczów pomijanych,
                 900+ dla faz playoff)
        """
        round_str = ""
        for div in round_div:
            round_info = div.text.strip()
            round_str = round_info.split(" - ")[-1].strip()
        if round_str == 'NHL':
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
        """
        Mapuje nazwę rundy playoff na odpowiedni numer ID w bazie danych.
        
        Metoda pobiera ID rundy z tabeli special_rounds na podstawie nazwy rundy.
        
        Args:
            round_str (str): Tekstowa nazwa rundy w formacie "FAZA, X runda"
            
        Returns:
            int: ID rundy zgodne z mapowaniem w bazie danych (900-966)
                 lub None jeśli runda nie została znaleziona
        """
        cursor = self.conn.cursor()
        query = "SELECT id FROM special_rounds WHERE name = %s"
        cursor.execute(query, (round_str,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return result[0]
        else:
            print(f"UWAGA: Nie znaleziono ID dla rundy: {round_str}")
            return -1
        


    def parse_match_date(self, match_date):
        """
        Konwertuje datę meczu z formatu FlashScore na format bazy danych.
        
        Args:
            match_date (str): Data w formacie "dd.mm.yyyy HH:MM"
            
        Returns:
            str: Data w formacie "yyyy-mm-dd HH:MM" gotowa do wstawienia do bazy danych
        """
        date_object = datetime.strptime(match_date, "%d.%m.%Y %H:%M")
        date_formatted = date_object.strftime("%Y-%m-%d %H:%M")
        return date_formatted

    def get_match_links(self, games, timer, driver):
        """
        Pobiera linki do wszystkich meczów z strony wyników FlashScore w nowym formacie z parametrem mid.
        
        Args:
            games (str): URL strony z wynikami meczów na FlashScore
            driver: WebDriver Selenium
            timer: Timer do pomiaru czasu

        Returns:
            list: Lista linków do szczegółów poszczególnych meczów w formacie z ?mid=
        """
        links = []
        driver.get(games)
        time.sleep(timer)
        game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
        for element in game_divs:
            try:
                # Pobieramy link bezpośrednio z elementu (nowy format z ?mid=)
                link_element = element.find_element(By.TAG_NAME, "a")
                href = link_element.get_attribute('href')
                if href and 'flashscore.pl/mecz/' in href and '?mid=' in href:
                    links.append(href)
                else:
                    print(f"UWAGA: Nie znaleziono linku w nowym formacie dla elementu {element.get_attribute('id')}")
            except Exception as e:
                print(f"BŁĄD: Nie można pobrać linku dla elementu {element.get_attribute('id')}: {e}")
        return links

    def parse_match_page_data(self, driver):
        """
        Parsuje dane meczu ze strony FlashScore i zwraca przetworzone informacje.
        
        Args:
            driver: WebDriver Selenium
            
        Returns:
            tuple: (match_info, ot_flag) gdzie:
                - match_info (list): Lista z informacjami o meczu [data, -, gospodarze, -, goście, wynik, ...]
                - ot_flag (int): 0-brak dogrywki, 1-dogrywka, 2-rzuty karne
        """
        match_info = []
        ot_flag = 0
        # Pobieranie elementów ze strony
        time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
        team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
        score_divs = driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")
        full_time_divs = driver.find_elements(By.CLASS_NAME, "detailScore__fullTime")
        extra_time_divs = driver.find_elements(By.CLASS_NAME, "detailScore__status")
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
        return match_info, ot_flag

    def get_match_info(self, link, team_id, match_data, update=False):
        """
        Pobiera podstawowe informacje o meczu ze strony FlashScore.
        
        Metoda ekstraktuje dane takie jak wynik, drużyny, data, informacje o dogrywce
        i sprawdza czy mecz już istnieje w bazie danych.
        
        Args:
            link (str): URL do strony szczegółów meczu na FlashScore
            team_id (dict): Mapowanie nazw drużyn na ich ID w bazie danych
            match_data (dict): Słownik do wypełnienia danymi meczu
            update (bool): Czy aktualizować istniejące mecze (pomija sprawdzenie duplikatów)
            
        Returns:
            tuple: (ot_flag, ot_winner) gdzie:
                - ot_flag (int): 0-brak dogrywki, 1-dogrywka, 2-rzuty karne
                - ot_winner (int): 0-brak dogrywki, 1-gospodarze wygrali, 2-goście wygrali
                Lub (-1, -1) jeśli mecz należy pominąć
        """
        match_info = []
        ot_flag = 0
        ot_winner = 0 # 0 - brak dogrywki, 1 - gospodarze wygrali, 2 - goście wygrali
        self.driver.get(link)
        time.sleep(5)
        round_div = self.driver.find_elements(By.CLASS_NAME, "wcl-scores-overline-03_KIU9F")
        game_div = self.driver.find_elements(By.CLASS_NAME, "infoBox__info")
        match_data['round'] = self.extract_round(round_div, game_div)
        if match_data['round'] == -1:
            return -1, -1
            
        # Parsowanie danych ze strony przy użyciu wyodrębnionej funkcji
        match_info, ot_flag = self.parse_match_page_data(self.driver)
        
        # Wypełnienie danych meczu
        match_data['league'] = self.league_id
        match_data['season'] = self.season_id
        match_data['home_team'] = team_id[match_info[1]]
        match_data['away_team'] = team_id[match_info[3]]
        match_data['game_date'] = self.parse_match_date(match_info[0])
        check_id = check_if_in_db(match_data['home_team'], match_data['away_team'], game_date=match_data['game_date'])
        if check_id != -1 and not update:
            print(f"#Ten mecz znajduje się już w bazie danych!, ID:{check_id}")
            return -1, -1
        elif check_id != -1 and update:
            print(f"#Aktualizacja meczu o ID:{check_id}")
            match_data['existing_id'] = check_id  # Zapisujemy ID istniejącego meczu
        score = match_info[5].split('\n')
        home_goals = int(score[0])
        away_goals = int(score[2])
        if ot_flag:
            # Wynik w score będzie po dogrywce - pobieramy wynik z czasu regularnego
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
        """
        Mapuje nazwy zdarzeń z FlashScore na odpowiednie ID w bazie danych.
        Args:
            event (str): Nazwa klasy CSS reprezentującej typ zdarzenia
        Returns:
            int: ID typu zdarzenia w bazie danych lub 0 jeśli zdarzenie nie zostało rozpoznane
        """
        # Mapowanie na sztywno - raczej nie poprawiam
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

    def add_player(self, common_name, flash_id):
        """
        Dodaje nowego gracza do bazy danych z podaną nazwą i ID z FlashScore.
        
        Args:
            common_name (str): Powszechna nazwa gracza
            flash_id (str): Zewnętrzne ID gracza z FlashScore
            
        Returns:
            int: ID nowo dodanego gracza lub -1 w przypadku błędu
        """
        query = "INSERT INTO players(common_name, external_flash_id) VALUES (%s, %s)"
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (common_name, flash_id))
            self.conn.commit()
            cursor.execute("SELECT LAST_INSERT_ID()")
            print(f"Gracz dodany do bazy danych: {common_name}, flash_id: {flash_id}")
            player_id = cursor.fetchone()[0]
            return player_id
        except Exception as e:
            print(f"Error adding player to database: {e}")
            return -1
        finally:
            cursor.close()

    def get_player_id(self, common_name, flash_id = None):
        """
        Pobiera ID gracza z bazy danych na podstawie nazwy i opcjonalnie flash_id.
        
        Metoda implementuje logikę wyszukiwania gracza:
        1. Jeśli nie ma gracza o podanej nazwie, próbuje znaleźć po flash_id lub dodaje nowego
        2. Jeśli jest dokładnie jeden gracz o podanej nazwie, zwraca jego ID
        3. Jeśli jest więcej graczy o tej samej nazwie, używa flash_id do rozróżnienia
        
        Args:
            common_name (str): Powszechna nazwa gracza
            flash_id (str, optional): Zewnętrzne ID gracza z FlashScore
            
        Returns:
            int: ID gracza w bazie danych lub -1 jeśli nie znaleziono
        """
        player_id = -1
        cursor = self.conn.cursor()
        try:
            # 1. Sprawdź ilu jest graczy z podanym common_name
            query_count = "SELECT COUNT(*) FROM players WHERE common_name = %s and sports_id = 2"
            cursor.execute(query_count, (common_name,))
            count = cursor.fetchone()[0]
            if count == 0:
                flash_player_id = "SELECT id FROM players where external_flash_id = %s and sports_id = 2"
                cursor.execute(flash_player_id, (flash_id,))
                result = cursor.fetchone()
                if result:
                    player_id = result[0]
                else:
                    player_id = self.add_player(common_name, flash_id)
                    print(f'BRAK GRACZA O PODANYM COMMON_NAME. Common name: {common_name}, flash_id: {flash_id}')
                    print(f'#Dodano gracza do bazy danych: {common_name}')
            elif count == 1:
                # 2. Jeśli jest dokładnie jeden gracz, pobierz jego id
                query_single = "SELECT id FROM players WHERE common_name = %s and sports_id = 2"
                cursor.execute(query_single, (common_name,))
                result = cursor.fetchone()
                if result:
                    player_id = result[0]
            else:
                # 3. Jeśli jest więcej niż jeden gracz, użyj flash_id do znalezienia właściwego
                query_by_flash_id = """
                    SELECT id FROM players 
                    WHERE common_name = %s AND external_flash_id = %s  and sports_id = 2
                """
                cursor.execute(query_by_flash_id, (common_name, flash_id))
                result = cursor.fetchone()
                if result:
                    player_id = result[0]
                else:
                    print(f'#BRAK GRACZA O PODANYM external_flash_id. Common name: {common_name}, flash_id: {flash_id}')
        except Exception as e:
            print(f"Wystąpił błąd: {e}")
        finally:
            cursor.close()
        return player_id
    
    def insert_match(self):
        """
        Placeholder dla metody wstawiania meczu do bazy danych.
        
        Returns:
            None
        """
        pass

    def get_player_team_id(self, shortcut):
        """
        Pobiera ID drużyny na podstawie skrótu, uwzględniając tłumaczenia z FlashScore.
        
        Args:
            shortcut (str): Skrót nazwy drużyny z FlashScore
            
        Returns:
            int: ID drużyny w bazie danych
        """
        # Tłumaczenia z FlashScore na skróty używane w bazie danych
        translations = {
            'NAS': 'NSH',
            'WIN': 'WPG',
            'LOS': 'LAK',
            'MON': 'MTL'
        }
        
        shortcut = translations.get(shortcut, shortcut)
        return self.shortcuts[shortcut]

    def get_match_events(self, link, match_id, home_team, away_team):
        """
        Pobiera szczegółowe zdarzenia z meczu (gole, kary, asysy itp.) ze strony FlashScore.
        
        Args:
            link (str): URL do strony szczegółów meczu
            match_id (int): ID meczu w bazie danych
            home_team (int): ID drużyny gospodarzy
            away_team (int): ID drużyny gości
            
        Returns:
            list: Lista słowników zawierających dane o zdarzeniach meczu:
                - event_id: ID typu zdarzenia
                - match_id: ID meczu
                - team_id: ID drużyny
                - player_id: ID gracza (lub 0 jeśli nieznany)
                - period: Numer okresu (1-5, gdzie 4=dogrywka, 5=karne)
                - event_time: Czas zdarzenia w formacie tekstowym
                - pp_flag: Flaga gola w przewadze (1/0)
                - en_flag: Flaga gola do pustej bramki (1/0)
                - description: Opis zdarzenia
        """
        self.driver.get(link)
        time.sleep(5)
        match_events_lists = []
        game_log = self.driver.find_element(By.CLASS_NAME, "smv__verticalSections.section")
        game_events_divs = game_log.find_elements(By.XPATH, "./*")
        current_period = 0
        for div in game_events_divs:
            if "wclHeaderSection--summary" in div.get_attribute("class"):
                # Jeśli napotkamy nowy nagłówek, zapisujemy aktualny licznik i resetujemy
                # PERIOD 4 = DOGRYWKA
                # PERIOD 5 = KARNE
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
                if match_events['player_id'] == 0 and (match_events['event_id'] in [183, 186, 184]):
                    match_events['player_id'] = 2002 # Definicja gracza w bazie
                match_events_lists.append(match_events)
        return match_events_lists

    def get_match_stats_add(self, link, match_data, match_stats_add, ot_flag, ot_winner):
        stats = []
        self.driver.get(link)
        #print("MATCH_STATS_ADD")
        time.sleep(5)
        if ot_flag == 1:
            match_stats_add["OT"] = 1
            match_stats_add["OTwinner"] = ot_winner
        if ot_flag == 2:
            match_stats_add["OT"] = 1
            match_stats_add["SO"] = 1
            match_stats_add["OTwinner"] = 3
            match_stats_add["SOwinner"] = ot_winner
        stat_divs = self.driver.find_elements(By.CLASS_NAME, "wcl-row_2oCpS")
        for div in stat_divs:
            stats.append(div.text.strip())
        for element in stats:
            stat = element.split('\n')
            ### SEKCJA MATCH_DATA
            if(stat[1] == 'Strzały na bramkę'):
                match_data['home_team_sog'] = stat[0]
                match_data['away_team_sog'] = stat[2]
            elif(stat[1] == "Strzały niecelne"):
                match_data['home_team_sc'] = str(int(match_data['home_team_sog']) + int(stat[0]))
                match_data['away_team_sc'] = str(int(match_data['away_team_sog']) + int(stat[2]))
            elif(stat[1] == "Suma kar"):
                match_data["home_team_fk"] = stat[0]
                match_data["away_team_fk"] = stat[2]
            elif(stat[1] == "Kary"):
                match_data["home_team_fouls"] = stat[0]
                match_data["away_team_fouls"] = stat[2]
            elif(stat[2] == "Skuteczność %"):
                match_stats_add["home_team_shots_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_shots_acc"] = stat[3].split("%")[0]
            elif(stat[1] == "Strzały obronione"):
                match_stats_add["home_team_saves"] = stat[0]
                match_stats_add["away_team_saves"] = stat[2]
            elif(stat[2] == "Strzały obr. %"):
                match_stats_add["home_team_saves_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_saves_acc"] = stat[3].split("%")[0]  
            elif(stat[1] == "Gole w przewadze"):
                match_stats_add["home_team_pp_goals"] = stat[0]             
                match_stats_add["away_team_pp_goals"] = stat[2] 
            elif(stat[1] == "Gole w osłabieniu"):
                match_stats_add["home_team_sh_goals"] = stat[0]
                match_stats_add["away_team_sh_goals"] = stat[2]
            elif(stat[2] == "Gole w przewadze %"):
                match_stats_add["home_team_pp_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_pp_acc"] = stat[3].split("%")[0]
            if(stat[2] == "Obr. w osłabieniu %"):
                match_stats_add["home_team_pk_acc"] = stat[0].split("%")[0]
                match_stats_add["away_team_pk_acc"] = stat[3].split("%")[0]
            elif(stat[1] == "Gra ciałem"):
                match_stats_add["home_team_hits"] = stat[0]
                match_stats_add["away_team_hits"] = stat[2]
            elif(stat[1] == "Wznowienia wygrane"):
                match_stats_add["home_team_faceoffs"] = stat[0]
                match_stats_add["away_team_faceoffs"] = stat[2]
            elif(stat[1] == "Wznowienia %"):
                match_stats_add["home_team_faceoffs_acc"] = stat[0].split("%")[0]  
                match_stats_add["away_team_faceoffs_acc"] = stat[2].split("%")[0]  
            elif(stat[1] == "Straty"):
                match_stats_add["home_team_to"] = stat[0]
                match_stats_add["away_team_to"] = stat[2]
            elif(stat[1] == "Gole do p. bramki"):
                match_stats_add["home_team_en"] = stat[0]
                match_stats_add["away_team_en"] = stat[2]
            else:
                pass #Niepotrzebna statystyka
        if match_data['home_team_sc'] == 0:
            match_data['home_team_sc'] = match_data['home_team_sog']
        if match_data['away_team_sc'] == 0:
            match_data['away_team_sc'] = match_data['away_team_sog']        

    def get_match_boxscore(self, link, match_id):
        boxscore = []
        self.driver.get(link)
        time.sleep(5)
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
            'toi'
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
                    stat = "0" if stat == "-" else stat
                    current_player_info.append(stat)
                current_column = current_column + 1
                #print(current_player_info)
            #Drobna poprawka dla strzałów
            if len(current_player_info) == 8:
                saves_stat = current_player_info[6].split('-')
                current_player_info[6] = saves_stat[0]
                if len(saves_stat) > 1:
                    current_player_info.append(saves_stat[1])
                player_stats = dict(zip(columns_goaltender, current_player_info))
                '''player_stats = [
                    current_player_info[0],
                    current_player_info[1],
                    current_player_info[2],
                    current_player_info[3],
                    current_player_info[4],
                    current_player_info[5],
                    current_player_info[6],
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1,
                    -1]
                player_stats = dict(zip(columns_player, current_player_info))'''
            #Tragiczny kod, ale to tylko dla starych meczow, potem usuwam
            #Obejscie dla zawodnikow dla starych danych (brak wzowien)
            elif len(current_player_info) == 15:
                current_player_info.insert(-2, 0)
                current_player_info.insert(-2, 0)
                player_stats = dict(zip(columns_player, current_player_info))
            elif len(current_player_info) == 16:
                faceoff_won = 0
                if int(current_player_info[-2]) != 0:
                    faceoff_won = round((100 * int(current_player_info[-3])) / int(current_player_info[-2]))
                current_player_info.insert(-3, faceoff_won)
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
                                    '60:00:00', 
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
                                    '60:00:00', 
                                    current_player_info[8],
                                    current_player_info[9],
                                    current_player_info[10]]
                player_stats = dict(zip(columns_goaltender, goaltender_stats))                
            elif len(current_player_info) == 11:
                saves_stat = current_player_info[9].split('-')
                current_player_info[9] = saves_stat[0]
                if len(saves_stat) > 1:
                    current_player_info.append(saves_stat[1])
                else:
                    current_player_info.append(0)
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
        time.sleep(5)
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
                if len(player_info) < 2:
                    player_info.insert(0, '00')
                if len(flash_id) < 2:
                    flash_id = flash_id.insert(0, '00')
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
                if len(player_info) < 2:
                    player_info.insert(0, '00')
                if len(flash_id) < 2:
                    flash_id = flash_id.insert(0, '00')
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

    def pretty_print(self, match_data, match_stats_add, match_events, match_boxscore, match_rosters):
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

    def get_upcoming_matches(self, link, team_id, timer, driver):
        match_data = {
            'league': 0,
            'season': 0,
            'home_team' : 0,
            'away_team' : 0,
            'game_date' : 0,
            'round' : 0,
            'result' : 0,
            'sport_id' : 2}
        match_info = []
        self.driver.get(link)
        time.sleep(timer)
        round_div = self.driver.find_elements(By.CLASS_NAME, "wcl-scores-overline-03_KIU9F")
        game_div = self.driver.find_elements(By.CLASS_NAME, "infoBox__info")
        match_data['round'] = self.extract_round(round_div, game_div)
        if match_data['round'] == -1:
            return -1
        # Parsowanie danych ze strony przy użyciu wyodrębnionej funkcji
        match_info, _ = self.parse_match_page_data(self.driver)
        # Wypełnienie danych meczu
        match_data['league'] = self.league_id
        match_data['season'] = self.season_id
        match_data['home_team'] = team_id[match_info[1]]
        match_data['away_team'] = team_id[match_info[3]]
        match_data['game_date'] = self.parse_match_date(match_info[0])
        
        # Sprawdzenie czy data meczu nie jest późniejsza niż jutrzejsza data
        today = date.today()
        tomorrow = today + timedelta(days=1)
        match_date_obj = datetime.strptime(match_data['game_date'], "%Y-%m-%d %H:%M").date()
        
        if match_date_obj > tomorrow:
            print(f"#Mecz z dnia {match_date_obj} jest późniejszy niż jutrzejsza data ({tomorrow}). Przerywanie pobierania.")
            return -1
        
        check_id = check_if_in_db(match_data['home_team'], match_data['away_team'], game_date=match_data['game_date'])
        if check_id != -1:
            print(f"#Ten mecz znajduje się już w bazie danych!, ID:{check_id}")
            return -1
        
        upcoming_match_id = self.insert_match_data(match_data)
        print(f"#Dodano nadchodzący mecz do bazy danych: {upcoming_match_id}")
        return upcoming_match_id


    def get_match_data(self, link, team_id, automate=False, update=False):
        """
        Główna metoda pobierająca wszystkie dane meczu z FlashScore i zapisująca je do bazy danych.
        
        Metoda wykonuje kompletny proces scrapowania meczu:
        1. Pobiera podstawowe informacje o meczu
        2. Pobiera dodatkowe statystyki hokejowe
        3. Pobiera zdarzenia meczowe (gole, kary itp.)
        4. Pobiera statystyki graczy (boxscore)
        5. Pobiera składy drużyn
        6. Zapisuje wszystkie dane do odpowiednich tabel w bazie danych (jeśli automate=True)
        
        Args:
            link (str): Bazowy URL meczu na FlashScore (bez końcówki)
            team_id (dict): Mapowanie nazw drużyn na ich ID w bazie danych
            automate (bool): Czy automatycznie zapisywać dane do bazy danych
            update (bool): Czy aktualizować istniejące mecze (działa tylko gdy automate=True)
            
        Returns:
            tuple: (match_data, match_stats_add, match_events, match_boxscore, match_rosters)
                lub (-1, -1, -1, -1, -1) jeśli mecz należy pominąć
        """
        # 1. Wczytać mecz standardowo do struktury matches
        # 2. Załadować statystyki istotne dla hokeja do tabeli hockey_matches_add
        # 3. Załadować zdarzenia meczowe do tabeli hockey_match_events
        # 4. Załadować boxscore do tabeli hockey_match_player_stats
        # 5. Załadować składy do tabeli hockey_match_roster
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
        
        # Funkcja do budowania URL-ów w nowym formacie FlashScore
        def build_url(base_link, path):        
            # Mapowanie ścieżek dla nowego formatu FlashScore
            path_mapping = {
                "statystyki/0": "szczegoly/statystyki/0", 
                "sklady/0": "szczegoly/sklady/0",
                "statystyki-gracza/ogolnie": "szczegoly/statystyki-gracza/ogolnie"
            }
            parts = base_link.split('?mid=')
            base_url = parts[0].rstrip('/')  # Usuwamy końcowy slash jeśli istnieje
            mapped_path = path_mapping.get(path, path)
            return f"{base_url}/{mapped_path}/?mid={parts[1]}"
        
        # 1. Pobieranie podstawowych danych meczu
        #szczegoly_url = build_url(link, "szczegoly-meczu")
        ot_flag, ot_winner = self.get_match_info(link, team_id, match_data, update)
        if ot_flag == -1 and ot_winner == -1:
            return -1, -1, -1, -1, -1
            
        # 2. Pobieranie dodatkowych statystyk hokejowych
        stats_url = build_url(link, "statystyki/0")
        self.get_match_stats_add(stats_url, match_data, match_stats_add, ot_flag, ot_winner)
        
        # Zapisywanie do bazy danych tylko jeśli automate=True
        if automate:
            if 'existing_id' in match_data and update:
                # Aktualizacja istniejącego meczu
                self.update_match_data(match_data, match_data['existing_id'])
                match_stats_add['match_id'] = match_data['existing_id']
                print(f"#AKTUALIZACJA MECZU O ID: {match_stats_add['match_id']}")
            else:
                # Nowy mecz
                match_stats_add['match_id'] = self.insert_match_data(match_data)
                print(f"#NOWY MECZ O ID: {match_stats_add['match_id']}")
            
            self.insert_procedure(match_stats_add, "hockey_matches_add")
        else:
            # Tryb testowy - tylko symulacja ID
            match_stats_add['match_id'] = 999999  # Tymczasowe ID dla trybu testowego
            print(f"#TRYB TESTOWY - SYMULACJA ID MECZU: {match_stats_add['match_id']}")

        # 3. Pobieranie zdarzeń meczowych
        match_events = self.get_match_events(link, match_stats_add['match_id'], match_data['home_team'], match_data['away_team'])

        # 4. Pobieranie statystyk graczy (boxscore)
        boxscore_url = build_url(link, "statystyki-gracza/ogolnie")
        match_boxscore = self.get_match_boxscore(boxscore_url, match_stats_add['match_id'])

        # 5. Pobieranie składów drużyn
        rosters_url = build_url(link, "sklady/0")
        match_rosters = self.get_match_roster(rosters_url, match_stats_add['match_id'], match_data['home_team'], match_data['away_team'])
        
        # Zapisywanie szczegółów tylko jeśli automate=True
        if automate:
            self.insert_match_details(match_events, match_boxscore, match_rosters)
            print(f"#Import meczu o ID {match_stats_add['match_id']} zakończony sukcesem")
        else:
            print(f"#Przetwarzanie meczu (tryb testowy) zakończone sukcesem")

        return match_data, match_stats_add, match_events, match_boxscore, match_rosters


    def insert_match_details(self, match_events, match_boxscore, match_rosters):
        """
        Wstawia wszystkie szczegółowe dane meczu do odpowiednich tabel w bazie danych.
        
        Args:
            match_events (list): Lista zdarzeń meczowych
            match_boxscore (list): Lista statystyk graczy
            match_rosters (list): Lista składów drużyn
            
        Returns:
            None
        """
        for element in match_events:
            self.insert_procedure(element, "hockey_match_events")
        for element in match_boxscore:
            self.insert_procedure(element, "hockey_match_player_stats")
        for element in match_rosters:
            self.insert_procedure(element, "hockey_match_rosters")

    def insert_procedure(self, data, tablename):
        """
        Uniwersalna procedura wstawiania danych do tabeli w bazie danych.
        
        Args:
            data (dict): Słownik z danymi do wstawienia (klucze = nazwy kolumn, wartości = dane)
            tablename (str): Nazwa tabeli docelowej
            
        Returns:
            None
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data)) 
        values = ', '.join([str(f"'{value}'") for value in data.values()])    
        query = f"INSERT INTO {tablename} ({columns}) VALUES ({placeholders});"
        debug_query = f"INSERT INTO {tablename} ({columns}) VALUES ({values});"
        print(debug_query)
        cursor = self.conn.cursor()
        cursor.execute(query, tuple(data.values()))
        self.conn.commit()
        cursor.close()

    def insert_match_data(self, match_data):
        """
        Wstawia podstawowe dane meczu do tabeli matches i zwraca ID nowego rekordu.
        
        Args:
            match_data (dict): Słownik z podstawowymi danymi meczu
            
        Returns:
            int: ID nowo wstawionego meczu
        """
        self.insert_procedure(match_data, "matches")
        cursor = self.conn.cursor()
        cursor.execute("SELECT LAST_INSERT_ID();")
        match_id = cursor.fetchone()[0]
        cursor.close()
        return match_id

    def update_match_data(self, match_data, match_id):
        """
        Aktualizuje istniejący mecz w tabeli matches.
        Args:
            match_data (dict): Słownik z danymi meczu do aktualizacji
            match_id (int): ID meczu do aktualizacji
        Returns:
            None
        """
        # Usuwamy existing_id z danych do aktualizacji (nie jest kolumną w tabeli)
        update_data = {k: v for k, v in match_data.items() if k != 'existing_id'}
        set_clause = ', '.join([f"{key} = %s" for key in update_data.keys()])
        query = f"UPDATE matches SET {set_clause} WHERE id = %s;"
        values = list(update_data.values())
        values.append(match_id)
        debug_values = ', '.join([f"{key} = '{value}'" for key, value in update_data.items()])
        debug_query = f"UPDATE matches SET {debug_values} WHERE id = {match_id};"
        print(debug_query)
        cursor = self.conn.cursor()
        cursor.execute(query, tuple(values))
        self.conn.commit()
        cursor.close()

def get_shortcuts(conn, country):
    """
    Pobiera mapowanie skrótów nazw drużyn na ich ID z bazy danych.
    
    Args:
        conn: Połączenie z bazą danych
        country (int): ID kraju, dla którego pobieramy drużyny
    
    Returns:
        dict: Słownik mapujący skróty drużyn na ich ID
    """
    query = "select shortcut, id from teams where country = {} and sport_id = 2".format(country)
    teams_df = pd.read_sql(query, conn)
    shortcuts = teams_df.set_index('shortcut')['id'].to_dict()
    return shortcuts

def get_country(conn, league_id):
    """
    Pobiera ID kraju na podstawie ID ligi.

    Args:
        conn: Połączenie z bazą danych
        league_id (int): ID ligi

    Returns:
        int: ID kraju
    """
    query = "select country from leagues where id = {}".format(league_id)
    country_df = pd.read_sql(query, conn)
    return country_df['country'].values[0]

def get_teams_ids(conn, country):
    """
    Pobiera słownik ID drużyn na podstawie ID kraju.

    Args:
        conn: Połączenie z bazą danych
        country (int): ID kraju

    Returns:
        dict: Słownik drużyn z ich ID
    """
    query = "select name, id from teams where country = {} and sport_id = 2".format(country)
    teams_df = pd.read_sql(query, conn)
    return teams_df.set_index('name')['id'].to_dict()

def parse_arguments():
    """
    Parsuje argumenty z linii poleceń dla scrapera meczów NHL z FlashScore.
    
    Returns:
        argparse.Namespace: Sparsowane argumenty z linii poleceń
    """
    parser = argparse.ArgumentParser(
        description="""Scraper danych meczów NHL z FlashScore.
        
        Skrypt umożliwia pobieranie danych o meczach w dwóch trybach:
        - Pobranie wielu meczów z listy wyników (domyślnie)
        - Pobranie pojedynczego meczu (gdy podano konkretny link)
        
        Przykłady użycia:
        - Pobranie wszystkich meczów z listy:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/wyniki/"
        
        - Pobranie meczów z pominięciem pierwszych 5:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/wyniki/" --skip 5
        
        - Pobranie tylko 10 meczów:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/wyniki/" --no_to_download 10
        
        - Pobranie meczów od 5. do 15.:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/wyniki/" --skip 5 --no_to_download 15
        
        - Pobranie konkretnego meczu:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/wyniki/" --one_link "https://www.flashscore.pl/mecz/hokej/san-jose-sharks-E588Co9j/utah-mammoth-hnwxhtVp/?mid=hh8uZJlL"
        
        - Tryb produkcyjny z zapisem do bazy danych:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/wyniki/" --automate
        
        - Aktualizacja istniejących meczów:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/wyniki/" --automate --update
        
        - Przetwarzanie przyszłych meczów:
          python nhl_all_scraper.py 45 7 "https://www.flashscore.pl/hokej/usa/nhl-2017-2018/" --upcoming
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('league_id', type=int, help='ID ligi w bazie danych')
    parser.add_argument('season_id', type=int, help='ID sezonu w bazie danych')
    parser.add_argument('games_url', type=str, help='Link do strony z wynikami na FlashScore')
    parser.add_argument('--one_link', type=str, default='-1', 
                       help='Link do konkretnego meczu (domyślnie: tryb wielu meczów)')
    parser.add_argument('--skip', type=int, default=0, 
                       help='Liczba meczów do pominięcia na początku listy (domyślnie: 0)')
    parser.add_argument('--no_to_download', type=int, default=-1, 
                       help='Liczba meczów do pobrania (domyślnie: wszystkie)')
    parser.add_argument('--automate', action='store_true',
                       help='Automatyczny zapis danych do bazy (domyślnie: tryb testowy bez zapisu)')
    parser.add_argument('--upcoming', action='store_true',
                       help='Wskazanie że są to przyszłe mecze (do późniejszej realizacji)')
    parser.add_argument('--update', action='store_true',
                       help='Aktualizuj już istniejące mecze w bazie danych')
    
    args = parser.parse_args()
    return args

def main():
    """
    Główna funkcja programu odpowiedzialna za scrapowanie danych meczów NHL z FlashScore.
    
    Funkcja umożliwia pobieranie danych o meczach w dwóch trybach:
    - Pobranie pojedynczego meczu (gdy podano konkretny link)
    - Pobranie wielu meczów z listy wyników
    
    Args:
        Argumenty są pobierane z linii poleceń przez funkcję parse_arguments():
        - league_id: ID ligi w bazie danych
        - season_id: ID sezonu w bazie danych
        - games_url: Link do strony z wynikami na FlashScore
        - one_link (opcjonalny): Link do konkretnego meczu (domyślnie: tryb wielu meczów)
        - skip (opcjonalny): Liczba meczów do pominięcia na początku listy (domyślnie: 0)
        - no_to_download (opcjonalny): Liczba meczów do pobrania (domyślnie: wszystkie)
    """
    args = parse_arguments()
    timer_dict = {'upcoming' : 5, 'update' : 5, 'default' : 5}
    timer = timer_dict['default']
    # Informowanie o trybie działania
    if args.automate:
        print("Tryb produkcyjny - dane będą zapisywane do bazy danych.")
        if args.update:
            print("Tryb aktualizacji - istniejące mecze będą aktualizowane.")
            timer = timer_dict['update']
    else:
        print("Tryb testowy - dane będą tylko przetwarzane bez zapisu do bazy.")

    conn = db_connect()
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    
    country = get_country(conn, args.league_id)
    team_id = get_teams_ids(conn, country)
    shortcuts = get_shortcuts(conn, country)
    game_data = Game(driver, args.league_id, args.season_id, shortcuts, conn)

    if args.upcoming:
        timer = timer_dict['upcoming']
        links = game_data.get_match_links(args.games_url, timer, driver)
        for link in links:
            match_id = game_data.get_upcoming_matches(link, team_id, timer, driver)
            if match_id == -1:
                print("# Zakończono przetwarzanie przyszłych meczów.")
                return

    if args.one_link == '-1':
        links = game_data.get_match_links(args.games_url, timer, driver)
        if args.no_to_download == -1:
            args.no_to_download = len(links)
        for link in links[args.skip:args.no_to_download]:
            match_data, _, _, _, _ = game_data.get_match_data(link, team_id, args.automate, args.update)
            if match_data == -1:
                print("# ALL STAR ALBO PRZEDSEZONOWA - POMIJAMY")
                return
    else:
        game_data.get_match_data(args.one_link, team_id, args.automate, args.update)
    conn.close() 
if __name__ == '__main__':
    main()