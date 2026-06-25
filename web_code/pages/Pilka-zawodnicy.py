import streamlit as st
import pandas as pd
from PIL import Image

import db_module
import graphs_module

st.set_page_config(page_title="Piłka nożna", page_icon="🧑", layout="wide")

# Cache'owane funkcje dla zapytań do bazy danych


@st.cache_data(ttl=300)  # Cache na 5 minut
def get_teams_data(countries_dict: dict):
    """Pobiera listę drużyn z krajami - rzadko się zmienia, więc można cache'ować na dłużej
    Args:
        countries_dict (dict): Słownik z mapowaniem nazw krajów które mają statystyki zawodników na ich ID
    """
    conn = db_module.db_connect()
    query_teams = f"""SELECT t.id, t.name, t.opta_name, c.id as country
                     FROM teams t 
                     JOIN countries c on t.country = c.id
                     WHERE t.sport_id = 1 and t.opta_name is not null and c.id in ({','.join(map(str, countries_dict.values()))})
                     ORDER BY t.name"""
    teams_df = pd.read_sql(query_teams, conn)
    conn.close()
    return teams_df


@st.cache_data(ttl=300)  # Cache na 5 minut
def get_countries_data():
    """Pobiera listę krajów z drużynami piłkarskimi, które mają ligi z OPTY - zwraca mapowanie nazwa -> ID"""
    conn = db_module.db_connect()
    query_countries = """SELECT DISTINCT c.id, c.name
                        FROM teams t 
                        JOIN countries c ON t.country = c.id
                        JOIN leagues l ON c.id = l.country
                        WHERE t.sport_id = 1 and l.has_player_stats = 1
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
    players_df = pd.read_sql(query_players, conn)
    conn.close()
    return players_df


@st.cache_data(ttl=60)  # Cache na 1 minutę
def get_player_season_stats_cached(player_id, season_id, limit_games):
    """Cache'owana wersja statystyk zawodnika"""
    conn = db_module.db_connect()
    query = f"""
        SELECT t1.name as Gospodarz, t2.name as Gość, date_format(cast(m.game_date as date), '%d.%m') AS Data, 
               stat.goals, stat.assists, stat.shots, stat.shots_on_target, stat.fouls_conceded, stat.yellow_cards,
               CASE WHEN t1.id = stat.team_id THEN t2.shortcut WHEN t2.id = stat.team_id THEN t1.shortcut END AS opponent
        FROM football_player_stats stat
        JOIN matches m on stat.match_id = m.id
        JOIN teams t1 on t1.id = m.home_team
        JOIN teams t2 on t2.id = m.away_team
        WHERE stat.player_id = {player_id} and m.season = {season_id}
        ORDER BY m.game_date desc
        LIMIT {limit_games}
    """
    stats_df = pd.read_sql(query, conn)
    stats_df.fillna(0, inplace=True)
    stats_df.reset_index(drop=True, inplace=True)
    conn.close()
    return stats_df


class FootballPlayers:
    def __init__(self):
        #self.conn = conn
        self.season = 1
        # Domyślnie ostatnie 50 meczów (cały sezon dla większości lig)
        self.games_limit = 50
        self.current_player_stats = pd.DataFrame()
        self.player_full_name = ""
        self.goals_line = 0.5
        self.assists_line = 0.5
        self.shots_line = 0.5
        self.shots_on_target_line = 0.5
        self.fouls_conceded_line = 0.5
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

    def get_player_season_stats(self, player_id):
        ''' Funkcja realizująca pobranie statystyk sezonowych zawodnika 
        Args:
            player_id (int): ID zawodnika
        '''
        return get_player_season_stats_cached(player_id, self.season, self.limit_games)

    def player_game_log(self):
        ''' Funkcja realizująca przedstawienie logów meczowych zawodnika w formie tabeli'''
        stat_column_mapping = {
            'Bramki': 'goals',
            'Asysty': 'assists',
            'Strzały': 'shots',
            'Strzały celne': 'shots_on_target',
            'Faule': 'fouls_conceded',
            'Żółte kartki': 'yellow_cards'
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
        display_df = self.current_player_stats[columns_to_display].rename(
            columns=display_names)
        # Reset indeksu na numerację od 1
        display_df.index = range(1, len(display_df) + 1)
        display_df.index.name = 'L.P.'
        st.dataframe(display_df, use_container_width=True)

    def player_graphs(self):
        ''' Funkcja realizująca przedstawienie wykresów dla wybranych statystyk '''
        if not self.selected_player_stats:
            st.info(
                "Wybierz statystyki do wyświetlenia w sekcji konfiguracji powyżej")
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
                if stat == "Bramki":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'],
                        self.current_player_stats['opponent'],
                        self.current_player_stats['goals'],
                        self.player_full_name,
                        self.goals_line,
                        "Liczba bramek"
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
                elif stat == "Strzały":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'],
                        self.current_player_stats['opponent'],
                        self.current_player_stats['shots'],
                        self.player_full_name,
                        self.shots_line,
                        "Liczba strzałów"
                    )
                elif stat == "Strzały celne":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'],
                        self.current_player_stats['opponent'],
                        self.current_player_stats['shots_on_target'],
                        self.player_full_name,
                        self.shots_on_target_line,
                        "Liczba strzałów celnych"
                    )
                elif stat == "Faule":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'],
                        self.current_player_stats['opponent'],
                        self.current_player_stats['fouls_conceded'],
                        self.player_full_name,
                        self.fouls_conceded_line,
                        "Liczba fauli popełnionych"
                    )
                elif stat == "Żółte kartki":
                    graphs_module.vertical_bar_chart(
                        self.current_player_stats['Data'],
                        self.current_player_stats['opponent'],
                        self.current_player_stats['yellow_cards'],
                        self.player_full_name,
                        0.5,
                        "Liczba żółtych kartek"
                    )

    def show_players(self, players_df):
        ''' Funkcja realizująca przedstawienie graczy'''
        for _, player in players_df.iterrows():
            # Inicjalizacja session_state dla zawodnika
            state_key = f"football_player_state_{player['id']}"
            
            if state_key not in st.session_state:
                st.session_state[state_key] = False
            
            button_label = player['common_name']
            self.player_full_name = button_label
            
            if not st.session_state[state_key]:
                if st.button(f"▶ {button_label}", key=f"football_show_player_{player['id']}", use_container_width=True):
                    st.session_state[state_key] = True
                    st.rerun()
            else:
                if st.button(f"▼ {button_label}", key=f"football_hide_player_{player['id']}", use_container_width=True):
                    st.session_state[state_key] = False
                    st.rerun()
                
                self.current_player_stats = self.get_player_season_stats(
                    player['id'])
                self.player_stats_summary()
                self.player_graphs()
                self.player_game_log()

    def get_players(self):
        ''' Pobierz zawodników na podstawie wybranych filtrów '''
        countries_dict = get_countries_data()
        teams_df = get_teams_data(countries_dict)
        seasons_dict = get_seasons_data()

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            # Filtr kraju - wyświetlamy nazwy krajów
            countries_names = list(countries_dict.keys())
            selected_country_name = st.selectbox(
                "Wybierz kraj:", countries_names, key='selected_country')
            # Używamy ID kraju do filtrowania
            selected_country_id = countries_dict[selected_country_name]
            filtered_teams_df = teams_df[teams_df['country']
                                            == selected_country_id]

        with col2:
            selected_team = st.selectbox(
                "Wybierz drużynę:", filtered_teams_df['name'])
            team_id = filtered_teams_df[filtered_teams_df['name']
                                        == selected_team]['id'].values[0]
        with col3:
            seasons_list = [season for season in seasons_dict.keys()]
            self.selected_season = st.selectbox(
                "Sezon", seasons_list, key='selected_season')
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
        players_df = get_players_for_season(self.season)
        if player_name:
            players_df = players_df[
                players_df['common_name'].str.contains(
                    player_name, case=False, na=False)
            ]
        else:
            players_df = players_df[players_df['current_club'] == team_id]
        return players_df

    def get_config_lines(self):
        ''' Wybór statystyk do wyświetlania '''
        st.subheader("Statystyki do wyświetlania")
        self.selected_player_stats = st.multiselect(
            "Wybierz statystyki zawodników, które chcesz wyświetlać:",
            options=["Bramki", "Asysty", "Strzały",
                     "Strzały celne", "Faule", "Żółte kartki"],
            default=["Bramki", "Asysty"],
            help="Możesz wybrać kilka opcji jednocześnie"
        )

        # Slidery dla linii progowych - tylko dla wybranych statystyk (z wyjątkiem żółtych kartek)
        stats_with_sliders = [
            stat for stat in self.selected_player_stats if stat != "Żółte kartki"]

        if stats_with_sliders:
            st.subheader("Linie progowe dla wykresów")
            cols = st.columns(len(stats_with_sliders))

            for i, stat in enumerate(stats_with_sliders):
                with cols[i]:
                    if stat == "Bramki":
                        self.goals_line = st.slider(
                            "Linia bramkowa", 0.0, 4.0, 0.5, 0.5, key="goals_slider")
                    elif stat == "Asysty":
                        self.assists_line = st.slider(
                            "Linia asystowa", 0.0, 4.0, 0.5, 0.5, key="assists_slider")
                    elif stat == "Strzały":
                        self.shots_line = st.slider(
                            "Linia strzałów", 0.0, 10.0, 0.5, 0.5, key="shots_slider")
                    elif stat == "Strzały celne":
                        self.shots_on_target_line = st.slider(
                            "Linia strzałów celnych", 0.0, 6.0, 0.5, 0.5, key="shots_target_slider")
                    elif stat == "Faule":
                        self.fouls_conceded_line = st.slider(
                            "Linia popełnionych fauli", 0.0, 6.0, 0.5, 0.5, key="fouls_slider")

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


def main():
    # Zainicjowanie połączenia z bazą danych tylko raz na sesję
    #if 'db_connection' not in st.session_state:
    #    st.session_state.db_connection = db_module.db_connect()

    football_players = FootballPlayers()
    st.title("Piłka nożna - Zawodnicy")
    players_df = football_players.get_players()
    football_players.get_config_lines()
    football_players.show_players(players_df)


if __name__ == '__main__':
    main()
