import streamlit as st
import pandas as pd
from PIL import Image

import db_module
import graphs_module

st.set_page_config(page_title = "Piłka nożna", page_icon = "🧑", layout="wide")

# Cache'owane funkcje dla zapytań do bazy danych
@st.cache_data(ttl=300)  # Cache na 5 minut
def get_teams_data():
    """Pobiera listę drużyn z krajami - rzadko się zmienia, więc można cache'ować na dłużej"""
    conn = db_module.db_connect()
    query_teams = """SELECT t.id, t.name, t.opta_name, c.id as country
                     FROM teams t 
                     JOIN countries c on t.country = c.id
                     WHERE t.sport_id = 1 
                     ORDER BY t.name"""
    teams_df = pd.read_sql(query_teams, conn)
    conn.close()
    return teams_df

@st.cache_data(ttl=300)  # Cache na 5 minut
def get_countries_data():
    """Pobiera listę krajów z drużynami piłkarskimi - zwraca mapowanie nazwa -> ID"""
    conn = db_module.db_connect()
    query_countries = """SELECT DISTINCT c.id, c.name
                        FROM teams t 
                        JOIN countries c ON t.country = c.id
                        WHERE t.sport_id = 1 
                        ORDER BY c.name"""
    countries_df = pd.read_sql(query_countries, conn)
    conn.close()
    # Zwracamy słownik {nazwa_kraju: id_kraju}
    return dict(zip(countries_df['name'], countries_df['id']))

@st.cache_data(ttl=300)  # Cache na 5 minut
def get_seasons_data():
    """Pobiera listę sezonów - rzadko się zmienia"""
    conn = db_module.db_connect()
    cursor = conn.cursor()
    seasons_query = "SELECT id, years from seasons where id in (select distinct(season) from matches m where m.sport_id = 1) order by years desc"
    cursor.execute(seasons_query)
    seasons_dict = {years: season_id for season_id, years in cursor.fetchall()}
    cursor.close()
    conn.close()
    return seasons_dict

@st.cache_data(ttl=60)  # Cache na 1 minutę - może się zmieniać częściej
def get_players_for_season(season_id):
    """Pobiera zawodników dla danego sezonu"""
    conn = db_module.db_connect()
    query_players = f'''SELECT distinct p.id, p.common_name, fps.team_id as current_club
                        FROM players p
                        JOIN football_player_stats fps ON p.id = fps.player_id
                        JOIN matches m ON fps.match_id = m.id
                        WHERE m.season = {season_id}
                        AND p.common_name IS NOT NULL
                        AND p.common_name != ''
                        ORDER BY p.common_name'''
    query_players = '''SELECT distinct p.id, p.common_name, fps.team_id as current_club
                        FROM players p
                        JOIN football_player_stats fps ON p.id = fps.player_id
                        JOIN matches m ON fps.match_id = m.id
                        WHERE m.season = %s
                        AND p.common_name IS NOT NULL
                        AND p.common_name != ''
                        ORDER BY p.common_name'''
    players_df = pd.read_sql(query_players, conn, params=(season_id,))
    conn.close()
    return players_df

@st.cache_data(ttl=60)  # Cache na 1 minutę
def get_player_season_stats_cached(player_id, season_id, limit_games):
    """Cache'owana wersja statystyk zawodnika"""
    conn = db_module.db_connect()
    query = f"""
        SELECT t1.name as Gospodarz, t2.name as Gość, date_format(cast(m.game_date as date), '%d.%m') AS Data, 
               stat.goals, stat.assists, stat.shots, stat.shots_on_target,
               CASE WHEN t1.id = stat.team_id THEN t2.shortcut WHEN t2.id = stat.team_id THEN t1.shortcut END AS opponent
        FROM football_player_stats stat
        JOIN matches m on stat.match_id = m.id
        JOIN teams t1 on t1.id = m.home_team
        JOIN teams t2 on t2.id = m.away_team
        WHERE stat.player_id = {player_id} and m.season = {season_id}
        ORDER BY m.game_date desc
        LIMIT {limit_games}
    """
        WHERE stat.player_id = %s and m.season = %s
        ORDER BY m.game_date desc
        LIMIT {limit_games}
    """.format(limit_games=limit_games_int)
    stats_df = pd.read_sql(query, conn, params=(player_id, season_id))
    stats_df.fillna(0, inplace=True)
    stats_df.reset_index(drop=True, inplace=True)
    conn.close()
    return stats_df

class FootballPlayers:
    def __init__(self, conn):
        self.conn = conn
        self.season = 1
        self.games_limit = 50  # Domyślnie ostatnie 50 meczów (cały sezon dla większości lig)
        self.current_player_stats = pd.DataFrame()
        self.player_full_name = ""
        self.goals_line = 0.5
        self.assists_line = 0.5
        self.shots_line = 0.5
        self.shots_on_target_line = 0.5
        st.markdown("""
            <style>
            .tile {
                text-align: center;
                padding: 10px;
                border: 1px solid #cccccc;
                border-radius: 8px;
                margin-bottom: 10px;
                height: 200px;
            }
            .tile-title {
                font-size: 36px;
                margin: 0;
            }
            .tile-header {
                font-size: 24px;
                margin: 5px 0;
            }
            .tile-description {
                font-size: 16px;
                color: #666;
            }
            </style>
        """, unsafe_allow_html=True)

    def get_player_season_stats(self, player_id):
        # Używamy cache'owanej wersji
        return get_player_season_stats_cached(player_id, self.season, self.limit_games)

    def player_game_log(self):
        # Create a dictionary mapping original column names to display names
        column_names = {
            'Gospodarz': 'Gospodarz',
            'Gość': 'Gość',
            'Data': 'Data',
            'goals': 'Bramki',
            'assists': 'Asysty',
            'shots': 'Strzały',
            'shots_on_target': 'Strzały celne'
        }
        
        # Create a copy of the DataFrame with renamed columns
        display_df = self.current_player_stats.drop(['opponent'], axis=1).rename(columns=column_names)
        
        # Reset index to start from 1
        display_df.index = range(1, len(display_df) + 1)
        display_df.index.name = 'L.P.'
        
        # Display the DataFrame with the new column names
        st.dataframe(display_df, use_container_width=True)

    def player_graphs(self):
        # Pierwszy wiersz: bramki i asysty
        col1, col2 = st.columns(2)
        with col1:
            # Wykres bramek
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['goals'],
                                        self.player_full_name,
                                        self.goals_line,
                                        "Liczba bramek")
        with col2:
            # Wykres asyst
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['assists'],
                                        self.player_full_name,
                                        self.assists_line,
                                        "Liczba asyst")
        
        # Drugi wiersz: strzały i strzały celne
        col3, col4 = st.columns(2)
        with col3:
            # Wykres strzałów
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['shots'],
                                        self.player_full_name,
                                        self.shots_line,
                                        "Liczba strzałów")
        with col4:
            # Wykres strzałów celnych
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['shots_on_target'],
                                        self.player_full_name,
                                        self.shots_on_target_line,
                                        "Liczba strzałów celnych")
        
    
    def show_players(self, players_df):
        for _, player in players_df.iterrows():
            button_label = player['common_name']
            self.player_full_name = button_label
            if st.button(button_label, key=f"player_{player['id']}", use_container_width=True):
                self.current_player_stats = self.get_player_season_stats(player['id'])
                self.player_stats_summary()
                self.player_graphs()
                self.player_game_log()

    def get_players(self):
        # Używamy cache'owanych danych
        teams_df = get_teams_data()
        countries_dict = get_countries_data()  # {nazwa_kraju: id_kraju}
        seasons_dict = get_seasons_data()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:  
            # Filtr kraju - wyświetlamy nazwy krajów
            countries_names = ["Wszystkie kraje"] + list(countries_dict.keys())
            selected_country_name = st.selectbox("Wybierz kraj:", countries_names, key='selected_country')
            
            # Filtruj drużyny według wybranego kraju
            if selected_country_name == "Wszystkie kraje":
                filtered_teams_df = teams_df
            else:
                # Używamy ID kraju do filtrowania
                selected_country_id = countries_dict[selected_country_name]
                filtered_teams_df = teams_df[teams_df['country'] == selected_country_id]
        
        with col2:
            selected_team = st.selectbox("Wybierz drużynę:", filtered_teams_df['name'])
            # Pobierz ID wybranej drużyny
            team_id = filtered_teams_df[filtered_teams_df['name'] == selected_team]['id'].values[0]
        with col3:
            seasons_list = [season for season in seasons_dict.keys()]
            self.selected_season = st.selectbox("Sezon", seasons_list, key='selected_season')
            self.season = seasons_dict[self.selected_season]
        with col4:
            limit_options = {
                "Cały sezon": 50,
                "Ostatnie 5 meczów": 5,
                "Ostatnie 10 meczów": 10, 
                "Ostatnie 15 meczów": 15
            }
            self.limit_games = st.selectbox(
                "Liczba meczów",
                options=list(limit_options.keys()),
                key='games_limit'
            )
            self.limit_games = limit_options[self.limit_games]
        with col5:
            player_name = st.text_input("Wpisz nazwę zawodnika")
        
        # Używamy cache'owanej funkcji do pobierania zawodników
        players_df = get_players_for_season(self.season)
        
        # Filtrowanie zawodników
        if player_name:
            players_df = players_df[
                players_df['common_name'].str.contains(player_name, case=False, na=False)
            ]
        else:
            players_df = players_df[players_df['current_club'] == team_id]
        return players_df
    
    def get_config_lines(self):
        # Pierwszy wiersz sliderów: bramki i asysty
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            self.goals_line = st.slider("Linia bramkowa", 0.0, 4.0, 0.5, 0.5)
        with col2:
            self.assists_line = st.slider("Linia asystowa", 0.0, 4.0, 0.5, 0.5)
        with col3:
            self.shots_line = st.slider("Linia strzałów", 0.0, 10.0, 0.5, 0.5)
        with col4:
            self.shots_on_target_line = st.slider("Linia strzałów celnych", 0.0, 6.0, 0.5, 0.5)
        with col5:
            # Pusta kolumna dla zachowania spójności layoutu
            st.write("")
        
    def player_stats_summary(self):
        # CSS for centering the content
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🎯</div>
                <div class="tile-header">{int(self.current_player_stats['goals'].sum())}</div>
                <div class="tile-description">Bramki</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🍎</div>
                <div class="tile-header">{int(self.current_player_stats['assists'].sum())}</div>
                <div class="tile-description">Asysty</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🏹</div>
                <div class="tile-header">{int(self.current_player_stats['shots'].sum())}</div>
                <div class="tile-description">Strzały</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🎯</div>
                <div class="tile-header">{int(self.current_player_stats['shots_on_target'].sum())}</div>
                <div class="tile-description">Strzały celne</div>
            </div>
            """, unsafe_allow_html=True)

if __name__ == '__main__':
    # Zainicjowanie połączenia z bazą danych tylko raz na sesję
    if 'db_connection' not in st.session_state:
        st.session_state.db_connection = db_module.db_connect()
    
    football_players = FootballPlayers(st.session_state.db_connection)
    st.title("Piłka nożna - Zawodnicy")
    players_df = football_players.get_players()
    football_players.get_config_lines()
    football_players.show_players(players_df)
