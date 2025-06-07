import streamlit as st
import pandas as pd
from PIL import Image

import db_module
import graphs_module

st.set_page_config(page_title = "NHL", page_icon = "🏒", layout="wide")

class HockeyPlayers:
    def __init__(self, conn):
        self.conn = conn
        self.season = 1
        self.games_limit = 200 #Nie bedzie wiecej niż 200 meczów w jednym sezonie, więc 200 oznacza "pobierz cały sezon"
        self.current_player_stats = pd.DataFrame()
        self.player_full_name = ""
        self.points_line = 0.5
        self.assists_line = 0.5
        self.goals_line = 0.5
        self.sog_line = 1.5
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
        query = f"""
            SELECT t1.name as Gospodarz, t2.name as Gość, date_format(cast(m.game_date as date), '%d.%m') AS Data, stat.points, stat.goals, stat.assists, stat.plus_minus, stat.sog, stat.toi,
            CASE WHEN t1.id = stat.team_id THEN t2.shortcut WHEN t2.id = stat.team_id THEN t1.shortcut END AS opponent
            FROM hockey_match_player_stats stat
            JOIN matches m on stat.match_id = m.id
            JOIN teams t1 on t1.id = m.home_team
            JOIN teams t2 on t2.id = m.away_team
            WHERE stat.player_id = {player_id} and m.season = {self.season}
            ORDER BY m.game_date desc
            LIMIT {self.limit_games}
        """
        stats_df = pd.read_sql(query, self.conn)
        stats_df.fillna(0, inplace=True)
        stats_df['toi_minutes'] = stats_df['toi'].apply(self.toi_to_minutes)
        stats_df.reset_index(drop=True, inplace=True)
        return stats_df

    def player_game_log(self):
        # Create a dictionary mapping original column names to display names
        column_names = {
            'Gospodarz': 'Gospodarz',
            'Gość': 'Gość',
            'Data': 'Data',
            'points': 'Punkty',
            'goals': 'Bramki',
            'assists': 'Asysty',
            'plus_minus': '+/-',
            'sog': 'Strzały na bramkę',
            'toi': 'Czas na lodzie'
        }
        
        # Create a copy of the DataFrame with renamed columns
        display_df = self.current_player_stats.drop(['toi_minutes', 'opponent'], axis=1).rename(columns=column_names)
        
        # Reset index to start from 1
        display_df.index = range(1, len(display_df) + 1)
        display_df.index.name = 'L.P.'
        
        # Display the DataFrame with the new column names
        st.dataframe(display_df, use_container_width=True)

    def player_graphs(self):
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)
        with col1:
            #Wykres bramek
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['goals'],
                                        self.player_full_name,
                                        self.goals_line,
                                        "Liczba bramek")
        with col2:
            #Wykres asyst
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['assists'],
                                        self.player_full_name,
                                        self.assists_line,
                                        "Liczba asyst")
        with col3:
            #Wykres punktów
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['points'],
                                        self.player_full_name,
                                        self.points_line,
                                        "Liczba punktów")
        with col4:
            #Wykres strzałów na bramkę
            graphs_module.vertical_bar_chart(self.current_player_stats['Data'], 
                                        self.current_player_stats['opponent'],
                                        self.current_player_stats['sog'],
                                        self.player_full_name,
                                        self.sog_line,
                                        "Liczba strzałów na bramkę")
        
    
    def show_players(self, players_df):
        for _, player in players_df.iterrows():
            button_label = f"{player['first_name']} {player['last_name']}"
            self.player_full_name = button_label
            if st.button(button_label, key=f"player_{player['id']}", use_container_width=True):
                self.current_player_stats = self.get_player_season_stats(player['id'])
                self.player_stats_summary()
                self.player_graphs()
                self.player_game_log()

    def get_players(self):
        query_teams = "SELECT id, name FROM teams WHERE sport_id = 2"
        teams_df = pd.read_sql(query_teams, self.conn)
        query_players = f'''SELECT p.id, p.first_name, p.last_name, p.position, p.current_club
                        FROM players p
                        JOIN hockey_match_player_stats stat ON p.id = stat.player_id
                        JOIN matches m ON stat.match_id = m.id
                        WHERE m.season = {self.season}
                        GROUP BY p.id, p.first_name, p.last_name
                        ORDER BY p.first_name, p.last_name'''
        players_df = pd.read_sql(query_players, self.conn)
        col1, col2, col3, col4 = st.columns(4)
        with col1:  
            selected_team = st.selectbox("Wybierz drużynę:", teams_df['name'])
            # Pobierz ID wybranej drużyny
            team_id = teams_df[teams_df['name'] == selected_team]['id'].values[0]
        with col2:
            cursor = self.conn.cursor()
            seasons_query = "SELECT id, years from SEASONS where id in (select distinct(season) from matches m where m.sport_id = 2) order by years desc"
            cursor.execute(seasons_query)
            self.seasons = {years: season_id for season_id, years in cursor.fetchall()}
            seasons_list = [season for season in self.seasons.keys()]
            self.selected_season = st.selectbox("Sezon", seasons_list, key='selected_season')
            self.season = self.seasons[self.selected_season]
            cursor.close()
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
            if player_name:
                players_df = players_df[
                    players_df['first_name'].str.contains(player_name, case=False) |
                    players_df['last_name'].str.contains(player_name, case=False) |
                    players_df.apply(lambda x: f"{x['first_name']} {x['last_name']}".lower(), axis=1).str.contains(player_name.lower())
                ]
            else:
                players_df = players_df[players_df['current_club'] == team_id]
        return players_df
    
    def get_config_lines(self):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            self.points_line = st.slider("Linia punktowa", 0.0, 4.0, 0.5, 0.5)
        with col2:
            self.goals_line = st.slider("Linia bramkowa", 0.0, 4.0, 0.5, 0.5)
        with col3:
            self.assists_line = st.slider("Linia asystowa", 0.0, 4.0, 0.5, 0.5)
        with col4:
            self.sog_line = st.slider("Linia strzałów na bramkę", 0.0, 6.0, 1.5, 0.5)
        
    def player_stats_summary(self):
        # CSS for centering the content
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

if __name__ == '__main__':
    conn = db_module.db_connect()
    hockey_players = HockeyPlayers(conn)
    st.title("NHL - Zawodnicy")
    players_df = hockey_players.get_players()
    hockey_players.get_config_lines()
    hockey_players.show_players(players_df)

