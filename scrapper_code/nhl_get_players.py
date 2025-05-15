import requests
import json
import pandas as pd
import sys

import db_module
def get_data_from_api(api_url):
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Błąd, kod: {response.status_code}")
            return None
    except Exception as e:
        print(f"Bład pobierania danych: {e}")
        return None
    
def insert_roster(cursor, api_call, club, countries_dict, teams_dict, year_id):
    players = get_data_from_api(api_call)
    #print(players['defensemen'])
    #print(players['forwards'])
    query = "SELECT external_id from players where sports_id = 2"
    cursor.execute(query)
    result = cursor.fetchall()
    external_ids = [row[0] for row in result]
    for current_key in ['goalies', 'defensemen', 'forwards']:
        for player in players[current_key]:
            #print(player)
            player_data = {
            'first_name' : '',
            'last_name' : '',
            'common_name' : '',
            'current_club' : teams_dict[club],
            'current_country' : '',
            'sports_id' : 2, #hokej
            'position' : '',
            'external_id': 0
            }
            if str(player['id']) in external_ids:
                #JEŚLI ZMIENIŁA SIĘ DRUŻYNA TO AKTUALIZUJEMY, JESLI NIE TO SKIP
                #if old_team != new_team
                #SELECT ID, OLD TEAM FROM PLAYERS
                query = "SELECT id, current_club from players where external_id = {}".format(player['id'])
                cursor.execute(query)
                result = cursor.fetchall()
                player_old_team = [list(row) for row in result][0]
                if int(player_old_team[1]) != int(teams_dict[club]):
                    current_season = f"{year_id[:4]}/{year_id[6:8]}"
                    query = "select id from seasons where years = '{}'".format(current_season)
                    cursor.execute(query)
                    result = cursor.fetchall()
                    season = result[0][0]
                    #INSERT INTO TRANSFERS
                    sql = '''INSERT INTO transfers(player_id, old_team_id, new_team_id, season_id) values ({}, {}, {}, {})'''.format(player_old_team[0], player_old_team[1], teams_dict[club], season)
                    cursor.execute(sql.encode('ascii', errors='replace').decode('ascii'))
                    print(sql)
                    #UPDATE PLAYER
                    sql = 'UPDATE players set `current_club` = {} where id = {}'.format(player_data['current_club'], player_old_team[0])
                    cursor.execute(sql)
                    print(sql)   
                #else:
                    #print("BRAK ZMIANY KLUBU")          
            else:
            #first_name
                player_data['first_name'] = player['firstName']['default']
                #last_name
                player_data['last_name'] = player['lastName']['default']
                #common_name
                player_data['common_name'] = "{} {}.".format(player_data['last_name'], player_data['first_name'][0])
                #current_country
                if countries_dict[player['birthCountry']]:
                    player_data['current_country'] = countries_dict[player['birthCountry']]
                else:
                    print("BRAK KRAJU {} W BAZIE DANYCH".format(player['birthCountry'] ))
                    return
                #position
                player_data['position'] = player['positionCode']
                #external_id
                player_data['external_id'] = player['id']
                #print(player_data)
                sql = '''INSERT INTO players (first_name, \
last_name, \
common_name, \
current_club, \
current_country, \
sports_id, \
position, \
external_id) \
VALUES ("{first_name}", \
"{last_name}", \
"{common_name}", \
{current_club}, \
{current_country}, \
{sports_id}, \
"{position}", \
{external_id});'''.format(**player_data)
                print(sql.encode('ascii', errors='replace').decode('ascii'))
                cursor.execute(sql)
    

def get_players(conn, year_id):
    with conn.cursor() as cursor:
        #query = "SELECT id, shortcut FROM teams WHERE sport_id = 2 and shortcut not in ('VGK', 'SEA', 'UTA', 'KAR') order by shortcut" #tylko dla 20162017
        #query = "SELECT id, shortcut FROM teams WHERE sport_id = 2 and shortcut not in ('SEA', 'UTA', 'KAR')" #do 20202021 wlacznie
        #query = "SELECT id, shortcut FROM teams WHERE sport_id = 2 and shortcut not in ('UTA', 'KAR')" #do 20232024 wlacznie
        query = "SELECT id, shortcut FROM teams WHERE sport_id = 2 and shortcut not in ('ARI', 'KAR')"
        cursor.execute(query)
        result = cursor.fetchall()
        teams_dict = {row[0]: row[1] for row in result} 
        query = "SELECT id, short FROM countries"
        cursor.execute(query)
        result = cursor.fetchall()
        countries_dict = {row[0]: row[1] for row in result}
        #WYMAGANE ZMIANY TYLKO NA HOKEJ!
        countries_dict[20] = 'USA'
        countries_dict[4] = 'DEU'
        countries_dict[12] = 'CZE'
        countries_dict[23] = 'AUT'
        countries_dict[5] = 'ITA'
        countries_dict[18] = 'CHE'
        countries_dict[3] = 'FRA'
        countries_dict[13] = 'NLD'
        countries_dict[10] = 'AUS'
        countries_dict[11] = 'BEL'
        countries_dict = {value: key for key, value in countries_dict.items()}
        teams_dict = {value: key for key, value in teams_dict.items()}
        #print(countries_dict)
        for key, _ in teams_dict.items():
            print('# {}'.format(key))
            get_roster = "https://api-web.nhle.com/v1/roster/{}/{}".format(key, year_id) #roster drużyny na dany rok
            insert_roster(cursor, get_roster, key, countries_dict, teams_dict, year_id)
            conn.commit()

def main():
    conn = db_module.db_connect()
    year_id = sys.argv[1]
    get_players(conn, year_id)
    #Zwróć wszystkie hokejowe drużyny
    #get_landing = "https://api-web.nhle.com/v1/gamecenter/2023020204/landing" #only match events (goals / penalties)
    #get_boxscore = "https://api-web.nhle.com/v1/gamecenter/2023020204/boxscore" #stats per player
    #get_story = "https://api-web.nhle.com/v1/wsc/game-story/2023020204"

    '''data = get_data_from_api('https://api-web.nhle.com/v1/roster/NYR/20202021')
    
    if data:
        #for element in data:
        #     print(element)
        print(json.dumps(data, indent=4))'''

    conn.close()
    
if __name__ == "__main__":
        main()