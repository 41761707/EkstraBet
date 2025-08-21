import db_module
import argparse
import traceback
from datetime import datetime

def football_player_team(league_id, automate=False):
    """
    Funkcja do śledzenia transferów zawodników piłkarskich.
    Analizuje wpisy z tabeli football_player_stats i identyfikuje zmiany klubów zawodników.
    
    Args:
        league_id (int): ID ligi do analizy
        automate (bool): Czy automatycznie wprowadzać zmiany do bazy (domyślnie False)
    """
    conn = None
    try:
        # Nawiązanie połączenia z bazą danych
        conn = db_module.db_connect()
        cursor = conn.cursor()
        # Zapytanie pobierające wszystkie wpisy z football_player_stats dla danej ligi
        # posortowane chronologicznie (od najstarszego do najnowszego)
        query = """
            SELECT fps.id, fps.match_id, fps.player_id, fps.team_id, m.game_date, m.season, p.current_club
            FROM football_player_stats fps
            JOIN matches m ON fps.match_id = m.id
            JOIN players p ON fps.player_id = p.id
            WHERE m.league = %s
            ORDER BY m.game_date ASC, fps.id ASC
        """
        cursor.execute(query, (league_id,))
        results = cursor.fetchall()
        if not results:
            print(f"Brak danych dla ligi ID: {league_id}")
            return
        # Słownik do śledzenia poprzedniego klubu każdego zawodnika
        player_previous_club = {}
        transfers_detected = 0
        transfers_processed = 0
        for record in results:
            stat_id, match_id, player_id, team_id, game_date, season_id, current_club = record
            # Sprawdzenie czy zawodnik już występował wcześniej
            if player_id in player_previous_club:
                previous_club = player_previous_club[player_id]
                # Jeśli team_id z tego meczu różni się od poprzedniego klubu
                if team_id != previous_club and previous_club is not None:
                    transfers_detected += 1
                    if automate:
                        try:
                            # Sprawdzenie czy transfer już istnieje w bazie
                            check_transfer_query = """
                                SELECT id FROM transfers 
                                WHERE player_id = %s 
                                AND old_team_id = %s 
                                AND new_team_id = %s 
                                AND season_id = %s
                            """
                            cursor.execute(check_transfer_query, (player_id, previous_club, team_id, season_id))
                            existing_transfer = cursor.fetchone()
                            if not existing_transfer:
                                # Wstawienie nowego transferu do tabeli transfers
                                insert_transfer_query = """
                                    INSERT INTO transfers (player_id, old_team_id, new_team_id, season_id)
                                    VALUES (%s, %s, %s, %s)
                                """
                                cursor.execute(insert_transfer_query, (player_id, previous_club, team_id, season_id))
                                # Aktualizacja current_club w tabeli players
                                update_player_query = """
                                    UPDATE players 
                                    SET current_club = %s 
                                    WHERE id = %s
                                """
                                cursor.execute(update_player_query, (team_id, player_id))
                                conn.commit()
                                transfers_processed += 1
                                
                        except Exception as e:
                            print(f"Błąd podczas zapisywania transferu: {str(e)}")
                            conn.rollback()
            
            # Aktualizacja poprzedniego klubu dla zawodnika
            player_previous_club[player_id] = team_id
        
        # Sprawdzenie zawodników z current_club = null i uzupełnienie na podstawie player_previous_club
        null_club_updates = 0
        for player_id, last_team_id in player_previous_club.items():
            # Sprawdzenie czy zawodnik ma current_club = null
            check_player_query = """
                SELECT current_club FROM players WHERE id = %s
            """
            cursor.execute(check_player_query, (player_id,))
            result = cursor.fetchone()
            
            if result and result[0] is None:  # current_club is null
                if automate:
                    try:
                        # Aktualizacja current_club w tabeli players
                        update_player_query = """
                            UPDATE players 
                            SET current_club = %s 
                            WHERE id = %s AND current_club IS NULL
                        """
                        cursor.execute(update_player_query, (last_team_id, player_id))
                        
                        if cursor.rowcount > 0:
                            conn.commit()
                            null_club_updates += 1
                            
                    except Exception as e:
                        print(f"  ✗ Błąd podczas aktualizacji: {str(e)}")
                        conn.rollback()
        print("=" * 80)
        print(f"PODSUMOWANIE:")
        print(f"Wykryte transfery: {transfers_detected}")
        if automate:
            print(f"Przetworzone transfery: {transfers_processed}")
            print(f"Zaktualizowane current_club (z null): {null_club_updates}")
        else:
            print("Tryb podglądu - użyj --automate aby wprowadzić zmiany do bazy")
    except Exception as e:
        print(f"Wystąpił błąd: {str(e)}")
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def main():
    """
    Główna funkcja obsługująca argumenty linii poleceń.
    """
    parser = argparse.ArgumentParser(
        description="Mechanizm śledzenia transferów zawodników piłkarskich"
    )
    parser.add_argument(
        "league_id",
        type=int,
        help="ID ligi do analizy transferów"
    )
    parser.add_argument(
        "--automate",
        action="store_true",
        help="Automatycznie wprowadź zmiany do bazy danych (domyślnie tylko podgląd)"
    )
    args = parser.parse_args()
    football_player_team(args.league_id, args.automate)

if __name__ == "__main__":
    main()