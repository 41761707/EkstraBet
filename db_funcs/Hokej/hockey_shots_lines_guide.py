import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_module import db_connect

def parse_arguments():
    """
    Parsowanie argumentów wiersza poleceń.
    
    Returns:
        argparse.Namespace: Obiekt z sparsowanymi argumentami
    """
    parser = argparse.ArgumentParser(
        description='Przewodnik po liniach strzałów zawodników NHL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s --date 2025-10-28 --league 1 --season 7
  %(prog)s --date 2025-10-28 --league 1 --season 7 --top 50
  %(prog)s --date 2025-10-28 --league 1 --season 7 --event-id 191
        """
    )
    
    parser.add_argument(
        '--date',
        type=str,
        required=True,
        help='Data meczów w formacie YYYY-MM-DD (np. 2025-10-28)'
    )
    
    parser.add_argument(
        '--league',
        type=int,
        required=True,
        help='ID ligi z tabeli leagues (np. 45 dla NHL)'
    )
    
    parser.add_argument(
        '--season',
        type=int,
        required=True,
        help='ID sezonu z tabeli seasons'
    )
    
    parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='Liczba top zawodników do wyświetlenia (domyślnie: 10)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Ścieżka zapisu grafiki PNG (domyślnie: ./shots_line_guide/shots_guide_YYYY-MM-DD.png)'
    )
    
    parser.add_argument(
        '--event-id',
        type=int,
        default=190,
        help='ID zdarzenia do analizy (190 - Powyżej X strzałów, 191 - Poniżej X strzałów)'
    )
    
    args = parser.parse_args()
    
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        parser.error("Data musi być w formacie YYYY-MM-DD")
    
    if args.top < 1:
        parser.error("Wartość --top musi być większa od 0")
    
    if args.event_id not in [190, 191]:
        parser.error("Wartość --event-id musi być 190 lub 191") #TODO: Rozszerzenie o pozostałe zdarzenia
    
    return args

def get_matches_for_date(conn, date_str, league_id, season_id):
    """
    Pobiera wszystkie mecze hokejowe dla podanej daty, ligi i sezonu.
    Args:
        conn: Połączenie z bazą danych
        date_str (str): Data w formacie YYYY-MM-DD
        league_id (int): ID ligi
        season_id (int): ID sezonu
    Returns:
        pandas.DataFrame: DataFrame z meczami (kolumny: match_id, home_team_id, away_team_id, 
                         home_team_name, away_team_name, game_date)
    """
    query = """
    SELECT 
        m.ID as match_id,
        m.HOME_TEAM as home_team_id,
        m.AWAY_TEAM as away_team_id,
        ht.NAME as home_team_name,
        ht.SHORTCUT as home_team_shortcut,
        at.NAME as away_team_name,
        at.SHORTCUT as away_team_shortcut,
        m.GAME_DATE as game_date
    FROM matches m
    JOIN teams ht ON m.HOME_TEAM = ht.ID
    JOIN teams at ON m.AWAY_TEAM = at.ID
    WHERE DATE(m.GAME_DATE) = %s
        AND m.LEAGUE = %s
        AND m.SEASON = %s
        AND m.SPORT_ID = 2
    ORDER BY m.GAME_DATE
    """
    df = pd.read_sql(query, conn, params=(date_str, league_id, season_id))
    return df

def get_players_with_lines(conn, match_ids, event_id):
    """
    Pobiera zawodników wraz z liniami zakładowymi dla podanych meczów.
    Args:
        conn: Połączenie z bazą danych
        match_ids (list): Lista ID meczów
        event_id (int): ID zdarzenia (190 lub 191)
    Returns:
        pandas.DataFrame: DataFrame z zawodnikami i liniami
    """
    if not match_ids:
        return pd.DataFrame()
    match_ids_str = ','.join(map(str, match_ids))
    query = f"""
    SELECT 
        ppl.PLAYER_ID as player_id,
        ppl.MATCH_ID as match_id,
        ppl.TEAM_ID as team_id,
        ppl.LINE as line,
        ppl.ODDS as odds,
        p.COMMON_NAME as player_name,
        p.FIRST_NAME as first_name,
        p.LAST_NAME as last_name,
        p.POSITION as position,
        t.NAME as team_name,
        t.SHORTCUT as team_shortcut,
        b.NAME as bookmaker_name
    FROM player_props_lines ppl
    JOIN players p ON ppl.PLAYER_ID = p.ID
    JOIN teams t ON ppl.TEAM_ID = t.ID
    JOIN bookmakers b ON ppl.BOOKMAKER_ID = b.ID
    WHERE ppl.MATCH_ID IN ({match_ids_str})
        AND ppl.EVENT_ID = %s
        AND p.POSITION != 'G'
    """
    df = pd.read_sql(query, conn, params=(event_id,))
    return df

def get_last_10_games_stats(conn, player_id, match_date, season_id):
    """
    Pobiera statystyki ostatnich 10 meczów zawodnika przed podaną datą w ramach tego samego sezonu.
    Args:
        conn: Połączenie z bazą danych
        player_id (int): ID zawodnika
        match_date (str): Data meczu (YYYY-MM-DD)
        season_id (int): ID sezonu - zapewnia że mecze są z tego samego sezonu
    Returns:
        pandas.DataFrame: DataFrame ze statystykami SOG z ostatnich 10 meczów
    """
    query = """
    SELECT 
        hps.SOG as sog,
        m.GAME_DATE as game_date,
        m.SEASON as season
    FROM hockey_match_player_stats hps
    JOIN matches m ON hps.MATCH_ID = m.ID
    WHERE hps.PLAYER_ID = %s
        AND m.GAME_DATE <= %s
        AND m.SEASON = %s
        AND hps.SOG IS NOT NULL
        AND hps.SOG >= 0
    ORDER BY m.GAME_DATE DESC
    LIMIT 10
    """
    df = pd.read_sql(query, conn, params=(player_id, match_date, season_id))
    return df

def analyze_players(conn, players_df, match_date, season_id, event_id):
    """
    Analizuje zawodników pod kątem przekraczania linii w ostatnich 10 meczach w ramach tego samego sezonu.
    Args:
        conn: Połączenie z bazą danych
        players_df (pandas.DataFrame): DataFrame z zawodnikami i liniami
        match_date (str): Data meczu
        season_id (int): ID sezonu - zapewnia że analizujemy tylko mecze z tego samego sezonu
        event_id (int): ID zdarzenia (190 lub 191)
    Returns:
        tuple: (DataFrame z analizą zawodników, nazwa bukmachera)
    """
    results = []
    bookmaker_name = None
    for _, row in players_df.iterrows():
        player_id = row['player_id']
        line = row['line']
        if bookmaker_name is None and 'bookmaker_name' in row:
            bookmaker_name = row['bookmaker_name']
        last_games = get_last_10_games_stats(conn, player_id, match_date, season_id)
        if len(last_games) == 0:
            continue
        games_count = len(last_games)
        over_line_count = 0
        if event_id == 190:  # Powyżej X strzałów
            over_line_count = (last_games['sog'] > line).sum()
        else:  # Poniżej X strzałów
            over_line_count = (last_games['sog'] < line).sum()
        percentage = (over_line_count / games_count * 100) if games_count > 0 else 0
        results.append({
            'player_id': player_id,
            'player_name': row['player_name'],
            'team_shortcut': row['team_shortcut'],
            'position': row['position'],
            'line': line,
            'odds': row['odds'],
            'games_played': games_count,
            'over_line_count': over_line_count,
            'percentage': percentage,
            'match_id': row['match_id']
        })
    if not results:
        return pd.DataFrame(), bookmaker_name
    result_df = pd.DataFrame(results)
    # Sortowanie po procencie przekroczeń (malejąco), a następnie po liczbie przekroczeń jako drugie kryterium
    result_df = result_df.sort_values(['percentage', 'over_line_count'], ascending=[False, False])
    result_df['rank'] = range(1, len(result_df) + 1)
    return result_df, bookmaker_name

def get_color_for_percentage(percentage):
    """
    Zwraca kolor dla danego procentu przekroczeń (gradient od ciemnego do jasnego zielonego).
    Args:
        percentage (float): Procent przekroczeń (0-100)
    Returns:
        str: Kolor w formacie hex
    """
    if percentage >= 70:
        return '#2d5f3f'
    elif percentage >= 50:
        return '#3a6f4a'
    elif percentage >= 30:
        return '#4a5f4a'
    else:
        return '#3a3a3a'

def generate_table_image(data_df, output_path, date_str, event_id, bookmaker_name=None):
    """
    Generuje obraz PNG z tabelą zawodników.
    Args:
        data_df (pandas.DataFrame): DataFrame z danymi do wyświetlenia
        output_path (str): Ścieżka zapisu pliku PNG
        date_str (str): Data analizy
        event_id (int): ID zdarzenia
        bookmaker_name (str, optional): Nazwa bukmachera
    """
    if len(data_df) == 0:
        print("Brak danych do wygenerowania grafiki")
        return
    fig, ax = plt.subplots(figsize=(14, len(data_df) * 0.4 + 2))
    ax.axis('tight')
    ax.axis('off')
    fig.patch.set_facecolor('#1a1a1a')
    event_names_dict = {
        190: "Powyżej X strzałów",
        191: "Poniżej X strzałów"
    }
    event_name = event_names_dict[event_id]
    title = f'Przewodnik linii strzałów NHL - {date_str}\n{event_name} - Ranking TOP {len(data_df)} zawodników'
    ax.text(0.5, 0.98, title, transform=fig.transFigure, 
            ha='center', va='top', fontsize=16, color='white', weight='bold')
    subtitle = f'Dane z ostatnich meczów każdego zawodnika (maks. 10, tylko z aktualnego sezonu)'
    ax.text(0.5, 0.85, subtitle, transform=fig.transFigure,
            ha='center', va='top', fontsize=10, color='#888888', style='italic')
    columns = ['#', 'Zawodnik', 'Drużyna', 'Pozycja', 'Linia', 'Kurs', 'Przekroczenia', '%']
    
    table_data = []
    for idx, row in data_df.iterrows():
        table_data.append([
            int(row['rank']),
            row['player_name'],
            row['team_shortcut'],
            row['position'],
            f"{row['line']:.1f}",
            f"{row['odds']:.2f}",
            f"{int(row['over_line_count'])}/{int(row['games_played'])}",
            f"{row['percentage']:.0f}%"
        ])
    cell_colors = []
    for idx, row in data_df.iterrows():
        row_colors = []
        for col_idx in range(len(columns)):
            if col_idx in [6, 7]:
                row_colors.append(get_color_for_percentage(row['percentage']))
            else:
                row_colors.append('#2a2a2a')
        cell_colors.append(row_colors)
    header_color = '#1a1a1a'
    header_colors = [header_color] * len(columns)
    table = ax.table(cellText=table_data, colLabels=columns,
                     cellLoc='center', loc='center',
                     cellColours=cell_colors,
                     colColours=header_colors,
                     bbox=[0.05, 0.05, 0.9, 0.85])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    for (row, _), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=10)
            cell.set_facecolor(header_color)
            cell.set_edgecolor('#444444')
            cell.set_linewidth(1.5)
        else:
            cell.set_text_props(color='white')
            cell.set_edgecolor('#444444')
            cell.set_linewidth(0.5)
    
    bookmaker_info = f"Kursy: {bookmaker_name}" if bookmaker_name else "Dane: ekstrabet database"
    footer_text = f'Wygenerowano przez EkstraBet | {bookmaker_info}'
    ax.text(0.5, 0.01, footer_text, transform=fig.transFigure,
            ha='center', va='bottom', fontsize=8, color='#666666')
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#1a1a1a')
    plt.close()
    
    print(f"Grafika zapisana: {output_path}")

def main():
    """
    Główna funkcja programu.
    """
    args = parse_arguments()
    conn = None
    try:
        conn = db_connect()
        print("\nPołączono z bazą danych")

        print(f"\n[1/5] Pobieranie meczów z dnia {args.date}...")
        matches_df = get_matches_for_date(conn, args.date, args.league, args.season)
        if len(matches_df) == 0:
            print(f"BŁĄD: Nie znaleziono meczów dla podanych parametrów")
            print(f"  - Data: {args.date}")
            print(f"  - Liga ID: {args.league}")
            print(f"  - Sezon ID: {args.season}")
            return
        print(f"Znaleziono {len(matches_df)} meczów:")
        for idx, match in matches_df.iterrows():
            print(f"  - {match['home_team_shortcut']} vs {match['away_team_shortcut']}")

        print(f"\n[2/5] Pobieranie zawodników z liniami zakładowymi...")
        match_ids = matches_df['match_id'].tolist()
        players_df = get_players_with_lines(conn, match_ids, args.event_id)
        if len(players_df) == 0:
            print(f"BŁĄD: Nie znaleziono zawodników z liniami dla tych meczów")
            print(f"Sprawdź czy w tabeli player_props_lines istnieją wpisy dla:")
            print(f"  - ID meczów: {match_ids}")
            print(f"  - ID zdarzenia: {args.event_id}")
            return
        print(f"Znaleziono {len(players_df)} zawodników z liniami")
        
        print(f"\n[3/5] Analiza ostatnich meczów dla każdego zawodnika (maksymalnie 10, tylko z sezonu {args.season})...")
        analyzed_df, bookmaker_name = analyze_players(conn, players_df, args.date, args.season, int(args.event_id))
        if len(analyzed_df) == 0:
            print(f"BŁĄD: Brak danych historycznych dla zawodników")
            return
        print(f"Przeanalizowano {len(analyzed_df)} zawodników")
        if bookmaker_name:
            print(f"Bukmacher: {bookmaker_name}")
        
        print(f"\n[4/5] Filtrowanie do TOP {args.top} zawodników...")
        top_df = analyzed_df.head(args.top)
        print(f"Wybrano TOP {len(top_df)} zawodników")
        if args.output is None:
            output_path = f"./shots_line_guide/shots_guide_{args.date}.png"
        else:
            output_path = args.output
        
        print(f"\n[5/5] Generowanie grafiki PNG...")
        generate_table_image(top_df, output_path, args.date, args.event_id, bookmaker_name)
        
        print("\n" + "=" * 70)
        print("PODSUMOWANIE TOP 10:")
        print("=" * 70)
        for idx, row in top_df.head(10).iterrows():
            print(f"{int(row['rank']):2d}. {row['player_name']:25s} ({row['team_shortcut']}) - "
                  f"Linia: {row['line']:.1f}, Kurs: {row['odds']:.2f}, "
                  f"Przekroczenia: {int(row['over_line_count'])}/{int(row['games_played'])} ({row['percentage']:.0f}%)")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\nBŁĄD podczas wykonywania analizy:")
        print(f"{e}")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            print("\nZamknięto połączenie z bazą danych")

if __name__ == "__main__":
    main()
