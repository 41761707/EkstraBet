import numpy as np
import pandas as pd
import sys
import db_module
import warnings
import argparse
from utils import update_db

def get_pred(event_id: int, conn, match_id: int)  -> tuple[int, int] | tuple[None, None]:
    """ Pobiera predykcję dla danego zdarzenia i meczu z bazy danych.
    Args:
        event_id (int): ID zdarzenia (np. 1 - wygrana gospodarzy, 2 - remis, 3 - wygrana gości itp.).
        conn: Połączenie do bazy danych.
        match_id (int): ID meczu.

    Zwraca:
        tuple[int, int] | tuple[None, None]: Wartość predykcji i ID modelu lub (None, None) jeśli brak.
    """
    query = f"SELECT value, model_id FROM predictions WHERE match_id = {match_id} AND event_id = {event_id}"
    result = pd.read_sql(query, conn).to_numpy()
    return result[0] if len(result) > 0 else (None, None)

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

def generate_predictions(conn, query: str, to_automate: int) -> None:
    """
    Generuje predykcje i wylicza EV dla wszystkich meczów danej ligi i sezonu rozgrywanych dzisiaj.
    Wyniki zapisuje do tabeli bets, jeśli to_automate == 1.

    Args:
        conn: Połączenie do bazy danych.
        query (str): Zapytanie SQL do pobrania meczów.
        to_automate (int): Flaga automatycznego zapisu do bazy (1 = zapisuj).
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
    #W pętli dla każdego meczu
    # Pobrać wszystkie wpisy z tabeli "predictions" dla powyższych parametrów
    # Pobrać wszystkie wpisy z tabeli "odds" dla powyższych parametrów
    for match_id in matches_id:
        home_win, home_win_model = get_pred(1, conn, match_id)
        draw, draw_model = get_pred(2, conn, match_id)
        guest_win, guest_win_model = get_pred(3, conn, match_id)
        btts_yes, btts_yes_model = get_pred(6, conn, match_id)
        btts_no, btts_no_model = get_pred(172, conn, match_id)
        over_2_5, over_2_5_model = get_pred(8, conn, match_id)
        under_2_5, under_2_5_model = get_pred(12, conn, match_id)
        goals_pred = []
        for event_id in range(174, 181):
            val, _ = get_pred(event_id, conn, match_id)
            goals_pred.append(val if val is not None else 0)

        # Pobierz kursy bukmacherów dla danego meczu
        odds_query = ("SELECT b.name AS bookmaker, o.event AS event, o.odds AS odds "
            "FROM odds o JOIN bookmakers b ON o.bookmaker = b.id "
            f"WHERE match_id = {match_id}")
        odds_details = pd.read_sql(odds_query, conn)
        home_win_odds = [0] * len(bookie_dict)
        draw_odds = [0] * len(bookie_dict)
        guest_win_odds = [0] * len(bookie_dict)
        btts_yes_odds = [0] * len(bookie_dict)
        btts_no_odds = [0] * len(bookie_dict)
        over_odds = [0] * len(bookie_dict)
        under_odds = [0] * len(bookie_dict)

        # Uzupełnij kursy z bazy
        for _, row in odds_details.iterrows():
            idx = bookie_dict.get(row.bookmaker, 0)
            if row.event == 1:
                home_win_odds[idx] = row.odds
            elif row.event == 2:
                draw_odds[idx] = row.odds
            elif row.event == 3:
                guest_win_odds[idx] = row.odds
            elif row.event == 6:
                btts_yes_odds[idx] = row.odds
            elif row.event == 172:
                btts_no_odds[idx] = row.odds
            elif row.event == 8:
                over_odds[idx] = row.odds
            elif row.event == 12:
                under_odds[idx] = row.odds

        home_win_odds = model_odds(home_win) + home_win_odds[1:]
        draw_odds = model_odds(draw) + draw_odds[1:]
        guest_win_odds = model_odds(guest_win) + guest_win_odds[1:]
        btts_yes_odds = model_odds(btts_yes) + btts_yes_odds[1:]
        btts_no_odds = model_odds(btts_no) + btts_no_odds[1:]
        over_odds = model_odds(over_2_5) + over_odds[1:]
        under_odds = model_odds(under_2_5) + under_odds[1:]

        home_win_EV = calc_ev(home_win, home_win_odds)
        draw_EV = calc_ev(draw, draw_odds)
        guest_win_EV = calc_ev(guest_win, guest_win_odds)
        btts_yes_EV = calc_ev(btts_yes, btts_yes_odds)
        btts_no_EV = calc_ev(btts_no, btts_no_odds)
        over_EV = calc_ev(over_2_5, over_odds)
        under_EV = calc_ev(under_2_5, under_odds)

        #Przez wybory modelu rozumiemy największe % dla danego typu zdarzenia 
        # (Rezultat, BTTS, OU) - 3 predykcje dla jednego spotkania
        results_prediction = np.array([home_win or 0, draw or 0, guest_win or 0])
        btts_predictions = np.array([btts_no or 0, btts_yes or 0])
        ou_predictions = np.array([under_2_5 or 0, over_2_5 or 0])
        result_pred_id = np.argmax(results_prediction)
        btts_pred_id = np.argmax(btts_predictions)
        ou_pred_id = np.argmax(ou_predictions)
 
        # Dodaj do listy zapytań SQL (tylko jeśli predykcja istnieje)
        # Rezultat meczu
        if results_prediction[result_pred_id] > 0:
            event_id = [1, 2, 3][result_pred_id]
            EV = [home_win_EV, draw_EV, guest_win_EV][result_pred_id]
            odds = [home_win_odds, draw_odds, guest_win_odds][result_pred_id]
            best_odds = max(odds[1:], default=0)
            bookmaker = np.argmax(odds[1:]) + 1 if len(odds) > 1 else 0
            model_id = int([home_win_model, draw_model, guest_win_model][result_pred_id])
            sql = (
                "INSERT INTO bets(match_id, event_id, odds, bookmaker, EV, model_id) "
                f"VALUES ({match_id}, {event_id}, {best_odds}, {bookmaker}, {EV}, {model_id});"
            )
            print(sql)
            inserts.append(sql)

        # BTTS
        if btts_predictions[btts_pred_id] > 0:
            event_id = [172, 6][btts_pred_id]
            EV = [btts_no_EV, btts_yes_EV][btts_pred_id]
            odds = [btts_no_odds, btts_yes_odds][btts_pred_id]
            best_odds = max(odds[1:], default=0)
            bookmaker = np.argmax(odds[1:]) + 1 if len(odds) > 1 else 0
            model_id = int(btts_yes_model if btts_pred_id == 1 else btts_no_model)
            sql = (
                "INSERT INTO bets(match_id, event_id, odds, bookmaker, EV, model_id) "
                f"VALUES ({match_id}, {event_id}, {best_odds}, {bookmaker}, {EV}, {model_id});"
            )
            print(sql)
            inserts.append(sql)

        # Over/Under 2.5
        if ou_predictions[ou_pred_id] > 0:
            event_id = [12, 8][ou_pred_id]
            EV = [under_EV, over_EV][ou_pred_id]
            odds = [under_odds, over_odds][ou_pred_id]
            best_odds = max(odds[1:], default=0)
            bookmaker = np.argmax(odds[1:]) + 1 if len(odds) > 1 else 0
            model_id = int(over_2_5_model if ou_pred_id == 1 else under_2_5_model)
            sql = (
                "INSERT INTO bets(match_id, event_id, odds, bookmaker, EV, model_id) "
                f"VALUES ({match_id}, {event_id}, {best_odds}, {bookmaker}, {EV}, {model_id});"
            )
            print(sql)
            inserts.append(sql)
    if to_automate:
        pass
        update_db(inserts, conn)

def bet_to_automate(mode: str, league_id: int, season_id: int, round_num: int = None, date_from: str = None, date_to: str = None, match_id: int = None) -> None:
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
    """
    to_automate = 1
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    conn = db_module.db_connect()
    if mode == 'today':
        query = f"SELECT id FROM matches WHERE league = {league_id} AND season = {season_id} AND CAST(game_date AS DATE) = CURRENT_DATE"
    elif mode == 'round':
        query = f"SELECT id FROM matches WHERE league = {league_id} AND season = {season_id} AND round = {round_num}"
    elif mode == 'date_range':
        query = f"SELECT id FROM matches WHERE league = {league_id} AND season = {season_id} AND CAST(game_date AS DATE) BETWEEN '{date_from}' AND '{date_to}'"
    elif mode == 'match':
        query = f"SELECT id FROM matches WHERE id = {match_id}" #Trochę redundancja, ale niech będzie
    generate_predictions(conn, query, to_automate)
    conn.close()

def main() -> None:
    """Główna funkcja do uruchomienia skryptu."""
    parser = argparse.ArgumentParser(
        description=(
            "Generuje zakłady według wybranego trybu dla wybranej ligi i sezonu.\n"
            "\nPrzykłady użycia:\n"
            "  python bet_all.py today 1 11\n"
            "  python bet_all.py round 1 11 --round_num 5\n"
            "  python bet_all.py date_range 1 11 --date_from 2024-07-01 --date_to 2024-07-20\n"
            "  python bet_all.py match 1 11 --match 12345\n"
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

    args = parser.parse_args()

    # Walidacja parametrów w zależności od trybu
    if args.mode == "round" and args.round_num is None:
        parser.error("W trybie 'round' wymagany jest parametr --round_num.")
    if args.mode == "date_range" and (args.date_from is None or args.date_to is None):
        parser.error("W trybie 'date_range' wymagane są parametry --date_from oraz --date_to.")
    if args.mode == "match" and args.match_id is None:
        parser.error("W trybie 'match' wymagany jest parametr --match_id (pojedynczy id meczu).")

    bet_to_automate(
        mode=args.mode,
        league_id=args.league_id,
        season_id=args.season_id,
        round_num=args.round_num,
        date_from=args.date_from,
        date_to=args.date_to,
        match_id=args.match_id
    )

if __name__ == "__main__":
    main()