#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scraper danych meczów koszykówki z FlashScore - obsługa nowego formatu URL z parametrem ?mid=

Ten skrypt obsługuje wyłącznie nowy format URL-ów FlashScore z parametrem ?mid=.
Stary format z fragmentami (#/) nie jest już obsługiwany.

Przykład obsługiwanego formatu URL:
https://www.flashscore.pl/mecz/koszykowka/indiana-pacers-YPohMUTt/oklahoma-city-thunder-0fHFHEWD/?mid=YasLoKTi

Pobierane dane:
1. Podstawowe informacje o meczu (tabela MATCHES)
2. Dodatkowe statystyki koszykarskie (tabela BASKETBALL_MATCHES_ADD)
3. Statystyki zawodników (tabela BASKETBALL_MATCH_PLAYER_STATS)
4. Składy drużyn (tabela BASKETBALL_MATCH_ROSTERS)
"""

import time
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime
import pandas as pd
import re
from dataclasses import fields, asdict
from tqdm import tqdm
from utils import (check_if_in_db, BasketballMatchData, BasketballMatchStatsAdd, 
                   BasketballPlayerStats, BasketballMatchRoster, build_basketball_url,
                   parse_match_date, calculate_result, parse_score, safe_int, safe_plus_minus)

from db_module import db_connect

class Game:
    
    def __init__(self, driver, league_id, season_id, shortcuts, conn, test_print=False):
        """
        Inicjalizuje obiekt klasy Game dla koszykówki.
        
        Args:
            driver: WebDriver Selenium do automatyzacji przeglądarki
            league_id (int): ID ligi w bazie danych
            season_id (int): ID sezonu w bazie danych
            shortcuts (dict): Mapowanie skrótów drużyn na ich ID
            conn: Połączenie z bazą danych
            test_print (bool): Czy wyświetlać szczegółowe komunikaty diagnostyczne
        """
        self.driver = driver 
        self.league_id = league_id
        self.season_id = season_id
        self.conn = conn
        self.test_print = test_print
        self.shortcuts = shortcuts
        self.shortcuts = shortcuts
        
    def extract_round(self, round_div, game_div):
        """
        Ekstraktuje informacje o rundzie/fazie rozgrywek z elementów strony koszykarskiej.
        
        Args:
            round_div: Lista elementów HTML zawierających informacje o rundzie
            game_div: Lista elementów HTML zawierających dodatkowe informacje o grze
            
        Returns:
            int: Numer rundy (100 dla regularnego sezonu, -1 dla pomijanych, 900+ dla playoff)
        """
        round_str = ""
        for div in round_div:
            round_info = div.text.strip()
            round_str = round_info.split(" - ")[-1].strip()
        
        # Mapowanie dla różnych lig koszykarskich
        if round_str in ['NBA']:
            return 100
        if round_str in ['All Stars', 'Przedsezonowy']:
            return -1
            
        # Playoff - do rozbudowy w przyszłości
        for div in game_div:
            game_info = div.text.strip()
            match = re.search(r"(\d+\s+runda)", game_info)
            if match:
                game_str = match.group(1)
                round_str = round_str + ", " + game_str
                
        return self.get_special_round(round_str)

    def get_special_round(self, round_str):
        """
        Pobiera ID rundy specjalnej z bazy danych na podstawie nazwy rundy.
        
        Args:
            round_str (str): Tekstowa nazwa rundy
            
        Returns:
            int: ID rundy z tabeli special_rounds lub 100 (sezon regularny) jeśli nie znaleziono
        """
        query = "SELECT id FROM special_rounds WHERE name = %s"
        cursor = self.conn.cursor()
        cursor.execute(query, (round_str,))
        result = cursor.fetchone()
        cursor.close()
        round_id = result[0]
        return round_id

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
        Pobiera linki do wszystkich meczów koszykarskich z strony wyników FlashScore.
        
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
                link_element = element.find_element(By.TAG_NAME, "a")
                href = link_element.get_attribute('href')
                if href and 'flashscore.pl/mecz/' in href and '?mid=' in href:
                    links.append(href)
                else:
                    if self.test_print:
                        print(f"UWAGA: Nie znaleziono linku w nowym formacie dla elementu {element.get_attribute('id')}")
            except Exception as e:
                if self.test_print:
                    print(f"BŁĄD: Nie można pobrać linku dla elementu {element.get_attribute('id')}: {e}")
        
        if self.test_print:
            print(f"Znaleziono {len(links)} linków do meczów koszykarskich")
        return links



    def add_player(self, common_name, flash_id, team_shortcut=None):
        """
        Dodaje nowego gracza koszykarskiego do bazy danych.
        
        Args:
            common_name (str): Powszechna nazwa gracza
            flash_id (str): Zewnętrzne ID gracza z FlashScore
            team_shortcut (str, optional): Skrót drużyny dla current_club
            
        Returns:
            int: ID nowo dodanego gracza lub -1 w przypadku błędu
        """
        # Pobierz ID klubu na podstawie skrótu drużyny
        current_club_id = None
        if team_shortcut:
            current_club_id = self.shortcuts.get(team_shortcut)
        query = "INSERT INTO players(common_name, external_flash_id, sports_id, current_club) VALUES (%s, %s, 3, %s)" #sports_id - stała i niech tak zostanie
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, (common_name, flash_id, current_club_id))
            self.conn.commit()
            cursor.execute("SELECT LAST_INSERT_ID()")
            if self.test_print:
                print(f"Gracz koszykarski dodany do bazy danych: {common_name}, flash_id: {flash_id}, current_club: {current_club_id}")
            player_id = cursor.fetchone()[0]
            return player_id
        except Exception as e:
            if self.test_print:
                print(f"Błąd podczas dodawania gracza do bazy danych: {e}")
            return -1
        finally:
            cursor.close()

    def get_player_id(self, common_name, flash_id, team_shortcut=None):
        """
        Pobiera ID gracza koszykarskiego z bazy danych.
        
        Args:
            common_name (str): Powszechna nazwa gracza
            flash_id (str): Zewnętrzne ID gracza z FlashScore (zawsze znane)
            team_shortcut (str, optional): Skrót drużyny dla current_club
            
        Returns:
            int: ID gracza w bazie danych lub -1 jeśli nie znaleziono
        """
        player_id = -1
        cursor = self.conn.cursor()
        try:
            # Najpierw sprawdź po flash_id (najnowocześniejszy i najbardziej unikalny identyfikator)
            flash_player_query = "SELECT id FROM players WHERE external_flash_id = %s"
            cursor.execute(flash_player_query, (flash_id,))
            result = cursor.fetchone()
            
            if result:
                player_id = result[0]
            else:
                # Jeśli nie ma gracza z takim flash_id, dodaj nowego
                player_id = self.add_player(common_name, flash_id, team_shortcut)
                        
        except Exception as e:
            if self.test_print:
                print(f"Wystąpił błąd podczas pobierania ID gracza: {e}")
        finally:
            cursor.close()
            
        return player_id

    def parse_match_page_data(self, driver):
        """
        Parsuje dane meczu koszykarskiego ze strony FlashScore i zwraca przetworzone informacje.
        
        Args:
            driver: WebDriver Selenium
            
        Returns:
            tuple: (match_info, ot_flag) gdzie:
                - match_info (list): Lista z informacjami o meczu [data, -, gospodarze, -, goście, wynik, ...]
                - ot_flag (int): 0-brak dogrywki, 1-dogrywka (w koszykówce nie ma rzutów karnych)
        """
        match_info = []
        ot_flag = 0
        
        # Pobieranie elementów ze strony (identyczne selektory jak w hokeju)
        time_divs = driver.find_elements(By.CLASS_NAME, "duelParticipant__startTime")
        team_divs = driver.find_elements(By.CLASS_NAME, "participant__participantName")
        score_divs = driver.find_elements(By.CLASS_NAME, "detailScore__wrapper")
        full_time_divs = driver.find_elements(By.CLASS_NAME, "detailScore__fullTime")
        extra_time_divs = driver.find_elements(By.CLASS_NAME, "detailScore__status")
        
        # Zbieranie informacji o czasie meczu
        for div in time_divs:
            match_info.append(div.text.strip())
            
        # Zbieranie nazw drużyn
        for div in team_divs:
            match_info.append(div.text.strip())
            
        # Zbieranie wyników
        for div in score_divs:
            match_info.append(div.text.strip())
            
        # Sprawdzanie czy był pełny czas (może oznaczać dogrywkę)
        for div in full_time_divs:
            ot_flag = 1
            match_info.append(div.text.strip())
            
        # Sprawdzanie statusu meczu (w koszykówce nie ma rzutów karnych)
        for div in extra_time_divs:
            extra_time = div.text.strip()
            if extra_time == 'PO DOGRYWCE':
                ot_flag = 1
            match_info.append(extra_time)
            
        return match_info, ot_flag

    def get_match_info(self, link, team_id, match_data: BasketballMatchData, update=False):
        """
        Pobiera podstawowe informacje o meczu koszykarskim z głównej strony meczu.
        
        Args:
            link (str): URL meczu na FlashScore
            team_id (dict): Mapowanie ID drużyn
            match_data (BasketballMatchData): Obiekt do wypełnienia danymi meczu
            update (bool): Czy aktualizować istniejący mecz
            
        Returns:
            tuple: (overtime_flag, winner) - informacje o dogrywce i zwycięzcy
        """
        self.driver.get(link)
        time.sleep(3)
        
        if self.test_print:
            print(f"Pobieranie informacji o meczu koszykarskim: {link}")
        
        # Pobieranie informacji o rundzie (analogicznie do hokeja)
        round_div = self.driver.find_elements(By.CLASS_NAME, "wcl-scores-overline-03_KIU9F")
        game_div = self.driver.find_elements(By.CLASS_NAME, "infoBox__info")
        match_data.round = self.extract_round(round_div, game_div)
        
        # Sprawdzanie czy mecz należy pominąć (All Stars, przedsezonowy itp.)
        if match_data.round == -1:
            return -1, -1
            
        # Parsowanie danych ze strony przy użyciu wyodrębnionej funkcji
        match_info, ot_flag = self.parse_match_page_data(self.driver)
        
        # Wypełnienie podstawowych danych meczu
        match_data.league = self.league_id
        match_data.season = self.season_id
        match_data.home_team = team_id[match_info[1]]
        match_data.away_team = team_id[match_info[3]]
        match_data.game_date = parse_match_date(match_info[0])

        # Sprawdzenie czy mecz już istnieje w bazie danych
        check_id = check_if_in_db(
            match_data.home_team, 
            match_data.away_team, 
            match_date=match_data.game_date,
            conn=self.conn
        )
        
        if check_id != -1 and not update:
            if self.test_print:
                print(f"Ten mecz koszykarski znajduje się już w bazie danych! ID: {check_id}")
            return -1, -1
            
        # Parsowanie wyniku meczu
        score = match_info[7].split('\n')
        home_points = int(score[0])
        away_points = int(score[2])
        
        overtime_winner = 0
        
        if ot_flag:
            # W koszykówce wynik regularnego czasu może być różny niż w hokeju
            # Zapisujemy końcowy wynik (po dogrywce)
            match_data.home_team_goals = home_points
            match_data.away_team_goals = away_points

            # Określenie zwycięzcy dogrywki
            if home_points > away_points:
                overtime_winner = 1
                match_data.result = 1
            else:
                overtime_winner = 2
                match_data.result = 2
        else:
            # Mecz bez dogrywki
            match_data.home_team_goals = home_points
            match_data.away_team_goals = away_points

            # Obliczanie wyniku (w koszykówce remisy są bardzo rzadkie)
            match_data.result = calculate_result(home_points, away_points)

        if self.test_print:
            print(f"Mecz: {match_info[1]} {match_data.home_team_goals} - {match_data.away_team_goals} {match_info[3]}")
        if ot_flag and self.test_print:
            print(f"Mecz zakończony po dogrywce")
            
        return ot_flag, overtime_winner

    def get_match_stats_add(self, link, match_data: BasketballMatchData, match_stats_add: BasketballMatchStatsAdd, overtime_flag):
        """
        Pobiera dodatkowe statystyki koszykarskie z sekcji statystyki meczu.
        
        Przykładowy URL: https://www.flashscore.pl/mecz/.../szczegoly/statystyki/0/?mid=...
        
        Args:
            link (str): URL do statystyk meczu
            match_data (BasketballMatchData): Podstawowe dane meczu
            match_stats_add (BasketballMatchStatsAdd): Obiekt do wypełnienia dodatkowymi statystykami
            overtime_flag (int): Flaga dogrywki
            
        Returns:
            None - dane są zapisywane do match_stats_add
        """
        self.driver.get(link)
        time.sleep(3)
        stats = []
        stat_divs = self.driver.find_elements(By.CLASS_NAME, "wcl-row_2oCpS")
        for div in stat_divs:
            stats.append(div.text.strip())
        for element in stats:
            stat = element.split('\n')
            ### SEKCJA MATCH_DATA
            if(stat[1] == 'Rzuty z gry'):
                match_stats_add.home_team_field_goals_attempts = stat[0] 
                match_stats_add.away_team_field_goals_attempts = stat[2]
            elif(stat[1] == 'Rzuty z gry - trafione'):
                match_stats_add.home_team_field_goals_made = stat[0] 
                match_stats_add.away_team_field_goals_made = stat[2]
            elif(stat[1] == '% punktów z pola'):
                match_stats_add.home_team_field_goals_acc = stat[0].split("%")[0]
                match_stats_add.away_team_field_goals_acc = stat[2].split("%")[0]
            elif(stat[1] == 'Rzuty za 2 p. - łącznie'):
                match_stats_add.home_team_2_p_field_goals_attempts = stat[0]
                match_stats_add.away_team_2_p_field_goals_attempts = stat[2]
            elif(stat[1] == 'Rzuty za 2 p. - trafione'):
                match_stats_add.home_team_2_p_field_goals_made = stat[0]
                match_stats_add.away_team_2_p_field_goals_made = stat[2]
            elif(stat[1] == '% za 2 punkty'):
                match_stats_add.home_team_2_p_acc = stat[0].split("%")[0]
                match_stats_add.away_team_2_p_acc = stat[2].split("%")[0]
            elif(stat[1] == 'Rzuty za 3 p. - łącznie'):
                match_stats_add.home_team_3_p_field_goals_attempts = stat[0]
                match_stats_add.away_team_3_p_field_goals_attempts = stat[2]
            elif(stat[1] == 'Rzuty za 3 p. - trafione'):
                match_stats_add.home_team_3_p_field_goals_made = stat[0]
                match_stats_add.away_team_3_p_field_goals_made = stat[2]
            elif(stat[1] == '% za 3 punkty'):
                match_stats_add.home_team_3_p_acc = stat[0].split("%")[0]
                match_stats_add.away_team_3_p_acc = stat[2].split("%")[0]
            elif(stat[1] == 'Rzuty osobiste łącznie'):
                match_stats_add.home_team_ft_attempts = stat[0]
                match_stats_add.away_team_ft_attempts = stat[2]
            elif(stat[1] == 'Rzuty osobiste trafione'):
                match_stats_add.home_team_ft_made = stat[0]
                match_stats_add.away_team_ft_made = stat[2]
            elif(stat[1] == '% osobistych'):
                match_stats_add.home_team_ft_acc = stat[0].split("%")[0]
                match_stats_add.away_team_ft_acc = stat[2].split("%")[0]
            elif(stat[1] == 'Zbiórki w ataku'):
                match_stats_add.home_team_off_rebounds = stat[0]
                match_stats_add.away_team_off_rebounds = stat[2]
            elif(stat[1] == 'Zbiórki w obronie'):
                match_stats_add.home_team_def_rebounds = stat[0]
                match_stats_add.away_team_def_rebounds = stat[2]
            elif(stat[1] == 'Suma zbiórek'):
                match_stats_add.home_team_rebounds_total = stat[0]
                match_stats_add.away_team_rebounds_total = stat[2]
            elif(stat[1] == 'Asysty'):
                match_stats_add.home_team_assists = stat[0]
                match_stats_add.away_team_assists = stat[2]
            elif(stat[1] == 'Bloki'):
                match_stats_add.home_team_blocks = stat[0]
                match_stats_add.away_team_blocks = stat[2]
            elif(stat[1] == 'Przechwyty'):
                match_stats_add.home_team_steals = stat[0]
                match_stats_add.away_team_steals = stat[2]
            elif(stat[1] == 'Straty - kontrataki'):
                match_stats_add.home_team_turnovers = stat[0]
                match_stats_add.away_team_turnovers = stat[2]
            elif(stat[1] == 'Faule osobiste'):
                match_stats_add.home_team_personal_fouls = stat[0]
                match_stats_add.away_team_personal_fouls = stat[2]
            elif(stat[1] == 'Faule techniczne'):
                match_stats_add.home_team_technical_fouls = stat[0]
                match_stats_add.away_team_technical_fouls = stat[2]

    def get_match_player_stats(self, link, match_id):
        """
        Pobiera statystyki wszystkich zawodników z meczu koszykarskiego.
        
        Przykładowy URL: https://www.flashscore.pl/mecz/.../szczegoly/statystyki-gracza/?mid=...
        
        Args:
            link (str): URL do statystyk zawodników
            match_id (int): ID meczu w bazie danych
            
        Returns:
            list[BasketballPlayerStats]: Lista obiektów ze statystykami zawodników
        """
        self.driver.get(link)
        time.sleep(3)
        
        if self.test_print:
            print("Pobieranie statystyk zawodników koszykarskich...")
        
        player_stats = []
        
        try:
            # Znajdź główną tabelę ze statystykami
            stats_table = self.driver.find_element(By.CLASS_NAME, "playerStatsTable")
            
            # Znajdź wszystkie wiersze z zawodnikami
            player_rows = stats_table.find_elements(By.CLASS_NAME, "playerStatsTable__row")
            
            for row in player_rows:
                try:
                    # Pobierz wszystkie komórki z danego wiersza
                    cells = row.find_elements(By.CLASS_NAME, "playerStatsTable__cell")
                    
                    if len(cells) < 23:  # Sprawdź czy wiersz ma wszystkie potrzebne kolumny
                        if self.test_print:
                            print(f"Pominięto wiersz z {len(cells)} kolumnami (oczekiwano 23)")
                        continue
                    
                    # Pobierz link do gracza i wyciągnij flash_id
                    try:
                        player_link_element = row.find_element(By.CLASS_NAME, "playerStatsTable__participantCell")
                        player_href = player_link_element.get_attribute('href')
                        flash_id = player_href.split('/')[-2] if player_href else None
                        
                        # Pobierz nazwę gracza
                        player_name_element = cells[0].find_element(By.CLASS_NAME, "playerStatsTable__participantNameCell")
                        player_name = player_name_element.text.strip()
                    except Exception as e:
                        if self.test_print:
                            print(f"Błąd podczas pobierania danych gracza: {e}")
                        continue
                    
                    # Pobierz skrót drużyny
                    team_shortcut = cells[1].text.strip()
                    
                    # Pobierz ID gracza i drużyny
                    player_id = self.get_player_id(player_name, flash_id, team_shortcut)
                    team_id = self.shortcuts.get(team_shortcut, -1)
                    
                    if player_id == -1 or team_id == -1:
                        if self.test_print:
                            print(f"Nie można znaleźć gracza {player_name} (ID: {player_id}) lub drużyny {team_shortcut} (ID: {team_id})")
                        continue
                    
                    # Parsuj dane z kolejnych kolumn
                    # Kolumny: Zawodnik(0), Zespół(1), P(2), ZB(3), A(4), MIN(5), PG(6), RG(7), 
                    #          2RT(8), 2RG(9), 3RT(10), 3RG(11), RWT(12), RW(13), +/-(14), 
                    #          ZA(15), ZO(16), PO(17), PRZ(18), S(19), B(20), Z(21), FAT(22)
                    
                    points = safe_int(cells[2].text)
                    rebounds = safe_int(cells[3].text)
                    assists = safe_int(cells[4].text)
                    time_played = cells[5].text.strip() if cells[5].text.strip() != '-' else '00:00'
                    field_goals_made = safe_int(cells[6].text)
                    field_goals_attempts = safe_int(cells[7].text)
                    two_p_made = safe_int(cells[8].text)
                    two_p_attempts = safe_int(cells[9].text)
                    three_p_made = safe_int(cells[10].text)
                    three_p_attempts = safe_int(cells[11].text)
                    ft_made = safe_int(cells[12].text)
                    ft_attempts = safe_int(cells[13].text)
                    plus_minus = safe_plus_minus(cells[14].text)
                    off_rebounds = safe_int(cells[15].text)
                    def_rebounds = safe_int(cells[16].text)
                    personal_fouls = safe_int(cells[17].text)
                    steals = safe_int(cells[18].text)
                    turnovers = safe_int(cells[19].text)
                    blocked_shots = safe_int(cells[20].text)
                    blocks_against = safe_int(cells[21].text)
                    technical_fouls = safe_int(cells[22].text)
                    
                    # Utwórz obiekt statystyk gracza
                    player_stat = BasketballPlayerStats(
                        match_id=match_id,
                        team_id=team_id,
                        player_id=player_id,
                        points=points,
                        rebounds=rebounds,
                        assists=assists,
                        time_played=time_played,
                        field_goals_made=field_goals_made,
                        field_goals_attempts=field_goals_attempts,
                        two_p_field_goals_made=two_p_made,
                        two_p_field_goals_attempts=two_p_attempts,
                        three_p_field_goals_made=three_p_made,
                        three_p_field_goals_attempts=three_p_attempts,
                        ft_made=ft_made,
                        ft_attempts=ft_attempts,
                        plus_minus=plus_minus,
                        off_rebounds=off_rebounds,
                        def_rebounds=def_rebounds,
                        personal_fouls=personal_fouls,
                        steals=steals,
                        turnovers=turnovers,
                        blocked_shots=blocked_shots,
                        blocks_against=blocks_against,
                        technical_fouls=technical_fouls
                    )
                    player_stats.append(player_stat)
                except Exception as e:
                    if self.test_print:
                        print(f"Błąd podczas przetwarzania wiersza gracza: {e}")
                    continue
        except Exception as e:
            if self.test_print:
                print(f"Błąd podczas pobierania statystyk zawodników: {e}")
        return player_stats

    def get_match_rosters(self, link, match_id, home_team, away_team):
        """
        Pobiera składy drużyn koszykarskich z meczu.
        
        Przykładowy URL: https://www.flashscore.pl/mecz/.../szczegoly/sklady/?mid=...
        
        Args:
            link (str): URL do składów meczu
            match_id (int): ID meczu w bazie danych
            home_team (int): ID drużyny gospodarzy
            away_team (int): ID drużyny gości
            
        Returns:
            list[BasketballMatchRoster]: Lista obiektów ze składami drużyn
        """
        self.driver.get(link)
        time.sleep(3)
        
        if self.test_print:
            print("Pobieranie składów drużyn koszykarskich...")
        
        match_rosters = []
        
        try:
            # Znajdź główny kontener ze składami
            lineup_container = self.driver.find_element(By.CLASS_NAME, "lf__lineUp")
            
            # Pobierz wszystkie sekcje (składy wyjściowe, rezerwowi)
            sections = lineup_container.find_elements(By.CLASS_NAME, "section")
            
            # Przetwarzaj tylko pierwsze dwie sekcje (składy wyjściowe i rezerwowi)
            for section_idx, section in enumerate(sections[:2]):
                # Określ czy to składy wyjściowe (starter=1) czy rezerwowi (starter=0)
                starter = 1 if section_idx == 0 else 0
                
                try:
                    # Sprawdź nagłówek sekcji
                    header = section.find_element(By.CSS_SELECTOR, "[data-testid='wcl-headerSection-text'] span")
                    header_text = header.text.strip()
                    if self.test_print:
                        print(f"Przetwarzanie sekcji: {header_text}")
                    
                    # Znajdź kontener z drużynami
                    sides_box = section.find_element(By.CLASS_NAME, "lf__sidesBox")
                    sides = sides_box.find_elements(By.CLASS_NAME, "lf__side")
                    
                    # Przetwarzaj obie drużyny
                    for side_idx, side in enumerate(sides):
                        # Określ ID drużyny - lewa strona to drużyna gospodarzy, prawa to goście
                        team_id = home_team if side_idx == 0 else away_team
                        
                        # Znajdź wszystkich zawodników w tej drużynie
                        participants = side.find_elements(By.CLASS_NAME, "lf__participantNew")
                        
                        for participant in participants:
                            try:
                                # Pobierz numer zawodnika
                                number_elem = participant.find_element(By.CSS_SELECTOR, "[data-testid='wcl-scores-simple-text-01'].wcl-number_lTBFk")
                                number = safe_int(number_elem.text.strip())
                                
                                # Pobierz link do zawodnika i wyciągnij flash_id
                                player_link = participant.find_element(By.CSS_SELECTOR, "a[href*='/zawodnik/']")
                                href = player_link.get_attribute("href")
                                
                                # Wyciągnij flash_id z linku (format: /zawodnik/nazwa-zawodnika/FLASH_ID)
                                flash_id = None
                                if href:
                                    flash_id_match = re.search(r'/zawodnik/[^/]+/([^/?]+)', href)
                                    if flash_id_match:
                                        flash_id = flash_id_match.group(1)
                                
                                # Pobierz nazwę zawodnika
                                player_name_elem = participant.find_element(By.CSS_SELECTOR, "strong.wcl-name_ZggyJ")
                                player_name = player_name_elem.text.strip()
                                
                                # Określ skrót drużyny dla funkcji get_player_id
                                team_shortcut = None
                                for shortcut, team_id_check in self.shortcuts.items():
                                    if team_id_check == team_id:
                                        team_shortcut = shortcut
                                        break
                                
                                # Pobierz ID zawodnika z bazy danych
                                player_id = self.get_player_id(player_name, flash_id, team_shortcut)
                                
                                # Utwórz obiekt składu
                                roster_entry = BasketballMatchRoster(
                                    match_id=match_id,
                                    team_id=team_id,
                                    player_id=player_id,
                                    number=number,
                                    starter=starter
                                )
                                match_rosters.append(roster_entry)
                                
                                if self.test_print:
                                    print(f"Dodano do składu: {player_name} (#{number}) - ID: {player_id}, Drużyna: {team_id}, Starter: {starter}")
                                
                            except Exception as e:
                                if self.test_print:
                                    print(f"Błąd podczas przetwarzania zawodnika: {e}")
                                continue
                                
                except Exception as e:
                    if self.test_print:
                        print(f"Błąd podczas przetwarzania sekcji {section_idx}: {e}")
                    continue
                    
        except Exception as e:
            if self.test_print:
                print(f"Błąd podczas pobierania składów: {e}")
            
        print(f"Pobrano składy dla {len(match_rosters)} zawodników")
        return match_rosters

    def get_match_data(self, link, team_id, automate=False, update=False):
        """
        Główna metoda pobierająca wszystkie dane meczu koszykarskiego z wykorzystaniem dataclass'ów.
        
        Args:
            link (str): URL meczu na FlashScore
            team_id (dict): Mapowanie ID drużyn
            automate (bool): Czy zapisywać dane do bazy
            update (bool): Czy aktualizować istniejący mecz
            
        Returns:
            tuple: (match_data, match_stats_add, player_stats, match_rosters, status)
        """
        # Inicjalizacja struktur danych z użyciem dataclass'ów
        match_data = BasketballMatchData(
            league=self.league_id,
            season=self.season_id,
            home_team=0,
            away_team=0,
            game_date='',
            round=100
        )
        
        match_stats_add = BasketballMatchStatsAdd()
        
        print(f"Rozpoczęcie przetwarzania meczu koszykarskiego: {link}")
        
        # 1. Pobieranie podstawowych danych meczu
        overtime_flag, winner = self.get_match_info(link, team_id, match_data, update)
        if overtime_flag == -1 and winner == -1:
            return -1, -1, -1, -1, -1
        
        # 2. Pobieranie dodatkowych statystyk koszykarskich
        stats_url = build_basketball_url(link, "statystyki/0")
        self.get_match_stats_add(stats_url, match_data, match_stats_add, overtime_flag)
        
        # Zapisywanie do bazy danych tylko jeśli automate=True
        if automate:
            match_stats_add.match_id = self.insert_match_data(match_data)
            print(f"NOWY MECZ KOSZYKARSKI O ID: {match_stats_add.match_id}")
            self.insert_procedure(match_stats_add, "basketball_matches_add")
        else:
            match_stats_add.match_id = 999999
            print(f"TRYB TESTOWY - SYMULACJA ID MECZU KOSZYKARSKIEGO: {match_stats_add.match_id}")

        # 3. Pobieranie statystyk zawodników
        player_stats_url = build_basketball_url(link, "statystyki-gracza")
        player_stats = self.get_match_player_stats(player_stats_url, match_stats_add.match_id)

        # 4. Pobieranie składów drużyn
        rosters_url = build_basketball_url(link, "sklady")
        match_rosters = self.get_match_rosters(rosters_url, match_stats_add.match_id, 
                                               match_data.home_team, match_data.away_team)
        
        # Zapisywanie szczegółów tylko jeśli automate=True
        if automate:
            self.insert_match_details(player_stats, match_rosters)
            print(f"Import meczu koszykarskiego o ID {match_stats_add.match_id} zakończony sukcesem")
        else:
            print(f"Przetwarzanie meczu koszykarskiego (tryb testowy) zakończone sukcesem")

        return match_data, match_stats_add, player_stats, match_rosters, 1

    def insert_match_data(self, match_data: BasketballMatchData):
        """
        Wstawia podstawowe dane meczu do tabeli MATCHES.
        
        Args:
            match_data (BasketballMatchData): Obiekt z podstawowymi danymi meczu
            
        Returns:
            int: ID nowo wstawionego meczu
        """
        self.insert_procedure(match_data, "matches")
        cursor = self.conn.cursor()
        cursor.execute("SELECT LAST_INSERT_ID();")
        match_id = cursor.fetchone()[0]
        cursor.close()
        return match_id

    def insert_procedure(self, data, table_name):
        """
        Uniwersalna procedura wstawiania danych do odpowiedniej tabeli.
        Działa z obiektami dataclass, konwertując je na format słownikowy.
        
        Args:
            data: Obiekt dataclass z danymi do wstawienia
            table_name (str): Nazwa tabeli docelowej
            
        Returns:
            None
        """
        # Mapowanie nazw kolumn dla tabel koszykarskich - zamiana słownej formy cyfr na cyfry
        # Mega kaszane odwalilem z nazwami kolumn, ale niech juz tak zostanie
        column_mapping = {
            'two_p_field_goals_made': '2_p_field_goals_made',
            'two_p_field_goals_attempts': '2_p_field_goals_attempts', 
            'three_p_field_goals_made': '3_p_field_goals_made',
            'three_p_field_goals_attempts': '3_p_field_goals_attempts'
        }
        
        # Konwertujemy dataclass na słownik, pomijając pola z wartością None
        if hasattr(data, '__dataclass_fields__'):
            # To jest dataclass - konwertujemy na słownik
            data_dict = {}
            for field in fields(data):
                value = getattr(data, field.name)
                # Pomijamy pola z wartością None (np. existing_id gdy nie jest używane)
                if value is not None:
                    # Specjalne przetwarzanie dla pola existing_id - zmieniamy na match_id
                    if field.name == 'existing_id':
                        data_dict['match_id'] = value
                    else:
                        # Mapowanie nazw kolumn dla tabel koszykarskich
                        mapped_field_name = column_mapping.get(field.name, field.name)
                        data_dict[mapped_field_name] = value
        else:
            # Fallback dla zwykłych słowników (zachowanie kompatybilności)
            data_dict = data
        
        # Generowanie zapytania SQL na podstawie pól dataclass
        columns = ', '.join(data_dict.keys())
        placeholders = ', '.join(['%s'] * len(data_dict))
        values_for_debug = ', '.join([str(f"'{value}'") for value in data_dict.values()])
        
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
        debug_query = f"INSERT INTO {table_name} ({columns}) VALUES ({values_for_debug});"
        
        print(debug_query)
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, tuple(data_dict.values()))
            self.conn.commit()
            print(f"Pomyślnie wstawiono dane do tabeli {table_name}")
        except Exception as e:
            print(f"Błąd podczas wstawiania danych do tabeli {table_name}: {e}")
            self.conn.rollback()
        finally:
            cursor.close()

    def insert_match_details(self, player_stats, match_rosters):
        """
        Wstawia wszystkie szczegółowe dane meczu koszykarskiego do odpowiednich tabel.
        
        Args:
            player_stats (list): Lista statystyk zawodników
            match_rosters (list): Lista składów drużyn
            
        Returns:
            None
        """
        for element in player_stats:
            self.insert_procedure(element, "basketball_match_player_stats")
        for element in match_rosters:
            self.insert_procedure(element, "basketball_match_roster")


def get_shortcuts(conn, country):
    """
    Pobiera mapowanie skrótów nazw drużyn na ich ID z bazy danych.
    
    Args:
        conn: Połączenie z bazą danych
        country (int): ID kraju, dla którego pobieramy drużyny
    
    Returns:
        dict: Słownik mapujący skróty drużyn na ich ID
    """
    query = "select shortcut, id from teams where country = {} and sport_id = 3".format(country)
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
    query = "select name, id from teams where country = {} and sport_id = 3".format(country)
    teams_df = pd.read_sql(query, conn)
    return teams_df.set_index('name')['id'].to_dict()

def parse_arguments():
    """
    Parsuje argumenty wiersza poleceń dla scrapera koszykówki.
    
    Returns:
        argparse.Namespace: Sparsowane argumenty
    """
    parser = argparse.ArgumentParser(
        description="""
        Scraper danych meczów koszykówki z FlashScore
        
        Skrypt obsługuje pobieranie danych koszykarskich w następujących trybach:
        - Pobranie wszystkich meczów z listy wyników
        - Pobranie pojedynczego meczu (gdy podano konkretny link)
        
        Przykłady użycia:
        - Pobranie wszystkich meczów z listy:
          python nba_all_scrapper.py 1 1 "https://www.flashscore.pl/koszykowka/usa/nba-2023-2024/wyniki/"
        
        - Pobranie konkretnego meczu:
          python nba_all_scrapper.py 1 1 "link_do_ligi" --one_link "https://www.flashscore.pl/mecz/koszykowka/indiana-pacers-YPohMUTt/oklahoma-city-thunder-0fHFHEWD/?mid=YasLoKTi"
        
        - Tryb produkcyjny z zapisem do bazy danych:
          python nba_all_scrapper.py 1 1 "link_do_ligi" --automate
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
    parser.add_argument('--test_print', action='store_true',
                       help='Wyświetlaj szczegółowe komunikaty diagnostyczne (domyślnie: tylko podstawowe komunikaty)')
    
    args = parser.parse_args()
    return args

def main():
    """
    Główna funkcja programu odpowiedzialna za scrapowanie danych meczów koszykówki z FlashScore.
    """
    args = parse_arguments()
    timer_dict = {'upcoming': 5, 'update': 5, 'default': 50}
    timer = timer_dict['default']
    
    # Informowanie o trybie działania
    if args.automate:
        print("Tryb produkcyjny - dane będą zapisywane do bazy danych.")
        if args.update:
            print("Tryb aktualizacji - istniejące mecze będą aktualizowane.")
            timer = timer_dict['update']
    else:
        print("Tryb testowy - dane będą tylko przetwarzane bez zapisu do bazy.")
    
    if args.upcoming:
        print("Tryb przyszłych meczów - funkcjonalność do późniejszej implementacji.")
        timer = timer_dict['upcoming']

    conn = db_connect()
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    
    country = get_country(conn, args.league_id)
    team_id = get_teams_ids(conn, country)
    shortcuts = get_shortcuts(conn, country)
    game_data = Game(driver, args.league_id, args.season_id, shortcuts, conn, args.test_print)
    
    if args.one_link == '-1':
        links = game_data.get_match_links(args.games_url, timer, driver)
        if args.no_to_download == -1:
            args.no_to_download = len(links)
        
        # Przygotowanie listy meczów do pobrania
        matches_to_process = links[args.skip:args.no_to_download]
        
        # Pętla z paskiem postępu tqdm
        for i, link in enumerate(tqdm(matches_to_process, desc="Pobieranie meczów koszykarskich", unit="mecz"), 1):
            print(f"Rozpoczęto pobieranie meczu {i}")
            match_data, _, _, _, status = game_data.get_match_data(link, team_id, args.automate, args.update)
            if status == -1:
                if args.test_print:
                    print("MECZ POMIJANY (All Star albo przedsezonowy albo już w bazie)")
            else:
                print(f"Pobieranie meczu {i} zakończone sukcesem")
    else:
        game_data.get_match_data(args.one_link, team_id, args.automate, args.update)
        
    driver.quit()
    conn.close()

if __name__ == '__main__':
    main()
