import numpy as np
import pandas as pd
import sys
import db_module
import warnings


def update_db(queries, conn):
    """Wykonuje listę zapytań SQL w transakcji. Zatwierdza zmiany tylko, jeśli wszystkie zapytania się powiodą.
    
    Argumenty:
        queries (list): Lista zapytań SQL do wykonania.
        conn: Połączenie do bazy danych (np. z psycopg2/sqlite3).
    
    Zwraca:
        bool: True, jeśli wszystkie zapytania wykonano pomyślnie, False w przeciwnym przypadku.
    """
    cursor = conn.cursor()
    try:
        for query in queries:
            cursor.execute(query)
        conn.commit() 
        return True
    except Exception as error:
        conn.rollback()
        print(f"Błąd bazy danych: {error}, cofnięto całe wgranie zmian.") 
        return False
    finally:
        cursor.close() 

def generate_predictions(conn, league, season, current_round, to_automate):
    #Pobieramy wszystkie mecze w danym dniu dla danej ligi i sezonu (sezon trochę zbyteczny tutaj chyba)
    #W argumentach jest jeszcze current_round, jakbyśmy chcieli hurtowo generować dla wszystkich meczów w danej kolejce
    query = "select id from matches where league = {} and season = {} and cast(game_date as date) = current_date".format(league, season)
    #print(query)
    matches_id = pd.read_sql(query,conn)
    matches_id_np = matches_id.values.flatten() 
    inserts = []
    #W pętli dla każdego meczu
    #3. Pobrać wszystkie wpisy z tabeli "predictions" dla powyższych parametrów
    #4. Pobrać wszystkie wpisy z tabeli "odds" dla powyższych parametrów
    for id in matches_id_np:
        query = "select value, model_id from predictions where match_id = {} and event_id = {}".format(id, 1)
        home_win = pd.read_sql(query, conn).to_numpy()
        query  = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 2)
        draw = pd.read_sql(query, conn).to_numpy()
        query  = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 3)
        guest_win = pd.read_sql(query, conn).to_numpy()
        query  = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 6)
        btts_yes = pd.read_sql(query, conn).to_numpy()
        query  = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 172)
        btts_no = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 173)
        exact_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 8)
        over_2_5 = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 12)
        under_2_5 = pd.read_sql(query, conn).to_numpy()

        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 174)
        zero_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 175)
        one_goal = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 176)
        two_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 177)
        three_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 178)
        four_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 179)
        five_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value, model_id  from predictions where match_id = {} and event_id = {}".format(id, 180)
        six_plus_goals = pd.read_sql(query, conn).to_numpy()

        bookie_dict = {
            'USTALONE' : 0,
            'Superbet' : 1,
            'Betclic' : 2,
            'Fortuna': 3,
            'STS' : 4,
            'LvBet': 5,
            'Betfan' : 6,
            'Etoto' : 7,
            'Fuksiarz' : 8,
        }
        if len(home_win) > 0:
            query = 'select b.name as bookmaker, o.event as event, o.odds as odds from odds o join bookmakers b on o.bookmaker = b.id where match_id = {}'.format(id)
            odds_details = pd.read_sql(query, conn)
            home_win_odds = [round(100/home_win[0][0], 2)] + [0] * (len(bookie_dict) - 1)
            draw_odds = [round(100/draw[0][0], 2)] + [0] * (len(bookie_dict) - 1)
            guest_win_odds = [round(100/guest_win[0][0], 2)] + [0] * (len(bookie_dict) - 1)
            btts_no_odds = [round(100/btts_no[0][0], 2)] + [0] * (len(bookie_dict) - 1)
            btts_yes_odds = [round(100/btts_yes[0][0], 2)] + [0] * (len(bookie_dict) - 1)
            under_odds = [round(100/under_2_5[0][0], 2)] + [0] * (len(bookie_dict) - 1)
            over_odds = [round(100/over_2_5[0][0], 2)] + [0] * (len(bookie_dict) - 1)
            for _, row in odds_details.iterrows():
                if row.event == 1: #GOSPO WIN
                    home_win_odds[bookie_dict[row.bookmaker]] = row.odds
                if row.event == 2: #GOSPO WIN
                    draw_odds[bookie_dict[row.bookmaker]] = row.odds
                if row.event == 3: #GOSPO WIN
                    guest_win_odds[bookie_dict[row.bookmaker]] = row.odds
                if row.event == 6:
                    btts_yes_odds[bookie_dict[row.bookmaker]] = row.odds
                if row.event  == 172:
                    btts_no_odds[bookie_dict[row.bookmaker]] = row.odds
                if row.event == 8:
                    over_odds[bookie_dict[row.bookmaker]] = row.odds
                if row.event == 12:
                    under_odds[bookie_dict[row.bookmaker]] = row.odds

            home_win_EV = round((home_win[0][0]) * max(home_win_odds[1:]) - 1, 2)
            draw_EV = round((draw[0][0]) * max(draw_odds[1:]) - 1, 2)
            guest_win_EV = round((guest_win[0][0]) * max(guest_win_odds[1:]) - 1, 2)
            btts_no_EV = round((btts_no[0][0]) * max(btts_no_odds[1:]) - 1, 2)
            btts_yes_EV = round((btts_yes[0][0]) * max(btts_yes_odds[1:]) - 1, 2)
            under_EV = round((under_2_5[0][0]) * max(under_odds[1:]) - 1, 2)
            over_EV = round((over_2_5[0][0]) * max(over_odds[1:]) - 1, 2)
            EVs = [home_win_EV, draw_EV, guest_win_EV, btts_no_EV, btts_yes_EV, under_EV, over_EV]
            #print(EVs)

            #5. Do tabeli final_predictions wpisać wybory modelu.
            results_prediction = np.array([home_win[0][0], draw[0][0], guest_win[0][0]])
            btts_predictions = np.array([btts_no[0][0], btts_yes[0][0]])
            ou_predictions = np.array([under_2_5[0][0], over_2_5[0][0]])
            goals_no = [zero_goals[0][0], one_goal[0][0], two_goals[0][0], three_goals[0][0], four_goals[0][0], five_goals[0][0], six_plus_goals[0][0]]
            #print(results_prediction)
            #print(btts_predictions)
            #print(ou_predictions)
            #print(goals_no)
            result_pred_id = np.argmax(results_prediction)
            btts_pred_id = np.argmax(btts_predictions)
            ou_pred_id = np.argmax(ou_predictions)
            exact_pred_id = np.argmax(goals_no)
            #print(exact_pred_id)
            event_id = -1
            confidence = -1
            EV = -1
            odds = -1
            bookmaker = -1
            #RESULT
            if result_pred_id == 0:
                event_id = 1
                confidence = home_win[0][0]
                #if home_win_EV > 0:
                EV = home_win_EV
                odds = max(home_win_odds[1:])
                bookmaker = np.argmax(home_win_odds[1:]) + 1
            elif result_pred_id == 1:
                event_id = 2
                confidence = draw[0][0]
                #if draw_EV > 0:
                EV = draw_EV
                odds = max(draw_odds[1:])
                bookmaker = np.argmax(draw_odds[1:]) + 1
            else:
                event_id = 3
                confidence = guest_win[0][0]
                #if guest_win_EV > 0:
                EV = guest_win_EV
                odds = max(guest_win_odds[1:])
                bookmaker = np.argmax(guest_win_odds[1:]) + 1
            if event_id in (1, 2, 3): #and EV > 0:
                model_id = int(home_win[0][1])
                print("insert into bets(match_id, event_id, odds, bookmaker, EV, model_id) values ({}, {}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV, model_id))
                inserts.append("insert into bets(match_id, event_id, odds, bookmaker, EV, model_id) values ({}, {}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV, model_id))
            EV = 0
            #BTTS
            if btts_pred_id == 0:
                event_id = 172
                confidence = btts_no[0][0]
                #if btts_no_EV > 0:
                EV = btts_no_EV
                odds = max(btts_no_odds[1:])
                bookmaker = np.argmax(btts_no_odds[1:]) + 1
            else:
                event_id = 6
                confidence = btts_yes[0][0] 
            # if btts_yes_EV > 0:
                EV = btts_yes_EV
                odds = max(btts_yes_odds[1:])
                bookmaker = np.argmax(btts_yes_odds[1:]) + 1
            if event_id in (6, 172):
                model_id = int(btts_yes[0][1])
                print("insert into bets(match_id, event_id, odds, bookmaker, EV, model_id) values ({}, {}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV, model_id))
                inserts.append("insert into bets(match_id, event_id, odds, bookmaker, EV, model_id) values ({}, {}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV, model_id))
            #OU
            EV = 0
            if ou_pred_id == 0:
                event_id = 12
                confidence = under_2_5[0][0]
                #if under_EV > 0:
                EV = under_EV
                odds = max(under_odds[1:])
                bookmaker = np.argmax(under_odds[1:]) + 1
            else:
                event_id = 8
                confidence = over_2_5[0][0] 
                #if over_EV > 0:
                EV = over_EV
                odds = max(over_odds[1:])
                bookmaker = np.argmax(over_odds[1:]) + 1
            #print(event_id, " ", EV, " " , EVs)
            if event_id in (8, 12): #and EV > 0:
                model_id = int(over_2_5[0][1])
                print("insert into bets(match_id, event_id, odds, bookmaker, EV, model_id) values ({}, {}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV, model_id))
                inserts.append("insert into bets(match_id, event_id, odds, bookmaker, EV, model_id) values ({}, {}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV, model_id))
            #Przez wybory modelu rozumiemy największe % dla danego typu zdarzenia (Rezultat, BTTS, OU) - 3 predykcje dla jednego spotkania
    if to_automate:
        update_db(inserts, conn)

def bet_to_automate(league, season, mode):
    to_automate = 1
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    conn = db_module.db_connect()
    query = "select round from matches where league = {} and season = {} and cast(game_date as date) = current_date order by game_date limit 1".format(league, season)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    if len(results) == 0:
        print("BRAK SPOTKAŃ")
        return
    current_round = results[0][0]
    print("RUNDA: ", current_round)
    if mode == 0:
        generate_predictions(conn, league, season, current_round, to_automate)
    conn.close()    

def main():
    to_automate = 1
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    #1. Wybrać dla jakiej ligi, jakiego sezonu i jakiej rundy wygenerować zestawienie
    league = int(sys.argv[1])
    season = int(sys.argv[2])
    current_round = int(sys.argv[3])
    mode = int(sys.argv[4])
    #2. Wyciągnąć wszystkie idki meczów spełniających powyższe wymagania
    conn = db_module.db_connect()
    
    if mode == 0:
        generate_predictions(conn, league, season, current_round, to_automate)
    conn.close()

if __name__ == '__main__':
    main()