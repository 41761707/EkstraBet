import argparse
import traceback
import db_module

def update_active_status(league_id, season_id):
    """
    Aktualizuje status aktywności zawodników hokejowych na podstawie ich udziału w danej lidze i sezonie.
    Args:
        league_id (int): ID ligi, dla której sprawdzamy aktywność zawodników
        season_id (int): ID sezonu, dla którego sprawdzamy aktywność zawodników
    Returns:
        tuple: Liczba aktywowanych zawodników, liczba dezaktywowanych zawodników
    """
    conn = None
    try:
        conn = db_module.db_connect()
        cursor = conn.cursor()
        # Dezaktywacja wszystkich zawodników hokejowych (sport_id=2)
        cursor.execute("""
            UPDATE players 
            SET active = 0 
            WHERE sports_id = 2
        """)
        deactivated_count = cursor.rowcount
        # Aktywacja zawodników, którzy zagrali w meczu w podanym sezonie i lidze
        cursor.execute("""
            UPDATE players p
            JOIN hockey_match_rosters hmr ON p.id = hmr.player_id
            JOIN matches m ON hmr.match_id = m.id
            SET p.active = 1
            WHERE p.sports_id = 2
                AND m.season = %s
                AND m.league = %s
        """, (season_id, league_id))
        activated_count = cursor.rowcount
        conn.commit()
        return activated_count, deactivated_count
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Błąd podczas aktualizacji statusu aktywności zawodników:")
        traceback.print_exc()
        raise
    finally:
        if conn:
            conn.close()

def create_argument_parser():
    """
    Tworzy parser argumentów wiersza poleceń.
    Returns:
        argparse.ArgumentParser: Skonfigurowany parser argumentów
    """
    parser = argparse.ArgumentParser(
        description='Skrypt do aktualizacji statusu aktywności zawodników hokejowych w bazie danych',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  # Aktualizacja dla ligi NHL (ID=45) w sezonie 2024/2025 (ID=11)
  python nhl_calculate_active.py --league_id 45 --season_id 11

  # Aktualizacja dla innej ligi i sezonu
  python nhl_calculate_active.py --league_id 3 --season_id 7

Opis:
  Skrypt ustawia active=1 dla zawodników hokejowych (sport_id=2), którzy:
    - Są przypisani do drużyny w tabeli hockey_rosters
    - Ta drużyna rozegrała przynajmniej jeden mecz w podanej lidze i sezonie
  Pozostali zawodnicy hokejowi otrzymują active=0.
        """
    )
    parser.add_argument(
        '--league_id',
        required=True,
        type=int,
        help='ID ligi w bazie danych (wymagany)')
    parser.add_argument(
        '--season_id',
        required=True,
        type=int,
        help='ID sezonu w bazie danych (wymagany)')
    return parser

def main():
    """
    Funkcja główna uruchamiająca skrypt.
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    activated, deactivated = update_active_status(args.league_id, args.season_id)
    print(f"Zaktualizowano status zawodników dla ligi ID={args.league_id}, sezon ID={args.season_id}")
    print(f"Aktywowano: {activated} zawodników")
    print(f"Dezaktywowano: {deactivated} zawodników")

if __name__ == "__main__":
    main()
