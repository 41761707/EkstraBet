import requests
import json

def get_data_from_api(api_url):
    try:
        # Wykonanie zapytania GET
        response = requests.get(api_url)
        
        # Sprawdzenie statusu odpowiedzi
        if response.status_code == 200:
            # Konwersja odpowiedzi do formatu JSON
            data = response.json()
            return data
        else:
            print(f"Error: Received status code {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Przykład użycia
def main():
    get_season = "https://api-web.nhle.com/v1/season"
    get_game_info = "https://api-web.nhle.com/v1/meta/game/2023020204"
    get_boxscore = "https://api-web.nhle.com/v1/gamecenter/2023020204/landing"
    data = get_data_from_api(get_boxscore)
    
    if data:
        #for element in data:
        #     print(element)
        print(json.dumps(data, indent=4))
    
if __name__ == "__main__":
        main()