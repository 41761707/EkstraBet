# Test uruchamiania API EkstraBet
# Szybki test czy wszystko jest poprawnie skonfigurowane

import sys
import os
from pathlib import Path

# Dodaj katalog api_code do ścieżki
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_imports():
    """Test importowania wszystkich modułów"""
    print("🔍 Testowanie importów...")
    
    try:
        # Test importu modułu teams
        from api_teams import router as teams_router
        print("✅ api_teams - OK")
        
        # Test importu głównej aplikacji
        from start_api import app, create_app
        print("✅ start_api - OK")
        
        # Test utworzenia aplikacji
        test_app = create_app()
        print("✅ create_app() - OK")
        
        # Test routerów
        if hasattr(test_app, 'routes'):
            routes_count = len(test_app.routes)
            print(f"✅ Liczba zarejestrowanych route: {routes_count}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Błąd importu: {e}")
        return False
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False

def test_environment_variables():
    """Test wymaganych zmiennych środowiskowych"""
    print("\n🔍 Testowanie zmiennych środowiskowych...")
    required_vars = ["DB_PASSWORD"]
    optional_vars = ["DB_HOST", "DB_USER", "DB_NAME", "DB_PORT", "SECRET_KEY"]
    
    missing_required = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        print(f"❌ Brak wymaganych zmiennych: {', '.join(missing_required)}")
        print("   Utwórz plik .env na podstawie .env.example")
        return False
    
    print("✅ Wymagane zmienne środowiskowe - OK")
    
    # Pokaż opcjonalne zmienne
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            # Nie pokazuj pełnych haseł/kluczy
            if "PASSWORD" in var or "SECRET" in var or "KEY" in var:
                masked_value = value[:3] + "*" * (len(value) - 3)
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")
    
    return True

def test_database_connection():
    """Test połączenia z bazą danych"""
    print("\n🔍 Testowanie połączenia z bazą danych...")
    
    # Sprawdź zmienne środowiskowe
    import os
    db_password = os.getenv("DB_PASSWORD")
    
    if not db_password:
        print("❌ Brak zmiennej środowiskowej DB_PASSWORD")
        print("   Utwórz plik .env lub ustaw zmienną DB_PASSWORD")
        return False
    
    try:
        import db_module
        conn = db_module.db_connect()
        
        if conn.is_connected():
            print("✅ Połączenie z bazą danych - OK")
            conn.close()
            return True
        else:
            print("❌ Nie można połączyć się z bazą danych")
            return False
            
    except Exception as e:
        print(f"❌ Błąd połączenia z bazą: {e}")
        return False

def test_uvicorn_compatibility():
    """Test kompatybilności z uvicorn"""
    print("\n🔍 Testowanie kompatybilności z uvicorn...")
    
    try:
        import uvicorn
        print("✅ uvicorn zainstalowany")
        
        # Test czy aplikacja może być importowana jako string
        from start_api import app
        print("✅ Aplikacja dostępna jako start_api:app")
        
        return True
        
    except ImportError as e:
        print(f"❌ Błąd uvicorn: {e}")
        return False
    except Exception as e:
        print(f"❌ Błąd: {e}")
        return False

def main():
    """Główna funkcja testowa"""
    print("🚀 Test konfiguracji API EkstraBet")
    print("=" * 50)
    
    # Uruchom testy
    tests = [
        test_imports,
        test_environment_variables,
        test_database_connection,
        test_uvicorn_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Wynik testów: {passed}/{total}")
    
    if passed == total:
        print("✅ Wszystkie testy przeszły pomyślnie!")
        print("🚀 API jest gotowe do uruchomienia:")
        print("   python start_api.py")
        print("   lub")
        print("   uvicorn start_api:app --host 0.0.0.0 --port 8000 --reload")
    else:
        print("❌ Niektóre testy nie przeszły. Sprawdź konfigurację.")
        sys.exit(1)

if __name__ == "__main__":
    main()
