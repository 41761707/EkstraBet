import numpy as np
import pandas as pd
import sys
import db_module
import warnings

def main():
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    conn = db_module.db_connect()
    query = "select id, stake, gambler_id from gambler_parlays where settled = 0"
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    parlay_ids = [[x[0], x[1], x[2]] for x in results]
    print(parlay_ids)
    for id in parlay_ids:
        parlay_id, stake, gambler_id = id
        profit = -1 * stake
        parlay_odds = 1
        parlay_outcome = 1
        all_concluded = 1
        query = "select e.bet_id from events_parlays e where e.parlay_id = {}".format(parlay_id)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        for event in results:
            if all_concluded:
                event_info = event[0]
                query = "select b.odds, b.outcome from bets b where b.id = {} and b.outcome is not null".format(event_info)
                cursor = conn.cursor()
                cursor.execute(query)
                results = cursor.fetchall()
                if (len(results) == 0):
                    print("Kupon: {} - nie wszystkie zdarzenia zostały jeszcze rozliczone!".format(parlay_id))
                    all_concluded = 0
                    continue
                bet_info = results[0]
                if(bet_info[1] == 0):
                    parlay_outcome = 0
                parlay_odds = round(parlay_odds * bet_info[0],2)
        if all_concluded:
            print("Kupon: {}, Kurs: {}, Czy wygrany: {}".format(parlay_id, parlay_odds, parlay_outcome))
            if parlay_outcome == 1:
                profit = round(profit + stake * parlay_odds, 2)
            sql_gambler = "update gamblers g set g.parlays_played = g.parlays_played + 1, g.parlays_won = g.parlays_won + {}, g.balance = g.balance + {} where g.id = {}".format(parlay_outcome, profit, gambler_id)
            print(sql_gambler)
            cursor = conn.cursor()
            cursor.execute(sql_gambler)
            conn.commit()
            sql_gambler_parlays = "update gambler_parlays gp set gp.settled = 1, gp.parlay_outcome = {}, gp.profit = {}, gp.parlay_odds = {} where id = {}".format(parlay_outcome, profit, parlay_odds, parlay_id)
            print(sql_gambler_parlays)
            cursor = conn.cursor()
            cursor.execute(sql_gambler_parlays)
            conn.commit()

    conn.close()

if __name__ == '__main__':
    main()