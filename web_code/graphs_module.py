import numpy as np
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

def generate_comparision(labels, wins, loses):
    data = {
    'Zakład': [x for x in labels],
    'Wygrane': [x for x in wins],
    'Przegrane': [x for x in loses],
    }
    df = pd.DataFrame(data)
    sns.set_theme(style="darkgrid")

    fig, ax = plt.subplots(figsize=(10, 6))
    width = 0.35  # Szerokość słupka
    x = df.index

    bars1 = ax.bar(x - width/2, df['Wygrane'], width, label='Wygrane', color='green')
    bars2 = ax.bar(x + width/2, df['Przegrane'], width, label='Przegrane', color='orangered')

    ax.grid(False)
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{bet_type}" for bet_type in df['Zakład']])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.tick_params(colors='white', which='both', labelsize = 20)
    ax.set_facecolor('#291F1E')
    ax.legend()
    fig.patch.set_facecolor('black')

    for bars, outcomes in zip([bars1, bars2], [df['Wygrane'], df['Przegrane']]):
        for bar, outcome in zip(bars, outcomes):
            ax.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() - 1.5, 0.5), f'{int(outcome)}', 
                    ha='center', va='bottom', color='white', fontsize=20)

    # Wyświetlenie wykresu
    st.pyplot(fig)

def generate_pie_chart(data_labels, values, colors=None, title=None):
    """
    Generuje i wyświetla wykres kołowy o zmiennej liczbie segmentów przy użyciu Streamlit.
    
    Funkcja tworzy wykres kołowy przedstawiający proporcje między wartościami,
    z możliwością dostosowania etykiet, kolorów i automatycznym wyświetlaniem wartości procentowych.
    Wykres utrzymany jest w ciemnej stylistyce.
    
    Parametry:
    ----------
    data_labels : list
        Lista etykiet tekstowych dla segmentów wykresu
    values : list
        Lista wartości liczbowych dla poszczególnych segmentów
    colors : list, opcjonalne
        Lista kolorów dla segmentów (domyślnie: automatyczna paleta)
    title : str, opcjonalne
        Tytuł wykresu (domyślnie brak)
        
    Zwraca:
    -------
    None
        Funkcja wyświetla wykres bezpośrednio w interfejsie Streamlit za pomocą st.pyplot()
    
    Przykłady użycia:
    ----------------
    >>> # Wersja z dwoma segmentami
    >>> generate_pie_chart(['Wygrane gospodarzy', 'Wygrane gości'], [65, 35])
    
    >>> # Wersja z trzema segmentami
    >>> generate_pie_chart(['Wygrane gospodarzy', 'Remisy', 'Wygrane gości'], [60, 15, 25],
    >>>                   colors=['orangered', 'gold', 'lightgreen'])
    
    >>> # Wersja z własnymi kolorami i tytułem
    >>> generate_pie_chart(['Gole 1. połowa', 'Gole 2. połowa', 'Dogrywka'], [45, 50, 5],
    >>>                   colors=['#FF9999','#66B2FF','#99FF99'],
    >>>                   title="Rozkład strzelonych goli")
    """
    # Sprawdzenie poprawności danych wejściowych
    if len(data_labels) != len(values):
        raise ValueError("Liczba etykiet musi odpowiadać liczbie wartości")
    
    if colors and len(colors) != len(values):
        raise ValueError("Liczba kolorów musi odpowiadać liczbie wartości")
    
    # Domyślna paleta kolorów jeśli nie podano
    if not colors:
        colors = plt.cm.tab20c.colors[:len(values)]
    
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame({'Label': data_labels, 'Value': values})
    
    # Utworzenie wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    wedges, texts, autotexts = ax.pie(
        df['Value'], 
        labels=df['Label'], 
        autopct='%1.1f%%', 
        colors=colors,
        textprops=dict(color="white"), 
        startangle=140,
        pctdistance=0.85
    )
    
    # Dodanie tytułu jeśli podano
    if title:
        ax.set_title(title, loc='left', fontsize=24, color='white', pad=40)
    
    # Konfiguracja stylu
    fig.patch.set_facecolor('black')
    ax.axis('equal')
    
    # Dostosowanie wyglądu tekstu
    for text in texts:
        text.set_color('white')
        text.set_fontsize(20)
    
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(22)
    
    # Wyświetlenie wykresu
    st.pyplot(fig)

def highlight_cells_EV(val):
    color = 'background-color: lightgreen; color : black' if float(val) > 0.0 else ''
    return color

def highlight_cells_profit(val):
    color = 'background-color: lightgreen; color : black' if float(val) > 0.0 else 'background-color: lightcoral'
    return color

def highlight_cells_plus_minus(val):
    color = ''
    if val > 0:
        color = 'background-color: lightgreen; color : black'
    elif val < 0:
        color = 'background-color: lightcoral; color : black'
    return color

def vertical_bar_chart(date, opponent, stats, team_name, ou_line, title):
    """
    Generuje i wyświetla pionowy wykres słupkowy przedstawiający wybraną statystykę drużyny w kolejnych meczach.
    
    Funkcja tworzy interaktywny wykres z następującymi cechami:
    - Wizualizacja liczby goli w formie słupków
    - Podświetlenie wyników powyżej/poniżej ustalonej linii odniesienia
    - Automatyczne obliczenie statystyk (średnia, hit rate)
    - Ciemny motyw graficzny dopasowany do aplikacji
    
    Parametry:
    ----------
    date : list
        Lista dat meczów w formacie string (np. ['2023-01-01', '2023-01-08'])
    opponent : list
        Lista nazw drużyn przeciwnych (np. ['Team A', 'Team B'])
    stats : list
        Lista danych danej statystyki w każdym meczu (np. liczba strzelonych goli: [2, 3, 0])
    team_name : str
        Pełna nazwa analizowanej drużyny (np. 'FC Barcelona')
    ou_line : float
        Wartość linii odniesienia (over/under line) do obliczenia hit rate
    title : str
        Tytuł wykresu wyświetlany w nagłówku (np. 'Statystyki ofensywne')
    
    Zwraca:
    -------
    None
        Funkcja wyświetla wykres bezpośrednio w interfejsie Streamlit za pomocą st.pyplot()
    
    Szczegóły implementacji:
    ------------------------
    1. Przygotowanie danych:
       - Zamienia wartości 0 goli na 0.3 dla lepszej wizualizacji
       - Tworzy DataFrame z odwróconą kolejnością meczów (najnowsze na górze)
    
    2. Konfiguracja wykresu:
       - Używa stylu 'darkgrid' z biblioteki seaborn
       - Ustawia czarne tło wykresu i szare słupki domyślne
       - Dodaje linię odniesienia (ou_line) jako białą linię przerywaną
    
    3. Obliczenia statystyczne:
       - Oblicza średnią liczbę goli
       - Oblicza hit rate (% meczów powyżej linii odniesienia)
    
    4. Stylizacja:
       - Koloruje słupki: zielone powyżej linii, czerwone poniżej
       - Dodaje etykiety z dokładną liczbą goli na każdym słupku
       - Formatuje oś X jako kombinację daty i przeciwnika
       - Ustawia białe czcionki dla lepszej czytelności
    
    5. Wyświetlanie:
       - Dodaje kompleksowy tytuł ze statystykami
       - Używa dużych czcionek dla lepszej czytelności
       - Zachowuje spójną kolorystykę z aplikacją
    
    Przykład użycia:
    ----------------
    >>> dates = ['2023-01-01', '2023-01-08', '2023-01-15']
    >>> opponents = ['Team A', 'Team B', 'Team C']
    >>> stats = [2, 3, 0]
    >>> vertical_bar_chart(dates, opponents, stats, 'FC Barcelona', 1.5, 'Statystyki ofensywne')
    
    Uwagi:
    ------
    - Wartości 0 goli są zmieniane na 0.3 dla lepszej widoczności na wykresie
    - Hit rate jest obliczany jako procent meczów z liczbą goli > ou_line
    - Kolejność meczów na wykresie jest odwrócona (najnowsze u góry)
    - Wykres jest zoptymalizowany pod wyświetlanie w Streamlit
    """
    stats_graph = [0.3 if int(g) == 0 else g for g in stats] #Poprawa widocznosci (małe słupki czerwone zamiast nicości)
    stats = pd.DataFrame(stats)
    data = {
    'Date': [x for x in reversed(date)],
    'Opponent': [x for x in reversed(opponent)],
    'Stat': [x for x in reversed(stats_graph)],
    }
    df = pd.DataFrame(data)

    # Konfigurowanie stylu wykresu
    sns.set_theme(style="darkgrid")

    # Tworzenie wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df.index, df['Stat'], color='gray')
    avg_stats = np.mean(stats)
    hit_rate = (stats > ou_line).mean().iloc[0] * 100
    # Ustawienia osi
    ax.grid(False)
    ax.axhline(y=ou_line, color='white', linestyle='--', linewidth=2)
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{opponent}\n{date}" for opponent, date in zip(df['Opponent'], df['Date'])])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("{}: {} \nŚrednia: {:.1f} \nHitrate O {}: {:.1f}%".format(title, team_name, avg_stats, ou_line, hit_rate), loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny

    # Kolorowanie pasków na czerwono lub zielono
    for bar, stat in zip(bars, df['Stat']):
        if stat > ou_line:
            bar.set_color('green')
        else:
            bar.set_color('red')
        ax.text(bar.get_x() + bar.get_width() / 2, max(bar.get_height() - 0.4, 0.2), f'{int(stat)}', 
            ha='center', va='bottom', color='white', fontsize=16)

    # Wyświetlenie wykresu
    st.pyplot(fig)

def btts_bar_chart(date, opponent, btts, team_name):
    data = {
    'Date': [x for x in reversed(date)],
    'Opponent': [x for x in reversed(opponent)],
    'BTTS': [x for x in reversed(btts)],
    }
    df = pd.DataFrame(data)

    # Konfigurowanie stylu wykresu
    sns.set_theme(style="darkgrid")

    # Tworzenie wykresu goals
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df.index, df['BTTS'], color='gray')
    hit_rate = (df['BTTS'] == 1).mean() * 100
    # Ustawienia osi
    ax.grid(False)
    ax.axhline(y=0, color='white', linestyle='-', linewidth=2, label='Goal Threshold')
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{opponent}\n{date}" for opponent, date in zip(df['Opponent'], df['Date'])])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("BTTS w meczach: {} \nLiczba BTTS: {} \nHitrate BTTS: {:.1f}%".format(team_name, (df['BTTS'] == 1).sum(),  hit_rate), loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny

    # Kolorowanie pasków na czerwono lub zielono
    for bar, btts in zip(bars, df['BTTS']):
        if btts == 1:
            bar.set_color('green')
        else:
            bar.set_color('red')

    # Wyświetlenie wykresu
    st.pyplot(fig)

def graph_winner(home, draw, away):
    # Dane do wykresu
    data = {
    'Label': ["Gospodarz", "Remis", "Gość"],
    'Ppb': [home, draw, away],
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df.index, df['Ppb'], color=['lightgreen', 'lightblue', 'orangered'])
    ax.grid(False)
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Rozkład prawdopodobieństwa zdarzenia: Rezultat", loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, ppb in zip(bars, df['Ppb']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 5, f'{float(ppb)}%', 
            ha='center', va='bottom', color='black', fontsize=22)
    st.pyplot(fig)

def graph_exact_goals(goals_no):
        # Dane do wykresu
    data = {
    'Label': ["0 bramek", "1 bramka", "2 bramki", "3 bramki", "4 bramki", "5 bramek", "6 lub więcej"],
    'Ppb': [x for x in goals_no],
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df.index, df['Ppb'], color=['lightblue' for x in range(7)])
    ax.grid(False)
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 13)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Rozkład ppb. zdarzenia: Dokładna liczba bramek", loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, ppb in zip(bars, df['Ppb']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 3, f'{float(ppb)}%', 
            ha='center', va='bottom', color='black', fontsize=16)
    st.pyplot(fig)

def graph_btts(no, yes):
    # Dane do wykresu
    data = {
    'Label': ["Nie", "Tak"],
    'Ppb': [no, yes],
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df.index, df['Ppb'], color=['orangered', 'lightgreen'])
    ax.grid(False)
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Rozkład prawdopodobieństwa zdarzenia: BTTS", loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, ppb in zip(bars, df['Ppb']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 5, f'{float(ppb)}%', 
            ha='center', va='bottom', color='black', fontsize=22)
    st.pyplot(fig)

def goals_line_chart(date, opponent, goals, team_name, ou_line):
    data = {
    'Date': [x for x in reversed(date)],
    'Opponent': [x[:3] for x in reversed(opponent)],
    'Goals': [x for x in reversed(goals)],
    }
    df = pd.DataFrame(data)

    # Konfigurowanie stylu wykresu
    sns.set_theme(style="darkgrid")

    # Tworzenie wykresu goals
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df.index, df['Goals'], color='gray')
    avg_goals = df['Goals'].mean()
    hit_rate = (df['Goals'] > ou_line).mean() * 100
    # Ustawienia osi
    ax.grid(False)
    ax.axhline(y=ou_line, color='white', linestyle='-', linewidth=2)
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{opponent}\n{date}" for opponent, date in zip(df['Opponent'], df['Date'])])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Bramki w meczach: {} \nŚrednia: {:.1f} \nHitrate O {}: {:.1f}%".format(team_name, avg_goals, ou_line, hit_rate), loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny

    # Kolorowanie pasków na czerwono lub zielono
    for bar, goals in zip(bars, df['Goals']):
        if goals > ou_line:
            bar.set_color('green')
        else:
            bar.set_color('red')
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 0.25, f'{int(goals)}', 
            ha='center', va='bottom', color='black', fontsize=12)

    # Wyświetlenie wykresu
    st.pyplot(fig)

def winner_bar_chart(opponent, home_team, result, team_name):
    wins, draws, loses = 0, 0, 0
    for i in range(len(opponent)):
        if home_team[i] == team_name:
            if result[i] == '1':
                wins = wins + 1
            elif result[i] == 'X':
                draws = draws + 1
            else:
                loses = loses + 1
        else:
            if result[i] == '1':
                loses = loses + 1
            elif result[i] == 'X':
                draws = draws + 1
            else:
                wins = wins + 1
    data = {
    'Label': ["Porażki", "Remisy", "Wygrane"],
    'Results' : [loses, draws, wins]
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df.index, df['Results'], color=['orangered', 'slategrey', 'lightgreen'])
    ax.grid(False)
    ax.set_yticks(df.index)
    ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_title("Rezultaty meczów: {}".format(team_name), loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, result in zip(bars, df['Results']):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2, f'{int(result)}', 
            ha='center', va='center', color='white', fontsize=22)
    st.pyplot(fig)

def graph_ou(under, over, title):
        # Dane do wykresu
    data = {
    'Label': ["Under 2.5", "Over 2.5"],
    'Ppb': [under, over],
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(df.index, df['Ppb'], color=['orangered', 'lightgreen'])
    ax.grid(False)
    ax.set_xticks(df.index)
    ax.set_xticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_title("Rozkład prawdopodobieństwa zdarzenia: {}".format(title), loc='left', fontsize=28, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, ppb in zip(bars, df['Ppb']):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 5, f'{float(ppb)}%', 
            ha='center', va='bottom', color='black', fontsize=22)
    st.pyplot(fig)

def team_compare_graph(teams, accs, type='acc'):
    """
    Generuje poziomy wykres słupkowy porównujący dokładność predykcji lub zysk dla drużyn.
    
    Args:
        teams (list): Lista nazw drużyn (ostatni element to średnia)
        accs (list): Lista wartości dokładności/zysku odpowiadających drużynom
        type (str): Typ danych ('acc' dla dokładności, 'profit' dla zysku)
    
    Returns:
        None (wyświetla wykres przy użyciu st.pyplot)
    
    Raises:
        ValueError: Jeśli dane wejściowe są puste lub niepoprawne
    """
    # Walidacja danych wejściowych
    if not teams or not accs:
        st.warning("Brak danych do wygenerowania wykresu.")
        return
        
    if len(teams) != len(accs):
        st.error("Liczba drużyn i wartości dokładności nie zgadza się.")
        return
        
    if len(teams) == 0 or len(accs) == 0:
        st.warning("Brak danych do wygenerowania wykresu.")
        return

    try:
        num_rows = len(teams)
        # Ogranicz wysokość wykresu dla dużej liczby drużyn
        max_height = min(num_rows * 0.8, 50)  # Maksymalna wysokość 50 cali
        fig_height = min(10 + num_rows * 0.2, max_height)
        
        teams_accs = zip(teams, accs)
        average = accs[-1]
        teams_accs_sorted = sorted(teams_accs, key=lambda x: x[1])
        
        data = {
            'Label': [x[0] for x in teams_accs_sorted],
            'Results': [x[1] for x in teams_accs_sorted]
        }
        
        sns.set_theme(style="darkgrid")
        df = pd.DataFrame(data)
        
        # Utwórz wykres z zabezpieczeniem przed zbyt dużym rozmiarem
        fig, ax = plt.subplots(figsize=(10, fig_height))
        
        # Generuj kolory słupków
        colors = []
        for result in df['Results']:
            if result == average:
                colors.append('deepskyblue')
            elif result < average:
                colors.append('red')
            else:
                colors.append('green')
                
        bars = ax.barh(df.index, df['Results'], color=colors)
        
        # Konfiguracja wyglądu wykresu
        ax.grid(False)
        ax.set_yticks(df.index)
        ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize=min(20, 200/num_rows))
        ax.set_ylabel("")
        ax.set_xlabel("")
        
        title_fontsize = min(28, 300/num_rows)
        ax.set_title("Porównanie procenta dokładności predykcji" if type == 'acc' else "Porównanie zysku", 
                    loc='left', fontsize=title_fontsize, color='white')
        
        ax.tick_params(colors='white', which='both')
        ax.set_facecolor('#291F1E')
        fig.patch.set_facecolor('black')
        
        # Dodawanie wartości na słupkach
        for bar, result in zip(bars, df['Results']):
            offset = max(df['Results']) * 0.05  # Dynamiczne przesunięcie tekstu
            if type == 'profit':
                ax.text(bar.get_width() + offset, bar.get_y() + bar.get_height()/2, 
                       f'{float(result):.2f} u', ha='center', va='center', 
                       color='white', fontsize=min(22, 200/num_rows))
            else:  
                ax.text(bar.get_width() + offset, bar.get_y() + bar.get_height()/2, 
                       f'{float(result):.2f}%', ha='center', va='center', 
                       color='white', fontsize=min(22, 200/num_rows))
        
        # Automatyczne dostosowanie layoutu
        plt.tight_layout()
        st.pyplot(fig)
        
    except Exception as e:
        st.error(f"Wystąpił błąd podczas generowania wykresu: {str(e)}")


def side_bar_graph(labels, values, title):
    data = {
    'Label': [x for x in labels],
    'Results' : [x for x in values]
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df.index, df['Results'], color=['orangered', 'slategrey', 'lightgreen'])
    ax.grid(False)
    ax.set_yticks(df.index)
    ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_title(title, loc='left', fontsize=30, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, result in zip(bars, df['Results']):
        ax.text(bar.get_width() - 5, bar.get_y() + bar.get_height() / 2, f'{float(result)} %', 
            ha='center', va='center', color='black', fontsize=22)
    st.pyplot(fig)


def winner_bar_chart_v2(results, team_name):
    wins = results.count('W')
    draws = results.count('X')
    loses = results.count('L')
    data = {
    'Label': ["Porażki", "Remisy", "Wygrane"],
    'Results' : [loses, draws, wins]
    }
    sns.set_theme(style="darkgrid")
    df = pd.DataFrame(data)
    # Ustawienia wykresu
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df.index, df['Results'], color=['orangered', 'slategrey', 'lightgreen'])
    ax.grid(False)
    ax.set_yticks(df.index)
    ax.set_yticklabels([f"{label}" for label in df['Label']], fontsize = 20)
    ax.set_ylabel("")
    ax.set_xlabel("")
    ax.set_title("Rezultaty meczów: {}".format(team_name), loc='left', fontsize=24, color='white')
    ax.tick_params(colors='white', which='both')  # Ustawienia koloru tekstu na biały
    ax.set_facecolor('#291F1E')  # Ustawienia koloru tła osi na czarny
    fig.patch.set_facecolor('black')  # Ustawienia koloru tła figury na czarny
    for bar, result in zip(bars, df['Results']):
        ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2, f'{int(result)}', 
            ha='center', va='center', color='white', fontsize=22)
    st.pyplot(fig)