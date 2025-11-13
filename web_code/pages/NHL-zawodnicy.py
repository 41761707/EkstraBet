import streamlit as st
import pandas as pd
from PIL import Image

import db_module
import graphs_module

st.set_page_config(page_title = "NHL", page_icon = "🏒", layout="wide")

# Cache'owane funkcje dla zapytań do bazy danych

@st.cache_data(ttl=300)  # Cache na 5 minut
def get_teams_data():
    """Pobiera listę drużyn NHL - rzadko się zmienia, więc można cache'ować na dłużej"""
    conn = db_module.db_connect()
    query_teams = "SELECT id, name FROM teams WHERE sport_id = 2"
    teams_df = pd.read_sql(query_teams, conn)
    conn.close()
    return teams_df

@st.cache_data(ttl=300)  # Cache na 5 minut  
def get_seasons_data():
    """Pobiera listę sezonów - rzadko się zmienia"""
    conn = db_module.db_connect()
    cursor = conn.cursor()
    seasons_query = "SELECT id, years from seasons where id in (select distinct(season) from matches m where m.sport_id = 2) order by years desc"
    cursor.execute(seasons_query)
    seasons_dict = {years: season_id for season_id, years in cursor.fetchall()}
    cursor.close()
    conn.close()
    return seasons_dict

@st.cache_data(ttl=60)  # Cache na 1 minutę - może się zmieniać częściej
def get_players_for_season(season_id):
    """Pobiera zawodników dla danego sezonu"""
    conn = db_module.db_connect()
    query_players = f'''SELECT p.id, p.first_name, p.last_name, p.position, p.current_club
                        FROM players p
                        JOIN hockey_match_player_stats stat ON p.id = stat.player_id
                        JOIN matches m ON stat.match_id = m.id
                        WHERE m.season = {season_id}
                        GROUP BY p.id, p.first_name, p.last_name
                        ORDER BY p.first_name, p.last_name'''
    players_df = pd.read_sql(query_players, conn)
    conn.close()
    return players_df

@st.cache_data(ttl=60)  # Cache na 1 minutę
def get_player_season_stats_cached(player_id, season_id, limit_games):
    """Cache'owana wersja statystyk zawodnika
    Args:
        player_id (int): ID zawodnika
        season_id (int): ID sezonu
        limit_games (int): liczba meczów do pobrania
    Returns:
        tuple: (DataFrame ze statystykami, bool czy jest bramkarzem)
        """
    conn = db_module.db_connect()
    position_query = f"SELECT position FROM players WHERE id = {player_id}"
    position_result = pd.read_sql(position_query, conn)
    is_goalie = position_result['position'].iloc[0] == 'G' if not position_result.empty else False
    if is_goalie:
        query = f"""
            SELECT t1.name as Gospodarz, t2.name as Gość, date_format(cast(m.game_date as date), '%d.%m') AS Data, 
                   stat.shots_against, stat.shots_saved, stat.saves_acc, stat.toi,
                   CASE WHEN t1.id = stat.team_id THEN t2.shortcut WHEN t2.id = stat.team_id THEN t1.shortcut END AS opponent
            FROM hockey_match_player_stats stat
            JOIN matches m on stat.match_id = m.id
            JOIN teams t1 on t1.id = m.home_team
            JOIN teams t2 on t2.id = m.away_team
            WHERE stat.player_id = {player_id} and m.season = {season_id}
            ORDER BY m.game_date desc
            LIMIT {limit_games}
        """
    else:
        # Zapytanie dla zawodników z pola
        query = f"""
            SELECT t1.name as Gospodarz, t2.name as Gość, date_format(cast(m.game_date as date), '%d.%m') AS Data, 
                   stat.points, stat.goals, stat.assists, stat.plus_minus, stat.sog, stat.toi,
                   CASE WHEN t1.id = stat.team_id THEN t2.shortcut WHEN t2.id = stat.team_id THEN t1.shortcut END AS opponent
            FROM hockey_match_player_stats stat
            JOIN matches m on stat.match_id = m.id
            JOIN teams t1 on t1.id = m.home_team
            JOIN teams t2 on t2.id = m.away_team
            WHERE stat.player_id = {player_id} and m.season = {season_id}
            ORDER BY m.game_date desc
            LIMIT {limit_games}
        """
    stats_df = pd.read_sql(query, conn)
    stats_df.fillna(0, inplace=True)
    stats_df['toi_minutes'] = stats_df['toi'].apply(lambda toi_str: int(toi_str.split(':')[0]) + int(toi_str.split(':')[1]) / 60)
    stats_df.reset_index(drop=True, inplace=True)
    conn.close()
    return stats_df, is_goalie

class HockeyPlayers:
    def __init__(self):
        self.season = 1
        self.games_limit = 200 #Nie bedzie wiecej niż 200 meczów w jednym sezonie, więc 200 oznacza "pobierz cały sezon"
        self.current_player_stats = pd.DataFrame()
        self.player_full_name = ""
        self.is_goalie = False  # Flaga określająca czy zawodnik jest bramkarzem
        self.points_line = 0.5
        self.assists_line = 0.5
        self.goals_line = 0.5
        self.sog_line = 1.5
        self.plus_minus_line = 0.5
        self.toi_line = 15.0
        self.selected_player_stats = []  # Lista wybranych statystyk do wyświetlania
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

    def toi_to_minutes(self, toi_str):
        minutes, seconds = map(int, toi_str.split(':'))
        return minutes + seconds / 60

    def get_player_season_stats(self, player_id):
        ''' Funkcja realizująca pobranie statystyk sezonowych zawodnika 
        Args:
            player_id (int): ID zawodnika
        Returns:
            tuple: (DataFrame ze statystykami, bool czy jest bramkarzem)
        '''
        return get_player_season_stats_cached(player_id, self.season, self.limit_games)

    def player_game_log(self):
        ''' Funkcja realizująca przedstawienie logów meczowych zawodnika w formie tabeli'''
        if self.is_goalie:
            # Dla bramkarzy - stały zestaw kolumn
            stat_column_mapping = {
                'Strzały na bramkę': 'shots_against',
                'Obrony': 'shots_saved', 
                'Skuteczność obron (%)': 'saves_acc',
                'Czas na lodzie': 'toi'
            }
            base_columns = ['Gospodarz', 'Gość', 'Data']
            columns_to_display = base_columns.copy()
            display_names = {
                'Gospodarz': 'Gospodarz',
                'Gość': 'Gość',
                'Data': 'Data'
            }
            
            # Dla bramkarzy dodajemy wszystkie dostępne kolumny
            for stat_name, column_name in stat_column_mapping.items():
                if column_name in self.current_player_stats.columns:
                    columns_to_display.append(column_name)
                    display_names[column_name] = stat_name
        else:
            # Dla zawodników z pola - wybieralne kolumny
            stat_column_mapping = {
                'Punkty': 'points',
                'Bramki': 'goals',
                'Asysty': 'assists',
                'Plus/Minus': 'plus_minus',
                'Strzały na bramkę': 'sog',
                'Czas na lodzie': 'toi'
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
        
        display_df = self.current_player_stats[columns_to_display].rename(columns=display_names)
        display_df.index = range(1, len(display_df) + 1)
        display_df.index.name = 'L.P.'
        st.dataframe(display_df, use_container_width=True)

    def player_graphs(self):
        ''' Funkcja realizująca przedstawienie wykresów dla wybranych statystyk '''
        if self.is_goalie:
            available_stats = []
            
            # Sprawdzamy które statystyki są dostępne w danych
            if 'shots_against' in self.current_player_stats.columns:
                available_stats.append('Strzały na bramkę')
            if 'shots_saved' in self.current_player_stats.columns:
                available_stats.append('Obrony')
            if 'saves_acc' in self.current_player_stats.columns:
                available_stats.append('Skuteczność obron (%)')
            if 'toi' in self.current_player_stats.columns:
                available_stats.append('Czas na lodzie')
            
            stats_to_show = available_stats
        else:
            # Dla zawodników z pola - wybieralne statystyki
            if not self.selected_player_stats:
                st.info("Wybierz statystyki do wyświetlenia w sekcji konfiguracji powyżej")
                return
            stats_to_show = self.selected_player_stats
        
        # Organizacja wykresów w zależności od liczby wybranych statystyk
        num_stats = len(stats_to_show)
        if num_stats == 0:
            st.info("Brak dostępnych statystyk do wyświetlenia")
            return
        elif num_stats == 1:
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
        
        for i, stat in enumerate(stats_to_show):
            with cols[i]:
                if stat == "Bramki":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['goals'],
                        self.player_full_name,
                        self.goals_line,
                        "Liczba bramek")
                elif stat == "Asysty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['assists'],
                        self.player_full_name,
                        self.assists_line,
                        "Liczba asyst")
                elif stat == "Punkty":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['points'],
                        self.player_full_name,
                        self.points_line,
                        "Liczba punktów")
                elif stat == "Strzały na bramkę" and not self.is_goalie:
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['sog'],
                        self.player_full_name,
                        self.sog_line,
                        "Liczba strzałów na bramkę")
                elif stat == "Plus/Minus":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['plus_minus'],
                        self.player_full_name,
                        self.plus_minus_line,
                        "Plus/Minus")
                elif stat == "Czas na lodzie":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['toi_minutes'],
                        self.player_full_name,
                        self.toi_line,
                        "Czas na lodzie (minuty)")
                # Wykresy specyficzne dla bramkarzy
                elif stat == "Strzały na bramkę" and self.is_goalie:
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['shots_against'],
                        self.player_full_name,
                        28,  # Domyślna linia dla strzałów na bramkarza
                        "Strzały na bramkę bramkarza")
                elif stat == "Obrony":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['shots_saved'],
                        self.player_full_name,
                        28,  # Domyślna linia dla obron
                        "Liczba obron")
                elif stat == "Skuteczność obron (%)":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'], 
                        self.current_player_stats['opponent'],
                        self.current_player_stats['saves_acc'],
                        self.player_full_name,
                        90,  # Domyślna linia dla skuteczności obron
                        "Skuteczność obron (%)")
        
    
    def show_players(self, players_df):
        ''' Funkcja realizująca przedstawienie graczy'''
        for _, player in players_df.iterrows():
            button_label = f"{player['first_name']} {player['last_name']}"
            self.player_full_name = button_label
            if st.button(button_label, key=f"player_{player['id']}", use_container_width=True):
                self.current_player_stats, self.is_goalie = self.get_player_season_stats(player['id'])
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
                "Ostatnie 10 meczów": 10, 
                "Ostatnie 5 meczów": 5,
                "Ostatnie 15 meczów": 15,
                "Ostatnie 20 meczów": 20,
                "Cały sezon": 200
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
                players_df['first_name'].str.contains(player_name, case=False, na=False) |
                players_df['last_name'].str.contains(player_name, case=False, na=False) |
                players_df.apply(lambda x: f"{x['first_name']} {x['last_name']}".lower(), axis=1).str.contains(player_name.lower())
            ]
        else:
            players_df = players_df[players_df['current_club'] == team_id]
        return players_df
    
    def get_config_lines(self):
        ''' Wybór statystyk do wyświetlania '''
        if not self.is_goalie:  # Tylko dla zawodników z pola pokazujemy wybór statystyk
            st.subheader("Statystyki do wyświetlania")
            self.selected_player_stats = st.multiselect(
                "Wybierz statystyki zawodników, które chcesz wyświetlać:",
                options=["Punkty", "Bramki", "Asysty", "Strzały na bramkę", "Plus/Minus", "Czas na lodzie"],
                default=["Punkty", "Bramki", "Asysty", "Strzały na bramkę"],
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
                            self.points_line = st.slider("Linia punktowa", 0.0, 4.0, 0.5, 0.5, key="points_slider")
                        elif stat == "Bramki":
                            self.goals_line = st.slider("Linia bramkowa", 0.0, 4.0, 0.5, 0.5, key="goals_slider")
                        elif stat == "Asysty":
                            self.assists_line = st.slider("Linia asystowa", 0.0, 4.0, 0.5, 0.5, key="assists_slider")
                        elif stat == "Strzały na bramkę":
                            self.sog_line = st.slider("Linia strzałów na bramkę", 0.0, 6.0, 1.5, 0.5, key="sog_slider")
                        elif stat == "Plus/Minus":
                            self.plus_minus_line = st.slider("Linia Plus/Minus", -3.0, 3.0, 0.5, 0.5, key="plus_minus_slider")
                        elif stat == "Czas na lodzie":
                            self.toi_line = st.slider("Linia czasu na lodzie (minuty)", 5.0, 25.0, 15.0, 0.5, key="toi_slider")
        else:
            st.info("Dla bramkarzy wyświetlane są wszystkie dostępne statystyki: strzały na bramkę, obrony, skuteczność obron i czas na lodzie.")
        
    def player_stats_summary(self):
        # CSS for centering the content
        if self.is_goalie:
            # Podsumowanie dla bramkarzy
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_shots_against = round(self.current_player_stats['shots_against'].mean(), 2) if 'shots_against' in self.current_player_stats.columns else 0
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">🎯</div>
                    <div class="tile-header">{total_shots_against}</div>
                    <div class="tile-description">Średnia liczba strzałów</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                total_saves = round(self.current_player_stats['shots_saved'].mean(), 2) if 'shots_saved' in self.current_player_stats.columns else 0
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">🛡️</div>
                    <div class="tile-header">{total_saves}</div>
                    <div class="tile-description">Średnia liczba obron</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                avg_saves_acc = round(self.current_player_stats['saves_acc'].mean(), 1) if 'saves_acc' in self.current_player_stats.columns else 0
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">📊</div>
                    <div class="tile-header">{avg_saves_acc}%</div>
                    <div class="tile-description">Średnia skuteczność obron</div>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                average_toi = self.current_player_stats['toi_minutes'].mean() if 'toi_minutes' in self.current_player_stats.columns else 0
                average_minutes = int(average_toi)
                average_seconds = int(round((average_toi - average_minutes) * 60))
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">🕓</div>
                    <div class="tile-header">{average_minutes}:{average_seconds:02d}</div>
                    <div class="tile-description">Średni czas na lodzie</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            # Podsumowanie dla zawodników z pola
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">📄</div>
                    <div class="tile-header">{int(self.current_player_stats['points'].sum())}</div>
                    <div class="tile-description">Punkty</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">🎯</div>
                    <div class="tile-header">{int(self.current_player_stats['goals'].sum())}</div>
                    <div class="tile-description">Bramki</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">🍎</div>
                    <div class="tile-header">{int(self.current_player_stats['assists'].sum())}</div>
                    <div class="tile-description">Asysty</div>
                </div>
                """, unsafe_allow_html=True)
            with col4:
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">➕➖</div>
                    <div class="tile-header">{int(self.current_player_stats['plus_minus'].sum())}</div>
                    <div class="tile-description">Plus minus</div>
                </div>
                """, unsafe_allow_html=True)
            with col5:
                average_toi = self.current_player_stats['toi_minutes'].mean()
                average_minutes = int(average_toi)
                average_seconds = int(round((average_toi - average_minutes) * 60))
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">🕓</div>
                    <div class="tile-header">{average_minutes}:{average_seconds:02d}</div>
                    <div class="tile-description">Średni czas na lodzie</div>
                </div>
                """, unsafe_allow_html=True)
            with col6:
                st.markdown(f"""
                <div class="tile">
                    <div class="tile-title">🏒</div>
                    <div class="tile-header">{round(float(self.current_player_stats['sog'].mean()), 2)}</div>
                    <div class="tile-description">Strzały celne na mecz</div>
                </div>
                """, unsafe_allow_html=True)

def main():
    hockey_players = HockeyPlayers()
    st.title("NHL - Zawodnicy")
    players_df = hockey_players.get_players()
    if hockey_players.current_player_stats.empty:
        hockey_players.get_config_lines()
    hockey_players.show_players(players_df)

if __name__ == '__main__':
    main()

