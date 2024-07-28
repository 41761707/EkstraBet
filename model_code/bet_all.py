import numpy as np
import pandas as pd
import sys
import db_module
import warnings

def generate_predictions(conn, league, season, current_round):
    query = "select id from matches where league = {} and season = {} and round = {} and cast(game_date as date) = current_date".format(league, season, current_round)
    #query = "select id from matches where cast(game_date as date) > '2024-07-01' and cast(game_date as date) < '2024-07-23'"
    #print(query)
    matches_id = pd.read_sql(query,conn)
    matches_id_np = matches_id.values.flatten() 
    #W pętli dla każdego meczu
    #3. Pobrać wszystkie wpisy z tabeli "predictions" dla powyższych parametrów
    #4. Pobrać wszystkie wpisy z tabeli "odds" dla powyższych parametrów
    for id in matches_id_np:
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 1)
        home_win = pd.read_sql(query, conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 2)
        draw = pd.read_sql(query, conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 3)
        guest_win = pd.read_sql(query, conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 6)
        btts_yes = pd.read_sql(query, conn).to_numpy()
        query  = "select value from predictions where match_id = {} and event_id = {}".format(id, 172)
        btts_no = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 173)
        exact_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 8)
        over_2_5 = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 12)
        under_2_5 = pd.read_sql(query, conn).to_numpy()

        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 174)
        zero_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 175)
        one_goal = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 176)
        two_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 177)
        three_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 178)
        four_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 179)
        five_goals = pd.read_sql(query, conn).to_numpy()
        query = "select value from predictions where match_id = {} and event_id = {}".format(id, 180)
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

            home_win_EV = round((home_win[0][0] / 100) * max(home_win_odds[1:]) - 1, 2)
            draw_EV = round((draw[0][0] / 100) * max(draw_odds[1:]) - 1, 2)
            guest_win_EV = round((guest_win[0][0] / 100) * max(guest_win_odds[1:]) - 1, 2)
            btts_no_EV = round((btts_no[0][0] / 100) * max(btts_no_odds[1:]) - 1, 2)
            btts_yes_EV = round((btts_yes[0][0] / 100) * max(btts_yes_odds[1:]) - 1, 2)
            under_EV = round((under_2_5[0][0] / 100) * max(under_odds[1:]) - 1, 2)
            over_EV = round((over_2_5[0][0] / 100) * max(over_odds[1:]) - 1, 2)
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
            print("insert into final_predictions(match_id, event_id, confidence) values({}, {}, {});".format(id, event_id,confidence))
            if event_id in (1, 2, 3): #and EV > 0:
                print("insert into bets(match_id, event_id, odds, bookmaker, EV) values ({}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV))
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
            print("insert into final_predictions(match_id, event_id, confidence) values({}, {}, {});".format(id, event_id,confidence))
            #print(event_id, " ", EV)
            #print(EVs)
            if event_id in (6, 172): #and EV > 0:
                print("insert into bets(match_id, event_id, odds, bookmaker, EV) values ({}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV))
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
            print("insert into final_predictions(match_id, event_id, confidence) values({}, {}, {});".format(id, event_id,confidence))
            #print(event_id, " ", EV, " " , EVs)
            if event_id in (8, 12): #and EV > 0:
                print("insert into bets(match_id, event_id, odds, bookmaker, EV) values ({}, {}, {}, {}, {});".format(id, event_id, odds, bookmaker, EV))
            #Przez wybory modelu rozumiemy największe % dla danego typu zdarzenia (Rezultat, BTTS, OU) - 3 predykcje dla jednego spotkania
            #6. Do tabeli bets wpisać te, których EV wyszło dodanie i są to pierwsze wybory modelu (podzbiór final_predictions)


def generate_statistics(conn, league, season, current_round):
    query = 'select id, result, home_team_goals as home_goals, away_team_goals as away_goals, home_team_goals + away_team_goals as total from matches where league = {} and season = {} and round = {}'.format(league, season, current_round)
    match_stats_df = pd.read_sql(query, conn)
    correct_ou_pred = 0
    correct_ou_bets = 0
    ou_no_bets = 0
    ou_profit_bets = 0
    correct_btts_pred = 0
    correct_btts_bets = 0
    btts_no_bets = 0
    btts_profit_bets = 0
    correct_result_pred = 0
    correct_result_bets = 0
    result_no_bets = 0
    result_profit_bets = 0

    for index, row in match_stats_df.iterrows():
        if row['result'] == '0':
            continue
        id = row['id']
        query = 'select event_id from final_predictions where match_id = {}'.format(id)
        predictions_df = pd.read_sql(query, conn)
        query = 'select event_id, odds, bookmaker from bets where match_id = {}'.format(id)
        bets_df = pd.read_sql(query, conn)
        for index, predict in predictions_df.iterrows():
            if predict['event_id'] == 8 and row['total'] > 2.5:
                correct_ou_pred = correct_ou_pred + 1
            elif predict['event_id'] == 12 and row['total'] < 2.5:
                correct_ou_pred = correct_ou_pred + 1
            elif predict['event_id'] == 1 and row['result'] == '1':
                correct_result_pred = correct_result_pred + 1
            elif predict['event_id'] == 2 and row['result'] == 'X':
                correct_result_pred = correct_result_pred + 1
            elif predict['event_id'] == 3 and row['result'] == '2':
                correct_result_pred = correct_result_pred + 1
            elif predict['event_id'] == 6 and (row['home_goals'] >0 and row['away_goals'] > 0 ):
                correct_btts_pred = correct_btts_pred + 1
            elif predict['event_id'] == 172 and not (row['home_goals'] > 0 and row['away_goals'] > 0):
                correct_btts_pred = correct_btts_pred + 1
            else:
                pass

        for index, bet in bets_df.iterrows():
            if bet['event_id'] in (8,12):
                    ou_no_bets = ou_no_bets + 1
                    ou_profit_bets = ou_profit_bets - 1
            if bet['event_id'] in (1,2,3):
                    result_no_bets = result_no_bets + 1
                    result_profit_bets = result_profit_bets - 1
            if bet['event_id'] in (6,172):
                    btts_no_bets = btts_no_bets + 1
                    btts_profit_bets = btts_profit_bets - 1

            if bet['event_id'] == 8 and row['total'] > 2.5:
                correct_ou_bets = correct_ou_bets + 1
                ou_profit_bets = ou_profit_bets + bet['odds']
            elif bet['event_id'] == 12 and row['total'] < 2.5:
                correct_ou_bets = correct_ou_bets + 1
                ou_profit_bets = ou_profit_bets + bet['odds']
            elif bet['event_id'] == 1 and row['result'] == '1':
                correct_result_bets = correct_result_bets + 1
                result_profit_bets = result_profit_bets + bet['odds']
            elif bet['event_id'] == 2 and row['result'] == 'X':
                correct_result_bets = correct_result_bets + 1
                result_profit_bets = result_profit_bets + bet['odds']
            elif bet['event_id'] == 3 and row['result'] == '2':
                correct_result_bets = correct_result_bets + 1
                result_profit_bets = result_profit_bets + bet['odds']
            elif bet['event_id'] == 6 and (row['home_goals'] >0 and row['away_goals'] > 0 ):
                correct_btts_bets = correct_btts_bets + 1
                btts_profit_bets = btts_profit_bets + bet['odds']
            elif bet['event_id'] == 172 and not (row['home_goals'] > 0 and row['away_goals'] > 0):
                correct_btts_bets = correct_btts_bets + 1
                btts_profit_bets = btts_profit_bets + bet['odds']
            else:
                pass
    print("Liczba przewidywań OU: {}, liczba poprawnych: {:.2f}, skuteczność: {:.2f}%".format(len(match_stats_df), correct_ou_pred, 100 * correct_ou_pred / len(match_stats_df)))
    print("Liczba przewidywań BTTS: {}, liczba poprawnych: {:.2f}, skuteczność: {:.2f}%".format(len(match_stats_df), correct_btts_pred, 100 * correct_btts_pred / len(match_stats_df)))
    print("Liczba przewidywań RESULT: {}, liczba poprawnych: {:.2f}, skuteczność: {:.2f}%".format(len(match_stats_df), correct_result_pred, 100 * correct_result_pred / len(match_stats_df)))
    print("Liczba zakładów OU: {}, liczba poprawnych: {}, profit: {:.2f}, skuteczność: {:.2f}%".format(ou_no_bets, correct_ou_bets, ou_profit_bets, 100 * correct_ou_bets / ou_no_bets))
    print("Liczba zakładów BTTS: {}, liczba poprawnych: {}, profit: {:.2f}, skuteczność: {:.2f}%".format(btts_no_bets, correct_btts_bets, btts_profit_bets, 100 * correct_btts_bets / btts_no_bets))
    print("Liczba zakładów RESULT: {}, liczba poprawnych: {}, profit: {:.2f}, skuteczność: {:.2f}%".format(result_no_bets, correct_result_bets, result_profit_bets, 100 * correct_result_bets / result_no_bets))

def main():
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    #1. Wybrać dla jakiej ligi, jakiego sezonu i jakiej rundy wygenerować zestawienie
    league = int(sys.argv[1])
    season = int(sys.argv[2])
    current_round = int(sys.argv[3])
    mode = int(sys.argv[4])
    #2. Wyciągnąć wszystkie idki meczów spełniających powyższe wymagania
    conn = db_module.db_connect()
    if mode == 0:
        generate_predictions(conn, league, season, current_round)
    if mode == 1:
        generate_statistics(conn, league, season, current_round)
    conn.close()

if __name__ == '__main__':
    main()