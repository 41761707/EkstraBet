import streamlit as st
st.set_page_config(page_title = "Kupony graczy", page_icon = "💸", layout="wide")
import pandas as pd

import db_module

def generate_site(conn):
    st.header("Kupony graczy")
    st.page_link("Home.py", label="Strona domowa", icon="🏠")
    st.subheader("Konfiguracja prezentowanych danych")
    query = "select id, gambler_name, parlays_played, parlays_won, balance, active from gamblers where active = 1 order by id"
    gamblers_df = pd.read_sql(query, conn)
    gamblers_dict = gamblers_df.set_index('gambler_name')['id'].to_dict()
    col1, col2 = st.columns(2)
    chosen_gambler, unit_size = 0, 0
    with col1:
        chosen_gambler = st.selectbox(
        "Gracz",
        (g for g in gamblers_dict.keys()), placeholder="Wybierz gracza z listy")
    with col2:
        unit_size = st.number_input("Rozmiar unita", min_value = 1, value = 1)
    gambler_info(gamblers_df, gamblers_dict[chosen_gambler], unit_size, conn)
    add_parlay(chosen_gambler, conn)


def get_parlays_for_gambler(current_gambler_id, conn):
    query = f'''
        select gp.id as parlay_id, m.game_date as game_date, gp.stake as stake, gp.profit as profit,
                l.name as league, t1.name as home_team, t2.name as away_team, e.name as bet_type, b.odds as odds, b.outcome as bet_result,
                m.home_team_goals as home_team_goals, m.away_team_goals as away_team_goals, s.name as sport,
                gp.parlay_outcome as parlay_outcome, gp.parlay_odds as parlay_odds
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
            where gp.gambler_id = {current_gambler_id}
            order by gp.id asc'''
    return pd.read_sql(query, conn)

def get_roi(parlays_df):
    amount_spent = parlays_df.drop_duplicates(subset='parlay_id')['stake'].sum()
    amount_gained = amount_spent + parlays_df.drop_duplicates(subset='parlay_id')['profit'].sum()
    roi = round((amount_gained - amount_spent) * 100.0 / amount_spent, 2)
    return roi

def profit_with_tax(parlays_df, unit_size, tax_value):
    unique_parlays_df = parlays_df.drop_duplicates(subset='parlay_id')
    profit_sum = unique_parlays_df.apply(
        lambda row: row['profit'] * unit_size if row['bet_result_Zdarzenia'] == 'win' 
        else row['stake'] * unit_size * tax_value * row['odds'] - row['stake'] * unit_size, axis=1
    ).sum()
    return round(profit_sum, 2)

def gambler_info(gamblers_df, current_gambler_id, unit_size, conn):
    parlays_df = get_parlays_for_gambler(current_gambler_id, conn)
    current_df = gamblers_df[gamblers_df['id'] == current_gambler_id]
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
        balance = f"{round(float(current_df['balance'].iloc[0]) * unit_size, 2)}zł" if unit_size != 1 else f"{current_df['balance'].iloc[0]}u"
        #balance = profit_with_tax(parlays_df, unit_size, 0.12) 
        st.markdown(f"""
        <div class="tile">
            <div class="tile-title">💸</div>
            <div class="tile-header">{balance}</div>
            <div class="tile-description">Balans konta</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        roi = get_roi(parlays_df)
        st.markdown(f"""
        <div class="tile">
            <div class="tile-title">📈</div>
            <div class="tile-header">{roi}%</div>
            <div class="tile-description">ROI</div>
        </div>
        """, unsafe_allow_html=True)
    parlay_info(parlays_df, unit_size)

def split_into_chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def render_single_bet(col, row):
    bet_result = "✅" if row['bet_result'] == 1 else "❌"
    col.markdown("""
        <style>
        .single_bet {
            text-align: center;
            padding: 10px;
            border: 1px solid #cccccc;
            border-radius: 8px;
            margin-bottom: 5px;
        }
        </style>
    """, unsafe_allow_html=True)
    col.markdown(f"""
        <div class="single_bet">
            <div class="league_info">{row['sport']}: {row['league']}</div>
            <div class="date_info">{row['game_date']}</div>
            <div class="teams">Wynik: {row['home_team']} - {row['away_team']}</div>
            <div class="result">{row['home_team_goals']} - {row['away_team_goals']}</div>
            <div class="bet_info">Zakład: {row['bet_type']}</div>
            <div class="odds_info">Kurs: {row['odds']}</div>
            <div class="bet_result">Wynik: {bet_result}</div>
        </div>
    """, unsafe_allow_html=True)

def show_parlays(parlays_df, unit_size):
    unique_entries = parlays_df['parlay_id'].unique()
    for entry in unique_entries:
        current_parlay_outcome = "✅" if parlays_df[parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] == 1 else "❌"
        button_label = f"Kupon o numerze id: {entry}, Rezultatu kuponu: {current_parlay_outcome}"
        
        if st.button(button_label, use_container_width=True):
            filtered_df = parlays_df[parlays_df['parlay_id'] == entry]
            parlay_odds = parlays_df[parlays_df['parlay_id'] == entry].parlay_odds.iloc[0]
            stake = parlays_df[parlays_df['parlay_id'] == entry].stake.iloc[0] 
            profit = parlays_df[parlays_df['parlay_id'] == entry].profit.iloc[0]
            outcome_str = "Strata: " if parlays_df[parlays_df['parlay_id'] == entry].parlay_outcome.iloc[0] == 0 else "Zysk: "
            rows = list(split_into_chunks(filtered_df.to_dict('records'), 3))
            for row_group in rows[:-1]:
                cols = st.columns(len(row_group))
                for col, row in zip(cols, row_group):
                    render_single_bet(col, row)
            last_row = rows[-1]
            if len(last_row) == 1:
                with st.columns(3)[1]:
                    render_single_bet(st, last_row[0])
            elif len(last_row) == 2:
                for col, row in zip(st.columns(2), last_row):
                    render_single_bet(col, row)
            else:
                for col, row in zip(st.columns(3), last_row):
                    render_single_bet(col, row)    

            st.markdown("""
                <style>
                .summary{
                    text-align: center;
                    padding: 10px;
                    background-color: gray;
                    border-radius: 8px;
                    margin-bottom: 10px;
                }
                </style>
            """, unsafe_allow_html=True)
            st.markdown(f"""
                <div class="summary">
                    <div>PODSUMOWANIE ZAKŁADU</div>
                    <div class="parlay_odds">Kurs kuponu: {parlay_odds}</div>
                    <div class="stake">Stawka: {round(stake * unit_size, 2)}zł</div>
                    <div class="return">{outcome_str} {round(profit * unit_size, 2)}zł</div>
                </div>
                """, unsafe_allow_html=True)

def parlay_info(parlays_df, unit_size):
    with st.expander("Kupony wybranego gracza"):
        show_parlays(parlays_df, unit_size)

def add_parlay(chosen_gambler, conn):
    with st.expander(f"Dodaj kupon dla gracza: {chosen_gambler}"):
        query = "select distinct id, name from leagues where active = 1 order by name"
        leagues_df = pd.read_sql(query, conn)
        leagues_dict = leagues_df.set_index('name')['id'].to_dict()
        chosen_league = st.selectbox("Wybierz ligę", [k for k in leagues_dict.keys()], placeholder="Wybierz ligę z listy")
        st.write(chosen_league)
        query = f"select distinct m.season, s.years from matches m join seasons s on m.season = s.id where m.league = {leagues_dict[chosen_league]} order by s.years desc "
        seasons_df = pd.read_sql(query, conn)
        seasons_dict = seasons_df.set_index('years')['season'].to_dict()
        chosen_season = st.selectbox("Wybierz sezon", [k for k in seasons_dict.keys()], placeholder="Wybierz sezon z listy")
        st.write(chosen_season)
        query = f"select round, game_date from matches where league = {leagues_dict[chosen_league]} and season = {seasons_dict[chosen_season]} order by game_date desc"
        rounds_df = pd.read_sql(query, conn)
        rounds_list = rounds_df['round'].unique().tolist()
        chosen_round = st.selectbox("Wybierz kolejkę", rounds_list, placeholder="Wybierz kolejkę z listy")
        query = f'''select t1.name as GOSPODARZ, t2.name as GOŚĆ, e.name as ZDARZENIE, m.game_date as DATA_SPOTKANIA, b.odds as KURS, b.EV as VB, f.confidence as PEWNOSC_MODELU
                    from bets b
                        join final_predictions f on (b.match_id = f.match_id and b.event_id = f.event_id)
                        join matches m on b.match_id = m.id
                        join teams t1 on m.home_team = t1.id
                        join teams t2 on m.away_team = t2.id
                        join events e on b.event_id = e.id
                        join leagues l on m.league = l.id
                        where m.league = {leagues_dict[chosen_league]} and m.season = {seasons_dict[chosen_season]} and m.round = {chosen_round}
                        order by m.game_date desc''' 
        bets_df = pd.read_sql(query, conn)
        #bets_df['button'] = bets_df.apply(lambda x: st.checkbox("Dodaj zakład"), axis=1)
        bets_df.index = range(1, len(bets_df) + 1)
        st.dataframe(bets_df, use_container_width=True, hide_index=True)

def main():
    conn = db_module.db_connect()
    generate_site(conn)
    conn.close()
        

if __name__ == '__main__':
    main()