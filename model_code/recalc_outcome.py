import numpy as np
import pandas as pd
import sys
import db_module
import warnings

def main():
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    conn = db_module.db_connect()
    query = "select m.id as match_id, p.id as predict, p.event_id as event, m.result as result, m.home_team_goals as home, m.away_team_goals as away from predictions p join matches m on p.match_id = m.id where outcome is null and m.result != '0' and p.outcome is null and p.is_final = 1"
    null_outcome_df = pd.read_sql(query, conn)
    for _, row in null_outcome_df.iterrows():
        outcome = 0
        goals = row['home'] + row['away']
        btts = 1 if row['home'] > 0 and row['away'] > 0 else 0
        if row['event'] == 8 and goals > 2.5:
            outcome = 1
        if row['event'] == 12 and goals < 2.5:
             outcome = 1
        if row['event'] == 1 and row['result'] == '1':
            outcome = 1
        if row['event'] == 2 and row['result'] == 'X':
            outcome = 1
        if row['event'] == 3 and row['result'] == '2':
            outcome = 1
        if row['event'] == 6 and btts == 1:
            outcome = 1
        if row['event'] == 172 and btts == 0:
            outcome = 1
        print("update predictions set outcome = {} where id = {};".format(outcome, row['predict']))
    
    query = "select m.id as match_id, f.id as predict, f.event_id as event, m.result as result, m.home_team_goals as home, m.away_team_goals as away from bets f join matches m on f.match_id = m.id where outcome is null and m.result != '0'"
    null_outcome_df = pd.read_sql(query, conn)
    for _, row in null_outcome_df.iterrows():
        outcome = 0
        goals = row['home'] + row['away']
        btts = 1 if row['home'] > 0 and row['away'] > 0 else 0
        if row['event'] == 8 and goals > 2.5:
            outcome = 1
        if row['event'] == 12 and goals < 2.5:
             outcome = 1
        if row['event'] == 1 and row['result'] == '1':
            outcome = 1
        if row['event'] == 2 and row['result'] == 'X':
            outcome = 1
        if row['event'] == 3 and row['result'] == '2':
            outcome = 1
        if row['event'] == 6 and btts == 1:
            outcome = 1
        if row['event'] == 172 and btts ==0:
            outcome = 1
        print("update bets set outcome = {} where id = {};".format(outcome, row['predict']))

if __name__ == '__main__':
    main()