import numpy as np
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime




def matches_list(date, home_team, home_team_score, away_team, away_team_score, team_name):
    outcome = []
    for i in range(len(date)):
        if home_team[i] == team_name:
            if home_team_score[i] > away_team_score[i]:
                outcome.append('✅')
            elif home_team_score[i] < away_team_score[i]:
                outcome.append('❌')
            else:
                outcome.append('🤝')
        else:
            if home_team_score[i] < away_team_score[i]:
                outcome.append('✅')
            elif home_team_score[i] > away_team_score[i]:
                outcome.append('❌')
            else:
                outcome.append('🤝')
    data = {
    'Data': [x for x in date],
    'Gospodarz' : [x for x in home_team],
    'Wynik' : [str(x) + "-" + str(y) for x,y in zip(home_team_score, away_team_score)],
    'Gość' : [x for x in away_team],
    'Rezultat' : [x for x in outcome]
    }
    df = pd.DataFrame(data)
    df.index = range(1, len(df) + 1)
    st.dataframe(df, use_container_width=True, hide_index=True)

def matches_list_h2h(date, home_team, home_team_score, away_team, away_team_score):
    data = {
    'Data': [x for x in date],
    'Gospodarz' : [x for x in home_team],
    'Wynik' : [str(x) + "-" + str(y) for x,y in zip(home_team_score, away_team_score)],
    'Gość' : [x for x in away_team],
    }
    df = pd.DataFrame(data)
    df.index = range(1, len(df) + 1)
    st.dataframe(df, use_container_width=True, hide_index=True)