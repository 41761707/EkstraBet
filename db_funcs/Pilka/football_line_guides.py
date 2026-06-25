import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_module import db_connect

def validate_arguments(args):
    """
    Walidacja argumentów wiersza poleceń.
    Args:
        args (argparse.Namespace): Obiekt z argumentami
        
    Raises:
        ValueError: Jeśli którykolwiek z argumentów jest nieprawidłowy
    """
    try:
        datetime.strptime(args.date_from, '%Y-%m-%d')
        datetime.strptime(args.date_to, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Daty muszą być w formacie YYYY-MM-DD")
    if args.date_from > args.date_to:
        raise ValueError("Data początkowa nie może być późniejsza niż data końcowa")
    if args.last < 1:
        raise ValueError("Wartość --last musi być większa od 0")
    analysis_modes = sum([args.btts, bool(args.over), bool(args.under), args.form])
    if analysis_modes != 1:
        raise ValueError("Musisz wybrać dokładnie jeden tryb analizy: --btts, --over, --under lub --form")
    if args.over is not None and args.over <= 0:
        raise ValueError("Wartość --over musi być większa od 0")
    if args.under is not None and args.under <= 0:
        raise ValueError("Wartość --under musi być większa od 0")

def parse_arguments():
    """
    Parsowanie argumentów wiersza poleceń.
    Returns:
        argparse.Namespace: Obiekt z sparsowanymi argumentami
    """
    parser = argparse.ArgumentParser(
        description='Przewodnik po zdarzeniach w piłce nożnej (BTTS, Over/Under, Forma)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s --date-from 2026-01-01 --date-to 2026-01-02 --btts --last 10
  %(prog)s --date-from 2026-01-01 --date-to 2026-01-02 --over 2.5 --last 10
  %(prog)s --date-from 2026-01-01 --date-to 2026-01-02 --under 2.5 --last 10
  %(prog)s --date-from 2026-01-01 --date-to 2026-01-02 --form --last 5
        """)
    parser.add_argument(
        '--date-from',
        type=str,
        required=True,
        help='Data początkowa w formacie YYYY-MM-DD (włącznie)')
    parser.add_argument(
        '--date-to',
        type=str,
        required=True,
        help='Data końcowa w formacie YYYY-MM-DD (włącznie)')
    parser.add_argument(
        '--last',
        type=int,
        default=10,
        help='Liczba ostatnich meczów do analizy (domyślnie: 10)')
    parser.add_argument(
        '--btts',
        action='store_true',
        help='Analiza zdarzenia: obie drużyny strzelą gola')
    parser.add_argument(
        '--over',
        type=float,
        default=None,
        help='Analiza zdarzenia: więcej niż X bramek (np. --over 2.5)')
    parser.add_argument(
        '--under',
        type=float,
        default=None,
        help='Analiza zdarzenia: mniej niż X bramek (np. --under 2.5)')
    parser.add_argument(
        '--form',
        action='store_true',
        help='Analiza formy drużyny (zwycięstwa, remisy, porażki)')
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Ścieżka zapisu grafiki PNG (domyślnie: ./football_line_guide/event_guide_YYYY-MM-DD.png)')
    args = parser.parse_args()
    validate_arguments(args)
    return args

def get_matches_in_date_range(conn, date_from, date_to):
    """
    Pobiera wszystkie mecze piłkarskie w podanym zakresie dat.
    Args:
        conn: Połączenie z bazą danych
        date_from (str): Data początkowa (YYYY-MM-DD)
        date_to (str): Data końcowa (YYYY-MM-DD)
    Returns:
        pandas.DataFrame: DataFrame z meczami
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
        m.GAME_DATE as game_date,
        l.NAME as league_name
    FROM matches m
    JOIN teams ht ON m.HOME_TEAM = ht.ID
    JOIN teams at ON m.AWAY_TEAM = at.ID
    JOIN leagues l ON m.LEAGUE = l.ID
    WHERE DATE(m.GAME_DATE) BETWEEN %s AND %s
        AND m.SPORT_ID = 1
        AND m.RESULT = '0'
    ORDER BY m.GAME_DATE
    """
    df = pd.read_sql(query, conn, params=(date_from, date_to))
    return df

def get_team_last_matches(conn, team_id, before_date, last_n):
    """
    Pobiera ostatnie N meczów drużyny przed podaną datą.
    Args:
        conn: Połączenie z bazą danych
        team_id (int): ID drużyny
        before_date (str): Data meczu (YYYY-MM-DD)
        last_n (int): Liczba meczów do pobrania  
    Returns:
        pandas.DataFrame: DataFrame z ostatnimi meczami drużyny
    """
    query = """
    SELECT 
        m.ID as match_id,
        m.HOME_TEAM as home_team_id,
        m.AWAY_TEAM as away_team_id,
        m.HOME_TEAM_GOALS as home_goals,
        m.AWAY_TEAM_GOALS as away_goals,
        m.RESULT as result,
        m.GAME_DATE as game_date
    FROM matches m
    WHERE (m.HOME_TEAM = %s OR m.AWAY_TEAM = %s)
        AND m.GAME_DATE < %s
        AND m.SPORT_ID = 1
        AND m.RESULT != '0'
        AND m.HOME_TEAM_GOALS IS NOT NULL
        AND m.AWAY_TEAM_GOALS IS NOT NULL
    ORDER BY m.GAME_DATE DESC
    LIMIT %s
    """
    df = pd.read_sql(query, conn, params=(team_id, team_id, before_date, last_n))
    return df

def analyze_btts(matches_df):
    """
    Analizuje zdarzenie BTTS (obie drużyny strzelą).
    Args:
        matches_df (pandas.DataFrame): DataFrame z meczami
    Returns:
        tuple: (liczba wystąpień, liczba meczów)
    """
    if len(matches_df) == 0:
        return 0, 0
    btts_count = ((matches_df['home_goals'] > 0) & (matches_df['away_goals'] > 0)).sum()
    return btts_count, len(matches_df)

def analyze_over(matches_df, threshold):
    """
    Analizuje zdarzenie Over (więcej niż X bramek).
    
    Args:
        matches_df (pandas.DataFrame): DataFrame z meczami
        threshold (float): Próg bramek
        
    Returns:
        tuple: (liczba wystąpień, liczba meczów)
    """
    if len(matches_df) == 0:
        return 0, 0
    
    over_count = ((matches_df['home_goals'] + matches_df['away_goals']) > threshold).sum()
    return over_count, len(matches_df)

def analyze_under(matches_df, threshold):
    """
    Analizuje zdarzenie Under (mniej niż X bramek).
    
    Args:
        matches_df (pandas.DataFrame): DataFrame z meczami
        threshold (float): Próg bramek
        
    Returns:
        tuple: (liczba wystąpień, liczba meczów)
    """
    if len(matches_df) == 0:
        return 0, 0
    
    under_count = ((matches_df['home_goals'] + matches_df['away_goals']) < threshold).sum()
    return under_count, len(matches_df)

def analyze_form(matches_df, team_id):
    """
    Analizuje formę drużyny (zwycięstwa, remisy, porażki).
    
    Args:
        matches_df (pandas.DataFrame): DataFrame z meczami
        team_id (int): ID drużyny
        
    Returns:
        tuple: (zwycięstwa, remisy, porażki, liczba meczów)
    """
    if len(matches_df) == 0:
        return 0, 0, 0, 0
    
    wins = 0
    draws = 0
    losses = 0
    
    for _, match in matches_df.iterrows():
        is_home = match['home_team_id'] == team_id
        result = match['result']
        
        if result == 'X':
            draws += 1
        elif (is_home and result == '1') or (not is_home and result == '2'):
            wins += 1
        else:
            losses += 1
    
    return wins, draws, losses, len(matches_df)

def get_odds_for_match(conn, match_id, event_id):
    """
    Pobiera najwyższy kurs dla danego meczu i zdarzenia.
    
    Args:
        conn: Połączenie z bazą danych
        match_id (int): ID meczu
        event_id (int): ID zdarzenia
        
    Returns:
        tuple: (kurs, nazwa bukmachera) lub (None, None)
    """
    query = """
    SELECT 
        o.ODDS as odds,
        b.NAME as bookmaker_name
    FROM odds o
    JOIN bookmakers b ON o.BOOKMAKER = b.ID
    WHERE o.MATCH_ID = %s
        AND o.EVENT = %s
    ORDER BY o.ODDS DESC
    LIMIT 1
    """
    result = pd.read_sql(query, conn, params=(match_id, event_id))
    
    if len(result) == 0:
        return None, None
    
    return result['odds'].iloc[0], result['bookmaker_name'].iloc[0]

def get_event_id_for_analysis(args):
    """
    Zwraca event_id na podstawie typu analizy.
    
    Args:
        args: Argumenty programu
        
    Returns:
        int: Event ID lub None dla formy
    """
    if args.btts:
        return 6
    elif args.over is not None:
        if args.over == 2.5:
            return 8
        else:
            return None
    elif args.under is not None:
        if args.under == 2.5:
            return 12
        else:
            return None
    elif args.form:
        return None
    return None

def analyze_matches(conn, matches_df, args):
    """
    Główna funkcja analizująca mecze dla każdej drużyny.
    
    Args:
        conn: Połączenie z bazą danych
        matches_df (pandas.DataFrame): DataFrame z meczami
        args: Argumenty programu
        
    Returns:
        pandas.DataFrame: DataFrame z wynikami analizy
    """
    results = []
    event_id = get_event_id_for_analysis(args)
    
    for _, match in matches_df.iterrows():
        match_id = match['match_id']
        game_date = match['game_date']
        league_name = match['league_name']
        
        for team_id, team_name, team_shortcut, is_home in [
            (match['home_team_id'], match['home_team_name'], match['home_team_shortcut'], True),
            (match['away_team_id'], match['away_team_name'], match['away_team_shortcut'], False)
        ]:
            last_matches = get_team_last_matches(conn, team_id, game_date, args.last)
            
            if len(last_matches) == 0:
                continue
            
            if args.btts:
                event_count, total_matches = analyze_btts(last_matches)
                event_name = f"BTTS: {team_shortcut}"
            elif args.over is not None:
                event_count, total_matches = analyze_over(last_matches, args.over)
                event_name = f"Over {args.over}: {team_shortcut}"
            elif args.under is not None:
                event_count, total_matches = analyze_under(last_matches, args.under)
                event_name = f"Under {args.under}: {team_shortcut}"
            elif args.form:
                wins, draws, losses, total_matches = analyze_form(last_matches, team_id)
                event_count = wins
                event_name = f"Forma {team_shortcut} (Z-R-P: {wins}-{draws}-{losses})"
            
            percentage = (event_count / total_matches * 100) if total_matches > 0 else 0
            
            odds = None
            bookmaker_name = None
            if event_id is not None:
                odds, bookmaker_name = get_odds_for_match(conn, match_id, event_id)
            elif args.form:
                form_event_id = 1 if is_home else 3
                odds, bookmaker_name = get_odds_for_match(conn, match_id, form_event_id)
            
            opponent_name = match['away_team_name'] if is_home else match['home_team_name']
            
            results.append({
                'match_id': match_id,
                'game_date': game_date,
                'league_name': league_name,
                'home_team': match['home_team_name'],
                'away_team': match['away_team_name'],
                'team_name': team_name,
                'team_shortcut': team_shortcut,
                'opponent_name': opponent_name,
                'is_home': is_home,
                'event_name': event_name,
                'event_count': event_count,
                'total_matches': total_matches,
                'percentage': percentage,
                'odds': odds,
                'bookmaker_name': bookmaker_name
            })
    
    if not results:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values(
        ['percentage', 'event_count', 'odds'],
        ascending=[False, False, False]
    )
    result_df['rank'] = range(1, len(result_df) + 1)
    
    return result_df

def get_color_for_percentage(percentage):
    """
    Zwraca kolor dla danego procentu wystąpień.
    
    Args:
        percentage (float): Procent wystąpień (0-100)
        
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

def generate_table_image(data_df, output_path, date_from, date_to, event_description):
    """
    Generuje obraz PNG z tabelą wyników.
    
    Args:
        data_df (pandas.DataFrame): DataFrame z danymi
        output_path (str): Ścieżka zapisu pliku PNG
        date_from (str): Data początkowa
        date_to (str): Data końcowa
        event_description (str): Opis zdarzenia
    """
    if len(data_df) == 0:
        print("Brak danych do wygenerowania grafiki")
        return
    
    fig, ax = plt.subplots(figsize=(18, len(data_df) * 0.4 + 2))
    ax.axis('tight')
    ax.axis('off')
    fig.patch.set_facecolor('#1a1a1a')
    
    title = f'Przewodnik zdarzeniowy - Piłka Nożna ({date_from} do {date_to})\n{event_description}'
    ax.text(0.5, 0.98, title, transform=fig.transFigure,
            ha='center', va='top', fontsize=16, color='white', weight='bold')
    
    subtitle = f'Analiza ostatnich meczów dla każdej drużyny'
    ax.text(0.5, 0.85, subtitle, transform=fig.transFigure,
            ha='center', va='top', fontsize=10, color='#888888', style='italic')
    
    columns = ['#', 'Data', 'Liga', 'Gospodarz', 'Gość', 'Zdarzenie', 'Częstotliwość', '%', 'Kurs']
    
    table_data = []
    for idx, row in data_df.iterrows():
        game_date_str = row['game_date'].strftime('%Y-%m-%d')
        frequency_str = f"{int(row['event_count'])}/{int(row['total_matches'])}"
        odds_str = f"{row['odds']:.2f}" if row['odds'] is not None else 'Brak'
        
        table_data.append([
            int(row['rank']),
            game_date_str,
            row['league_name'],
            row['home_team'],
            row['away_team'],
            row['event_name'],
            frequency_str,
            f"{row['percentage']:.0f}%",
            odds_str
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
    table.set_fontsize(8)
    table.scale(1, 2)
    
    for (row, _), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=9)
            cell.set_facecolor(header_color)
            cell.set_edgecolor('#444444')
            cell.set_linewidth(1.5)
        else:
            cell.set_text_props(color='white')
            cell.set_edgecolor('#444444')
            cell.set_linewidth(0.5)
    
    bookmaker_info = f"Kursy: najwyższe dostępne od bukmacherów"
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
        
        print(f"\n[1/4] Pobieranie meczów z zakresu {args.date_from} - {args.date_to}...")
        matches_df = get_matches_in_date_range(conn, args.date_from, args.date_to)
        
        if len(matches_df) == 0:
            print(f"BŁĄD: Nie znaleziono meczów dla podanych parametrów")
            print(f"  - Zakres dat: {args.date_from} do {args.date_to}")
            return
        
        print(f"Znaleziono {len(matches_df)} meczów")
        
        print(f"\n[2/4] Analiza ostatnich {args.last} meczów dla każdej drużyny...")
        analyzed_df = analyze_matches(conn, matches_df, args)
        
        if len(analyzed_df) == 0:
            print(f"BŁĄD: Brak danych historycznych dla drużyn")
            return
        
        print(f"Przeanalizowano {len(analyzed_df)} wystąpień drużyn")
        
        if args.btts:
            event_desc = "Obie drużyny strzelą (BTTS)"
            file_suffix = "btts"
        elif args.over is not None:
            event_desc = f"Powyżej {args.over} bramek"
            file_suffix = f"over_{args.over}"
        elif args.under is not None:
            event_desc = f"Poniżej {args.under} bramek"
            file_suffix = f"under_{args.under}"
        elif args.form:
            event_desc = "Forma drużyn (zwycięstwa)"
            file_suffix = "form"
        
        if args.output is None:
            os.makedirs('./football_line_guide', exist_ok=True)
            output_path = f"./football_line_guide/{file_suffix}_guide_{args.date_from}_{args.date_to}.png"
        else:
            output_path = args.output
        
        print(f"\n[3/4] Generowanie grafiki PNG...")
        generate_table_image(analyzed_df, output_path, args.date_from, args.date_to, event_desc)
        
        print("\n" + "=" * 100)
        print("PODSUMOWANIE:")
        print("=" * 100)
        for idx, row in analyzed_df.iterrows():
            game_date_str = row['game_date'].strftime('%Y-%m-%d')
            odds_str = f"{row['odds']:.2f}" if row['odds'] is not None else 'Brak'
            print(f"{int(row['rank']):2d}. {game_date_str} | {row['home_team']:25s} vs {row['away_team']:25s} | "
                  f"{row['event_name']:30s} | {int(row['event_count'])}/{int(row['total_matches'])} ({row['percentage']:.0f}%) | "
                  f"Kurs: {odds_str}")
        print("\n" + "=" * 100)
        
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
