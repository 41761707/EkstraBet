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
    """Test endpointu statystyk drużyny"""
    print("\n🔍 Test: GET /teams/{team_id}/stats")
    
    # Najpierw pobierz listę drużyn żeby mieć prawdziwe ID
    try:
        response = requests.get(f"{BASE_URL}/teams/all?page_size=1")
        if response.status_code == 200:
            teams = response.json()['teams']
            if teams:
                team_id = teams[0]['id']
                
                # Test statystyk
                stats_response = requests.get(f"{BASE_URL}/teams/{team_id}/stats")
                if stats_response.status_code == 200:
                    stats = stats_response.json()
                    print(f"✅ Statystyki dla {stats['team_name']}:")
                    print(f"   Mecze: {stats['total_matches']} (dom: {stats['home_matches']}, wyjazd: {stats['away_matches']})")
                    print(f"   Bilans: {stats['wins']}W {stats['draws']}R {stats['losses']}P")
                    print(f"   Bramki: {stats['goals_scored']} strzelonych, {stats['goals_conceded']} straconych")
                else:
                    print(f"❌ Błąd pobierania statystyk: {stats_response.status_code}")
        
        # Test nieistniejącej drużyny
        response = requests.get(f"{BASE_URL}/teams/99999/stats")
        if response.status_code == 404:
            print("✅ Test nieistniejącej drużyny: prawidłowy błąd 404")
        else:
            print(f"❌ Oczekiwano 404, otrzymano: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Błąd testu statystyk: {e}")

def test_helper_endpoints():
    """Test endpointów pomocniczych"""
    print("\n🔍 Test: Endpointy pomocnicze")
    
    # Test krajów
    try:
        response = requests.get(f"{BASE_URL}/teams/countries")
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
        response = requests.get(f"{BASE_URL}/teams/sports")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Sporty: {data['total_sports']} sportów")
            if data['sports']:
                example = data['sports'][0]
                print(f"   Przykład: {example['name']} ({example['teams_count']} drużyn)")
    except Exception as e:
        print(f"❌ Błąd testu sportów: {e}")

def test_api_performance():
    """Test wydajności API"""
    print("\n⚡ Test wydajności")
    
    endpoints = [
        "/",
        "/health",
        "/teams/",
        "/teams/all?page_size=10",
        "/teams/search?country_name=Polska",
        "/teams/countries",
        "/teams/sports"
    ]
    
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
    
    # Testy funkcjonalne
    test_get_all_teams()
    test_search_teams()
    test_team_stats()
    test_helper_endpoints()
    
    # Test wydajności
    test_api_performance()
    
    print("\n" + "=" * 60)
    print("✅ Testy zakończone")

if __name__ == "__main__":
    run_all_tests()
