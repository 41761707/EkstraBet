import argparse
import traceback
from datetime import datetime
import db_module

def get_matches_for_date(conn, league_id, season_id, match_date):
    """
    Pobiera wszystkie mecze dla danej ligi, sezonu i daty.
    Args:
        conn: Połączenie z bazą danych
        league_id (int): ID ligi
        season_id (int): ID sezonu
        match_date (str): Data meczu w formacie YYYY-MM-DD
    
    Returns:
        list: Lista krotek (match_id, home_team_id, away_team_id)
    """
    cursor = conn.cursor()
    query = """
        SELECT id, home_team, away_team
        FROM matches
        WHERE league = %s
            AND season = %s
            AND cast(game_date as date) = %s
    """
    cursor.execute(query, (league_id, season_id, match_date))
    matches = cursor.fetchall()
    cursor.close()
    return matches

def get_active_players_for_team(conn, team_id):
    """
    Pobiera aktywnych zawodników należących do danej drużyny.
    Args:
        conn: Połączenie z bazą danych
        team_id (int): ID drużyny
    
    Returns:
        list: Lista krotek (player_id,)
    """
    cursor = conn.cursor()
    query = """
        SELECT id
        FROM players
        WHERE current_club = %s
            AND active = 1
    """
    cursor.execute(query, (team_id,))
    players = cursor.fetchall()
    cursor.close()
    return players

def insert_roster_entry(conn, player_id, team_id):
    """
    Insertuje wpis do tabeli hockey_match_rosters.
    Args:
        conn: Połączenie z bazą danych
        player_id (int): ID zawodnika
        team_id (int): ID drużyny
    Returns:
        bool: True jeśli insert się powiódł, False w przypadku duplikatu
    """
    cursor = conn.cursor()
    query = """
        INSERT INTO hockey_rosters (player_id, team_id)
        VALUES (%s, %s)"""
    try:
        cursor.execute(query, (player_id, team_id))
        cursor.close()
        return cursor.rowcount > 0
    except Exception as e:
        cursor.close()
        return False

def create_rosters_for_date(league_id, season_id, match_date):
    """
    Tworzy składy drużyn dla wszystkich meczów w danej dacie.
    Args:
        league_id (int): ID ligi
        season_id (int): ID sezonu
        match_date (str): Data meczu w formacie YYYY-MM-DD
    """
    conn = None
    stats = {
        'matches_processed': 0,
        'teams_processed': 0,
        'rosters_inserted': 0,
        'rosters_skipped': 0
    }
    try:
        conn = db_module.db_connect()
        # Pobierz mecze dla danej daty
        matches = get_matches_for_date(conn, league_id, season_id, match_date)
        print(f"Znaleziono {len(matches)} meczów dla daty {match_date}")
        if not matches:
            print("Brak meczów do przetworzenia")
            return stats
        for match_id, home_team_id, away_team_id in matches:
            print(f"\nPrzetwarzanie meczu ID={match_id}: Gospodarze={home_team_id} vs Goście={away_team_id}")
            for team_id in [home_team_id, away_team_id]:
                players = get_active_players_for_team(conn, team_id)
                print(f"  Drużyna ID={team_id}: znaleziono {len(players)} aktywnych zawodników")
                for (player_id,) in players:
                    inserted = insert_roster_entry(conn, player_id, team_id)
                    if inserted:
                        stats['rosters_inserted'] += 1
                    else:
                        stats['rosters_skipped'] += 1
                stats['teams_processed'] += 1
            stats['matches_processed'] += 1
        conn.commit()
        return stats
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Błąd podczas tworzenia składów drużyn:")
        traceback.print_exc()
        raise
    finally:
        if conn:
            conn.close()

def print_stats(stats):
    """Wyświetla statystyki operacji tworzenia składów drużyn.
    Args:
        stats (dict): Słownik ze statystykami
    """
    print(f"\nPodsumowanie operacji:")
    print(f"  - Przetworzonych meczów: {stats['matches_processed']}")
    print(f"  - Przetworzonych drużyn: {stats['teams_processed']}")
    print(f"  - Dodanych wpisów do rosters: {stats['rosters_inserted']}")
    print(f"  - Pominiętych wpisów (duplikaty): {stats['rosters_skipped']}")

def create_argument_parser():
    """
    Tworzy parser argumentów wiersza poleceń.
    Returns:
        argparse.ArgumentParser: Skonfigurowany parser argumentów
    """
    parser = argparse.ArgumentParser(
        description='Tworzy składy drużyn hokejowych dla meczów w wybranej dacie',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s --league_id 45 --season_id 11 --match_date 2024-10-30
  %(prog)s --league_id 45 --season_id 11 --match_date 2025-11-05
  
  gdzie:
    - 45 to ID ligi NHL
    - 11 to ID sezonu 2024/2025
    - 2024-10-30 to data meczów
        """)
    parser.add_argument(
        '--league_id',
        type=int,
        help='ID ligi (np. 45 dla NHL)')
    parser.add_argument(
        '--season_id',
        type=int,
        help='ID sezonu (np. 11 dla sezonu 2024/2025)')
    parser.add_argument(
        '--match_date',
        type=str,
        help='Data meczu w formacie YYYY-MM-DD (np. 2024-10-30)')
    return parser

def validate_date_format(date_string):
    """
    Waliduje format daty.
    Args:
        date_string (str): Data do walidacji
    
    Returns:
        bool: True jeśli data jest poprawna, False w przeciwnym przypadku
    """
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def main():
    """Główna funkcja uruchamiająca skrypt."""
    parser = create_argument_parser()
    args = parser.parse_args()
    if not validate_date_format(args.match_date):
        print(f"Błąd: Niepoprawny format daty '{args.match_date}'. Użyj formatu YYYY-MM-DD")
        return
    try:
        stats = create_rosters_for_date(args.league_id, args.season_id, args.match_date)
        print_stats(stats)
        print("\nOperacja zakończona pomyślnie")
    except Exception as e:
        print(f"\nOperacja zakończona niepowodzeniem")

if __name__ == "__main__":
    main()
