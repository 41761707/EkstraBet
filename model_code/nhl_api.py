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

def main():
    #Zwróć wszystkie hokejowe drużyny
    #get_landing = "https://api-web.nhle.com/v1/gamecenter/2023020204/landing" #only match events (goals / penalties)
    #get_boxscore = "https://api-web.nhle.com/v1/gamecenter/2023020204/boxscore" #stats per player
    #get_story = "https://api-web.nhle.com/v1/wsc/game-story/2023020204"

    data = get_data_from_api("https://api-web.nhle.com/v1/wsc/game-story/2023020204")
    
    if data:
        #for element in data:
        #     print(element)
        print(json.dumps(data, indent=4))
    
if __name__ == "__main__":
        main()