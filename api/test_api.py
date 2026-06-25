# Skrypt testowy dla API EkstraBet
# Plik zawiera przykładowe testy endpointów API

import requests
import json
import time
from typing import Dict, Any

# Konfiguracja
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

def test_api_connection() -> bool:
    """Test podstawowego połączenia z API"""
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Połączenie z API działa")
            print(f"Odpowiedź: {response.json()}")
            return True
        else:
            print(f"❌ Błąd połączenia: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Błąd połączenia: {e}")
        return False

def test_health_check():
    """Test endpointu health check"""
    print("\n🔍 Test: GET /health")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status aplikacji: {data['status']}")
            print(f"   Baza danych: {data['database']}")
        else:
            print(f"❌ Błąd health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu health check: {e}")

def test_teams_info():
    """Test endpointu informacji o module teams"""
    print("\n🔍 Test: GET /teams/")
    
    try:
        response = requests.get(f"{BASE_URL}/teams/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Informacje o module teams: {data['module']}")
            print(f"   Dostępne endpointy: {len(data['endpoints'])}")
        else:
            print(f"❌ Błąd informacji teams: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu teams info: {e}")

def test_get_all_teams():
    """Test endpointu pobierania wszystkich drużyn"""
    print("\n🔍 Test: GET /teams/all")
    
    try:
        # Test podstawowy
        response = requests.get(f"{BASE_URL}/teams/all")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pobrano {len(data['teams'])} drużyn")
            print(f"   Całkowita liczba: {data['total_count']}")
            print(f"   Strona: {data['page']}")
            
            # Wyświetl pierwszą drużynę jako przykład
            if data['teams']:
                first_team = data['teams'][0]
                print(f"   Przykład drużyny: {first_team['name']} ({first_team['country_name']})")
        
        # Test z paginacją
        response = requests.get(f"{BASE_URL}/teams/all?page=1&page_size=5")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test paginacji: {len(data['teams'])} drużyn na stronie")
        
    except Exception as e:
        print(f"❌ Błąd testu: {e}")

def test_search_teams():
    """Test endpointu wyszukiwania drużyn"""
    print("\n🔍 Test: GET /teams/search")
    
    test_cases = [
        {"country_name": "Polska", "description": "drużyny z Polski"},
        {"sport_name": "hokej", "description": "drużyny hokejowe"},
        {"team_name": "United", "description": "drużyny z 'United' w nazwie"},
        {"team_shortcut": "MUN", "description": "drużyna ze skrótem 'MUN'"}
    ]
    
    for test_case in test_cases:
        try:
            params = {k: v for k, v in test_case.items() if k != "description"}
            response = requests.get(f"{BASE_URL}/teams/search", params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {test_case['description']}: {len(data['teams'])} wyników")
                
                if data['teams']:
                    example = data['teams'][0]
                    print(f"   Przykład: {example['name']} ({example['country_name']})")
            else:
                print(f"❌ Błąd dla {test_case['description']}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Błąd testu {test_case['description']}: {e}")

def test_team_stats():
    """Test endpointu statystyk drużyny - rozszerzony z nowymi filtrami"""
    print("\n🔍 Test: GET /teams/{team_id}/stats")
    
    # Najpierw pobierz listę drużyn żeby mieć prawdziwe ID
    try:
        response = requests.get(f"{BASE_URL}/teams/all?page_size=1")
        if response.status_code == 200:
            teams = response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                team_name = teams[0]['name']
                
                # Test podstawowych statystyk
                stats_response = requests.get(f"{BASE_URL}/teams/{team_id}/stats")
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    print(f"✅ Statystyki podstawowe dla {stats['team_name']}:")
                    print(f"   Mecze: {stats['total_matches']} (dom: {stats['home_matches']}, wyjazd: {stats['away_matches']})")
                    print(f"   Bilans: {stats['wins']}W {stats['draws']}R {stats['losses']}P")
                    print(f"   Bramki: {stats['goals_scored']} strzelonych, {stats['goals_conceded']} straconych")
                    
                    # Test z filtrem ostatnich N meczów
                    if stats['total_matches'] > 5:
                        last_n_response = requests.get(f"{BASE_URL}/teams/{team_id}/stats?last_n_matches=5")
                        if last_n_response.status_code == 200:
                            last_n_stats = last_n_response.json()
                            print(f"✅ Statystyki ostatnich 5 meczów dla {team_name}:")
                            print(f"   Mecze: {last_n_stats['total_matches']}")
                            print(f"   Bilans: {last_n_stats['wins']}W {last_n_stats['draws']}R {last_n_stats['losses']}P")
                            print(f"   Filtr: ostatnie {last_n_stats['last_n_matches']} meczów")
                        else:
                            print(f"❌ Błąd testu ostatnich N meczów: {last_n_response.status_code}")
                    else:
                        print("ℹ️  Za mało meczów do testu filtra ostatnich N")
                        
                else:
                    print(f"❌ Błąd pobierania statystyk: {stats_response.status_code}")
        
        # Test nieistniejącej drużyny
        response = requests.get(f"{BASE_URL}/teams/99999/stats")
        if response.status_code == 404:
            print("✅ Test nieistniejącej drużyny: prawidłowy błąd 404")
        else:
            print(f"❌ Oczekiwano 404, otrzymano: {response.status_code}")
            
        # Test nieprawidłowych parametrów
        response = requests.get(f"{BASE_URL}/teams/{team_id}/stats?last_n_matches=0")
        if response.status_code == 422:
            print("✅ Test nieprawidłowego parametru last_n_matches=0: prawidłowy błąd 422")
        else:
            print(f"❌ Test parametru last_n_matches=0: oczekiwano 422, otrzymano: {response.status_code}")
            
        response = requests.get(f"{BASE_URL}/teams/{team_id}/stats?last_n_matches=101")
        if response.status_code == 422:
            print("✅ Test nieprawidłowego parametru last_n_matches=101: prawidłowy błąd 422")
        else:
            print(f"❌ Test parametru last_n_matches=101: oczekiwano 422, otrzymano: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu statystyk: {e}")

def test_team_btts_stats():
    """Test endpointu statystyk BTTS drużyny"""
    print("\n🔍 Test: GET /teams/{team_id}/btts")
    
    try:
        response = requests.get(f"{BASE_URL}/teams/all?page_size=1")
        if response.status_code == 200:
            teams = response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                team_name = teams[0]['name']
                
                # Test podstawowych statystyk BTTS
                btts_response = requests.get(f"{BASE_URL}/teams/{team_id}/btts")
                if btts_response.status_code == 200:
                    btts = btts_response.json()
                    print(f"✅ Statystyki BTTS dla {btts['team_name']}:")
                    print(f"   Mecze: {btts['total_matches']}")
                    print(f"   BTTS Tak: {btts['btts_yes']} ({btts['btts_yes_percentage']}%)")
                    print(f"   BTTS Nie: {btts['btts_no']} ({btts['btts_no_percentage']}%)")
                    
                    # Test z filtrem ostatnich N meczów
                    if btts['total_matches'] > 3:
                        last_n_response = requests.get(f"{BASE_URL}/teams/{team_id}/btts?last_n_matches=3")
                        if last_n_response.status_code == 200:
                            last_n_btts = last_n_response.json()
                            print(f"✅ Statystyki BTTS ostatnich 3 meczów dla {team_name}:")
                            print(f"   Mecze: {last_n_btts['total_matches']}")
                            print(f"   BTTS Tak: {last_n_btts['btts_yes']} ({last_n_btts['btts_yes_percentage']}%)")
                            print(f"   Filtr: ostatnie {last_n_btts['last_n_matches']} meczów")
                        else:
                            print(f"❌ Błąd testu BTTS ostatnich N meczów: {last_n_response.status_code}")
                    else:
                        print("ℹ️  Za mało meczów do testu filtra ostatnich N")
                        
                else:
                    print(f"❌ Błąd pobierania statystyk BTTS: {btts_response.status_code}")
        
        # Test nieistniejącej drużyny
        response = requests.get(f"{BASE_URL}/teams/99999/btts")
        if response.status_code == 404:
            print("✅ Test nieistniejącej drużyny BTTS: prawidłowy błąd 404")
        else:
            print(f"❌ Oczekiwano 404, otrzymano: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu BTTS: {e}")

def test_season_filtering():
    """Test filtrowania statystyk według sezonu"""
    print("\n🔍 Test: Filtrowanie według sezonu")
    
    try:
        # Najpierw pobierz listę sezonów
        seasons_response = requests.get(f"{BASE_URL}/helper/seasons")
        if seasons_response.status_code == 200:
            seasons_data = seasons_response.json()
            print(f"✅ Pobrano {seasons_data['total_seasons']} sezonów")
            
            if seasons_data['seasons']:
                # Weź pierwszy sezon z meczami
                season_with_matches = None
                for season in seasons_data['seasons']:
                    if season['matches_count'] > 0:
                        season_with_matches = season
                        break
                
                if season_with_matches:
                    season_id = season_with_matches['id']
                    season_years = season_with_matches['years']
                    
                    # Pobierz drużynę
                    teams_response = requests.get(f"{BASE_URL}/teams/all?page_size=1")
                    if teams_response.status_code == 200:
                        teams = teams_response.json()['teams']
                        if teams:
                            team_id = teams[0]['id']
                            team_name = teams[0]['name']
                            
                            # Test statystyk z filtrem sezonu
                            stats_response = requests.get(f"{BASE_URL}/teams/{team_id}/stats?season_id={season_id}")
                            if stats_response.status_code == 200:
                                stats = stats_response.json()
                                print(f"✅ Statystyki dla {team_name} w sezonie {season_years}:")
                                print(f"   Mecze: {stats['total_matches']}")
                                print(f"   Sezon: {stats['season_years']} (ID: {stats['season_id']})")
                            else:
                                print(f"❌ Błąd statystyk z filtrem sezonu: {stats_response.status_code}")
                            
                            # Test BTTS z filtrem sezonu
                            btts_response = requests.get(f"{BASE_URL}/teams/{team_id}/btts?season_id={season_id}")
                            if btts_response.status_code == 200:
                                btts = btts_response.json()
                                print(f"✅ Statystyki BTTS dla {team_name} w sezonie {season_years}:")
                                print(f"   Mecze: {btts['total_matches']}")
                                print(f"   BTTS Tak: {btts['btts_yes']} ({btts['btts_yes_percentage']}%)")
                            else:
                                print(f"❌ Błąd BTTS z filtrem sezonu: {btts_response.status_code}")
                            
                            # Test kombinacji filtrów (sezon + ostatnie N meczów)
                            combined_response = requests.get(f"{BASE_URL}/teams/{team_id}/stats?season_id={season_id}&last_n_matches=3")
                            if combined_response.status_code == 200:
                                combined_stats = combined_response.json()
                                print(f"✅ Statystyki dla {team_name} - ostatnie 3 mecze w sezonie {season_years}:")
                                print(f"   Mecze: {combined_stats['total_matches']}")
                                print(f"   Sezon: {combined_stats['season_years']}, ostatnie: {combined_stats['last_n_matches']}")
                            else:
                                print(f"❌ Błąd kombinacji filtrów: {combined_response.status_code}")
                else:
                    print("ℹ️  Brak sezonów z meczami do testowania")
        else:
            print(f"❌ Błąd pobierania sezonów: {seasons_response.status_code}")
        
        # Test nieistniejącego sezonu
        teams_response = requests.get(f"{BASE_URL}/teams/all?page_size=1")
        if teams_response.status_code == 200:
            teams = teams_response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                response = requests.get(f"{BASE_URL}/teams/{team_id}/stats?season_id=99999")
                if response.status_code == 404:
                    print("✅ Test nieistniejącego sezonu: prawidłowy błąd 404")
                else:
                    print(f"❌ Test nieistniejącego sezonu: oczekiwano 404, otrzymano: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu filtrowania według sezonu: {e}")

def test_helper_endpoints():
    """Test endpointów pomocniczych"""
    print("\n🔍 Test: Endpointy pomocnicze")
    
    # Test krajów
    try:
        response = requests.get(f"{BASE_URL}/helper/countries")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Kraje: {data['total_countries']} krajów")
            if data['countries']:
                example = data['countries'][0]
                print(f"   Przykład: {example['name']} ({example['teams_count']} drużyn)")
    except Exception as e:
        print(f"❌ Błąd testu krajów: {e}")
    
    # Test sportów
    try:
        response = requests.get(f"{BASE_URL}/helper/sports")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sporty: {data['total_sports']} sportów")
            if data['sports']:
                example = data['sports'][0]
                print(f"   Przykład: {example['name']} ({example['teams_count']} drużyn)")
    except Exception as e:
        print(f"❌ Błąd testu sportów: {e}")
    
    # Test sezonów
    try:
        response = requests.get(f"{BASE_URL}/helper/seasons")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sezony: {data['total_seasons']} sezonów")
            if data['seasons']:
                example = data['seasons'][0]
                print(f"   Przykład: {example['years']} ({example['matches_count']} meczów)")
        else:
            print(f"❌ Błąd pobierania sezonów: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu sezonów: {e}")

def test_api_performance():
    """Test wydajności API"""
    print("\n⚡ Test wydajności")
    
    endpoints = [
        "/",
        "/health",
        "/teams/",
        "/teams/all?page_size=10",
        "/teams/search?country_name=Polska",
        "/helper/countries",
        "/helper/sports",
        "/helper/seasons"
    ]
    
    # Dodaj testy statystyk dla pierwszej drużyny
    try:
        response = requests.get(f"{BASE_URL}/teams/all?page_size=1")
        if response.status_code == 200:
            teams = response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                endpoints.extend([
                    f"/teams/{team_id}/stats",
                    f"/teams/{team_id}/stats?last_n_matches=5",
                    f"/teams/{team_id}/btts",
                    f"/teams/{team_id}/btts?last_n_matches=3"
                ])
                
                # Dodaj testy dla endpointów hokejowych jeśli drużyna hokejowa
                hockey_response = requests.get(f"{BASE_URL}/teams/search?sport_name=hokej&page_size=1")
                if hockey_response.status_code == 200:
                    hockey_teams = hockey_response.json()['teams']
                    if hockey_teams:
                        hockey_team_id = hockey_teams[0]['id']
                        endpoints.extend([
                            f"/teams/{hockey_team_id}/hockey-stats",
                            f"/teams/{hockey_team_id}/hockey-stats?last_n_matches=5",
                            f"/teams/{hockey_team_id}/roster"
                        ])
    except:
        pass  # Jeśli nie można pobrać ID drużyny, kontynuuj bez testów statystyk
    
    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}")
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # w milisekundach
            
            if response.status_code == 200:
                print(f"✅ {endpoint}: {response_time:.2f}ms")
            else:
                print(f"❌ {endpoint}: błąd {response.status_code}")
                
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def test_team_hockey_stats():
    """Test endpointu statystyk hokejowych drużyny"""
    print("\n🔍 Test: GET /teams/{team_id}/hockey-stats")
    
    try:
        # Najpierw znajdź drużynę hokejową
        response = requests.get(f"{BASE_URL}/teams/search?sport_name=hokej&page_size=1")
        if response.status_code == 200:
            teams = response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                team_name = teams[0]['name']
                
                # Test podstawowych statystyk hokejowych
                hockey_response = requests.get(f"{BASE_URL}/teams/{team_id}/hockey-stats")
                if hockey_response.status_code == 200:
                    hockey = hockey_response.json()
                    print(f"✅ Statystyki hokejowe dla {hockey['team_name']}:")
                    print(f"   Mecze: {hockey['total_matches']}")
                    print(f"   Bilans: {hockey['wins']}W {hockey['losses']}P")
                    print(f"   Bramki: {hockey['goals_for']} strzelonych, {hockey['goals_against']} straconych")
                    print(f"   Dogrywki: {hockey['overtime_matches']}, Karne: {hockey['shootout_matches']}")
                    print(f"   Średnia strzałów: {hockey['avg_shots_on_target_for']} za / {hockey['avg_shots_on_target_against']} przeciwko")
                    print(f"   Skuteczność obron: {hockey['avg_saves_percentage']}%")
                    print(f"   Skuteczność przewagi: {hockey['avg_powerplay_percentage']}%")
                    print(f"   Skuteczność wznowień: {hockey['avg_faceoff_percentage']}%")
                    print(f"   Średnia uderzeń/mecz: {hockey['avg_hits_per_game']}")
                    
                    # Test z filtrem ostatnich N meczów
                    if hockey['total_matches'] > 5:
                        last_n_response = requests.get(f"{BASE_URL}/teams/{team_id}/hockey-stats?last_n_matches=5")
                        if last_n_response.status_code == 200:
                            last_n_hockey = last_n_response.json()
                            print(f"✅ Statystyki hokejowe ostatnich 5 meczów dla {team_name}:")
                            print(f"   Mecze: {last_n_hockey['total_matches']}")
                            print(f"   Bilans: {last_n_hockey['wins']}W {last_n_hockey['losses']}P")
                            print(f"   Filtr: ostatnie {last_n_hockey['last_n_matches']} meczów")
                        else:
                            print(f"❌ Błąd testu ostatnich N meczów: {last_n_response.status_code}")
                    else:
                        print("ℹ️  Za mało meczów do testu filtra ostatnich N")
                        
                elif hockey_response.status_code == 400:
                    print(f"✅ Drużyna {team_name} nie jest drużyną hokejową - prawidłowy błąd 400")
                else:
                    print(f"❌ Błąd pobierania statystyk hokejowych: {hockey_response.status_code}")
            else:
                print("ℹ️  Brak drużyn hokejowych w bazie danych")
        else:
            print(f"❌ Błąd wyszukiwania drużyn hokejowych: {response.status_code}")
        
        # Test dla drużyny nie-hokejowej (oczekiwany błąd 400)
        football_response = requests.get(f"{BASE_URL}/teams/search?sport_name=piłka&page_size=1")
        if football_response.status_code == 200:
            football_teams = football_response.json()['teams']
            if football_teams:
                football_team_id = football_teams[0]['id']
                hockey_stats_response = requests.get(f"{BASE_URL}/teams/{football_team_id}/hockey-stats")
                if hockey_stats_response.status_code == 400:
                    print("✅ Test drużyny piłkarskiej: prawidłowy błąd 400 (brak statystyk hokejowych)")
                else:
                    print(f"❌ Test drużyny piłkarskiej: oczekiwano 400, otrzymano: {hockey_stats_response.status_code}")
        
        # Test nieistniejącej drużyny
        response = requests.get(f"{BASE_URL}/teams/99999/hockey-stats")
        if response.status_code == 404:
            print("✅ Test nieistniejącej drużyny: prawidłowy błąd 404")
        else:
            print(f"❌ Oczekiwano 404, otrzymano: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu statystyk hokejowych: {e}")

def test_team_roster():
    """Test endpointu składu drużyny hokejowej"""
    print("\n🔍 Test: GET /teams/{team_id}/roster")
    
    try:
        # Znajdź drużynę hokejową
        response = requests.get(f"{BASE_URL}/teams/search?sport_name=hokej&page_size=1")
        if response.status_code == 200:
            teams = response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                team_name = teams[0]['name']
                
                # Test składu drużyny
                roster_response = requests.get(f"{BASE_URL}/teams/{team_id}/roster")
                if roster_response.status_code == 200:
                    roster = roster_response.json()
                    print(f"✅ Skład drużyny {roster['team_name']}:")
                    print(f"   Bramkarze: {len(roster['goalkeepers'])}")
                    print(f"   Obrońcy: {len(roster['defensemen'])}")
                    print(f"   Napastnicy: {len(roster['forwards'])}")
                    print(f"   Kontuzjowani: {roster['injured_players']}")
                    
                    # Pokaż przykłady zawodników z każdej kategorii
                    if roster['goalkeepers']:
                        gk = roster['goalkeepers'][0]
                        name = gk['common_name'] or f"{gk['first_name']} {gk['last_name']}"
                        print(f"   Przykład bramkarza: {name} ({gk['position']}, {gk['country']})")
                    
                    if roster['defensemen']:
                        def_player = roster['defensemen'][0]
                        name = def_player['common_name'] or f"{def_player['first_name']} {def_player['last_name']}"
                        print(f"   Przykład obrońcy: {name} ({def_player['position']}, linia {def_player['line']}, {def_player['country']})")
                    
                    if roster['forwards']:
                        forward = roster['forwards'][0]
                        name = forward['common_name'] or f"{forward['first_name']} {forward['last_name']}"
                        print(f"   Przykład napastnika: {name} ({forward['position']}, linia {forward['line']}, {forward['country']})")
                        
                elif roster_response.status_code == 400:
                    print(f"✅ Drużyna {team_name} nie jest drużyną hokejową - prawidłowy błąd 400")
                else:
                    print(f"❌ Błąd pobierania składu: {roster_response.status_code}")
            else:
                print("ℹ️  Brak drużyn hokejowych w bazie danych")
        else:
            print(f"❌ Błąd wyszukiwania drużyn hokejowych: {response.status_code}")
        
        # Test dla drużyny nie-hokejowej (oczekiwany błąd 400)
        football_response = requests.get(f"{BASE_URL}/teams/search?sport_name=piłka&page_size=1")
        if football_response.status_code == 200:
            football_teams = football_response.json()['teams']
            if football_teams:
                football_team_id = football_teams[0]['id']
                roster_response = requests.get(f"{BASE_URL}/teams/{football_team_id}/roster")
                if roster_response.status_code == 400:
                    print("✅ Test drużyny piłkarskiej: prawidłowy błąd 400 (brak składu hokejowego)")
                else:
                    print(f"❌ Test drużyny piłkarskiej: oczekiwano 400, otrzymano: {roster_response.status_code}")
        
        # Test nieistniejącej drużyny
        response = requests.get(f"{BASE_URL}/teams/99999/roster")
        if response.status_code == 404:
            print("✅ Test nieistniejącej drużyny: prawidłowy błąd 404")
        else:
            print(f"❌ Oczekiwano 404, otrzymano: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu składu drużyny: {e}")

def test_edge_cases():
    """Test przypadków brzegowych i walidacji"""
    print("\n🔍 Test: Przypadki brzegowe i walidacja")
    
    try:
        # Pobierz ID drużyny do testów
        response = requests.get(f"{BASE_URL}/teams/all?page_size=1")
        if response.status_code == 200:
            teams = response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                
                # Test nieprawidłowych wartości last_n_matches dla różnych endpointów
                edge_cases = [
                    {"param": "last_n_matches=-1", "expected": 422, "desc": "wartość ujemna"},
                    {"param": "last_n_matches=0", "expected": 422, "desc": "zero"},
                    {"param": "last_n_matches=101", "expected": 422, "desc": "powyżej maksimum"},
                    {"param": "last_n_matches=abc", "expected": 422, "desc": "tekst zamiast liczby"},
                    {"param": "season_id=-1", "expected": 404, "desc": "nieistniejący sezon"},
                    {"param": "season_id=abc", "expected": 422, "desc": "tekst jako ID sezonu"}
                ]
                
                # Test przypadków brzegowych dla różnych endpointów
                test_endpoints = [
                    f"/teams/{team_id}/stats",
                    f"/teams/{team_id}/btts"
                ]
                
                # Dodaj testy hokejowe jeśli dostępne
                hockey_response = requests.get(f"{BASE_URL}/teams/search?sport_name=hokej&page_size=1")
                if hockey_response.status_code == 200:
                    hockey_teams = hockey_response.json()['teams']
                    if hockey_teams:
                        hockey_team_id = hockey_teams[0]['id']
                        test_endpoints.append(f"/teams/{hockey_team_id}/hockey-stats")
                
                for endpoint in test_endpoints:
                    print(f"\n   Testy dla {endpoint.split('/')[-1]}:")
                    for case in edge_cases:
                        test_url = f"{BASE_URL}{endpoint}?{case['param']}"
                        response = requests.get(test_url)
                        
                        if response.status_code == case['expected']:
                            print(f"   ✅ {case['desc']}: prawidłowy błąd {case['expected']}")
                        else:
                            print(f"   ❌ {case['desc']}: oczekiwano {case['expected']}, otrzymano {response.status_code}")
                
                # Test granicznych wartości prawidłowych
                boundary_tests = [
                    {"param": "last_n_matches=1", "desc": "minimalna prawidłowa wartość"},
                    {"param": "last_n_matches=100", "desc": "maksymalna prawidłowa wartość"}
                ]
                
                for test in boundary_tests:
                    test_url = f"{BASE_URL}/teams/{team_id}/stats?{test['param']}"
                    response = requests.get(test_url)
                    
                    if response.status_code == 200:
                        print(f"✅ Test {test['desc']}: prawidłowa odpowiedź")
                    else:
                        print(f"❌ Test {test['desc']}: błąd {response.status_code}")
                
                # Test kombinacji nieprawidłowych parametrów
                combo_url = f"{BASE_URL}/teams/{team_id}/btts?season_id=99999&last_n_matches=150"
                response = requests.get(combo_url)
                if response.status_code in [404, 422]:
                    print("✅ Test kombinacji nieprawidłowych parametrów: prawidłowy błąd")
                else:
                    print(f"❌ Test kombinacji nieprawidłowych parametrów: nieoczekiwany kod {response.status_code}")
                    
    except Exception as e:
        print(f"❌ Błąd testu przypadków brzegowych: {e}")

def test_matches_info():
    """Test endpointu informacji o module matches"""
    print("\n🔍 Test: GET /matches/")
    
    try:
        response = requests.get(f"{BASE_URL}/matches/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Info modułu matches: {data['module']}")
            print(f"   Wersja: {data['version']}")
            print(f"   Liczba endpointów: {len(data['endpoints'])}")
        else:
            print(f"❌ Błąd info matches: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu info matches: {e}")

def test_get_seasons_for_league():
    """Test pobierania sezonów dla ligi"""
    print("\n🔍 Test: GET /matches/seasons/{league_id}")
    
    # Test dla kilku popularnych lig
    test_leagues = [1, 2, 5]  # Przykładowe ID lig
    
    for league_id in test_leagues:
        try:
            response = requests.get(f"{BASE_URL}/matches/seasons/{league_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Liga {league_id}: {data['total_count']} sezonów")
                if data['seasons']:
                    latest_season = data['seasons'][0]
                    print(f"   Najnowszy sezon: {latest_season['years']} (ID: {latest_season['season_id']})")
            else:
                print(f"❌ Błąd dla ligi {league_id}: {response.status_code}")
        except Exception as e:
            print(f"❌ Błąd testu sezonów dla ligi {league_id}: {e}")

def test_get_rounds_for_season():
    """Test pobierania rund dla sezonu w lidze"""
    print("\n🔍 Test: GET /matches/rounds/{league_id}/{season_id}")
    
    # Najpierw pobierz sezon dla ligi
    test_league_id = 1
    try:
        seasons_response = requests.get(f"{BASE_URL}/matches/seasons/{test_league_id}")
        if seasons_response.status_code == 200:
            seasons_data = seasons_response.json()
            if seasons_data['seasons']:
                latest_season = seasons_data['seasons'][0]
                season_id = latest_season['season_id']
                
                # Teraz pobierz rundy
                rounds_response = requests.get(f"{BASE_URL}/matches/rounds/{test_league_id}/{season_id}")
                if rounds_response.status_code == 200:
                    rounds_data = rounds_response.json()
                    print(f"✅ Liga {test_league_id}, sezon {latest_season['years']}: {rounds_data['total_count']} rund")
                    if rounds_data['rounds']:
                        latest_round = rounds_data['rounds'][0]
                        print(f"   Najnowsza runda: {latest_round['round_number']} (data: {latest_round['game_date']})")
                else:
                    print(f"❌ Błąd pobierania rund: {rounds_response.status_code}")
            else:
                print("⚠️ Brak sezonów dla testowej ligi")
        else:
            print(f"❌ Błąd pobierania sezonów: {seasons_response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu rund: {e}")

def test_matches_edge_cases():
    """Test przypadków brzegowych dla API matches"""
    print("\n🔍 Test: Przypadki brzegowe API matches")
    
    # Test nieistniejącej ligi
    try:
        response = requests.get(f"{BASE_URL}/matches/seasons/999999")
        if response.status_code == 200:
            data = response.json()
            if data['total_count'] == 0:
                print("✅ Poprawna obsługa nieistniejącej ligi")
            else:
                print(f"⚠️ Nieoczekiwany wynik dla nieistniejącej ligi: {data['total_count']} sezonów")
        else:
            print(f"❌ Błąd dla nieistniejącej ligi: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu nieistniejącej ligi: {e}")
    
    # Test nieistniejącego sezonu
    try:
        response = requests.get(f"{BASE_URL}/matches/rounds/1/999999")
        if response.status_code == 200:
            data = response.json()
            if data['total_count'] == 0:
                print("✅ Poprawna obsługa nieistniejącego sezonu")
            else:
                print(f"⚠️ Nieoczekiwany wynik dla nieistniejącego sezonu: {data['total_count']} rund")
        else:
            print(f"❌ Błąd dla nieistniejącego sezonu: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu nieistniejącego sezonu: {e}")

def test_odds_info():
    """Test endpointu informacji o module odds"""
    print("\n🔍 Test: GET /odds/")
    
    try:
        response = requests.get(f"{BASE_URL}/odds/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Informacje o module odds: {data['module']}")
            print(f"   Opis: {data['description']}")
            print(f"   Dostępne endpointy: {len(data['endpoints'])}")
        else:
            print(f"❌ Błąd pobrania informacji o module odds: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu odds info: {e}")

def test_get_odds_for_match():
    """Test endpointu pobierania kursów dla meczu"""
    print("\n🔍 Test: GET /odds/match/{match_id}")
    
    # Test z istniejącym meczem (ID 1)
    try:
        match_id = 1
        response = requests.get(f"{BASE_URL}/odds/match/{match_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pobrano kursy dla meczu {match_id}")
            print(f"   Liczba kursów: {data['total_count']}")
            print(f"   ID meczu: {data['match_id']}")
            
            if data['odds']:
                first_odds = data['odds'][0]
                print(f"   Przykładowy kurs: {first_odds['bookmaker']} - {first_odds['event']} - {first_odds['odds']}")
            else:
                print("   Brak kursów dla tego meczu")
                
        elif response.status_code == 404:
            print(f"ℹ️  Mecz {match_id} nie istnieje lub nie ma kursów")
        else:
            print(f"❌ Błąd pobrania kursów: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu get odds for match: {e}")

def test_odds_edge_cases():
    """Test przypadków brzegowych dla modułu odds"""
    print("\n🔍 Test: Przypadki brzegowe - odds")
    
    # Test z nieistniejącym meczem
    try:
        match_id = 999999
        response = requests.get(f"{BASE_URL}/odds/match/{match_id}")
        
        if response.status_code == 404:
            print(f"✅ Poprawna obsługa nieistniejącego meczu (ID: {match_id})")
        else:
            print(f"❌ Niepoprawna obsługa nieistniejącego meczu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu edge cases odds: {e}")
    
    # Test z nieprawidłowym ID meczu
    try:
        response = requests.get(f"{BASE_URL}/odds/match/abc")
        
        if response.status_code == 422:  # Validation error
            print("✅ Poprawna obsługa nieprawidłowego formatu ID meczu")
        else:
            print(f"❌ Niepoprawna obsługa błędnego formatu ID: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu invalid match ID: {e}")

def test_predictions_info():
    """Test endpointu informacji o module predictions"""
    print("\n🔍 Test: GET /predictions/")
    
    try:
        response = requests.get(f"{BASE_URL}/predictions/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Informacje o module predictions: {data['module']}")
            print(f"   Opis: {data['description']}")
            print(f"   Dostępne endpointy: {len(data['endpoints'])}")
        else:
            print(f"❌ Błąd pobrania informacji o module predictions: {response.status_code}")
    except Exception as e:
        print(f"❌ Błąd testu predictions info: {e}")

def test_search_predictions_without_filters():
    """Test wyszukiwania predykcji bez filtrów"""
    print("\n🔍 Test: GET /predictions/search (bez filtrów)")
    
    try:
        response = requests.get(f"{BASE_URL}/predictions/search")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pobrano predykcje bez filtrów")
            print(f"   Liczba predykcji: {data['total_count']}")
            print(f"   Zwrócono na stronie: {len(data['predictions'])}")
            print(f"   Zastosowane filtry: {data['filters_applied']}")
            
            if data['predictions']:
                first_pred = data['predictions'][0]
                print(f"   Przykładowa predykcja: ID={first_pred['id']}, Match={first_pred['match_id']}, Event={first_pred['event_id']} ({first_pred['event_name']}), Model={first_pred['model_id']}, Value={first_pred['value']}")
                
        else:
            print(f"❌ Błąd wyszukiwania predykcji: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu search predictions without filters: {e}")

def test_search_predictions_with_filters():
    """Test wyszukiwania predykcji z filtrami"""
    print("\n🔍 Test: GET /predictions/search (z filtrami)")
    
    try:
        # Test z filtrem match_id
        params = {
            "match_id": 1,
            "page_size": 10
        }
        response = requests.get(f"{BASE_URL}/predictions/search", params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pobrano predykcje z filtrem match_id=1")
            print(f"   Liczba predykcji: {data['total_count']}")
            print(f"   Zastosowane filtry: {data['filters_applied']}")
            
            # Sprawdzenie czy wszystkie predykcje mają match_id=1
            if data['predictions']:
                all_match_correct = all(pred['match_id'] == 1 for pred in data['predictions'])
                if all_match_correct:
                    print("   ✅ Filtr match_id działa poprawnie")
                else:
                    print("   ❌ Filtr match_id nie działa poprawnie")
                    
        else:
            print(f"❌ Błąd wyszukiwania z filtrem: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu search predictions with filters: {e}")

def test_search_predictions_with_model_ids():
    """Test wyszukiwania predykcji z filtrem model_ids"""
    print("\n🔍 Test: GET /predictions/search (z model_ids)")
    
    try:
        # Test z filtrem model_ids
        params = {
            "model_ids": "1,2",
            "page_size": 10
        }
        response = requests.get(f"{BASE_URL}/predictions/search", params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pobrano predykcje z filtrem model_ids='1,2'")
            print(f"   Liczba predykcji: {data['total_count']}")
            print(f"   Zastosowane filtry: {data['filters_applied']}")
            
            # Sprawdzenie czy wszystkie predykcje mają model_id in [1,2]
            if data['predictions']:
                all_models_correct = all(pred['model_id'] in [1, 2] for pred in data['predictions'])
                if all_models_correct:
                    print("   ✅ Filtr model_ids działa poprawnie")
                else:
                    print("   ❌ Filtr model_ids nie działa poprawnie")
                    
        else:
            print(f"❌ Błąd wyszukiwania z filtrem model_ids: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu search predictions with model_ids: {e}")

def test_predictions_edge_cases():
    """Test przypadków brzegowych dla modułu predictions"""
    print("\n🔍 Test: Przypadki brzegowe - predictions")
    
    # Test z nieprawidłowym formatem model_ids
    try:
        params = {"model_ids": "abc,def"}
        response = requests.get(f"{BASE_URL}/predictions/search", params=params)
        
        if response.status_code == 400:
            print("✅ Poprawna obsługa nieprawidłowego formatu model_ids")
        else:
            print(f"❌ Niepoprawna obsługa błędnego formatu model_ids: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu invalid model_ids: {e}")
    
    # Test z nieistniejącym match_id
    try:
        params = {"match_id": 999999}
        response = requests.get(f"{BASE_URL}/predictions/search", params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data['total_count'] == 0:
                print("✅ Poprawna obsługa nieistniejącego match_id")
            else:
                print(f"⚠️ Nieoczekiwany wynik dla nieistniejącego match_id: {data['total_count']} predykcji")
        else:
            print(f"❌ Błąd dla nieistniejącego match_id: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu nieistniejącego match_id: {e}")

def test_get_team_predictions():
    """Test endpointu pobierania predykcji dla drużyny"""
    print("\n🔍 Test: GET /predictions/team/{team_id}/{season_id}")
    
    try:
        # Test z istniejącą drużyną i sezonem (ID 1, sezon 1)
        team_id = 1
        season_id = 1
        response = requests.get(f"{BASE_URL}/predictions/team/{team_id}/{season_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pobrano predykcje dla drużyny {team_id} w sezonie {season_id}")
            print(f"   Liczba predykcji: {data['total_count']}")
            print(f"   ID drużyny: {data['team_id']}")
            print(f"   ID sezonu: {data['season_id']}")
            
            if data['team_predictions']:
                first_pred = data['team_predictions'][0]
                outcome_str = "nie oceniona" if first_pred['outcome'] is None else first_pred['outcome']
                print(f"   Przykładowa predykcja: Event={first_pred['event_id']}, Outcome={outcome_str}")
            else:
                print("   Brak predykcji dla tej drużyny w tym sezonie")
                
        elif response.status_code == 404:
            print(f"ℹ️  Drużyna {team_id} lub sezon {season_id} nie istnieje")
        else:
            print(f"❌ Błąd pobrania predykcji drużyny: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu get team predictions: {e}")

def test_team_predictions_edge_cases():
    """Test przypadków brzegowych dla predykcji drużyny"""
    print("\n🔍 Test: Przypadki brzegowe - team predictions")
    
    # Test z nieistniejącą drużyną
    try:
        team_id = 999999
        season_id = 1
        response = requests.get(f"{BASE_URL}/predictions/team/{team_id}/{season_id}")
        
        if response.status_code == 404:
            print(f"✅ Poprawna obsługa nieistniejącej drużyny (ID: {team_id})")
        else:
            print(f"❌ Niepoprawna obsługa nieistniejącej drużyny: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu nieistniejącej drużyny: {e}")
    
    # Test z nieistniejącym sezonem
    try:
        team_id = 1
        season_id = 999999
        response = requests.get(f"{BASE_URL}/predictions/team/{team_id}/{season_id}")
        
        if response.status_code == 404:
            print(f"✅ Poprawna obsługa nieistniejącego sezonu (ID: {season_id})")
        else:
            print(f"❌ Niepoprawna obsługa nieistniejącego sezonu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu nieistniejącego sezonu: {e}")
    
    # Test z nieprawidłowymi parametrami
    try:
        response = requests.get(f"{BASE_URL}/predictions/team/abc/def")
        
        if response.status_code == 422:  # Validation error
            print("✅ Poprawna obsługa nieprawidłowych parametrów")
        else:
            print(f"❌ Niepoprawna obsługa błędnych parametrów: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu invalid parameters: {e}")

def test_get_match_predictions():
    """Test endpointu pobierania predykcji dla meczu"""
    print("\n🔍 Test: GET /predictions/match/{match_id}")
    
    try:
        # Test z istniejącym meczem (ID 1)
        match_id = 1
        response = requests.get(f"{BASE_URL}/predictions/match/{match_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pobrano predykcje dla meczu {match_id}")
            print(f"   Liczba predykcji: {data['total_count']}")
            print(f"   ID meczu: {data['match_id']}")
            
            if data['match_predictions']:
                first_pred = data['match_predictions'][0]
                outcome_str = "nie oceniona" if first_pred['outcome'] is None else first_pred['outcome']
                print(f"   Przykładowa predykcja: Event={first_pred['event_id']} ({first_pred['name']}), Model={first_pred['model_id']}, Outcome={outcome_str}")
            else:
                print("   Brak predykcji dla tego meczu")
                
        elif response.status_code == 404:
            print(f"ℹ️  Mecz {match_id} nie istnieje lub nie ma predykcji")
        else:
            print(f"❌ Błąd pobrania predykcji meczu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu get match predictions: {e}")

def test_match_predictions_edge_cases():
    """Test przypadków brzegowych dla predykcji meczu"""
    print("\n🔍 Test: Przypadki brzegowe - match predictions")
    
    # Test z nieistniejącym meczem
    try:
        match_id = 999999
        response = requests.get(f"{BASE_URL}/predictions/match/{match_id}")
        
        if response.status_code == 404:
            print(f"✅ Poprawna obsługa nieistniejącego meczu (ID: {match_id})")
        else:
            print(f"❌ Niepoprawna obsługa nieistniejącego meczu: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu nieistniejącego meczu: {e}")
    
    # Test z nieprawidłowym parametrem
    try:
        response = requests.get(f"{BASE_URL}/predictions/match/abc")
        
        if response.status_code == 422:  # Validation error
            print("✅ Poprawna obsługa nieprawidłowego formatu ID meczu")
        else:
            print(f"❌ Niepoprawna obsługa błędnego formatu ID: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu invalid match parameter: {e}")

def run_all_tests():
    """Uruchom wszystkie testy"""
    print("🚀 Rozpoczynam testy API EkstraBet")
    print("=" * 60)
    
    # Test połączenia
    if not test_api_connection():
        print("❌ Nie można połączyć się z API. Upewnij się, że serwer działa.")
        return
    
    # Testy systemowe
    test_health_check()
    test_teams_info()
    test_matches_info()
    test_odds_info()
    test_predictions_info()
    
    # Testy funkcjonalne podstawowe
    test_get_all_teams()
    test_search_teams()
    test_helper_endpoints()
    
    # Testy funkcjonalne matches
    test_get_seasons_for_league()
    test_get_rounds_for_season()
    
    # Testy funkcjonalne odds
    test_get_odds_for_match()
    
    # Testy funkcjonalne predictions
    test_search_predictions_without_filters()
    test_search_predictions_with_filters()
    test_search_predictions_with_model_ids()
    test_get_team_predictions()
    test_get_match_predictions()
    
    # Testy funkcjonalne zaawansowane (nowe funkcjonalności)
    test_team_stats()
    test_team_btts_stats()
    test_season_filtering()
    
    # Testy specjalistyczne hokejowe
    test_team_hockey_stats()
    test_team_roster()
    
    # Testy przypadków brzegowych
    test_edge_cases()
    test_matches_edge_cases()
    test_odds_edge_cases()
    test_predictions_edge_cases()
    test_team_predictions_edge_cases()
    test_match_predictions_edge_cases()
    
    # Test wydajności
    test_api_performance()
    
    print("\n" + "=" * 60)
    print("✅ Wszystkie testy zakończone")

if __name__ == "__main__":
    run_all_tests()
