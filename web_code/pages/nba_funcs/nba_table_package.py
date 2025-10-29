import streamlit as st
import pandas as pd

def get_divisions(league_id, conn):
    """
    Pobiera listę dywizji dla danej ligi.
    
    Args:
        league_id (int): ID ligi
        conn: Połączenie z bazą danych
        
    Returns:
        dict: Słownik {id_dywizji: nazwa_dywizji}
    """
    cursor = conn.cursor()
    query = "SELECT id, name FROM divisions WHERE league_id = %s"
    cursor.execute(query, [league_id])
    divisions = {division_id: name for division_id, name in cursor.fetchall()}
    cursor.close()
    return divisions

def get_conferences(league_id, conn):
    """
    Pobiera listę konferencji dla danej ligi.
    
    Args:
        league_id (int): ID ligi
        conn: Połączenie z bazą danych
        
    Returns:
        dict: Słownik {id_konferencji: nazwa_konferencji}
    """
    cursor = conn.cursor()
    query = "SELECT id, name FROM conferences WHERE league_id = %s"
    cursor.execute(query, [league_id])
    conferences = {conf_id: name for conf_id, name in cursor.fetchall()}
    cursor.close()
    return conferences

def get_teams(league_id, season_id, conn):
    """
    Pobiera listę drużyn dla danej ligi i sezonu.
    
    Args:
        league_id (int): ID ligi
        season_id (int): ID sezonu
        conn: Połączenie z bazą danych
        
    Returns:
        dict: Słownik {id_drużyny: nazwa_drużyny}
    """
    cursor = conn.cursor()
    query = """
        SELECT DISTINCT t.id, t.name 
        FROM teams t 
        JOIN matches m ON (t.id = m.home_team OR t.id = m.away_team)
        WHERE m.league = %s AND m.season = %s AND m.sport_id = 3
        ORDER BY t.name
    """
    cursor.execute(query, [league_id, season_id])
    teams = {team_id: name for team_id, name in cursor.fetchall()}
    cursor.close()
    return teams

def league_table(matches_df, team_ids, win_value, draw_value, loss_value, ot_loss_value, scope):
    """
    Tworzy tabelę ligową dla koszykówki.
    
    Args:
        matches_df (pd.DataFrame): DataFrame z meczami
        team_ids (dict): Słownik drużyn do wypełnienia statystykami
        win_value (int): Punkty za wygraną
        draw_value (int): Punkty za remis (nie używane w koszykówce)
        loss_value (int): Punkty za przegraną
        ot_loss_value (int): Punkty za przegraną po dogrywce
        scope (str): Zakres meczów ('all', 'home', 'away')
    """
    
    for _, match in matches_df.iterrows():
        home_team_id = match['home_team_id']
        away_team_id = match['away_team_id']
        
        # Filtrowanie według scope
        if scope == 'home':
            # Tylko mecze u siebie dla drużyn
            if home_team_id in team_ids:
                process_team_match(team_ids, home_team_id, match, True, win_value, loss_value, ot_loss_value)
        elif scope == 'away':
            # Tylko mecze na wyjeździe dla drużyn
            if away_team_id in team_ids:
                process_team_match(team_ids, away_team_id, match, False, win_value, loss_value, ot_loss_value)
        else:  # scope == 'all'
            # Wszystkie mecze
            if home_team_id in team_ids:
                process_team_match(team_ids, home_team_id, match, True, win_value, loss_value, ot_loss_value)
            if away_team_id in team_ids:
                process_team_match(team_ids, away_team_id, match, False, win_value, loss_value, ot_loss_value)

def process_team_match(team_ids, team_id, match, is_home, win_value, loss_value, ot_loss_value):
    """
    Przetwarza pojedynczy mecz dla drużyny w kontekście tabeli.
    
    Args:
        team_ids (dict): Słownik statystyk drużyn
        team_id (int): ID drużyny
        match: Dane meczu
        is_home (bool): Czy drużyna grała u siebie
        win_value (int): Punkty za wygraną
        loss_value (int): Punkty za przegraną
        ot_loss_value (int): Punkty za przegraną po dogrywce
    """
    # Pozycje w liście: [mecze, wygrane, remisy, przegrane, punkty_zdobyte, punkty_stracone, różnica, punkty, wygrane_po_dogrywce, przegrane_po_dogrywce]
    team_stats = team_ids[team_id]
    
    # Zwiększ licznik meczów
    team_stats[0] += 1
    
    # Określ punkty drużyny i przeciwnika
    if is_home:
        team_points = match['home_goals']
        opponent_points = match['away_goals']
    else:
        team_points = match['away_goals']
        opponent_points = match['home_goals']
    
    # Dodaj punkty zdobyte i stracone
    team_stats[4] += team_points
    team_stats[5] += opponent_points
    team_stats[6] = team_stats[4] - team_stats[5]  # różnica punktów
    
    # Określ wynik meczu
    if team_points > opponent_points:
        # Wygrana
        team_stats[1] += 1
        team_stats[7] += win_value
        
        # Sprawdź czy była dogrywka
        if hasattr(match, 'ot') and match['ot'] == 1:
            team_stats[8] += 1  # wygrana po dogrywce
    else:
        # Przegrana
        team_stats[3] += 1
        
        # Sprawdź czy była dogrywka
        if hasattr(match, 'ot') and match['ot'] == 1:
            team_stats[9] += 1  # przegrana po dogrywce
            team_stats[7] += ot_loss_value
        else:
            team_stats[7] += loss_value