import streamlit as st
import hockey_rink
import pandas as pd
import graphs_module

def match_predictions(match_id):
    st.write("Tutaj będą predykcje meczowe")

def get_match_lineups_data(match_id, conn):
    """
    Pobiera dane o składach meczowych z cachowaniem.
    
    Args:
        match_id (int): ID meczu
        conn: Połączenie z bazą danych
        
    Returns:
        pd.DataFrame: DataFrame z danymi składów
    """
    lineup_query = f'''SELECT 
        t.id AS Drużyna, 
        p.common_name AS Zawodnik, 
        line.position AS Pozycja, 
        line.number AS Numer, 
        line.line AS Linia
    FROM hockey_match_rosters line
    JOIN players p ON line.player_id = p.id
    JOIN matches m ON m.id = line.match_id
    JOIN teams t ON t.id = line.team_id
    WHERE m.id = {match_id}'''
    
    return pd.read_sql(lineup_query, conn)

def match_lineups(match_id, home_team, home_team_id, away_team, away_team_id, conn):
    """
    Wyświetla składy obu drużyn biorących udział w meczu hokeja w formie tabeli i wizualizacji na lodowisku.

    Pobiera dane o składach meczowych z bazy danych, a następnie prezentuje je w dwóch kolumnach — 
    jedna dla gospodarzy, druga dla gości — z podziałem na linie (pierwsza, druga, trzecia, czwarta). 
    Do każdej linii wyświetlana jest tabela z zawodnikami oraz wizualizacja rozmieszczenia na lodowisku.

    Args:
        match_id (int): ID meczu, dla którego mają zostać pobrane składy.
        home_team (str): Nazwa drużyny gospodarzy.
        home_team_id (int): ID drużyny gospodarzy.
        away_team (str): Nazwa drużyny gości.
        away_team_id (int): ID drużyny gości.
        conn (MySQLConnection): Połączenie do bazy danych  MySQL zawierającej informacje o składach.

    Returns:
        None: Funkcja nie zwraca żadnej wartości, ale renderuje dane w interfejsie Streamlit.
    """
    lineup_pd = get_match_lineups_data(match_id, conn)
    
    def display_lineup(team_name, team_id, column):
        with column:
            tabs = st.tabs([f"{i} linia" for i in ["Pierwsza", "Druga", "Trzecia", "Czwarta"]])
            for i, tab in enumerate(tabs, start=1):
                with tab:
                    st.subheader(team_name)
                    lineup = lineup_pd[
                        (lineup_pd['Drużyna'] == team_id) & (lineup_pd['Linia'] == i)
                    ].drop(columns=['Linia', 'Drużyna'])
                    st.dataframe(lineup, hide_index=True)
                    st.plotly_chart(hockey_rink.draw_hockey_rink(lineup, team_name.replace(" ", "_")))
    
    col1, col2 = st.columns(2)
    display_lineup(home_team, home_team_id, col1)
    display_lineup(away_team, away_team_id, col2)

def get_match_events_data(match_id, conn):
    """
    Pobiera dane o zdarzeniach meczowych z cachowaniem.
    
    Args:
        match_id (int): ID meczu
        conn: Połączenie z bazą danych
        
    Returns:
        pd.DataFrame: DataFrame ze zdarzeniami meczowymi
    """
    events_query = f'''select 
        t.name as Druzyna, p.common_name as Zawodnik, e.name as Zdarzenie, hme.period as Tercja, hme.event_time as Czas, hme.description as Opis
            from hockey_match_events hme 
            join players p on hme.player_id = p.id
            join events e on e.id = hme.event_id
            join matches m on m.id = hme.match_id
            join teams t on t.id = hme.team_id
            where m.id = {match_id}
            order by m.id, hme.period, hme.event_time
    '''
    return pd.read_sql(events_query, conn)

def match_events(match_id, home_team, conn):
    """
    Wyświetla zdarzenia z meczu hokejowego w podziale na tercje, dogrywkę i rzuty karne.

    Funkcja pobiera z bazy danych listę zdarzeń meczowych (np. gole, kary, asysty) 
    i prezentuje je w interfejsie Streamlit w podziale na kolumny dla drużyny gospodarzy i gości.
    Dla każdej tercji (1–3), dogrywki (4) i rzutów karnych (5) tworzy osobną sekcję z odpowiednimi nagłówkami.

    Args:
        match_id (int): ID meczu, dla którego mają zostać pobrane zdarzenia.
        home_team (str): Nazwa drużyny gospodarzy (używana do określenia strony tabeli).
        conn (mysql.connector.connection.MySQLConnection): Połączenie do bazy danych zawierającej dane o zdarzeniach.

    Returns:
        None: Funkcja nie zwraca żadnej wartości — dane są wyświetlane bezpośrednio w Streamlit.
    """
    
    events_pd = get_match_events_data(match_id, conn)
    for i in range(1, 6):
        events_pd_i = events_pd[events_pd['Tercja'] == i].drop(columns=['Tercja'])
        if len(events_pd_i) > 0:
            if i == 4:
                st.markdown("<h2 style='text-align: center;'>Dogrywka</h2>", unsafe_allow_html=True)
            elif i == 5:
                st.markdown("<h2 style='text-align: center;'>Rzuty karne</h2>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h2 style='text-align: center;'>Tercja {i}</h2>", unsafe_allow_html=True)
            home_team_col, away_team_col = st.columns(2)    
            for _, row in events_pd_i.iterrows():
                if row['Druzyna'] == home_team:
                    generate_event_entry(row, home_team_col, is_empty=False)
                    generate_event_entry(None, away_team_col, is_empty=True)
                else:
                    generate_event_entry(None, home_team_col, is_empty=True)
                    generate_event_entry(row, away_team_col, is_empty=False)

def generate_event_entry(event_row, team_col, is_empty):
    """
    Wyświetla pojedyncze zdarzenie meczowe w formie estetycznego kafelka lub wstawia puste miejsce, jeśli brak zdarzenia.

    Funkcja generuje kafelek HTML zawierający informacje o czasie zdarzenia, jego typie, 
    zawodniku oraz krótkim opisie. W przypadku pustego wpisu (np. brak zdarzenia dla jednej z drużyn w danej linii), 
    wstawia pusty blok o określonej wysokości, aby zachować symetrię układu w Streamlit.

    Args:
        event_row (pd.Series | None): Wiersz z informacjami o zdarzeniu
        team_col (streamlit.DeltaGenerator): Kolumna Streamlit, w której zostanie wyrenderowany wpis (po lewej lub prawej stronie).
        is_empty (bool): Czy zdarzenie jest puste (czyli brak zdarzenia dla jednej ze stron w danym momencie meczu).

    Returns:
        None: Funkcja renderuje dane bezpośrednio w interfejsie Streamlit.
    """

    if is_empty:
        team_col.write("<div style='height: 120px;'></div>", unsafe_allow_html=True)
    else:
        team_col.markdown(
            f"""
            <div style="
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                text-align: center;
            ">
                <h4 style="margin: 0; color: #333;">{event_row['Czas']} ({event_row['Zdarzenie']})</h4>
                <p style="margin: 5px 0; color: #555;">{event_row['Zawodnik']} ({event_row['Opis']})</p>
            </div>
            """,
            unsafe_allow_html=True
        )

def match_stats(match_row):
    """
    Wyświetla statystyki meczowe obu drużyn w postaci kart z danymi w Streamlit z dynamicznym kolorowaniem.

    Funkcja przekształca wiersz DataFrame (zawierający statystyki meczowe) do słownika i renderuje dane
    dla drużyny gospodarzy i gości w dwóch osobnych kolumnach interfejsu Streamlit. Każda statystyka
    prezentowana jest w formie estetycznej karty z kolorowaniem na podstawie porównania wartości
    (zielony dla lepszej, czerwony dla gorszej, szary dla równych wartości).

    Statystyki obejmują m.in. bramki, strzały na bramkę, skuteczność w przewagach, liczbę kar,
    uderzeń, wznowień i inne wskaźniki związane z przebiegiem meczu hokejowego.

    Args:
        match_row (pd.Series): Wiersz zawierający dane statystyczne meczu, w którym klucze mają prefiksy 
            `home_` lub `away_` dla odpowiednich drużyn oraz odpowiadają polom mapowanym w `stat_name`.

    Returns:
        None: Funkcja renderuje dane bezpośrednio w interfejsie Streamlit.
    """

    col1, col2, col3 = st.columns([2, 1, 2])
    match_row_dict = match_row.to_dict()

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
    
    stats_to_display = [
        ('goals', 'Bramki'),
        ('team_sog', 'Strzały na bramkę'),
        ('team_fk', 'Minuty kar'),
        ('team_fouls', 'Liczba kar'),
        ('team_pp_goals', 'Bramki w przewadze (PP)'),
        ('team_sh_goals', 'Bramki w osłabieniu (SH)'),
        ('team_shots_acc', 'Skuteczność strzałów (%)'),
        ('team_saves', 'Liczba obron'),
        ('team_saves_acc', 'Skuteczność obron (%)'),
        ('team_pp_acc', 'Skuteczność w przewadze (%)'),
        ('team_pk_acc', 'Skuteczność w osłabieniu (%)'),
        ('team_faceoffs', 'Wygrane wznowienia'),
        ('team_faceoffs_acc', 'Skuteczność wznowień (%)'),
        ('team_hits', 'Liczba uderzeń'),
        ('team_to', 'Liczba strat'),
        ('team_en', 'Bramki na pustą bramkę')
    ]
    reverse_stats = ['team_fk', 'team_fouls', 'team_to']

    for stat_key, stat_label in stats_to_display:
        home_key = f'home_{stat_key}'
        away_key = f'away_{stat_key}'
        home_raw_value = match_row_dict.get(home_key, None)
        away_raw_value = match_row_dict.get(away_key, None)
        home_value = home_raw_value
        away_value = away_raw_value
        
        # Specjalne formatowanie dla niektórych statystyk
        if home_value is not None and home_value != -1:
            if 'acc' in stat_key and home_value != 0:
                home_value = f"{float(home_value):.2f}%" if home_value != -1 else "Brak danych"
            elif stat_key == 'team_fk':
                home_value = f"{home_value} min" if home_value != -1 else "Brak danych"
            else:
                home_value = str(home_value) if home_value != -1 else "Brak danych"
        else:
            home_value = "Brak danych"
            
        if away_value is not None and away_value != -1:
            if 'acc' in stat_key and away_value != 0:
                away_value = f"{float(away_value):.2f}%" if away_value != -1 else "Brak danych"
            elif stat_key == 'team_fk':
                away_value = f"{away_value} min" if away_value != -1 else "Brak danych"
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
                    home_bg_color = "#f8d7da" 
                    away_bg_color = "#d4edda" 
                else:
                    home_bg_color = "#d4edda"
                    away_bg_color = "#f8d7da" 
            elif away_numeric > home_numeric:
                if is_reverse:
                    home_bg_color = "#d4edda"
                    away_bg_color = "#f8d7da"
                else:
                    home_bg_color = "#f8d7da"
                    away_bg_color = "#d4edda"
        with col1:
            col1.markdown(
                card_style.format(
                    value=home_value,
                    label=stat_label,
                    bg_color=home_bg_color
                ),
                unsafe_allow_html=True
            )
        # Brak col2 - pusta kolumna do oddzielenia
        with col3:
            col3.markdown(
                card_style.format(
                    value=away_value,
                    label=stat_label,
                    bg_color=away_bg_color
                ),
                unsafe_allow_html=True
            )

def get_match_boxscore_goalies_data(match_id, conn):
    """
    Pobiera statystyki bramkarzy z meczu z cachowaniem.
    
    Args:
        match_id (int): ID meczu
        conn: Połączenie z bazą danych
        
    Returns:
        pd.DataFrame: DataFrame ze statystykami bramkarzy
    """
    boxscore_goaltenders = f'''select 
            t.name as Drużyna, p.common_name as Zawodnik, box.points as Punkty, box.penalty_minutes as "Kary(MIN)", box.toi as TOI, 
            box.shots_against as Strzały, box.shots_saved as Obronione, box.saves_acc as "Skuteczność Obron(%)"
        from hockey_match_player_stats box 
        join players p on box.player_id = p.id
        join matches m on m.id = box.match_id
        join teams t on t.id = box.team_id
        where m.id = {match_id} and p.position = 'G' ''' 
    return pd.read_sql(boxscore_goaltenders, conn)
 
def get_match_boxscore_players_data(match_id, conn):
    """
    Pobiera statystyki zawodników z pola z meczu z cachowaniem.
    
    Args:
        match_id (int): ID meczu
        conn: Połączenie z bazą danych
        
    Returns:
        pd.DataFrame: DataFrame ze statystykami zawodników z pola
    """
    boxscore_others = f'''select 
            t.name as Drużyna, p.common_name as Zawodnik, box.goals as Bramki, box.assists as Asysty, box.points as Punkty, box.plus_minus as "+/-",
            box.penalty_minutes as "Kary(MIN)", box.sog as SOG, box.toi as TOI
        from hockey_match_player_stats box 
        join players p on box.player_id = p.id
        join matches m on m.id = box.match_id
        join teams t on t.id = box.team_id
        where m.id = {match_id} and p.position <> 'G' ''' 
    return pd.read_sql(boxscore_others, conn)

def match_boxscore(match_id, conn):
    """
    Wyświetla statystyki meczowe zawodników w formacie boxscore.

    Funkcja pobiera z bazy danych statystyki zawodników z meczu o podanym `match_id`.
    Dla bramkarzy prezentowane są takie dane jak liczba punktów, minuty kar, czas gry, liczba strzałów i skuteczność obron.
    Dla zawodników pola prezentowane są m.in. bramki, asysty, punkty, plus/minus, SOG (strzały na bramkę), minuty kar i czas gry.
    Wartości plus/minus są dodatkowo stylizowane kolorem za pomocą `highlight_cells_plus_minus`.

    Dane wyświetlane są w postaci tabel Streamlit.

    Args:
        match_id (int): Identyfikator meczu, dla którego mają zostać pobrane statystyki.
        conn (mysql.connector.connection_cext.CMySQLConnection): Połączenie z bazą danych MySQL.

    Returns:
        None: Funkcja renderuje dane bezpośrednio w interfejsie Streamlit.
    """
        
    st.subheader("Bramkarze")
    boxscore_goaltenders_pd = get_match_boxscore_goalies_data(match_id, conn)
    boxscore_goaltenders_pd.index = range(1, len(boxscore_goaltenders_pd) + 1)
    boxscore_goaltenders_pd['Skuteczność Obron(%)'] = boxscore_goaltenders_pd['Skuteczność Obron(%)'].apply(lambda x: f"{x:.2f}")
    st.table(boxscore_goaltenders_pd)
    st.subheader("Zawodnicy")
    boxscore_pd = get_match_boxscore_players_data(match_id, conn)
    boxscore_pd.index = range(1, len(boxscore_pd) + 1)
    players_styled = boxscore_pd.style.applymap(graphs_module.highlight_cells_plus_minus, subset = ["+/-"])
    st.table(players_styled)

def get_team_info(team_id, lookback, matches_df):
    """
    Przetwarza dane meczowe dla wybranej drużyny z cachowaniem.
    
    Args:
        team_id (int): ID drużyny
        lookback (int): Liczba ostatnich meczów do analizy
        matches_df (pd.DataFrame): DataFrame zawierający wszystkie mecze
    
    Returns:
        list: Lista słowników z przetworzonymi danymi meczowymi
    """
    # Filtrowanie meczów dla wybranej drużyny, ligi i sezonu
    team_matches = matches_df[
        ((matches_df['home_team_id'] == team_id) | (matches_df['away_team_id'] == team_id))
    ].sort_values('game_date', ascending=False).head(lookback)

    team_info_parsed = []
    for _, row in team_matches.iterrows():
        is_home = row['home_team_id'] == team_id
        team_key = 'home' if is_home else 'away'
        opponent_key = 'away' if is_home else 'home'
        
        # Określanie wyniku podstawowego
        if row['result'] == 'X':
            result = 'X'
        elif (is_home and row['result'] == "1") or (not is_home and row['result'] == "2"):
            result = 'W'
        else:
            result = 'L'
        
        match_data = {
            'match_id': row['id'],
            'match_date': row['game_date'].strftime('%d.%m'),
            'team_id': row[f'{team_key}_team_id'],
            'opponent_id': row[f'{opponent_key}_team_id'],
            'team_name': row[f'{team_key}_team'],
            'opponent_name': row[f'{opponent_key}_team'],
            'team_goals': row[f'{team_key}_goals'],
            'opponent_goals': row[f'{opponent_key}_goals'],
            'team_sog': row[f'{team_key}_team_sog'],
            'opponent_sog': row[f'{opponent_key}_team_sog'],
            'opponent_shortcut': row[f'{opponent_key}_team_shortcut'],
            'home_team' : row['home_team'],
            'away_team' : row['away_team'],
            'result': result,
            'is_overtime': row['OT'] != 0,
            'is_shootout': row['SO'] != 0,
            'ot_outcome': None,
            'so_outcome': None
        }
        
        # Obsługa dogrywki (OT)
        if row['OT'] != 0:
            if row['OTwinner'] == 1:
                match_data['ot_outcome'] = 'W' if is_home else 'L'
            elif row['OTwinner'] == 2:
                match_data['ot_outcome'] = 'L' if is_home else 'W'
            else:
                match_data['ot_outcome'] = 'X'
        
        # Obsługa rzutów karnych (SO)
        if row['SO'] != 0:
            if row['SOwinner'] == 1:
                match_data['so_outcome'] = 'W' if is_home else 'L'
            else:
                match_data['so_outcome'] = 'L' if is_home else 'W'
        
        team_info_parsed.append(match_data)
    
    return team_info_parsed

def get_team_players_stats(key, season, conn):
    """
    Pobiera dane o zawodnikach drużyny z bazy danych, zwraca osobne tabele dla bramkarzy i zawodników z pola.

    Args:
        key (int): ID drużyny, dla której mają zostać pobrane dane o zawodnikach.
        season (int): Sezon, dla którego mają zostać pobrane dane.
        conn (MySQLConnection): Połączenie do bazy danych.

    Returns:
        tuple: Dwie tabele (bramkarze_df, zawodnicy_df) zawierające dane o zawodnikach drużyny.
    """
    
    # Zapytanie dla bramkarzy (pozycja 'G')
    goalies_query = f'''SELECT 
        p.common_name as 'Zawodnik',
        COUNT(*) as 'Mecze',
        COALESCE(SUM(box.goals), 0) as 'Bramki',
        COALESCE(SUM(box.assists), 0) as 'Asysty',
        COALESCE(SUM(box.points), 0) as 'Punkty',
        ROUND(AVG(box.shots_against), 2) as 'Strzały na bramkę (AVG)',
        ROUND(AVG(box.shots_saved), 2) as 'Obrony (AVG)',
        ROUND(AVG(box.saves_acc), 2) as 'Skuteczność (%, AVG)',
        round(avg(box.toi), 2) as 'Czas gry (min, AVG)'
    FROM hockey_match_player_stats box
    JOIN players p ON box.player_id = p.id
    JOIN matches m ON m.id = box.match_id 
    WHERE box.team_id = {key} AND m.season = {season} AND p.position = 'G'
    GROUP BY p.id, p.common_name
    ORDER BY COUNT(*) DESC'''
    
    # Zapytanie dla zawodników z pola (pozycje inne niż 'G')
    players_query = f'''SELECT 
        p.common_name as 'Zawodnik',
        p.position as 'Pozycja',
        COUNT(*) as 'Mecze',
        SUM(box.goals) as 'Bramki',
        SUM(box.assists) as 'Asysty',
        SUM(box.points) as 'Punkty',
        SUM(box.plus_minus) as '+/-',
        ROUND(AVG(box.sog), 2) as 'Strzały na bramkę (AVG)',
        SUM(box.penalty_minutes) as 'Minuty kar',
        round(avg(box.toi), 2) as 'Czas gry (min, AVG)'
    FROM hockey_match_player_stats box
    JOIN players p ON box.player_id = p.id
    JOIN matches m ON m.id = box.match_id 
    WHERE box.team_id = {key} AND m.season = {season} AND p.position != 'G'
    GROUP BY p.id, p.common_name, p.position
    ORDER BY SUM(box.points) DESC, COUNT(*) DESC'''
    
    goalie_df = pd.read_sql(goalies_query, conn)
    goalie_df.index = range(1, len(goalie_df) + 1)
    players_df = pd.read_sql(players_query, conn)
    players_df.index = range(1, len(players_df) + 1)
    return goalie_df, players_df

def match_dev_info(row, league_id, season_id):
    """Wyświetla szczegółowe dane techniczne meczu NHL dla developerów w eleganckiej formie.
    
    Args:
        row (pd.Series): Wiersz DataFrame z danymi meczu NHL
        league_id (int): ID ligi
        season_id (int): ID sezonu
        
    Returns:
        None: Funkcja wyświetla dane w interfejsie Streamlit
    """
    st.header("Dla developerów")
    dev_data_ids = {
        "ID meczu": row.id,
        "ID Ligi": league_id,
        "ID sezonu": season_id,
        "Wynik (1/X/2)": row.result if hasattr(row, 'result') else "N/A",
        "Gole gospodarzy": row.home_goals if hasattr(row, 'home_goals') else "N/A",
        "Gole gości": row.away_goals if hasattr(row, 'away_goals') else "N/A",
        "Data meczu": row.game_date.strftime('%d.%m.%Y') if hasattr(row, 'game_date') and pd.notna(row.game_date) else "N/A"
    }
    
    for key, value in dev_data_ids.items():
        st.write(f"{key}: {value}")

