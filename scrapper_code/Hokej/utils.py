

def check_if_in_db(home_team: str, away_team: str, game_date: str = None, round_num: str = None, season: int = None, conn=None) -> int:
    """Sprawdza, czy mecz jest już w bazie danych.
    
    Funkcja umożliwia wyszukiwanie meczu na dwa sposoby:
    1. Według daty meczu (parametr game_date)
    2. Według kolejki i sezonu (parametry round_num i season)
    
    Args:
        home_team (str): Nazwa drużyny gospodarzy.
        away_team (str): Nazwa drużyny gości.
        game_date (str, opcjonalny): Data meczu. Wymagana, jeśli nie podano round_num i season.
        round_num (str, opcjonalny): Numer kolejki. Wymagana, jeśli nie podano game_date.
        season (int, opcjonalny): ID sezonu. Wymagany wraz z round_num.
        conn: Połączenie do bazy danych.
        
    Returns:
        int: ID meczu, jeśli istnieje, -1 w przeciwnym razie.
    """
    cursor = conn.cursor()
    try:
        if game_date is not None:
            # Wyszukiwanie według daty
            query = """
                SELECT m.id 
                FROM matches m 
                WHERE m.home_team = %s AND m.away_team = %s AND m.game_date = %s
                """
            cursor.execute(query, (home_team, away_team, game_date))
        else:
            # Wyszukiwanie według kolejki i sezonu
            # game_date może być None więc nie wiem czemu to jest wyszarzone?
            query = """ SELECT m.id 
                FROM matches m 
                WHERE m.home_team = %s AND m.away_team = %s AND m.round = %s AND m.season = %s
                """
            cursor.execute(query, (home_team, away_team, round_num, season))
        
        result = cursor.fetchone()
        return result[0] if result else -1
    finally:
        cursor.close()