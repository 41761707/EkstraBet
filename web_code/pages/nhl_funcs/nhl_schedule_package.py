import streamlit as st
import hockey_rink
import pandas as pd
import graphs_module

def match_predictions(match_id):
    st.write("Tutaj będą predykcje meczowe")

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
    
    lineup_pd = pd.read_sql(lineup_query, conn)
    
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
    events_pd = pd.read_sql(events_query, conn)
    for i in range(1, 6):
        events_pd_i = events_pd[events_pd['Tercja'] == i].drop(columns=['Tercja'])
        if len(events_pd_i) > 0:
            if i == 4:
                st.header("Dogrywka")
            elif i == 5:
                st.header("Rzuty karne")
            else:
                st.header("Tercja {}".format(i))
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
    Wyświetla statystyki meczowe obu drużyn w postaci kart z danymi w Streamlit.

    Funkcja przekształca wiersz DataFrame (zawierający statystyki meczowe) do słownika i renderuje dane
    dla drużyny gospodarzy i gości w dwóch osobnych kolumnach interfejsu Streamlit. Każda statystyka
    prezentowana jest w formie estetycznej karty z opisem i tłem kolorystycznie odróżniającym drużyny.

    Statystyki obejmują m.in. bramki, strzały na bramkę, skuteczność w przewagach, liczbę kar,
    uderzeń, wznowień i inne wskaźniki związane z przebiegiem meczu hokejowego.

    Args:
        match_row (pd.Series): Wiersz zawierający dane statystyczne meczu, w którym klucze mają prefiksy 
            `home_` lub `away_` dla odpowiednich drużyn oraz odpowiadają polom mapowanym w `stat_name`.

    Returns:
        None: Funkcja renderuje dane bezpośrednio w interfejsie Streamlit.
    """

    col1, _ , col3 = st.columns(3)
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
    
    # Mapowanie nazw statystyk
    stat_name = {
        'team': 'Nazwa drużyny',
        'goals': 'Bramki',
        'team_sog': 'Strzały na bramkę',
        'team_fk': 'Minuty kar',
        'team_fouls': 'Liczba kar',
        'team_pp_goals': 'Liczba bramek w przewadze (PP)',
        'team_sh_goals': "Liczba bramek w osłabieniu (SH)",
        'team_shots_acc': "Skuteczność strzałów (%)",
        'team_saves': "Liczba obron",
        'team_saves_acc': 'Skuteczność obron (%)',
        'team_pp_acc': 'Skuteczność gier w przewadze (%)',
        'team_pk_acc': 'Skuteczność gier w osłabieniu (%)',
        'team_faceoffs': 'Liczba wygranych wznowień',
        'team_faceoffs_acc': 'Skuteczność wznowień (%)',
        'team_hits': 'Liczba uderzeń',
        'team_to': 'Liczba strat',
        'team_en': 'Liczba bramek strzelonych na pustą bramkę'
    }

    # Iteracja przez statystyki i renderowanie
    for key, value in match_row_dict.items():
        if key in ('home_team_id', 'away_team_id'):
            continue
        if 'home' in key:
            col1.markdown(
                card_style.format(
                    value=value,
                    label=stat_name[key.replace('home_', '')],
                    bg_color="#e3f2fd"  # Jasnoniebieskie tło dla drużyny gospodarzy
                ),
                unsafe_allow_html=True
            )
        elif 'away' in key:
            col3.markdown(
                card_style.format(
                    value=value,
                    label=stat_name[key.replace('away_', '')],
                    bg_color="#ffebee"  # Jasnoczerwone tło dla drużyny gości
                ),
                unsafe_allow_html=True
            )

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
    boxscore_goaltenders = f'''select 
            t.name as Drużyna, p.common_name as Zawodnik, box.points as Punkty, box.penalty_minutes as "Kary(MIN)", box.toi as TOI, 
            box.shots_against as Strzały, box.shots_saved as Obronione, box.saves_acc as "Skuteczność Obron(%)"
        from hockey_match_player_stats box 
        join players p on box.player_id = p.id
        join matches m on m.id = box.match_id
        join teams t on t.id = box.team_id
        where m.id = {match_id} and p.position = 'G' ''' 
    boxscore_goaltenders_pd = pd.read_sql(boxscore_goaltenders, conn)
    boxscore_goaltenders_pd.index = range(1, len(boxscore_goaltenders_pd) + 1)
    boxscore_goaltenders_pd['Skuteczność Obron(%)'] = boxscore_goaltenders_pd['Skuteczność Obron(%)'].apply(lambda x: f"{x:.2f}")
    st.table(boxscore_goaltenders_pd)
    st.subheader("Zawodnicy")
    boxscore_others = f'''select 
            t.name as Drużyna, p.common_name as Zawodnik, box.goals as Bramki, box.assists as Asysty, box.points as Punkty, box.plus_minus as "+/-",
            box.penalty_minutes as "Kary(MIN)", box.sog as SOG, box.toi as TOI
        from hockey_match_player_stats box 
        join players p on box.player_id = p.id
        join matches m on m.id = box.match_id
        join teams t on t.id = box.team_id
        where m.id = {match_id} and p.position <> 'G' ''' 
    boxscore_pd = pd.read_sql(boxscore_others, conn)
    boxscore_pd.index = range(1, len(boxscore_pd) + 1)
    players_styled = boxscore_pd.style.applymap(graphs_module.highlight_cells_plus_minus, subset = ["+/-"])
    st.table(players_styled)

def get_teams(league, season, conn):
    all_teams = "select distinct t.id, t.name from matches m join teams t on (m.home_team = t.id or m.away_team = t.id) where m.league = {} and m.season = {} order by t.name ".format(league, season)
    all_teams_df = pd.read_sql(all_teams, conn)
    teams_dict = all_teams_df.set_index('id')['name'].to_dict()
    return teams_dict

def get_team_info(team_id, lookback, matches_df):
    """
    Przetwarza dane meczowe dla wybranej drużyny.
    
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
            'opponent_shortcut': row[f'{opponent_key}_team'], # Tutaj można dodać kolumnę shortcut jeśli jest dostępna
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

def league_table(matches, team_ids, winner_gain, draw_gain, ot_gain_winner, ot_gain_loser, scope='all'):
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

def get_team_players_stats(key, season, conn):
    """
    Pobiera dane o zawodnikach drużyny z bazy danych.

    Args:
        key (int): ID drużyny, dla której mają zostać pobrane dane o zawodnikach.
        conn (MySQLConnection): Połączenie do bazy danych.

    Returns:
        pd.DataFrame: DataFrame zawierający dane o zawodnikach drużyny.
    """

    #Logika i zapytanie do sporej poprawy
    query = f'''SELECT p.id, p.common_name, p.position, t.name, count(*) as games_played, sum(box.goals), sum(box.assists), sum(box.points), sum(box.plus_minus), round(avg(box.sog), 1), round(avg(box.toi), 2)
                FROM hockey_match_player_stats box
                JOIN players p ON box.player_id = p.id
                JOIN matches m ON m.id = box.match_id 
                JOIN teams t ON box.team_id = t.id 
                WHERE t.id = {key} and m.season = {season}
                group by p.id, p.common_name, p.position, t.name'''
    players_df = pd.read_sql(query, conn)
    return players_df

