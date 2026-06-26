# Test uruchamiania API EkstraBet
# Szybki test czy wszystko jest poprawnie skonfigurowane

import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))


def test_imports():
    """Test importowania wszystkich modułów"""
    print("🔍 Testowanie importów...")

    try:
        from api.routers.teams import router as teams_router
        print("✅ api.routers.teams - OK")

        from api.routers.leagues import router as leagues_router
        print("✅ api.routers.leagues - OK")

        from api.main import app, create_app
        print("✅ api.main - OK")

        test_app = create_app()
        print("✅ create_app() - OK")

        if hasattr(test_app, "routes"):
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
    required_vars = ["DB_PASSWORD", "SECRET_KEY"]
    optional_vars = ["DB_HOST", "DB_USER", "DB_NAME", "DB_PORT"]

    missing_required = []

    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)

    if missing_required:
        print(f"❌ Brak wymaganych zmiennych: {', '.join(missing_required)}")
        print("   Utwórz plik .env na podstawie .env.example")
        return False

    print("✅ Wymagane zmienne środowiskowe - OK")

    for var in optional_vars:
        value = os.getenv(var)
        if value:
            if "PASSWORD" in var or "SECRET" in var or "KEY" in var:
                masked_value = value[:3] + "*" * (len(value) - 3)
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")

    return True


def test_database_connection():
    """Test połączenia z bazą danych"""
    print("\n🔍 Testowanie połączenia z bazą danych...")

    db_password = os.getenv("DB_PASSWORD")

    if not db_password:
        print("❌ Brak zmiennej środowiskowej DB_PASSWORD")
        print("   Utwórz plik .env lub ustaw zmienną DB_PASSWORD")
        return False

    try:
        from backend.database import test_connection

        if test_connection():
            print("✅ Połączenie z bazą danych - OK")
            return True
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

        from api.main import app
        print("✅ Aplikacja dostępna jako api.main:app")

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

    tests = [
        test_imports,
        test_environment_variables,
        test_database_connection,
        test_uvicorn_compatibility,
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
        print("   python -m api.start_api")
        print("   lub")
        print("   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")
    else:
        print("❌ Niektóre testy nie przeszły. Sprawdź konfigurację.")
        sys.exit(1)


if __name__ == "__main__":
    main()
