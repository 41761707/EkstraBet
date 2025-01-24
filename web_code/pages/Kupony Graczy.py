import streamlit as st
st.set_page_config(page_title = "Kupony graczy", page_icon = "💸", layout="wide")
import pandas as pd

import db_module

class GamblerParlay:
    def __init__(self):
        self.conn = db_module.db_connect()
        self.gamblers_dict = {}
        self.gamblers = pd.DataFrame()
        self.chosen_gambler = -1
        self.unit_size = 1
        self.parlay_stake = 1.0
        self.parlays_df = pd.DataFrame()

    def generate_site(self):
        st.header("Kupony graczy")
        st.page_link("Home.py", label="Strona domowa", icon="🏠")
        st.subheader("Konfiguracja prezentowanych danych")
        query = "select id, gambler_name, parlays_played, parlays_won, balance, active from gamblers where active = 1 order by id"
        self.gamblers_df = pd.read_sql(query, self.conn)
        self.gamblers_dict = self.gamblers_df.set_index('gambler_name')['id'].to_dict()
        col1, col2, col3 = st.columns([2, 1, 1])
        chosen_gambler, unit_size = 0, 0
        with col1:
            self.chosen_gambler = st.selectbox(
            "Gracz",
            (g for g in self.gamblers_dict.keys()), placeholder="Wybierz gracza z listy")
        with col2:
            self.unit_size = st.number_input("Rozmiar unita", min_value = 1, value = 1)
        with col3:
            self.parlay_stake = st.number_input("Stawka nowego kuponu", min_value = 0.25, value = 1.0, step = 0.25)
        self.gambler_info(self.gamblers_dict[self.chosen_gambler])
        self.add_parlay(self.gamblers_dict[self.chosen_gambler])


    def get_parlays_for_gambler(self, current_gambler_id):
        query = f'''
            select gp.id as parlay_id, m.game_date as game_date, gp.stake as stake, gp.profit as profit,
                    l.name as league, t1.name as home_team, t2.name as away_team, e.name as event, b.odds as odds, b.outcome as bet_result,
                    m.home_team_goals as home_team_goals, m.away_team_goals as away_team_goals, s.name as sport,
                    gp.parlay_outcome as parlay_outcome, gp.parlay_odds as parlay_odds,
                    b.ev as vb, f.confidence as confidence
                from gambler_parlays gp
                join events_parlays ep on gp.id = ep.parlay_id
                join gamblers g on gp.gambler_id = g.id
                join bets b on b.id = ep.bet_id
                join events e on b.event_id = e.id
                join matches m on m.id = b.match_id
                join teams t1 on m.home_team = t1.id
                join teams t2 on m.away_team = t2.id
                join leagues l on l.id = m.league
                join sports s on m.sport_id = s.id
                join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                where gp.gambler_id = {current_gambler_id}
                order by gp.id asc'''
        return pd.read_sql(query, self.conn)

    def get_roi(self):
        amount_spent = self.parlays_df.drop_duplicates(subset='parlay_id')['stake'].sum()
        amount_gained = amount_spent + self.parlays_df.drop_duplicates(subset='parlay_id')['profit'].sum()
        roi = round((amount_gained - amount_spent) * 100.0 / amount_spent, 2)
        return roi

    def profit_with_tax(parlays_df, unit_size, tax_value):
        unique_parlays_df = parlays_df.drop_duplicates(subset='parlay_id')
        profit_sum = unique_parlays_df.apply(
            lambda row: row['profit'] * unit_size if row['bet_result_Zdarzenia'] == 'win' 
            else row['stake'] * unit_size * tax_value * row['odds'] - row['stake'] * unit_size, axis=1
        ).sum()
        return round(profit_sum, 2)

    def gambler_info(self,current_gambler_id):
        self.parlays_df = self.get_parlays_for_gambler(current_gambler_id)
        current_df = self.gamblers_df[self.gamblers_df['id'] == current_gambler_id]
        win_ratio = round(int(current_df['parlays_won'].iloc[0]) * 1.0 / int(current_df['parlays_played'].iloc[0]) * 100, 2)
        
        # CSS for centering the content
        st.markdown("""
            <style>
            .tile {
                text-align: center;
                padding: 10px;
                border: 1px solid #cccccc;
                border-radius: 8px;
                margin-bottom: 10px;
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

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">📄</div>
                <div class="tile-header">{current_df['parlays_played'].iloc[0]}</div>
                <div class="tile-description">Liczba kuponów</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">✅</div>
                <div class="tile-header">{current_df['parlays_won'].iloc[0]}</div>
                <div class="tile-description">Liczba wygranych</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">🎯</div>
                <div class="tile-header">{win_ratio}%</div>
                <div class="tile-description">Procent wygranych</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            balance = f"{round(float(current_df['balance'].iloc[0]) * self.unit_size, 2)}zł" if self.unit_size != 1 else f"{current_df['balance'].iloc[0]}u"
            #balance = profit_with_tax(parlays_df, unit_size, 0.12) 
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">💸</div>
                <div class="tile-header">{balance}</div>
                <div class="tile-description">Balans konta</div>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            roi = self.get_roi()
            st.markdown(f"""
            <div class="tile">
                <div class="tile-title">📈</div>
                <div class="tile-header">{roi}%</div>
                <div class="tile-description">ROI</div>
            </div>
            """, unsafe_allow_html=True)
        self.parlay_info()

    def split_into_chunks(self, lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def show_parlays(self):
        unique_entries = self.parlays_df['parlay_id'].unique()
        for entry in unique_entries:
            if self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] == 1:
                current_parlay_outcome = "✅"
            elif self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] == 0:
                current_parlay_outcome = "❌"
            else:
                current_parlay_outcome = "❓ (nierozliczono)"
            button_label = f"Kupon o numerze id: {entry}, Rezultatu kuponu: {current_parlay_outcome}"
            
            if st.button(button_label, use_container_width=True):
                filtered_df = self.parlays_df[self.parlays_df['parlay_id'] == entry]
                parlay_odds = self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_odds.iloc[0]
                stake = self.parlays_df[self.parlays_df['parlay_id'] == entry].stake.iloc[0] 
                profit = self.parlays_df[self.parlays_df['parlay_id'] == entry].profit.iloc[0]
                outcome_str = "Strata: " if self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] == 0 else "Zysk: "
                rows = list(self.split_into_chunks(filtered_df.to_dict('records'), 3))
                for row_group in rows[:-1]:
                    cols = st.columns(len(row_group))
                    for col, row in zip(cols, row_group):
                        bet_result = row['bet_result'] if self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] is not None else None
                        self.render_bet_card(col, row, "history", bet_result)
                last_row = rows[-1]
                if len(last_row) == 1:
                    with st.columns(3)[1]:
                        bet_result = last_row[0]['bet_result'] if self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] is not None else None
                        self.render_bet_card(st, last_row[0], "history", bet_result)
                elif len(last_row) == 2:
                    for col, row in zip(st.columns(2), last_row):
                        bet_result = row['bet_result'] if self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] is not None else None
                        self.render_bet_card(col, row, "history", bet_result)
                else:
                    for col, row in zip(st.columns(3), last_row):
                        bet_result = row['bet_result'] if self.parlays_df[self.parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] is not None else None
                        self.render_bet_card(col, row, "history", bet_result)   
                #PODSUMOWANIE KUPONU
                st.markdown(f"""
                    <style>
                        .summary-container {{
                            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
                            border-radius: 16px;
                            padding: 1.5rem;
                            margin: 1rem 0;
                            color: white;
                            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
                            position: relative;
                            overflow: hidden;
                            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        }}

                        .summary-container::before {{
                            content: "";
                            position: absolute;
                            top: -50%;
                            left: -50%;
                            width: 200%;
                            height: 200%;
                            background: linear-gradient(45deg, transparent 40%, rgba(255,255,255,0.1) 50%, transparent 60%);
                            animation: shine 3s infinite;
                        }}

                        @keyframes shine {{
                            0% {{ transform: translateX(-100%) rotate(45deg); }}
                            100% {{ transform: translateX(100%) rotate(45deg); }}
                        }}

                        .summary-header {{
                            font-size: 1.5rem;
                            font-weight: 700;
                            margin-bottom: 1rem;
                            position: relative;
                            display: flex;
                            align-items: center;
                            gap: 0.5rem;
                        }}

                        .summary-item {{
                            display: flex;
                            justify-content: space-between;
                            align-items: center;
                            padding: 0.75rem 0;
                            border-bottom: 1px solid rgba(255,255,255,0.1);
                        }}

                        .summary-item:last-child {{
                            border-bottom: none;
                        }}

                        .summary-label {{
                            display: flex;
                            align-items: center;
                            gap: 0.5rem;
                            font-size: 1.3rem;
                            opacity: 0.9;
                        }}

                        .summary-value {{
                            font-weight: 600;
                            font-size: 1.5rem;
                        }}

                        .profit-loss {{
                            font-size: 1.25rem;
                            font-weight: 800;
                            margin-top: 1rem;
                            padding: 0.5rem;
                            border-radius: 8px;
                            background: rgba(255,255,255,0.1);
                            text-align: center;
                            color: {'#4ade80' if profit > 0 else '#323232'};
                        }}
                    </style>

                    <div class="summary-container">
                        <div class="summary-header">
                            Podsumowanie zakładu
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">📈 Łączny kurs</span>
                            <span class="summary-value">{parlay_odds:.2f}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">💰 Stawka</span>
                            <span class="summary-value">{round(stake * self.unit_size, 2)} zł</span>
                        </div>
                        <div class="profit-loss">
                        💵 {outcome_str} {round(profit * self.unit_size, 2)} zł
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    def parlay_info(self):
        with st.expander("Kupony wybranego gracza"):
            self.show_parlays()

    #PROBLEM: UNIT_SIZE OKRESLA ROZMIAR UNITA, A NIE STAWKE! ROZWIAZAC PROBLEM
    def add_parlay(self, gambler_id):
        with st.expander(f"Dodaj kupon dla gracza: {self.chosen_gambler}"):
            # 1. Pobranie danych do selekcji
            query = "select distinct id, name from leagues where active = 1 order by name"
            leagues_df = pd.read_sql(query, self.conn)
            leagues_dict = leagues_df.set_index('name')['id'].to_dict()
            chosen_league = st.selectbox("Wybierz ligę", list(leagues_dict.keys()), placeholder="Wybierz ligę z listy")
            
            query = f"""
                select distinct m.season, s.years 
                from matches m 
                join seasons s on m.season = s.id 
                where m.league = {leagues_dict[chosen_league]} 
                order by s.years desc
            """
            seasons_df = pd.read_sql(query, self.conn)
            seasons_dict = seasons_df.set_index('years')['season'].to_dict()
            chosen_season = st.selectbox("Wybierz sezon", list(seasons_dict.keys()), placeholder="Wybierz sezon z listy")
            
            query = f"""
                select round, game_date 
                from matches 
                where league = {leagues_dict[chosen_league]} 
                    and season = {seasons_dict[chosen_season]} 
                order by game_date desc
            """
            rounds_df = pd.read_sql(query, self.conn)
            rounds_list = rounds_df['round'].unique().tolist()
            chosen_round = st.selectbox("Wybierz kolejkę", rounds_list, placeholder="Wybierz kolejkę z listy")

            # 2. Pobranie danych o zakładach
            query = f"""
                select 
                    t1.name as home_team, 
                    t2.name as away_team, 
                    e.name as event, 
                    m.game_date as game_date, 
                    b.odds as odds, 
                    b.EV as vb, 
                    f.confidence as confidence,
                    m.id as match_id,
                    e.id as event_id,
                    b.id as bet_id
                from bets b
                join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                join matches m on b.match_id = m.id
                join teams t1 on m.home_team = t1.id
                join teams t2 on m.away_team = t2.id
                join events e on b.event_id = e.id
                where m.league = {leagues_dict[chosen_league]} 
                    and m.season = {seasons_dict[chosen_season]} 
                    and m.round = {chosen_round}
                order by m.game_date desc
            """ 
            bets_df = pd.read_sql(query, self.conn)

            # 3. Inicjalizacja stanu sesji
            if 'selected_bets' not in st.session_state:
                st.session_state.selected_bets = []
            
            if 'current_parlay_id' not in st.session_state:
                st.session_state.current_parlay_id = None

            # 4. Wyświetlanie i obsługa przycisków
            col1, col2, col3 = st.columns(3)
            cols = [col1, col2, col3]
            counter = 0
            for idx, row in bets_df.iterrows():
                col = cols[counter]
                with col:
                    self.render_bet_card(col, row, "offer", None)
                if col.button("Dodaj do kuponu", key=f"add_{idx}", use_container_width=True):
                    try:
                        cursor = self.conn.cursor()
                        # Utwórz nowy kupon jeśli nie istnieje
                        if not st.session_state.current_parlay_id:
                            cursor.execute("""
                                INSERT INTO gambler_parlays (stake, gambler_id) 
                                VALUES (%s, %s)
                            """, (self.parlay_stake, gambler_id))
                            
                            cursor.execute("SELECT LAST_INSERT_ID()")
                            parlay_id = cursor.fetchone()[0]
                            st.session_state.current_parlay_id = parlay_id
                            # Natychmiastowe zatwierdzenie głównego wpisu
                            self.conn.commit()
                            self.conn.start_transaction()  # Nowa transakcja dla zdarzeń

                        # Dodaj zdarzenie do kuponu
                        cursor.execute(
                            "INSERT INTO events_parlays (parlay_id, bet_id) VALUES (%s, %s)",
                            (st.session_state.current_parlay_id, row['bet_id'])
                        )
                        
                        self.conn.commit()
                        st.session_state.selected_bets.append(row)
                        st.rerun()
                        
                    except Exception as e:
                        self.conn.rollback()
                        st.error(f"Błąd podczas dodawania zakładu: {str(e)}")
                counter += 1
                if counter == 3:
                    counter = 0

            # 5. Wyświetlanie aktualnego kuponu
            st.subheader("Aktualny kupon:")
            if st.session_state.selected_bets:
                for idx, bet in enumerate(st.session_state.selected_bets):
                    _, col1, _= st.columns([1, 2, 1])
                    with col1:
                        self.render_bet_card(col1, bet, "offer", None)
                    if col1.button("Usuń zakład", key=f"remove_{bet['bet_id']}", use_container_width=True):
                        # Usuń z bazy danych
                        try:
                            cursor = self.conn.cursor()
                            cursor.execute("""
                                DELETE FROM events_parlays 
                                WHERE parlay_id = %s AND bet_id = %s
                            """, (st.session_state.current_parlay_id, bet['bet_id']))
                            self.conn.commit()
                            
                            # Usuń z sesji
                            del st.session_state.selected_bets[idx]
                            st.rerun()
                            
                        except Exception as e:
                            self.conn.rollback()
                            st.error(f"Błąd podczas usuwania zakładu: {str(e)}")
                        finally:
                            cursor.close()
                #TO-DO: Jeśli nie ma zakładów, to trzeba usunąć utworzony kupon
                
                if st.button("Zatwierdź kupon", use_container_width=True):
                    st.success("Kupon został zapisany!")
                    st.markdown("""
                            <style>
                                .confetti {
                                    animation: confetti 2s ease-out;
                                    font-size: 3rem;
                                    text-align: center;
                                }
                                
                                @keyframes confetti {
                                    0% { transform: translateY(0) rotate(0); opacity: 1; }
                                    100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
                                }
                            </style>
                        """, unsafe_allow_html=True)

                    # W miejscu zatwierdzania:
                    st.markdown("<div class='confetti'>🎉</div>", unsafe_allow_html=True)
                    st.session_state.selected_bets = []
                    st.session_state.current_parlay_id = None
                    st.rerun()  # Kluczowa linijka!
            else:
                st.write("Brak zakładów w kuponie")

    def render_bet_card(self, col, row, type, outcome):
        #type = "offer" or "history" - jesli dopiero oferujemy kupon to offer, jesli pokazujemy historie to history
        try:
            vb_value = float(row['vb'])
        except (ValueError, TypeError):
            vb_value = 0.0
        try:
            confidence = int(row['confidence'])
        except (ValueError, TypeError):
            confidence = 0
        col.markdown(f"""
            <style>
                .bet-card {{
                    background: white !important;  # FORCE WHITE BACKGROUND
                    border: 1px solid #e0e0e0;
                    border-radius: 15px;
                    padding: 25px;
                    margin: 20px 0;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                    width: 100%;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: flex !important;
                    flex-direction: column !important;
                    align-items: center !important;
                    text-align: center !important;
                    max-width: 600px;
                }}
                
                .bet-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(0,0,0,0.12);
                }}
                
                .teams {{
                    font-size: 1.4rem;
                    color: #2d3436;
                    margin-bottom: 15px;
                    font-weight: 700;
                    line-height: 1.3;
                    width: 100% !important;
                    display: flex !important;
                    justify-content: center !important;
                    align-items: center !important;
                    gap: 8px !important;
                    flex-wrap: wrap !important;
                }}
                
                .event-type {{
                    color: #0984e3;
                    font-size: 1.2rem;
                    margin: 12px 0;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    width: 100% !important;
                    text-align: center !important;
                    margin: 12px 0 !important;
                }}
                
                .stats-container {{
                    display: flex;
                    flex-direction: column;
                    gap: 15px;
                    width: 100%;
                }}
                
                .metrics {{
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                }}
                
                .vb-indicator {{
                    color: #636e72;
                    font-size: 1.1rem;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}

                .confidence-indicator{{
                    color: #636e72;
                    font-size: 1.1rem;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                
                .confidence-wrapper {{
                    width: 100%;
                    max-width: 300px;
                    margin: 12px 0;
                }}
                
                .odds-badge {{
                    background: #0984e3;
                    color: white;
                    padding: 12px 30px;
                    border-radius: 25px;
                    font-size: 1.5rem;
                    font-weight: 700;
                    margin-top: 15px;
                    display: inline-block;
                }}
                
                .timestamp {{
                    color: #636e72;
                    font-size: 1.2rem;
                    margin-top: 10px;
                }}

                .bet-result {{
                margin-top: 15px;
                font-size: 1.3rem;
                color: #2d3436;
                font-weight: 600;
                }}
                
                .bet-result.positive {{
                    color: #00b894;
                }}
                
                .bet-result.negative {{
                    color: #d63031;
                }}

                .bet-result.neutral {{
                    color: #636e72;
                }}
                </style>

            <div class="bet-card">
                <div class="teams">
                    🏟️ {row['home_team']}
                    <br>vs<br>
                    ✈️ {row['away_team']}
                </div>
                <div class="event-type">Zdarzenie: {row['event']}</div>
                <div class="stats-container">
                    <div class="metrics">
                        <div class="vb-indicator">
                            Value Bet: {vb_value:.2f}
                        </div>
                        <div class="confidence-indicator">
                            Pewność: {confidence}%
                        </div>
                        <div class="confidence-wrapper">
                            <div class="timestamp">
                                📅 {pd.to_datetime(row['game_date']).strftime('%d.%m.%Y %H:%M')}<br>
                            </div>
                        </div>
                    </div>
                    <div class="odds-badge">
                        💵 Kurs: {row['odds']:.2f}
                    </div>
                    {f'''<div class="bet-result {'positive' if outcome == 1 else 'negative' if outcome == 0 else ''}"> 
                     { 'Rezultat: ✅ Wygrana' if outcome == 1 else 'Rezultat: ❌ Przegrana' if outcome == 0 else '❓ Nierozliczono'} 
                    </div>
                     ''' if type == "history" else ""}
            </div>
        """, unsafe_allow_html=True)


def main():
    conn = db_module.db_connect()
    gambler_site = GamblerParlay()
    gambler_site.generate_site()
    conn.close()
        

if __name__ == '__main__':
    main()