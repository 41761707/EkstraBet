import pandas as pd

def get_divisions(league, conn):
    """
    Pobiera listę dywizji dla danej ligi z cachowaniem.
    Args:
        league (int): ID ligi
        conn: Połączenie z bazą danych
    Returns:
        dict: Słownik {id_dywizji: nazwa_dywizji}
    """
    divisions_query = f'''
        select distinct d.id, d.name 
            from divisions d
            where d.league_id = {league}
            order by d.name'''
    divisions_df = pd.read_sql(divisions_query, conn)
    divisions_dict = divisions_df.set_index('id')['name'].to_dict()
    return divisions_dict

def get_conferences(league, conn):
    """
    Pobiera listę konferencji dla danej ligi z cachowaniem.
    Args:
        league (int): ID ligi
        conn: Połączenie z bazą danych
    Returns:
        dict: Słownik {id_konferencji: nazwa_konferencji}
    """
    conferences_query = f'''
        select distinct c.id, c.name 
            from conferences c
            where c.league_id = {league}
            order by c.name'''
    conferences_df = pd.read_sql(conferences_query, conn)
    conferences_dict = conferences_df.set_index('id')['name'].to_dict()
    return conferences_dict

def get_teams(league, season, conn):
    """
    Pobiera listę drużyn dla danej ligi i sezonu z cachowaniem.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
    Returns:
        dict: Słownik {id_drużyny: nazwa_drużyny}
    """
    all_teams = '''
        select distinct t.id, t.name 
            from matches m
            join teams t on (m.home_team = t.id or m.away_team = t.id) 
            where m.league = {} and m.season = {} 
            order by t.name'''.format(league, season)
    all_teams_df = pd.read_sql(all_teams, conn)
    teams_dict = all_teams_df.set_index('id')['name'].to_dict()
    return teams_dict


def league_table(matches, team_ids, winner_gain, draw_gain, ot_gain_winner, ot_gain_loser, scope='all'):
    '''Generowanie tabeli ligowej na podstawie meczów i drużyn
    Args:
        matches (pd.DataFrame): DataFrame z danymi meczów
        team_ids (dict): Słownik z danymi drużyn
        winner_gain (int): Punkty za wygraną
        draw_gain (int): Punkty za remis
        ot_gain_winner (int): Punkty za wygraną w OT/SO
        ot_gain_loser (int): Punkty za przegraną w OT/SO
        scope (str): Zakres meczów do uwzględnienia ('all', 'home', 'away')
    '''
    # team_ids zawiera słownik drużyn, w którym każda drużyna zawiera listę
    # [liczba meczów, wygrane, remisy (dla hokeja tez robimy), przegrane, bramki zdobyte, bramki stracone, różnica bramek, punkty
    # + w hokeju liczba wygranych po OT/SO, liczba przegranych po OT/SO]
    # scope: 'all' - wszystkie mecze, 'home' - tylko domowe, 'away' - tylko wyjazdowe
    
    for _, row in matches.iterrows():
        home_team_id = row['home_team_id']
        away_team_id = row['away_team_id']
        home_goals = row['home_goals']
        away_goals = row['away_goals']
        overtime_winner = row['OTwinner']
        shootout_winner = row['SOwinner']

        # Sprawdzamy zakres meczów do uwzględnienia
        process_home = (scope == 'all' or scope == 'home')
        process_away = (scope == 'all' or scope == 'away')

        # Aktualizacja meczów rozegranych
        if process_home:
            team_ids[home_team_id][0] += 1
        if process_away:
            team_ids[away_team_id][0] += 1

        # Aktualizacja bramek zdobytych i straconych
        if process_home:
            team_ids[home_team_id][4] += home_goals
            team_ids[home_team_id][5] += away_goals
        if process_away:
            team_ids[away_team_id][4] += away_goals
            team_ids[away_team_id][5] += home_goals

        # Określenie wyniku meczu
        if home_goals > away_goals:
            if process_home:
                team_ids[home_team_id][1] += 1  # Home team wins
                team_ids[home_team_id][7] += winner_gain
            if process_away:
                team_ids[away_team_id][3] += 1  # Away team loses
        elif home_goals < away_goals:
            if process_home:
                team_ids[home_team_id][3] += 1  # Home team loses
            if process_away:
                team_ids[away_team_id][1] += 1  # Away team wins
                team_ids[away_team_id][7] += winner_gain
        else:
            if process_home:
                team_ids[home_team_id][2] += 1  # Draw
                team_ids[home_team_id][7] += draw_gain
            if process_away:
                team_ids[away_team_id][2] += 1  # Draw
                team_ids[away_team_id][7] += draw_gain
            
            if overtime_winner == 1 or shootout_winner == 1:
                if process_home:
                    team_ids[home_team_id][8] += 1  # OT/SO win
                    team_ids[home_team_id][7] += ot_gain_winner
                    team_ids[home_team_id][4] += 1  # Extra goal for OT/SO win
                if process_away:
                    team_ids[away_team_id][9] += 1  # OT/SO loss
                    team_ids[away_team_id][7] += ot_gain_loser
                    team_ids[away_team_id][5] += 1  # Extra goal for OT/SO loss
            elif overtime_winner == 2 or shootout_winner == 2:
                if process_home:
                    team_ids[home_team_id][9] += 1
                    team_ids[home_team_id][7] += ot_gain_loser
                    team_ids[home_team_id][5] += 1  # Extra goal for OT/SO loss
                if process_away:
                    team_ids[away_team_id][8] += 1
                    team_ids[away_team_id][7] += ot_gain_winner
                    team_ids[away_team_id][4] += 1  # Extra goal for OT/SO win
        
        # Aktualizacja różnicy bramek
        if process_home:
            team_ids[home_team_id][6] = team_ids[home_team_id][4] - team_ids[home_team_id][5]
        if process_away:
            team_ids[away_team_id][6] = team_ids[away_team_id][4] - team_ids[away_team_id][5]