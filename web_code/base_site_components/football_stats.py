import streamlit as st
import pandas as pd

def display_match_players_stats(match_id : int, 
                                home_team_name: str, 
                                home_team_id: int, 
                                away_team_name: str, 
                                away_team_id: int,
                                conn) -> None:
    """Wyświetla statystyki zawodników dla danego spotkania
    Args:
        match_id (int): ID spotkania
        home_team_name (str): Nazwa drużyny gospodarza
        home_team_id (int): ID drużyny gospodarza
        away_team_name (str): Nazwa drużyny gościa
        away_team_id (int): ID drużyny gościa
        conn: Połączenie z bazą danych
    """
    # Pobierz statystyki wszystkich zawodników z danego meczu
    players_stats_query = """
        SELECT 
            p.common_name as zawodnik,
            t.name as druzyna,
            fps.team_id,
            fps.goals as bramki,
            fps.assists as asysty,
            fps.red_cards as czerwone_kartki,
            fps.yellow_cards as zolte_kartki,
            fps.corners_won as wywalczone_rozne,
            fps.shots as strzaly,
            fps.shots_on_target as strzaly_na_bramke,
            fps.blocked_shots as zablokowane_strzaly,
            fps.passes as podania,
            fps.crosses as wrzutki,
            fps.tackles as wslizgi,
            fps.offsides as spalone,
            fps.fouls_conceded as popelnione_faule,
            fps.fouls_won as wywalczone_wolne,
            fps.saves as obrony_bramkarskie
        FROM football_player_stats fps
        JOIN players p ON fps.player_id = p.id
        JOIN teams t ON fps.team_id = t.id
        WHERE fps.match_id = %s
        ORDER BY p.common_name ASC
    """
    
    try:
        all_players_stats = pd.read_sql(players_stats_query, conn, params=[match_id])
        
        if all_players_stats.empty:
            st.warning("Brak statystyk zawodników dla tego meczu")
            return
            
        # Zastąp wartości -1 na "Brak danych"
        stats_columns = ['bramki', 'asysty', 'czerwone_kartki', 'zolte_kartki', 'wywalczone_rozne', 
                        'strzaly', 'strzaly_na_bramke', 'zablokowane_strzaly', 'podania', 
                        'wrzutki', 'wslizgi', 'spalone', 'popelnione_faule', 'wywalczone_wolne', 'obrony_bramkarskie']

        for col in stats_columns:
            all_players_stats[col] = all_players_stats[col].replace(-1, "Brak danych")
        
        # Zmień nazwy kolumn na ładniejsze (bez podkreślników)
        column_mapping = {
            'zawodnik': 'Zawodnik',
            'druzyna': 'Drużyna',
            'bramki': 'Bramki',
            'asysty': 'Asysty',
            'czerwone_kartki': 'Czerwone kartki',
            'zolte_kartki': 'Żółte kartki',
            'wywalczone_rozne': 'Rzuty rożne',
            'strzaly': 'Strzały',
            'strzaly_na_bramke': 'Strzały na bramkę',
            'zablokowane_strzaly': 'Zablokowane strzały',
            'podania': 'Podania',
            'wrzutki': 'Wrzutki',
            'wslizgi': 'Wślizgi',
            'spalone': 'Spalone',
            'popelnione_faule': 'Popełnione faule',
            'wywalczone_wolne': 'Wywalczone wolne',
            'obrony_bramkarskie': 'Obrony'
        }
        
        # Zastosuj nowe nazwy kolumn
        all_players_stats.rename(columns=column_mapping, inplace=True)
        
        # Podziel zawodników na drużyny
        home_players = all_players_stats[all_players_stats['team_id'] == home_team_id].copy()
        away_players = all_players_stats[all_players_stats['team_id'] == away_team_id].copy()
        
        # Usuń kolumnę team_id z wyświetlania (nie jest potrzebna dla użytkownika)
        display_columns = ['Zawodnik', 'Drużyna', 'Bramki', 'Asysty', 'Czerwone kartki', 'Żółte kartki', 
                          'Rzuty rożne', 'Strzały', 'Strzały na bramkę', 'Zablokowane strzały', 
                          'Podania', 'Wrzutki', 'Wślizgi', 'Spalone', 'Popełnione faule', 
                          'Wywalczone wolne', 'Obrony']
        
        # Wyświetl dane w trzech zakładkach
        tab1, tab2, tab3 = st.tabs(["Wspólne", f"Gospodarz ({home_team_name})", f"Gość ({away_team_name})"])
        
        with tab1:
            st.subheader("Statystyki wszystkich zawodników")
            if not all_players_stats.empty:
                st.dataframe(
                    all_players_stats[display_columns], 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Brak danych statystycznych dla zawodników")
        
        with tab2:
            st.subheader(f"Statystyki zawodników - {home_team_name}")
            if not home_players.empty:
                st.dataframe(
                    home_players[display_columns], 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(f"Brak danych statystycznych dla zawodników drużyny {home_team_name}")
        
        with tab3:
            st.subheader(f"Statystyki zawodników - {away_team_name}")
            if not away_players.empty:
                st.dataframe(
                    away_players[display_columns], 
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(f"Brak danych statystycznych dla zawodników drużyny {away_team_name}")
                
    except Exception as e:
        st.error(f"Błąd podczas pobierania statystyk zawodników: {e}")
        return
    
def display_match_statistics(match_id: int, conn) -> None:
    """ Wyświetla statystyki meczowe
    Args:
        match_id (int): ID meczu
        conn: Połączenie z bazą danych
    """
    
    # Pobierz statystyki meczowe wraz z nazwami drużyn
    match_stats_query = """
        SELECT 
            ht.name as home_team,
            ht.shortcut as home_team_shortcut,
            at.name as away_team,
            at.shortcut as away_team_shortcut,
            m.home_team_goals,
            m.away_team_goals,
            m.home_team_xg,
            m.away_team_xg,
            m.home_team_bp,
            m.away_team_bp,
            m.home_team_sc,
            m.away_team_sc,
            m.home_team_sog,
            m.away_team_sog,
            m.home_team_fk,
            m.away_team_fk,
            m.home_team_ck,
            m.away_team_ck,
            m.home_team_off,
            m.away_team_off,
            m.home_team_fouls,
            m.away_team_fouls,
            m.home_team_yc,
            m.away_team_yc,
            m.home_team_rc,
            m.away_team_rc
        FROM matches m
        JOIN teams ht ON m.home_team = ht.id
        JOIN teams at ON m.away_team = at.id
        WHERE m.id = %s
    """
    
    try:
        match_stats = pd.read_sql(match_stats_query, conn, params=[match_id])
        
        if match_stats.empty:
            st.error("Nie znaleziono statystyk dla podanego meczu")
            return
            
        match_data = match_stats.iloc[0].to_dict()
        
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
        # Wyświetlenie w trzech kolumnach: Gospodarz | Statystyka | Gość
        col1, col2, col3 = st.columns([2, 1, 2])
        
        with col1:
            st.markdown(f"### {match_data['home_team']}")
            
        with col3:
            st.markdown(f"### {match_data['away_team']}")
        
        # Lista statystyk do wyświetlenia (bez nazw drużyn)
        stats_to_display = [
            ('team_goals', 'Bramki'),
            ('team_xg', 'Expected Goals (xG)'),
            ('team_bp', 'Posiadanie piłki (%)'),
            ('team_sc', 'Strzały (wszystkie)'),
            ('team_sog', 'Strzały na bramkę'),
            ('team_fk', 'Rzuty wolne'),
            ('team_ck', 'Rzuty rożne'),
            ('team_off', 'Spalone'),
            ('team_fouls', 'Faule'),
            ('team_yc', 'Żółte kartki'),
            ('team_rc', 'Czerwone kartki')
        ]
        
        # Iteracja przez statystyki i renderowanie w odpowiednich kolumnach
        for stat_key, stat_label in stats_to_display:
            home_key = f'home_{stat_key}'
            away_key = f'away_{stat_key}'
            
            # Pobierz surowe wartości numeryczne do porównania
            home_raw_value = match_data.get(home_key, 'N/A')
            away_raw_value = match_data.get(away_key, 'N/A')
            
            # Formatowanie wartości
            home_value = home_raw_value
            away_value = away_raw_value
            
            # Specjalne formatowanie dla niektórych statystyk
            if home_value != 'N/A' and home_value is not None:
                if stat_key == 'team_xg':
                    home_value = f"{float(home_value):.2f}" if home_value != -1 else "Brak danych"
                elif stat_key == 'team_bp':
                    home_value = f"{home_value}%" if home_value != -1 else "Brak danych"
                else:
                    home_value = str(home_value) if home_value != -1 else "Brak danych"
            else:
                home_value = "Brak danych"
                
            if away_value != 'N/A' and away_value is not None:
                if stat_key == 'team_xg':
                    away_value = f"{float(away_value):.2f}" if away_value != -1 else "Brak danych"
                elif stat_key == 'team_bp':
                    away_value = f"{away_value}%" if away_value != -1 else "Brak danych"
                else:
                    away_value = str(away_value) if away_value != -1 else "Brak danych"
            else:
                away_value = "Brak danych"
            
            # Określ kolory na podstawie porównania wartości
            home_bg_color = "#f0f0f0"  # Domyślny szary kolor
            away_bg_color = "#f0f0f0"  # Domyślny szary kolor
            
            # Porównaj wartości tylko jeśli obie są liczbami (nie "Brak danych")
            if (home_raw_value is not None and home_raw_value != 'N/A' and home_raw_value != -1 and
                away_raw_value is not None and away_raw_value != 'N/A' and away_raw_value != -1):
                try:
                    home_numeric = float(home_raw_value)
                    away_numeric = float(away_raw_value)
                    
                    if home_numeric > away_numeric:
                        home_bg_color = "#d4edda"  # Jasnozielony dla wyższej wartości
                        away_bg_color = "#f8d7da"  # Jasnoczerwony dla niższej wartości
                    elif away_numeric > home_numeric:
                        home_bg_color = "#f8d7da"  # Jasnoczerwony dla niższej wartości
                        away_bg_color = "#d4edda"  # Jasnozielony dla wyższej wartości
                    # Jeśli wartości są równe, pozostawiamy domyślny kolor szary
                except (ValueError, TypeError):
                    # Jeśli nie można porównać wartości, użyj domyślnych kolorów
                    pass
            
            # Wyświetlenie statystyk
            with col1:
                col1.markdown(
                    card_style.format(
                        value=home_value,
                        label=stat_label,
                        bg_color=home_bg_color
                    ),
                    unsafe_allow_html=True
                )
            
            with col3:
                col3.markdown(
                    card_style.format(
                        value=away_value,
                        label=stat_label,
                        bg_color=away_bg_color
                    ),
                    unsafe_allow_html=True
                )
                
    except Exception as e:
        st.error(f"Błąd podczas pobierania statystyk meczowych: {e}")
        return
