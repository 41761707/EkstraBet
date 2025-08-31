import numpy as np
import pandas as pd
from db_module import db_connect
import warnings
import argparse
from utils import update_db

def get_pred(event_id: int, conn, match_id: int) -> list[tuple[float, int]]:
    """ Pobiera predykcje dla danego zdarzenia i meczu z bazy danych dla wszystkich aktywnych modeli.
    Args:
        event_id (int): ID zdarzenia (np. 1 - wygrana gospodarzy, 2 - remis, 3 - wygrana gości itp.).
        conn: Połączenie do bazy danych.
        match_id (int): ID meczu.

    Zwraca:
        list[tuple[float, int]]: Lista krotek (wartość_predykcji, model_id) dla wszystkich aktywnych modeli.
    """
    query = f"""
    SELECT p.value, p.model_id 
    FROM predictions p 
    JOIN models m ON p.model_id = m.id 
    WHERE p.match_id = {match_id} AND p.event_id = {event_id} AND m.active = 1
    """
    result = pd.read_sql(query, conn)
    return [(row['value'], row['model_id']) for _, row in result.iterrows()]

def model_odds(val: float) -> list:
    """ Funkcja pomocnicza do przeliczenia wartości kursu na prawdopodobieństwo.
    Args: 
        val (float): Wartość kursu.
    Returns:
        list: Lista z jednym elementem - prawdopodobieństwem w procentach.
    """
    return [round(100 / val, 2) if val else 0]

def calc_ev(pred: float, odds: list) -> float:
    """Funkcja do obliczania wartości oczekiwanej (EV) dla danego predykcji i kursów bukmacherskich.
    Args:
        pred (float): Predykcja prawdopodobieństwa danego zdarzenia.
        odds (list): Lista kursów bukmacherskich dla danego zdarzenia.
    Returns:
        float: Wartość oczekiwana (EV) dla danego zdarzenia.
    """
    return round((pred or 0) * max(odds[1:], default=0) - 1, 2)

def generate_predictions(conn, query: str, automate: bool) -> None:
    """
    Generuje predykcje i wylicza EV dla wszystkich meczów danej ligi i sezonu rozgrywanych dzisiaj.
    Wyniki zapisuje do tabeli bets, jeśli automate == True.
    Tworzy zakłady dla każdego aktywnego modelu osobno.

    Args:
        conn: Połączenie do bazy danych.
        query (str): Zapytanie SQL do pobrania meczów.
        automate (bool): Flaga automatycznego zapisu do bazy (True = zapisuj).
    """
    # Pobierz wszystkie mecze dzisiaj dla danej ligi i sezonu
    matches_id = pd.read_sql(query, conn)["id"].tolist()
    bookie_dict = {
        'USTALONE': 0, 
        'Superbet': 1, 
        'Betclic': 2, 
        'Fortuna': 3,
        'STS': 4, 
        'LvBet': 5, 
        'Betfan': 6, 
        'Etoto': 7, 
        'Fuksiarz': 8
        }
    inserts = []
    active_models = pd.read_sql("SELECT id FROM models WHERE active = 1", conn)["id"].tolist()
    for match_id in matches_id:
        # Pobierz predykcje dla wszystkich aktywnych modeli
        home_win_preds = get_pred(1, conn, match_id)
        draw_preds = get_pred(2, conn, match_id)
        guest_win_preds = get_pred(3, conn, match_id)
        btts_yes_preds = get_pred(6, conn, match_id)
        btts_no_preds = get_pred(172, conn, match_id)
        over_2_5_preds = get_pred(8, conn, match_id)
        under_2_5_preds = get_pred(12, conn, match_id)
        odds_query = ("SELECT b.name AS bookmaker, o.event AS event, o.odds AS odds "
            "FROM odds o JOIN bookmakers b ON o.bookmaker = b.id "
            f"WHERE match_id = {match_id}")
        odds_details = pd.read_sql(odds_query, conn)      
        # Przygotuj słowniki kursów dla każdego zdarzenia
        event_odds = {}
        for event_id in [1, 2, 3, 6, 172, 8, 12]:
            event_odds[event_id] = [0] * len(bookie_dict)
        for _, row in odds_details.iterrows():
            idx = bookie_dict.get(row.bookmaker, 0)
            if row.event in event_odds:
                event_odds[row.event][idx] = row.odds
        for model_id in active_models:
            # Znajdź predykcje tego modelu dla każdego typu zdarzenia
            model_predictions = {
                'result': {},  # home_win, draw, guest_win
                'btts': {},    # btts_yes, btts_no
                'ou': {}       # over_2_5, under_2_5
            }
            for pred_value, pred_model_id in home_win_preds:
                if pred_model_id == model_id:
                    model_predictions['result'][1] = pred_value
            for pred_value, pred_model_id in draw_preds:
                if pred_model_id == model_id:
                    model_predictions['result'][2] = pred_value
            for pred_value, pred_model_id in guest_win_preds:
                if pred_model_id == model_id:
                    model_predictions['result'][3] = pred_value
            for pred_value, pred_model_id in btts_yes_preds:
                if pred_model_id == model_id:
                    model_predictions['btts'][6] = pred_value
            for pred_value, pred_model_id in btts_no_preds:
                if pred_model_id == model_id:
                    model_predictions['btts'][172] = pred_value
            for pred_value, pred_model_id in over_2_5_preds:
                if pred_model_id == model_id:
                    model_predictions['ou'][8] = pred_value
            for pred_value, pred_model_id in under_2_5_preds:
                if pred_model_id == model_id:
                    model_predictions['ou'][12] = pred_value

            # Stwórz zakłady dla najlepszych predykcji tego modelu
            if model_predictions['result']:
                best_result_event = max(model_predictions['result'], key=model_predictions['result'].get)
                best_result_value = model_predictions['result'][best_result_event]
                
                if best_result_value > 0:
                    odds_with_model = model_odds(best_result_value) + event_odds[best_result_event][1:]
                    ev = calc_ev(best_result_value, odds_with_model)
                    best_odds = max(odds_with_model[1:], default=0)
                    bookmaker = np.argmax(odds_with_model[1:]) + 1 if len(odds_with_model) > 1 else 0
                    
                    sql = (
                        "INSERT INTO bets(match_id, event_id, odds, bookmaker, EV, model_id) "
                        f"VALUES ({match_id}, {best_result_event}, {best_odds}, {bookmaker}, {ev}, {model_id});"
                    )
                    print(sql)
                    inserts.append(sql)

            if model_predictions['btts']:
                best_btts_event = max(model_predictions['btts'], key=model_predictions['btts'].get)
                best_btts_value = model_predictions['btts'][best_btts_event]
                
                if best_btts_value > 0:
                    odds_with_model = model_odds(best_btts_value) + event_odds[best_btts_event][1:]
                    ev = calc_ev(best_btts_value, odds_with_model)
                    best_odds = max(odds_with_model[1:], default=0)
                    bookmaker = np.argmax(odds_with_model[1:]) + 1 if len(odds_with_model) > 1 else 0
                    
                    sql = (
                        "INSERT INTO bets(match_id, event_id, odds, bookmaker, EV, model_id) "
                        f"VALUES ({match_id}, {best_btts_event}, {best_odds}, {bookmaker}, {ev}, {model_id});"
                    )
                    print(sql)
                    inserts.append(sql)
            
            if model_predictions['ou']:
                best_ou_event = max(model_predictions['ou'], key=model_predictions['ou'].get)
                best_ou_value = model_predictions['ou'][best_ou_event]
                
                if best_ou_value > 0:
                    odds_with_model = model_odds(best_ou_value) + event_odds[best_ou_event][1:]
                    ev = calc_ev(best_ou_value, odds_with_model)
                    best_odds = max(odds_with_model[1:], default=0)
                    bookmaker = np.argmax(odds_with_model[1:]) + 1 if len(odds_with_model) > 1 else 0
                    
                    sql = (
                        "INSERT INTO bets(match_id, event_id, odds, bookmaker, EV, model_id) "
                        f"VALUES ({match_id}, {best_ou_event}, {best_odds}, {bookmaker}, {ev}, {model_id});"
                    )
                    print(sql)
                    inserts.append(sql)
                    
    if automate:
        update_db(inserts, conn)

def bet_to_automate(mode: str, league_id: int, season_id: int, round_num: int = None, date_from: str = None, date_to: str = None, match_id: int = None, automate: bool = False) -> None:
    """
    Generuje zakłady według wybranego trybu:
    - 'today': generuje zakłady na dziś
    - 'round': generuje zakłady dla wskazanej rundy
    - 'date_range': generuje zakłady dla wskazanego przedziału czasowego
    - 'match': generuje zakłady dla podanych id meczów
    Wszystko odbywa się na podstawie wybranej ligi i sezonu (nie ma na ten moment betowania ogólnego).
    Args:
        mode (str): Typ generowania ('today', 'round', 'date_range', 'match')
        league_id (int, optional): ID ligi
        season_id (int, optional): ID sezonu
        round_num (int, optional): Numer rundy
        date_from (str, optional): Data początkowa (format 'YYYY-MM-DD')
        date_to (str, optional): Data końcowa (format 'YYYY-MM-DD')
        match_id (int, optional): ID meczu (dla trybu 'match')
        automate (bool): Czy automatycznie zapisywać zmiany do bazy danych
    """
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    conn = db_connect()
    if mode == 'today':
        query = f"SELECT id FROM matches WHERE league = {league_id} AND season = {season_id} AND CAST(game_date AS DATE) = CURRENT_DATE"
    elif mode == 'round':
        query = f"SELECT id FROM matches WHERE league = {league_id} AND season = {season_id} AND round = {round_num}"
    elif mode == 'date_range':
        query = f"SELECT id FROM matches WHERE league = {league_id} AND season = {season_id} AND CAST(game_date AS DATE) BETWEEN '{date_from}' AND '{date_to}'"
    elif mode == 'match':
        query = f"SELECT id FROM matches WHERE id = {match_id}" #Trochę redundancja, ale niech będzie
    generate_predictions(conn, query, automate)
    conn.close()

def main() -> None:
    """Główna funkcja do uruchomienia skryptu."""
    parser = argparse.ArgumentParser(
        description=(
            "Generuje zakłady według wybranego trybu dla wybranej ligi i sezonu.\n"
            "\nPrzykłady użycia:\n"
            "  python bet_all.py today 1 11\n"
            "  python bet_all.py today 1 11 --automate\n"
            "  python bet_all.py round 1 11 --round_num 5\n"
            "  python bet_all.py round 1 11 --round_num 5 --automate\n"
            "  python bet_all.py date_range 1 11 --date_from 2024-07-01 --date_to 2024-07-20\n"
            "  python bet_all.py date_range 1 11 --date_from 2024-07-01 --date_to 2024-07-20 --automate\n"
            "  python bet_all.py match 1 11 --match 12345\n"
            "  python bet_all.py match 1 11 --match 12345 --automate\n"
            "\nUwaga: Bez flagi --automate zakłady będą tylko wyświetlane, ale nie zapisywane do bazy.\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("mode", choices=["today", "round", "date_range", "match"], help="Tryb generowania zakładów")
    parser.add_argument("league_id", type=int, help="ID ligi")
    parser.add_argument("season_id", type=int, help="ID sezonu")
    parser.add_argument("--round_num", type=int, default=None, help="Numer rundy (wymagane dla trybu 'round')")
    parser.add_argument("--date_from", type=str, default=None, help="Data początkowa (format 'YYYY-MM-DD', wymagane dla trybu 'date_range')")
    parser.add_argument("--date_to", type=str, default=None, help="Data końcowa (format 'YYYY-MM-DD', wymagane dla trybu 'date_range')")
    parser.add_argument("--match", type=int, default=None, help="ID meczu (wymagane dla trybu 'match')")
    parser.add_argument("--automate", action="store_true", help="Automatycznie zapisuj zakłady do bazy danych (bez tej flagi będą tylko wyświetlane)")
    args = parser.parse_args()
    # Walidacja parametrów w zależności od trybu
    if args.mode == "round" and args.round_num is None:
        parser.error("W trybie 'round' wymagany jest parametr --round_num.")
    if args.mode == "date_range" and (args.date_from is None or args.date_to is None):
        parser.error("W trybie 'date_range' wymagane są parametry --date_from oraz --date_to.")
    if args.mode == "match" and args.match is None:
        parser.error("W trybie 'match' wymagany jest parametr --match (pojedynczy id meczu).")
    bet_to_automate(
        mode=args.mode,
        league_id=args.league_id,
        season_id=args.season_id,
        round_num=args.round_num,
        date_from=args.date_from,
        date_to=args.date_to,
        match_id=args.match,
        automate=args.automate
    )

if __name__ == "__main__":
    main()