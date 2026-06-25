import streamlit as st
import pandas as pd
import db_module

def match_predictions(match_id):
    """
    Wyświetla predykcje dla wybranego meczu koszykarskiego.
    
    Args:
        match_id (int): ID meczu
    """
    st.subheader("Predykcje dla meczu")
    st.write(f"Predykcje dla meczu ID: {match_id}")
    # TODO: Implementacja predykcji po utworzeniu odpowiednich modeli

def match_lineups(match_id, home_team, home_team_id, away_team, away_team_id, conn):
    """
    Wyświetla składy drużyn dla wybranego meczu.
    
    Args:
        match_id (int): ID meczu
        home_team (str): Nazwa drużyny gospodarzy
        home_team_id (int): ID drużyny gospodarzy
        away_team (str): Nazwa drużyny gości
        away_team_id (int): ID drużyny gości
        conn: Połączenie z bazą danych
    """
    st.subheader(f"Składy meczu {home_team} vs {away_team}")
    
    # Pobieranie składów z bazy danych
    lineup_query = """
        SELECT bmr.team_id, t.name as team_name, p.common_name as player_name, 
               bmr.number, bmr.starter
        FROM basketball_match_roster bmr
        JOIN players p ON bmr.player_id = p.id
        JOIN teams t ON bmr.team_id = t.id
        WHERE bmr.match_id = %s
        ORDER BY bmr.team_id, bmr.starter DESC, bmr.number
    """
    
    lineup_df = pd.read_sql(lineup_query, conn, params=[match_id])
    
    if not lineup_df.empty:
        # Legenda dla starterów
        st.info("⭐ - zawodnik podstawowy (starter)")
        
        col1, col2 = st.columns(2)
        
        # Składy drużyny gospodarzy
        with col1:
            st.write(f"**{home_team}**")
            home_lineup = lineup_df[lineup_df['team_id'] == home_team_id]
            if not home_lineup.empty:
                for _, player in home_lineup.iterrows():
                    starter_icon = "⭐" if player['starter'] == 1 else ""
                    st.write(f"{starter_icon} #{player['number']} {player['player_name']}")
            else:
                st.write("Brak danych o składzie")
        
        # Składy drużyny gości
        with col2:
            st.write(f"**{away_team}**")
            away_lineup = lineup_df[lineup_df['team_id'] == away_team_id]
            if not away_lineup.empty:
                for _, player in away_lineup.iterrows():
                    starter_icon = "⭐" if player['starter'] == 1 else ""
                    st.write(f"{starter_icon} #{player['number']} {player['player_name']}")
            else:
                st.write("Brak danych o składzie")
    else:
        st.write("Brak danych o składach dla tego meczu")

def match_stats(row):
    """
    Wyświetla statystyki pomeczowe dla wybranego meczu koszykarskiego w formie kart z dynamicznym kolorowaniem.
    
    Args:
        row: Wiersz z danymi meczu
    """
    st.subheader("Statystyki pomeczowe")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    match_row_dict = row.to_dict()

    # Stylizacja HTML dla kart z danymi
    card_style = """
    <div style="
        background-color: {bg_color};
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
    ">
        <div style="font-size: 24px; font-weight: bold; color: #333;">{value}</div>
        <div style="font-size: 16px; color: #777;">{label}</div>
    </div>
    """
    
    with col1:
        if 'home_team' in match_row_dict:
            st.markdown(f"### {match_row_dict['home_team']}")
        else:
            st.markdown("### Gospodarze")
    with col3:
        if 'away_team' in match_row_dict:
            st.markdown(f"### {match_row_dict['away_team']}")
        else:
            st.markdown("### Goście")
    
    # Statystyki koszykarskie do wyświetlenia
    stats_to_display = [
        ('goals', 'Punkty'),
        ('field_goals_made', 'Rzuty z gry trafione'),
        ('field_goals_attempts', 'Rzuty z gry oddane'),
        ('field_goals_acc', 'Skuteczność FG (%)'),
        ('3_p_field_goals_made', 'Rzuty za 3 pkt trafione'),
        ('3_p_field_goals_attempts', 'Rzuty za 3 pkt oddane'),
        ('3_p_acc', 'Skuteczność 3P (%)'),
        ('ft_made', 'Rzuty wolne trafione'),
        ('ft_attempts', 'Rzuty wolne oddane'),
        ('ft_acc', 'Skuteczność FT (%)'),
        ('rebounds_total', 'Zbiórki łącznie'),
        ('assists', 'Asysty'),
        ('steals', 'Przechwyty'),
        ('turnovers', 'Straty'),
        ('blocks', 'Bloki')
    ]
    
    # Statystyki gdzie mniejsza wartość jest lepsza
    reverse_stats = ['turnovers']

    for stat_key, stat_label in stats_to_display:
        home_key = f'home_team_{stat_key}'
        away_key = f'away_team_{stat_key}'
        home_raw_value = match_row_dict.get(home_key, None)
        away_raw_value = match_row_dict.get(away_key, None)
        home_value = home_raw_value
        away_value = away_raw_value
        
        # Specjalne formatowanie dla niektórych statystyk
        if home_value is not None and home_value != -1:
            if 'acc' in stat_key and home_value != 0:
                home_value = f"{float(home_value):.1f}%" if home_value != -1 else "Brak danych"
            else:
                home_value = str(home_value) if home_value != -1 else "Brak danych"
        else:
            home_value = "Brak danych"
            
        if away_value is not None and away_value != -1:
            if 'acc' in stat_key and away_value != 0:
                away_value = f"{float(away_value):.1f}%" if away_value != -1 else "Brak danych"
            else:
                away_value = str(away_value) if away_value != -1 else "Brak danych"
        else:
            away_value = "Brak danych"
        
        # Domyślne kolory
        home_bg_color = "#f0f0f0"
        away_bg_color = "#f0f0f0"
        
        # Porównaj wartości tylko jeśli obie są liczbami (nie "Brak danych")
        if (home_raw_value is not None and home_raw_value != -1 and
            away_raw_value is not None and away_raw_value != -1):
            home_numeric = float(home_raw_value) if home_raw_value != 0 else 0
            away_numeric = float(away_raw_value) if away_raw_value != 0 else 0
            is_reverse = stat_key in reverse_stats
            
            if home_numeric > away_numeric:
                if is_reverse:
                    home_bg_color = "#f8d7da"  # czerwony dla gorszego
                    away_bg_color = "#d4edda"  # zielony dla lepszego
                else:
                    home_bg_color = "#d4edda"  # zielony dla lepszego
                    away_bg_color = "#f8d7da"  # czerwony dla gorszego
            elif away_numeric > home_numeric:
                if is_reverse:
                    home_bg_color = "#d4edda"  # zielony dla lepszego
                    away_bg_color = "#f8d7da"  # czerwony dla gorszego
                else:
                    home_bg_color = "#f8d7da"  # czerwony dla gorszego
                    away_bg_color = "#d4edda"  # zielony dla lepszego
        
        with col1:
            col1.markdown(
                card_style.format(
                    value=home_value,
                    label=stat_label,
                    bg_color=home_bg_color
                ),
                unsafe_allow_html=True
            )
        
        # col2 pozostaje pusta dla oddzielenia
        with col3:
            col3.markdown(
                card_style.format(
                    value=away_value,
                    label=stat_label,
                    bg_color=away_bg_color
                ),
                unsafe_allow_html=True
            )

def match_boxscore(match_id, conn):
    """
    Wyświetla boxscore meczu - statystyki wszystkich zawodników.
    
    Args:
        match_id (int): ID meczu
        conn: Połączenie z bazą danych
    """
    st.subheader("Boxscore - statystyki zawodników")
    
    # Pobieranie statystyk zawodników
    boxscore_query = """
        SELECT bmps.team_id, t.name as team_name, p.common_name as player_name,
               bmps.points, bmps.rebounds, bmps.assists, bmps.time_played,
               bmps.field_goals_made, bmps.field_goals_attempts,
               bmps.3_p_field_goals_made as three_p_made, bmps.3_p_field_goals_attempts as three_p_attempts,
               bmps.ft_made, bmps.ft_attempts, bmps.plus_minus,
               bmps.off_rebounds, bmps.def_rebounds, bmps.personal_fouls,
               bmps.steals, bmps.turnovers, bmps.blocked_shots
        FROM basketball_match_player_stats bmps
        JOIN players p ON bmps.player_id = p.id
        JOIN teams t ON bmps.team_id = t.id
        WHERE bmps.match_id = %s
        ORDER BY bmps.team_id, bmps.points DESC
    """
    
    boxscore_df = pd.read_sql(boxscore_query, conn, params=[match_id])
    
    if not boxscore_df.empty:
        
        # Grupowanie po drużynach
        teams = boxscore_df['team_name'].unique()
        
        for team in teams:
            st.write(f"**{team}**")
            team_stats = boxscore_df[boxscore_df['team_name'] == team]
            
            # Wybieranie najważniejszych kolumn do wyświetlenia
            display_cols = ['player_name', 'points', 'rebounds', 'assists', 'time_played',
                          'field_goals_made', 'field_goals_attempts', 'three_p_made', 
                          'three_p_attempts', 'plus_minus']
            
            team_display = team_stats[display_cols].copy()
            team_display.columns = ['Zawodnik', 'Punkty', 'Zbiórki', 'Asysty', 'Czas gry',
                                  'FG', 'FGA', '3P', '3PA', '+/-']
            
            st.dataframe(team_display, use_container_width=True, hide_index=True)
            st.write("")
        
                # Legenda dla skrótów w boxscore
        st.info("""**Legenda:**  
FG - rzuty z gry trafione  
FGA - rzuty z gry oddane  
3P - rzuty za 3 pkt trafione  
3PA - rzuty za 3 pkt oddane  
+/- - bilans drużyny gdy zawodnik był na boisku""")
    else:
        st.write("Brak danych boxscore dla tego meczu")

def match_dev_info(row, league, season):
    """
    Wyświetla informacje deweloperskie o meczu.
    
    Args:
        row: Wiersz z danymi meczu
        league (int): ID ligi
        season (int): ID sezonu
    """
    st.subheader("Informacje deweloperskie")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**ID meczu:** {row.id}")
        st.write(f"**Liga:** {league}")
        st.write(f"**Sezon:** {season}")
        st.write(f"**Data meczu:** {row.game_date}")
    
    with col2:
        st.write(f"**ID drużyny gospodarzy:** {row.home_team_id}")
        st.write(f"**ID drużyny gości:** {row.away_team_id}")
        st.write(f"**Rezultat:** {row.result}")
        st.write(f"**Sport ID:** 3 (koszykówka)")

def get_team_info(team_id, lookback_games, matches_df):
    """
    Pobiera informacje o ostatnich meczach drużyny.
    
    Args:
        team_id (int): ID drużyny
        lookback_games (int): Liczba ostatnich meczów do analizy
        matches_df (pd.DataFrame): DataFrame z meczami
        
    Returns:
        list: Lista słowników z informacjami o meczach
    """
    team_matches = matches_df[
        (matches_df['home_team_id'] == team_id) | 
        (matches_df['away_team_id'] == team_id)
    ].head(lookback_games)
    
    if team_matches.empty:
        return []  # Brak meczów dla zadanego przedziału dla wskazanej drużyny
    
    team_info = []
    for _, match in team_matches.iterrows():
        is_home = match['home_team_id'] == team_id
        
        match_info = {
            'match_id': match['id'],
            'match_date': match['game_date'],
            'home_team': match['home_team'],
            'away_team': match['away_team'],
            'home_team_goals': match['home_goals'],
            'away_team_goals': match['away_goals'],
            'team_goals': match['home_goals'] if is_home else match['away_goals'],
            'opponent_goals': match['away_goals'] if is_home else match['home_goals'],
            'opponent_shortcut': match['away_team_shortcut'] if is_home else match['home_team_shortcut'],
            'result': match['result']
        }
        
        team_info.append(match_info)
    
    return team_info

def get_team_players_stats(team_id, season_id, conn):
    """
    Pobiera statystyki zawodników drużyny w danym sezonie.
    
    Args:
        team_id (int): ID drużyny
        season_id (int): ID sezonu
        conn: Połączenie z bazą danych
        
    Returns:
        pd.DataFrame: DataFrame ze statystykami zawodników
    """
    player_stats_query = """
        SELECT p.common_name as 'Zawodnik',
               COUNT(bmps.match_id) as 'Mecze',
               ROUND(AVG(bmps.points), 1) as 'Punkty',
               ROUND(AVG(bmps.rebounds), 1) as 'Zbiórki',
               ROUND(AVG(bmps.assists), 1) as 'Asysty',
               ROUND(AVG(CAST(bmps.field_goals_made AS FLOAT) / NULLIF(bmps.field_goals_attempts, 0) * 100), 1) as 'FG%',
               ROUND(AVG(CAST(bmps.3_p_field_goals_made AS FLOAT) / NULLIF(bmps.3_p_field_goals_attempts, 0) * 100), 1) as '3P%',
               ROUND(AVG(CAST(bmps.ft_made AS FLOAT) / NULLIF(bmps.ft_attempts, 0) * 100), 1) as 'FT%',
               ROUND(AVG(bmps.steals), 1) as 'Przechwyty',
               ROUND(AVG(bmps.turnovers), 1) as 'Straty'
        FROM basketball_match_player_stats bmps
        JOIN players p ON bmps.player_id = p.id
        JOIN matches m ON bmps.match_id = m.id
        WHERE bmps.team_id = %s AND m.season = %s
        GROUP BY p.id, p.common_name
        ORDER BY AVG(bmps.points) DESC
    """
    
    return pd.read_sql(player_stats_query, conn, params=[team_id, season_id])