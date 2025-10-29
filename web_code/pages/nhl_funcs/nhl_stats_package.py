import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import graphs_module

def get_team_shots_stats(league, season, conn, selected_round=None):
    """
    Pobiera statystyki strzałów dla wszystkich drużyn w danej lidze i sezonie.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): ID rundy (100 - sezon zasadniczy, pozostałe - playoffy)
    Returns:
        pd.DataFrame: DataFrame ze statystykami strzałów drużyn
    """
    round_filter = ""
    if selected_round is not None:
        if selected_round == 100:
            round_filter = "AND m.round = 100"
        else:
            round_filter = "AND m.round != 100"
    
    query = f'''
    SELECT 
        t.NAME as team_name,
        t.SHORTCUT as team_shortcut,
        ROUND(AVG(
            CASE 
                WHEN m.HOME_TEAM = t.ID THEN m.HOME_TEAM_SOG 
                WHEN m.AWAY_TEAM = t.ID THEN m.AWAY_TEAM_SOG 
            END), 2) as avg_shots_for,
        ROUND(AVG(
            CASE 
                WHEN m.HOME_TEAM = t.ID THEN m.AWAY_TEAM_SOG 
                WHEN m.AWAY_TEAM = t.ID THEN m.HOME_TEAM_SOG 
            END), 2) as avg_shots_against,
        COUNT(*) as matches_played
    FROM teams t
    JOIN matches m ON (m.HOME_TEAM = t.ID OR m.AWAY_TEAM = t.ID)
    WHERE m.league = {league}
        AND m.season = {season}
        AND m.RESULT != '0'
        AND m.HOME_TEAM_SOG IS NOT NULL 
        AND m.AWAY_TEAM_SOG IS NOT NULL
        {round_filter}
    GROUP BY t.ID, t.NAME, t.SHORTCUT
    ORDER BY avg_shots_for DESC
    '''
    return pd.read_sql(query, conn)

def get_team_goals_stats(league, season, conn, selected_round=None):
    """
    Pobiera statystyki bramek dla wszystkich drużyn w danej lidze i sezonie.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): ID rundy (100 - sezon zasadniczy, pozostałe - playoffy)
    Returns:
        pd.DataFrame: DataFrame ze statystykami bramek drużyn
    """
    round_filter = ""
    if selected_round is not None:
        if selected_round == 100:
            round_filter = "AND m.round = 100"
        else:
            round_filter = "AND m.round != 100"
    
    query = f'''
    SELECT 
        t.NAME as team_name,
        t.SHORTCUT as team_shortcut,
        ROUND(AVG(
            CASE 
                WHEN m.HOME_TEAM = t.ID THEN m.HOME_TEAM_GOALS 
                WHEN m.AWAY_TEAM = t.ID THEN m.AWAY_TEAM_GOALS 
            END), 2) as avg_goals_for,
        ROUND(AVG(
            CASE 
                WHEN m.HOME_TEAM = t.ID THEN m.AWAY_TEAM_GOALS 
                WHEN m.AWAY_TEAM = t.ID THEN m.HOME_TEAM_GOALS 
            END), 2) as avg_goals_against,
        COUNT(*) as matches_played
    FROM teams t
    JOIN matches m ON (m.HOME_TEAM = t.ID OR m.AWAY_TEAM = t.ID)
    WHERE m.league = {league}
        AND m.season = {season}
        AND m.RESULT != '0'
        AND m.HOME_TEAM_GOALS IS NOT NULL
        AND m.AWAY_TEAM_GOALS IS NOT NULL
        {round_filter}
    GROUP BY t.ID, t.NAME, t.SHORTCUT
    ORDER BY avg_goals_for DESC
    '''
    return pd.read_sql(query, conn)
    return pd.read_sql(query, conn)

def create_team_stats_chart(stats_df, data_type='for', stat_type='shots', title_suffix='ZA', color='#4ECDC4'):
    """
    Uniwersalna funkcja do tworzenia wykresów porównawczych dla drużyn
    Args:
        stats_df (pd.DataFrame): DataFrame ze statystykami
        data_type (str): Typ danych - 'for' lub 'against'
        stat_type (str): Typ statystyki - 'shots' lub 'goals'
        title_suffix (str): Suffix dla tytułu wykresu
        color (str): Kolor słupków
        limit (int): Limit drużyn do wyświetlenia (None = wszystkie)
    """
    if stats_df.empty:
        return
    # Wybór odpowiednich kolumn na podstawie typu statystyki 
    # TODO: To raczej do poprawienia / rozbicia na dwie metody, bo co jeśli będą inne statystyki? Bez sensu trochę
    if stat_type == 'shots':
        for_column = 'avg_shots_for'
        against_column = 'avg_shots_against'
        xlabel = 'Średnia strzałów celnych na mecz'
        title_prefix = 'Średnia strzałów celnych'
        decimal_places = 1
    else:  # goals
        for_column = 'avg_goals_for'
        against_column = 'avg_goals_against'
        xlabel = 'Średnie bramki na mecz'
        title_prefix = 'Średnie bramki'
        decimal_places = 2
    
    if data_type == 'for':
        teams_list = stats_df['team_shortcut'].tolist()
        values_list = stats_df[for_column].tolist()
        teams_values = list(zip(teams_list, values_list))
        # Dla statystyk "ZA" sortujemy malejąco (najlepsze na górze)
        teams_values_sorted = sorted(teams_values, key=lambda x: x[1])
    else:  # against
        teams_list = stats_df['team_shortcut'].tolist()
        values_list = stats_df[against_column].tolist()
        teams_values = list(zip(teams_list, values_list))
        # Dla statystyk "PRZECIW" sortujemy rosnąco (najniższe na górze są najlepsze)
        teams_values_sorted = sorted(teams_values, key=lambda x: x[1])
        # Dla wyświetlenia w odwrotnej kolejności (najlepsze na górze)
        if data_type == 'against' and stat_type == 'shots':
            teams_values_sorted = sorted(teams_values, key=lambda x: x[1], reverse=True)

    sorted_teams = [x[0] for x in teams_values_sorted]
    sorted_values = [x[1] for x in teams_values_sorted]
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(range(len(sorted_teams)), sorted_values, color=color)
    ax.set_yticks(range(len(sorted_teams)))
    ax.set_yticklabels(sorted_teams, fontsize=14)
    ax.set_xlabel(xlabel, color='white', fontsize=14)
    ax.set_title(f'{title_prefix} {title_suffix}', 
                color='white', fontsize=16, pad=20)
    
    # Stylizacja
    ax.set_facecolor('#291F1E')
    fig.patch.set_facecolor('black')
    ax.tick_params(colors='white', which='both')
    ax.grid(True, alpha=0.3)
    for bar, value in zip(bars, sorted_values):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, 
                f'{value:.{decimal_places}f}', ha='left', va='center', 
                color='white', fontsize=12)
    plt.tight_layout()
    st.pyplot(fig)

def display_shots_stats(league, season, conn, selected_round=None):
    """
    Wyświetla statystyki strzałów w formie tabeli i wykresów.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): ID rundy (100 - sezon zasadniczy, pozostałe - playoffy)
    """
    shots_df = get_team_shots_stats(league, season, conn, selected_round)
    if not shots_df.empty:
        st.markdown("### Statystyki strzałów na bramkę")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Najwyższa średnia strzałów celnych DRUŻYNY",
                f"{shots_df.iloc[0]['avg_shots_for']:.2f}",
                f"{shots_df.iloc[0]['team_name']}",
                "normal")
        with col2:
            lowest_against = shots_df.loc[shots_df['avg_shots_against'].idxmin()]
            st.metric(
                "Najniższa średnia strzałów celnych PRZECIW",
                f"{lowest_against['avg_shots_against']:.2f}",
                f"{lowest_against['team_name']}",
                "normal")
        with col3:
            avg_shots_league = shots_df['avg_shots_for'].mean()
            st.metric(
                "Średnia ligowa strzałów na mecz",
                f"{avg_shots_league:.2f}")
        
        shots_df_display = shots_df.copy()
        shots_df_display.columns = ['Drużyna', 'Skrót', 'Śr. strzały celne DRUŻYNY', 'Śr. strzały celne PRZECIW', 'Mecze']
        st.markdown("### Kompletna tabela statystyk")
        st.dataframe(
            shots_df_display,
            use_container_width=True,
            hide_index=True)
        st.markdown("### Najwięcej strzałów celnych DRUŻYNY")
        create_team_stats_chart(shots_df, data_type='for', stat_type='shots', title_suffix='DRUŻYNY', color='#4ECDC4')
        st.markdown("### Najmniej strzałów celnych PRZECIW")
        create_team_stats_chart(shots_df, data_type='against', stat_type='shots', title_suffix='PRZECIW', color='#96CEB4')
    else:
        st.warning("Brak danych o strzałach dla wybranego sezonu.")

def display_goals_stats(league, season, conn, selected_round=None):
    """
    Wyświetla statystyki bramek w formie tabeli i wykresów.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): ID rundy (100 - sezon zasadniczy, pozostałe - playoffy)
    """
    goals_df = get_team_goals_stats(league, season, conn, selected_round)
    if not goals_df.empty:
        st.markdown("### Statystyki bramek")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Najwyższa średnia bramek ZDOBYTYCH",
                f"{goals_df.iloc[0]['avg_goals_for']:.2f}",
                f"{goals_df.iloc[0]['team_name']}",
                "normal")
        with col2:
            lowest_against = goals_df.loc[goals_df['avg_goals_against'].idxmin()]
            st.metric(
                "Najniższa średnia bramek STRACONYCH",
                f"{lowest_against['avg_goals_against']:.2f}",
                f"{lowest_against['team_name']}",
                "normal")
        with col3:
            avg_goals_league = goals_df['avg_goals_for'].mean()
            st.metric(
                "Średnia ligowa bramek na mecz",
                f"{avg_goals_league:.2f}")
        # Formatowanie kolumn tabeli
        goals_df_display = goals_df.copy()
        goals_df_display.columns = ['Drużyna', 'Skrót', 'Śr. bramki STRZELONYCH', 'Śr. bramki STRACONYCH', 'Mecze']
        st.markdown("### Kompletna tabela statystyk")
        st.dataframe(
            goals_df_display,
            use_container_width=True,
            hide_index=True)       
        # Wykresy porównawcze
        st.markdown("### Średnia bramek STRZELONYCH")
        create_team_stats_chart(goals_df, data_type='for', stat_type='goals', title_suffix='STRZELONE', color='#45B7D1')
        st.markdown("### Średnia bramek STRACONYCH")
        create_team_stats_chart(goals_df, data_type='against', stat_type='goals', title_suffix='STRACONE', color='#96CEB4')
    else:
        st.warning("Brak danych o bramkach dla wybranego sezonu.")

def get_team_over_under_stats(league, season, conn, selected_round=None):
    """
    Pobiera statystyki Over/Under dla wszystkich drużyn w danej lidze i sezonie.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): ID rundy (100 - sezon zasadniczy, pozostałe - playoffy)
    Returns:
        pd.DataFrame: DataFrame ze statystykami Over/Under drużyn
    """
    round_filter = ""
    if selected_round is not None:
        if selected_round == 100:
            round_filter = "AND m.round = 100"
        else:
            round_filter = "AND m.round != 100"
    
    query = f'''
    SELECT 
        t.NAME as team_name,
        t.SHORTCUT as team_shortcut,
        COUNT(*) as total_matches,
        SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 4 THEN 1 ELSE 0 END) as over_4_5,
        SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 5 THEN 1 ELSE 0 END) as over_5_5,
        SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 6 THEN 1 ELSE 0 END) as over_6_5,
        SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 7 THEN 1 ELSE 0 END) as over_7_5,
        ROUND(SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as over_4_5_pct,
        ROUND(SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 5 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as over_5_5_pct,
        ROUND(SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 6 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as over_6_5_pct,
        ROUND(SUM(CASE WHEN (m.HOME_TEAM_GOALS + m.AWAY_TEAM_GOALS) > 7 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as over_7_5_pct
    FROM teams t
    JOIN matches m ON (m.HOME_TEAM = t.ID OR m.AWAY_TEAM = t.ID)
    WHERE m.league = {league}
        AND m.season = {season}
        AND m.RESULT != '0'  -- tylko rozegrane mecze
        AND m.HOME_TEAM_GOALS IS NOT NULL
        AND m.AWAY_TEAM_GOALS IS NOT NULL
        {round_filter}
    GROUP BY t.ID, t.NAME, t.SHORTCUT
    ORDER BY over_5_5_pct DESC
    '''
    return pd.read_sql(query, conn)

def get_league_goals_distribution(league, season, conn, selected_round=None):
    """
    Pobiera rozkład bramek w meczach dla całej ligi.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): ID rundy (100 - sezon zasadniczy, pozostałe - playoffy)
    Returns:
        dict: Słownik z liczbą meczów dla różnych kategorii bramek
    """
    round_filter = ""
    if selected_round is not None:
        if selected_round == 100:
            round_filter = "AND m.round = 100"
        else:
            round_filter = "AND m.round != 100"
    
    query = f'''
    SELECT 
        COUNT(*) as total_matches,
        SUM(CASE WHEN (HOME_TEAM_GOALS + AWAY_TEAM_GOALS) < 5 THEN 1 ELSE 0 END) as under_5,
        SUM(CASE WHEN (HOME_TEAM_GOALS + AWAY_TEAM_GOALS) = 5 THEN 1 ELSE 0 END) as exactly_5,
        SUM(CASE WHEN (HOME_TEAM_GOALS + AWAY_TEAM_GOALS) = 6 THEN 1 ELSE 0 END) as exactly_6,
        SUM(CASE WHEN (HOME_TEAM_GOALS + AWAY_TEAM_GOALS) = 7 THEN 1 ELSE 0 END) as exactly_7,
        SUM(CASE WHEN (HOME_TEAM_GOALS + AWAY_TEAM_GOALS) >= 8 THEN 1 ELSE 0 END) as over_7
    FROM matches m
    WHERE m.league = {league}
        AND m.season = {season}
        AND m.RESULT != '0'
        AND m.HOME_TEAM_GOALS IS NOT NULL
        AND m.AWAY_TEAM_GOALS IS NOT NULL
        {round_filter}
    '''
    result = pd.read_sql(query, conn)
    return result.iloc[0].to_dict() if not result.empty else {}

def create_goals_distribution_chart(league_stats):
    """
    Tworzy wykres kołowy rozkładu bramek w lidze.
    Args:
        league_stats (dict): Słownik ze statystykami ligowymi
    """
    if not league_stats:
        return
    
    labels = ['Mniej niż 5', 'Dokładnie 5', 'Dokładnie 6', 'Dokładnie 7', 'Więcej niż 7']
    values = [
        league_stats['under_5'],
        league_stats['exactly_5'], 
        league_stats['exactly_6'],
        league_stats['exactly_7'],
        league_stats['over_7']]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
    graphs_module.generate_pie_chart(labels, values, colors, "Rozkład bramek w meczach")

def create_over_under_comparison_chart(ou_df):
    """
    Tworzy wykres porównujący procenty Over 5.5 dla drużyn.
    Args:
        ou_df (pd.DataFrame): DataFrame ze statystykami Over/Under
    """
    if ou_df.empty:
        return
    teams_list = ou_df['team_shortcut'].tolist()
    ou_percentages = ou_df['over_5_5_pct'].tolist()
    # Tworzenie wykresu
    fig, ax = plt.subplots(figsize=(10, 8))
    teams_ou = list(zip(teams_list, ou_percentages))
    teams_ou_sorted = sorted(teams_ou, key=lambda x: x[1])
    sorted_teams = [x[0] for x in teams_ou_sorted]
    sorted_percentages = [x[1] for x in teams_ou_sorted]
    # Kolorowanie na podstawie procentów
    colors = ['#FF6B6B' if p >= 60 else '#4ECDC4' if p >= 50 else '#96CEB4' for p in sorted_percentages]
    bars = ax.barh(range(len(sorted_teams)), sorted_percentages, color=colors)
    ax.set_yticks(range(len(sorted_teams)))
    ax.set_yticklabels(sorted_teams, fontsize=12)
    ax.set_xlabel('Procent meczów Over 5.5 (%)', color='white', fontsize=12)
    ax.set_title('Procent meczów Over 5.5 (%)', color='white', fontsize=14)
    ax.set_facecolor('#291F1E')
    fig.patch.set_facecolor('black')
    ax.tick_params(colors='white', which='both')
    ax.grid(True, alpha=0.3)
    
    # Dodawanie linii średniej ligowej
    avg_ou = ou_df['over_5_5_pct'].mean()
    ax.axvline(x=avg_ou, color='yellow', linestyle='--', alpha=0.7, linewidth=2, label=f'Średnia: {avg_ou:.1f}%')
    ax.legend(fontsize=10)
    for bar, value in zip(bars, sorted_percentages):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                f'{value:.1f}%', ha='left', va='center', 
                color='white', fontsize=10)
    plt.tight_layout()
    st.pyplot(fig)

def create_over_under_multi_chart(ou_df):
    """
    Tworzy wykres porównujący różne linie Over/Under dla top 10 drużyn.
    Args:
        ou_df (pd.DataFrame): DataFrame ze statystykami Over/Under
    """
    if ou_df.empty:
        return
    top_10_ou = ou_df.head(10)
    teams = top_10_ou['team_shortcut'].tolist()
    over_45 = top_10_ou['over_4_5_pct'].tolist()
    over_55 = top_10_ou['over_5_5_pct'].tolist()
    over_65 = top_10_ou['over_6_5_pct'].tolist()
    over_75 = top_10_ou['over_7_5_pct'].tolist()
    sns.set_theme(style="darkgrid")
    fig, ax = plt.subplots(figsize=(14, 8))
    x = range(len(teams))
    width = 0.2
    bars1 = ax.bar([i - 1.5*width for i in x], over_45, width, label='Over 4.5', color='#FF6B6B', alpha=0.8)
    bars2 = ax.bar([i - 0.5*width for i in x], over_55, width, label='Over 5.5', color='#4ECDC4', alpha=0.8)
    bars3 = ax.bar([i + 0.5*width for i in x], over_65, width, label='Over 6.5', color='#45B7D1', alpha=0.8)
    bars4 = ax.bar([i + 1.5*width for i in x], over_75, width, label='Over 7.5', color='#96CEB4', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(teams, rotation=45, ha='right')
    ax.set_ylabel('Procent meczów (%)', color='white', fontsize=14)
    ax.set_title('Porównanie różnych linii Over/Under - Top 10 drużyn', 
                color='white', fontsize=16, pad=20)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    # Stylizacja
    ax.set_facecolor('#291F1E')
    fig.patch.set_facecolor('black')
    ax.tick_params(colors='white', which='both')
    for bar, value in zip(bars2, over_55):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{value:.1f}%', ha='center', va='bottom', 
                color='white', fontsize=10)
    plt.tight_layout()
    st.pyplot(fig)

def display_over_under_stats(league, season, conn, selected_round=None):
    """
    Wyświetla statystyki Over/Under w formie tabeli, wykresów oraz statystyk ligowych.
    Args:
        league (int): ID ligi
        season (int): ID sezonu
        conn: Połączenie z bazą danych
        selected_round (int): ID rundy (100 - sezon zasadniczy, pozostałe - playoffy)
    """
    ou_df = get_team_over_under_stats(league, season, conn, selected_round)
    league_stats = get_league_goals_distribution(league, season, conn, selected_round)
    if not ou_df.empty:
        st.subheader("Statystyki Over/Under")
        if league_stats:
            st.markdown("### Rozkład bramek w lidze")
            col1, col2, col3, col4, col5 = st.columns(5)
            total = league_stats['total_matches']
            with col1:
                st.metric(
                    "Mniej niż 5 bramek",
                    league_stats['under_5'],
                    f"{int(league_stats['under_5']/total*100)}%",
                    "normal")
            with col2:
                st.metric(
                    "Dokładnie 5 bramek",
                    league_stats['exactly_5'],
                    f"{int(league_stats['exactly_5']/total*100)}%",
                    "normal")
            with col3:
                st.metric(
                    "Dokładnie 6 bramek",
                    league_stats['exactly_6'],
                    f"{int(league_stats['exactly_6']/total*100)}%",
                    "normal")
            with col4:
                st.metric(
                    "Dokładnie 7 bramek",
                    league_stats['exactly_7'],
                    f"{int(league_stats['exactly_7']/total*100)}%",
                    "normal")
            with col5:
                st.metric(
                    "8+ bramek",
                    league_stats['over_7'],
                    f"{int(league_stats['over_7']/total*100)}%",
                    "normal")
            st.markdown("### Wizualny rozkład bramek w lidze")
            create_goals_distribution_chart(league_stats)
        
        # Wykresy porównawcze drużyn
        #TODO: TO najlepiej przenieść dla każdej drużyny w ich sekcji - będzie
        #st.markdown("Top 10 - najwyższy % Over 5.5")
        create_over_under_comparison_chart(ou_df)

        st.markdown("### Rekordziści")
        col1, col2, col3 = st.columns(3)
        with col1:
            best_over_55 = ou_df.loc[ou_df['over_5_5_pct'].idxmax()]
            st.metric(
                "Najwyższy % Over 5.5",
                f"{best_over_55['over_5_5_pct']:.1f}%",
                f"{best_over_55['team_shortcut']}",
                "normal")
        with col2:
            worst_over_55 = ou_df.loc[ou_df['over_5_5_pct'].idxmin()]
            st.metric(
                "Najniższy % Over 5.5",
                f"{worst_over_55['over_5_5_pct']:.1f}%",
                f"{worst_over_55['team_shortcut']}",
                "normal")
        with col3:
            avg_over_55 = ou_df['over_5_5_pct'].mean()
            st.metric(
                "Średni % Over 5.5 w lidze",
                f"{avg_over_55:.1f}%",
                "normal")
        # Wielokolumnowy wykres porównujący wszystkie linie O/U
        #TODO: Przenieść ten widok dla poszczególnych drużyn do osobnej sekcji?
        #st.markdown("### 📊 Porównanie wszystkich linii Over/Under")
        #create_over_under_multi_chart(ou_df)
        st.markdown("Szczegółowe statystyki Over/Under według drużyn")
        ou_df_display = ou_df.copy()
        ou_df_display['over_4_5_combined'] = ou_df_display.apply(
            lambda row: f"{int(row['over_4_5'])} ({row['over_4_5_pct']:.1f}%)", axis=1)
        ou_df_display['over_5_5_combined'] = ou_df_display.apply(
            lambda row: f"{int(row['over_5_5'])} ({row['over_5_5_pct']:.1f}%)", axis=1)
        ou_df_display['over_6_5_combined'] = ou_df_display.apply(
            lambda row: f"{int(row['over_6_5'])} ({row['over_6_5_pct']:.1f}%)", axis=1)
        ou_df_display['over_7_5_combined'] = ou_df_display.apply(
            lambda row: f"{int(row['over_7_5'])} ({row['over_7_5_pct']:.1f}%)", axis=1)
        # Wybór tylko potrzebnych kolumn
        ou_df_display = ou_df_display[[
            'team_name', 'team_shortcut', 'total_matches',
            'over_4_5_combined', 'over_5_5_combined', 
            'over_6_5_combined', 'over_7_5_combined']]
        ou_df_display.columns = [
            'Drużyna', 'Skrót', 'Mecze',
            'Over 4.5', 'Over 5.5', 'Over 6.5', 'Over 7.5']
        st.dataframe(
            ou_df_display,
            use_container_width=True,
            hide_index=True)
    else:
        st.warning("Brak danych o bramkach dla wybranego sezonu.")
