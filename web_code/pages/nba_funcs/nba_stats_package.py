import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def display_points_stats(league_id, season_id, conn, selected_round):
    """
    Wyświetla statystyki punktów w lidze.
    
    Args:
        league_id (int): ID ligi
        season_id (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): Wybrana runda (100 - sezon zasadniczy)
    """
    st.header("Statystyki punktów")
    
    # Pobieranie danych o punktach
    if selected_round == 100:
        round_filter = "AND m.round = 100"
    else:
        round_filter = "AND m.round != 100"
    
    query = f"""
        SELECT m.home_team_goals + m.away_team_goals as total_points,
               m.home_team_goals as home_points,
               m.away_team_goals as away_points
        FROM matches m
        WHERE m.league = %s AND m.season = %s AND m.sport_id = 3 {round_filter}
        ORDER BY m.game_date
    """
    
    points_df = pd.read_sql(query, conn, params=[league_id, season_id])
    
    if not points_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Rozkład łącznej liczby punktów")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(points_df['total_points'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax.set_xlabel('Łączna liczba punktów')
            ax.set_ylabel('Liczba meczów')
            ax.set_title('Rozkład łącznej liczby punktów w meczach')
            st.pyplot(fig)
            
            # Statystyki opisowe
            st.write(f"**Średnia punktów na mecz:** {points_df['total_points'].mean():.1f}")
            st.write(f"**Mediana:** {points_df['total_points'].median():.1f}")
            st.write(f"**Minimum:** {points_df['total_points'].min()}")
            st.write(f"**Maksimum:** {points_df['total_points'].max()}")
        
        with col2:
            st.subheader("Punkty gospodarzy vs gości")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.scatter(points_df['home_points'], points_df['away_points'], alpha=0.6)
            ax.set_xlabel('Punkty gospodarzy')
            ax.set_ylabel('Punkty gości')
            ax.set_title('Punkty gospodarzy vs gości')
            
            # Dodaj linię równości
            max_points = max(points_df['home_points'].max(), points_df['away_points'].max())
            ax.plot([0, max_points], [0, max_points], 'r--', alpha=0.5, label='Linia równości')
            ax.legend()
            st.pyplot(fig)
            
            st.write(f"**Średnia punktów gospodarzy:** {points_df['home_points'].mean():.1f}")
            st.write(f"**Średnia punktów gości:** {points_df['away_points'].mean():.1f}")
    else:
        st.write("Brak danych do wyświetlenia")

def display_shooting_stats(league_id, season_id, conn, selected_round):
    """
    Wyświetla statystyki rzutów w lidze.
    
    Args:
        league_id (int): ID ligi
        season_id (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): Wybrana runda
    """
    st.header("Statystyki rzutów")
    
    if selected_round == 100:
        round_filter = "AND m.round = 100"
    else:
        round_filter = "AND m.round != 100"
    
    query = f"""
        SELECT bma.home_team_field_goals_acc, bma.away_team_field_goals_acc,
               bma.home_team_3_p_acc, bma.away_team_3_p_acc,
               bma.home_team_ft_acc, bma.away_team_ft_acc
        FROM basketball_matches_add bma
        JOIN matches m ON bma.match_id = m.id
        WHERE m.league = %s AND m.season = %s AND m.sport_id = 3 {round_filter}
    """
    
    shooting_df = pd.read_sql(query, conn, params=[league_id, season_id])
    
    if not shooting_df.empty:
        # Usuń wiersze z wartościami -1 (brak danych)
        shooting_df = shooting_df.replace(-1, np.nan)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Skuteczność rzutów z gry")
            fg_data = pd.concat([shooting_df['home_team_field_goals_acc'], 
                               shooting_df['away_team_field_goals_acc']]).dropna()
            
            if len(fg_data) > 0:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.hist(fg_data, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
                ax.set_xlabel('Skuteczność rzutów z gry (%)')
                ax.set_ylabel('Liczba występowań')
                ax.set_title('Rozkład skuteczności rzutów z gry')
                st.pyplot(fig)
                
                st.write(f"**Średnia skuteczność:** {fg_data.mean():.1f}%")
        
        with col2:
            st.subheader("Skuteczność rzutów za 3 punkty")
            three_p_data = pd.concat([shooting_df['home_team_3_p_acc'], 
                                    shooting_df['away_team_3_p_acc']]).dropna()
            
            if len(three_p_data) > 0:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.hist(three_p_data, bins=20, alpha=0.7, color='orange', edgecolor='black')
                ax.set_xlabel('Skuteczność rzutów za 3 pkt (%)')
                ax.set_ylabel('Liczba występowań')
                ax.set_title('Rozkład skuteczności rzutów za 3 punkty')
                st.pyplot(fig)
                
                st.write(f"**Średnia skuteczność:** {three_p_data.mean():.1f}%")
    else:
        st.write("Brak danych do wyświetlenia")

def display_over_under_stats(league_id, season_id, conn, selected_round):
    """
    Wyświetla statystyki over/under dla koszykówki.
    
    Args:
        league_id (int): ID ligi
        season_id (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): Wybrana runda
    """
    st.header("Statystyki Over/Under")
    
    if selected_round == 100:
        round_filter = "AND m.round = 100"
    else:
        round_filter = "AND m.round != 100"
    
    query = f"""
        SELECT m.home_team_goals + m.away_team_goals as total_points
        FROM matches m
        WHERE m.league = %s AND m.season = %s AND m.sport_id = 3 {round_filter}
        ORDER BY m.game_date
    """
    
    points_df = pd.read_sql(query, conn, params=[league_id, season_id])
    
    if not points_df.empty:
        # Typowe linie O/U dla NBA
        ou_lines = [200, 210, 220, 230, 240]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Procent meczów Over dla różnych linii")
            
            ou_stats = []
            for line in ou_lines:
                over_count = (points_df['total_points'] > line).sum()
                total_count = len(points_df)
                over_percentage = (over_count / total_count) * 100
                ou_stats.append({'Linia': line, 'Over %': over_percentage, 'Under %': 100 - over_percentage})
            
            ou_df = pd.DataFrame(ou_stats)
            st.dataframe(ou_df, use_container_width=True)
        
        with col2:
            st.subheader("Wizualizacja Over/Under")
            
            # Wykres słupkowy pokazujący procent Over dla każdej linii
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(ou_df['Linia'], ou_df['Over %'], alpha=0.7, color='red', label='Over')
            ax.bar(ou_df['Linia'], ou_df['Under %'], bottom=ou_df['Over %'], alpha=0.7, color='blue', label='Under')
            
            ax.set_xlabel('Linia Over/Under')
            ax.set_ylabel('Procent meczów')
            ax.set_title('Rozkład Over/Under dla różnych linii')
            ax.legend()
            ax.set_ylim(0, 100)
            
            st.pyplot(fig)
    else:
        st.write("Brak danych do wyświetlenia")