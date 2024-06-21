import numpy as np
import pandas as pd
import db_module

def main():
    pass

if __name__ == '__main__':
    main()
    conn = db_module.db_connect()
    query = "select home_team, away_team from matches where league = 5 and season = 1  order by game_date;"
    upcoming_df = pd.read_sql(query, conn)
    upcoming_np = upcoming_df.to_numpy()
    rounds = []
    iter = 0
    tmp_list = []
    for i in range(len(upcoming_np)):
        tmp_list.append([upcoming_np[i][0], upcoming_np[i][1]])
        iter = iter + 1
        if iter % 10 == 0:
            rounds.append(tmp_list[:])
            tmp_list.clear()
    for round in rounds:
        print(round)
        