import streamlit as st
import pandas as pd
from PIL import Image

import db_module
import graphs_module

st.set_page_config(page_title = "NBA", page_icon = "🏀", layout="wide")

# Cache'owane funkcje dla zapytań do bazy danych

@st.cache_data(ttl=300)  # Cache na 5 minut
def get_teams_data():
    """Pobiera listę drużyn NBA - rzadko się zmienia, więc można cache'ować na dłużej"""
    conn = db_module.db_connect()
    query_teams = "SELECT id, name FROM teams WHERE sport_id = 3 AND country = 20"
    teams_df = pd.read_sql(query_teams, conn)
    conn.close()
    return teams_df

@st.cache_data(ttl=300)  # Cache na 5 minut  
def get_seasons_data():
    """Pobiera listę sezonów - rzadko się zmienia"""
    conn = db_module.db_connect()
    cursor = conn.cursor()
    seasons_query = "SELECT id, years from seasons where id in (select distinct(season) from matches m where m.sport_id = 3) order by years desc"
    cursor.execute(seasons_query)
    seasons_dict = {years: season_id for season_id, years in cursor.fetchall()}
    cursor.close()
    conn.close()
    return seasons_dict

@st.cache_data(ttl=60)  # Cache na 1 minutę - może się zmieniać częściej
def get_players_for_season(season_id):
    """Pobiera zawodników dla danego sezonu"""
    conn = db_module.db_connect()
    query_players = f'''SELECT p.id, p.common_name, p.position, p.current_club
                        FROM players p
                        JOIN basketball_match_player_stats stat ON p.id = stat.player_id
                        JOIN matches m ON stat.match_id = m.id
                        WHERE m.season = {season_id}
                        GROUP BY p.id, p.common_name
                        ORDER BY p.common_name'''
    players_df = pd.read_sql(query_players, conn)
    conn.close()
    return players_df

@st.cache_data(ttl=60)  # Cache na 1 minutę
def get_player_season_stats_cached(player_id, season_id, limit_games):
    """Cache'owana wersja statystyk zawodnika"""
    conn = db_module.db_connect()
    query = f"""
        SELECT t1.name as Gospodarz, t2.name as Gość, date_format(cast(m.game_date as date), '%d.%m') AS Data, 
        stat.points, stat.rebounds, stat.assists, stat.field_goals_made, stat.field_goals_attempts, 
        stat.2_p_field_goals_made, stat.2_p_field_goals_attempts, stat.3_p_field_goals_made, stat.3_p_field_goals_attempts, 
        stat.ft_made, stat.ft_attempts, stat.steals, stat.turnovers, stat.time_played,
        CASE WHEN t1.id = stat.team_id THEN t2.shortcut WHEN t2.id = stat.team_id THEN t1.shortcut END AS opponent
        FROM basketball_match_player_stats stat
        JOIN matches m on stat.match_id = m.id
        JOIN teams t1 on t1.id = m.home_team
        JOIN teams t2 on t2.id = m.away_team
        WHERE stat.player_id = {player_id} and m.season = {season_id}
        ORDER BY m.game_date desc
        LIMIT {limit_games}
    """
    stats_df = pd.read_sql(query, conn)
    stats_df.fillna(0, inplace=True)
    # Konwersja czasu gry na minuty
    stats_df['time_minutes'] = stats_df['time_played'].apply(lambda time_str: 
        int(time_str.split(':')[0]) + int(time_str.split(':')[1]) / 60 if isinstance(time_str, str) and ':' in time_str else 0)
    # Obliczanie skuteczności rzutów z gry
    stats_df['fg_percentage'] = stats_df.apply(lambda row: 
        (row['field_goals_made'] / row['field_goals_attempts'] * 100) if row['field_goals_attempts'] > 0 else 0, axis=1)
    # Obliczanie skuteczności rzutów za 2 punkty
    stats_df['2p_percentage'] = stats_df.apply(lambda row: 
        (row['2_p_field_goals_made'] / row['2_p_field_goals_attempts'] * 100) if row['2_p_field_goals_attempts'] > 0 else 0, axis=1)
    # Obliczanie skuteczności rzutów za 3 punkty
    stats_df['3p_percentage'] = stats_df.apply(lambda row: 
        (row['3_p_field_goals_made'] / row['3_p_field_goals_attempts'] * 100) if row['3_p_field_goals_attempts'] > 0 else 0, axis=1)
    # Obliczanie skuteczności rzutów wolnych
    stats_df['ft_percentage'] = stats_df.apply(lambda row: 
        (row['ft_made'] / row['ft_attempts'] * 100) if row['ft_attempts'] > 0 else 0, axis=1)
    stats_df.reset_index(drop=True, inplace=True)
    conn.close()
    return stats_df

class BasketballPlayers:
    def __init__(self):
        self.season = 1
        self.games_limit = 200 # Nie będzie więcej niż 200 meczów w jednym sezonie, więc 200 oznacza "pobierz cały sezon"
        self.current_player_stats = pd.DataFrame()
        self.player_full_name = ""
        self.points_line = 15.5
        self.rebounds_line = 5.5
        self.assists_line = 3.5
        self.field_goals_line = 5.5
        self.two_pointers_line = 3.5
        self.three_pointers_line = 1.5
        self.free_throws_line = 3.5
        self.steals_line = 1.5
        self.turnovers_line = 2.5
        self.time_line = 25.0
        self.selected_player_stats = []  # Lista wybranych statystyk do wyświetlania
        st.markdown("""
            <style>
            .tile {
                text-align: center;
                padding: 10px;
                border: 1px solid #cccccc;
                border-radius: 8px;
                margin-bottom: 10px;
                height: 175px;
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

    def time_to_minutes(self, time_str):
        if isinstance(time_str, str) and ':' in time_str:
            minutes, seconds = map(int, time_str.split(':'))
            return minutes + seconds / 60
        return 0

    def get_player_season_stats(self, player_id):
        ''' Funkcja realizująca pobranie statystyk sezonowych zawodnika 
        Args:
            player_id (int): ID zawodnika
        '''
        return get_player_season_stats_cached(player_id, self.season, self.limit_games)

    def player_game_log(self):
        ''' Funkcja realizująca przedstawienie logów meczowych zawodnika w formie tabeli'''
        stat_column_mapping = {
            'Punkty': 'points',
            'Zbiórki': 'rebounds',
            'Asysty': 'assists',
            'Rzuty z gry trafione': 'field_goals_made',
            'Rzuty za 2 punkty': '2_p_field_goals_made',
            'Rzuty za 3 punkty': '3_p_field_goals_made',
            'Rzuty wolne trafione': 'ft_made',
            'Przechwyty': 'steals',
            'Straty': 'turnovers',
            'Czas gry': 'time_played'
        }
        
        base_columns = ['Gospodarz', 'Gość', 'Data']
        columns_to_display = base_columns.copy()
        display_names = {
            'Gospodarz': 'Gospodarz',
            'Gość': 'Gość',
            'Data': 'Data'
        }
        
        for stat in self.selected_player_stats:
            if stat in stat_column_mapping:
                column_name = stat_column_mapping[stat]
                columns_to_display.append(column_name)
                display_names[column_name] = stat
        
        if not self.selected_player_stats:
            st.info("Wybierz statystyki do wyświetlenia w tabeli")
            return
        
        # Tworzenie kopii DataFrame z wybranymi kolumnami
        display_df = self.current_player_stats[columns_to_display].rename(columns=display_names)
        
        # Reset indeksu na numerację od 1
        display_df.index = range(1, len(display_df) + 1)
        display_df.index.name = 'L.P.'
        
        # Wyświetlenie DataFrame z nowymi nazwami kolumn
        st.dataframe(display_df, use_container_width=True)

    def player_graphs(self):
        ''' Funkcja realizująca przedstawienie wykresów dla wybranych statystyk '''
        if not self.selected_player_stats:
            st.info("Wybierz statystyki do wyświetlenia w sekcji konfiguracji powyżej")
            return
            
        # Organizacja wykresów w zależności od liczby wybranych statystyk
        num_stats = len(self.selected_player_stats)
        if num_stats == 1:
            # Jeden wykres na całą szerokość
            cols = [st.container()]
        elif num_stats == 2:
            # Dwa wykresy w jednym rzędzie
            cols = st.columns(2)
        else:
            # Więcej niż 2 - maksymalnie 2 w rzędzie
            cols = []
            for i in range(0, num_stats, 2):
                row_cols = st.columns(min(2, num_stats - i))
                cols.extend(row_cols)
        
        for i, stat in enumerate(self.selected_player_stats):
            with cols[i]:
                if stat == "Punkty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['points'],
                        self.player_full_name,
                        self.points_line,
                        "Liczba punktów"
                    )
                elif stat == "Zbiórki":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['rebounds'],
                        self.player_full_name,
                        self.rebounds_line,
                        "Liczba zbiórek"
                    )
                elif stat == "Asysty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['assists'],
                        self.player_full_name,
                        self.assists_line,
                        "Liczba asyst"
                    )
                elif stat == "Rzuty z gry trafione":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['field_goals_made'],
                        self.player_full_name,
                        self.field_goals_line,
                        "Rzuty z gry trafione"
                    )
                elif stat == "Rzuty za 2 punkty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['2_p_field_goals_made'],
                        self.player_full_name,
                        self.two_pointers_line,
                        "Rzuty za 2 punkty trafione"
                    )
                elif stat == "Rzuty za 3 punkty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['3_p_field_goals_made'],
                        self.player_full_name,
                        self.three_pointers_line,
                        "Rzuty za 3 punkty trafione"
                    )
                elif stat == "Rzuty wolne trafione":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['ft_made'],
                        self.player_full_name,
                        self.free_throws_line,
                        "Rzuty wolne trafione"
                    )
                elif stat == "Przechwyty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['steals'],
                        self.player_full_name,
                        self.steals_line,
                        "Liczba przechwytów"
                    )
                elif stat == "Straty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['turnovers'],
                        self.player_full_name,
                        self.turnovers_line,
                        "Liczba strat"
                    )
                elif stat == "Czas gry":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['time_minutes'],
                        self.player_full_name,
                        self.time_line,
                        "Czas gry (minuty)"
                    )
        
    
    def show_players(self, players_df):
        ''' Funkcja realizująca przedstawienie graczy'''
        for _, player in players_df.iterrows():
            button_label = player['common_name']
            self.player_full_name = button_label
            if st.button(button_label, key=f"player_{player['id']}", use_container_width=True):
                self.current_player_stats = self.get_player_season_stats(player['id'])
                self.player_stats_summary()
                self.player_graphs()
                self.player_game_log()

    def get_players(self):
        ''' Pobierz zawodników na podstawie wybranych filtrów '''
        teams_df = get_teams_data()
        seasons_dict = get_seasons_data()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:  
            selected_team = st.selectbox("Wybierz drużynę:", teams_df['name'])
            # Pobierz ID wybranej drużyny
            team_id = teams_df[teams_df['name'] == selected_team]['id'].values[0]
        with col2:
            seasons_list = [season for season in seasons_dict.keys()]
            self.selected_season = st.selectbox("Sezon", seasons_list, key='selected_season')
            self.season = seasons_dict[self.selected_season]
        with col3:
            limit_options = {
                "Cały sezon": 200,
                "Ostatnie 5 meczów": 5,
                "Ostatnie 10 meczów": 10, 
                "Ostatnie 15 meczów": 15,
                "Ostatnie 20 meczów": 20
            }
            self.limit_games = st.selectbox(
                "Liczba meczów",
                options=list(limit_options.keys()),
                key='games_limit'
            )
            self.limit_games = limit_options[self.limit_games]
        with col4:
            player_name = st.text_input("Wpisz imię lub nazwisko zawodnika")
            
        players_df = get_players_for_season(self.season)
        
        if player_name:
            players_df = players_df[
                players_df['common_name'].str.contains(player_name, case=False, na=False)
            ]
        else:
            players_df = players_df[players_df['current_club'] == team_id]
        return players_df
    
    def get_config_lines(self):
        ''' Wybór statystyk do wyświetlania '''
        st.subheader("Statystyki do wyświetlania")
        self.selected_player_stats = st.multiselect(
            "Wybierz statystyki zawodników, które chcesz wyświetlać:",
            options=["Punkty", "Zbiórki", "Asysty", "Rzuty z gry trafione", "Rzuty za 2 punkty", "Rzuty za 3 punkty", "Rzuty wolne trafione", "Przechwyty", "Straty", "Czas gry"],
            default=["Punkty", "Zbiórki", "Asysty", "Rzuty z gry trafione"],
            help="Możesz wybrać kilka opcji jednocześnie"
        )

        # Slidery dla linii progowych - tylko dla wybranych statystyk
        stats_with_sliders = self.selected_player_stats

        if stats_with_sliders:
            st.subheader("Linie progowe dla wykresów")
            cols = st.columns(len(stats_with_sliders))

            for i, stat in enumerate(stats_with_sliders):
                with cols[i]:
                    if stat == "Punkty":
                        self.points_line = st.slider("Linia punktowa", 0.0, 40.0, 15.5, 0.5, key="points_slider")
                    elif stat == "Zbiórki":
                        self.rebounds_line = st.slider("Linia zbiórek", 0.0, 20.0, 5.5, 0.5, key="rebounds_slider")
                    elif stat == "Asysty":
                        self.assists_line = st.slider("Linia asystowa", 0.0, 15.0, 3.5, 0.5, key="assists_slider")
                    elif stat == "Rzuty z gry trafione":
                        self.field_goals_line = st.slider("Linia rzutów z gry", 0.0, 20.0, 5.5, 0.5, key="field_goals_slider")
                    elif stat == "Rzuty za 2 punkty":
                        self.two_pointers_line = st.slider("Linia rzutów za 2 punkty", 0.0, 15.0, 3.5, 0.5, key="two_pointers_slider")
                    elif stat == "Rzuty za 3 punkty":
                        self.three_pointers_line = st.slider("Linia rzutów za 3 punkty", 0.0, 10.0, 1.5, 0.5, key="three_pointers_slider")
                    elif stat == "Rzuty wolne trafione":
                        self.free_throws_line = st.slider("Linia rzutów wolnych", 0.0, 15.0, 3.5, 0.5, key="free_throws_slider")
                    elif stat == "Przechwyty":
                        self.steals_line = st.slider("Linia przechwytów", 0.0, 5.0, 1.5, 0.5, key="steals_slider")
                    elif stat == "Straty":
                        self.turnovers_line = st.slider("Linia strat", 0.0, 10.0, 2.5, 0.5, key="turnovers_slider")
                    elif stat == "Czas gry":
                        self.time_line = st.slider("Linia czasu gry (minuty)", 0.0, 48.0, 25.0, 0.5, key="time_slider")
        
    def player_stats_summary(self):
        # CSS for centering the content
        col1, col2, col3, col4= st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">📊</div>
                <div class="tile-header">{round(float(self.current_player_stats['points'].mean()), 1)}</div>
                <div class="tile-description">Punkty na mecz</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🏀</div>
                <div class="tile-header">{round(float(self.current_player_stats['rebounds'].mean()), 1)}</div>
                <div class="tile-description">Zbiórki na mecz</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🤝</div>
                <div class="tile-header">{round(float(self.current_player_stats['assists'].mean()), 1)}</div>
                <div class="tile-description">Asysty na mecz</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            avg_fg_percentage = self.current_player_stats['fg_percentage'].mean()
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🎯</div>
                <div class="tile-header">{round(float(avg_fg_percentage), 1)}%</div>
                <div class="tile-description">Skuteczność rzutów z gry</div>
            </div>
            """, unsafe_allow_html=True)
        
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            avg_2p_percentage = self.current_player_stats['2p_percentage'].mean()
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🎲</div>
                <div class="tile-header">{round(float(avg_2p_percentage), 1)}%</div>
                <div class="tile-description">Skuteczność rzutów za 2</div>
            </div>
            """, unsafe_allow_html=True)
        with col6:
            avg_3p_percentage = self.current_player_stats['3p_percentage'].mean()
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🎪</div>
                <div class="tile-header">{round(float(avg_3p_percentage), 1)}%</div>
                <div class="tile-description">Skuteczność rzutów za 3</div>
            </div>
            """, unsafe_allow_html=True)
        with col7:
            avg_ft_percentage = self.current_player_stats['ft_percentage'].mean()
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">�</div>
                <div class="tile-header">{round(float(avg_ft_percentage), 1)}%</div>
                <div class="tile-description">Skuteczność rzutów wolnych</div>
            </div>
            """, unsafe_allow_html=True)
        with col8:
            average_time = self.current_player_stats['time_minutes'].mean()
            average_minutes = int(average_time)
            average_seconds = int(round((average_time - average_minutes) * 60))
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🕓</div>
                <div class="tile-header">{average_minutes}:{average_seconds:02d}</div>
                <div class="tile-description">Średni czas gry</div>
            </div>
            """, unsafe_allow_html=True)

def main():
    basketball_players = BasketballPlayers()
    st.title("NBA - Zawodnicy")
    players_df = basketball_players.get_players()
    basketball_players.get_config_lines()
    basketball_players.show_players(players_df)

if __name__ == '__main__':
    main()