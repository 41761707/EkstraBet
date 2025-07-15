import numpy as np
import pandas as pd
import sys
import db_module
import warnings


def update_db(queries, conn):
    """Wykonuje listę zapytań SQL w transakcji. Zatwierdza zmiany tylko, jeśli wszystkie zapytania się powiodą.
    
    Argumenty:
        queries (list): Lista zapytań SQL do wykonania.
        conn: Połączenie do bazy danych (np. z psycopg2/sqlite3).
    
    Zwraca:
        bool: True, jeśli wszystkie zapytania wykonano pomyślnie, False w przeciwnym przypadku.
    """
    cursor = conn.cursor()
    try:
        for query in queries:
            cursor.execute(query)
        conn.commit() 
        return True
    except Exception as error:
        conn.rollback()
        print(f"Błąd bazy danych: {error}, cofnięto całe wgranie zmian.") 
        return False
    finally:
        cursor.close() 

def get_pred(event_id, conn, match_id):
        query = f"SELECT value, model_id FROM predictions WHERE match_id = {match_id} AND event_id = {event_id}"
        result = pd.read_sql(query, conn).to_numpy()
        return result[0] if len(result) > 0 else (None, None)

def model_odds(val):
    """ Funkcja pomocnicza do przeliczenia wartości kursu na prawdopodobieństwo.
    Args: 
        val (float): Wartość kursu.
    Returns:
        list: Lista z jednym elementem - prawdopodobieństwem w procentach.
    """
    return [round(100 / val, 2) if val else 0]

def calc_ev(pred, odds):
    """Funkcja do obliczania wartości oczekiwanej (EV) dla danego predykcji i kursów bukmacherskich.
    Args:
        pred (float): Predykcja prawdopodobieństwa danego zdarzenia.
        odds (list): Lista kursów bukmacherskich dla danego zdarzenia.
    Returns:
        float: Wartość oczekiwana (EV) dla danego zdarzenia.
    """
    return round((pred or 0) * max(odds[1:], default=0) - 1, 2)

def generate_predictions(conn, league, season, current_round, to_automate):
    """
    Generuje predykcje i wylicza EV dla wszystkich meczów danej ligi i sezonu rozgrywanych dzisiaj.
    Wyniki zapisuje do tabeli bets, jeśli to_automate == 1.

    Argumenty:
        conn: Połączenie do bazy danych.
        league (int): ID ligi.
        season (int): ID sezonu.
        current_round (int): Numer kolejki (opcjonalnie).
        to_automate (int): Flaga automatycznego zapisu do bazy (1 = zapisuj).

    Zwraca:
        None
    """
    # Pobierz wszystkie mecze dzisiaj dla danej ligi i sezonu
    query = ("SELECT id FROM matches "
            "WHERE league = {} AND season = {} AND CAST(game_date AS DATE) = CURRENT_DATE").format(league, season)
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
    #3. Pobrać wszystkie wpisy z tabeli "predictions" dla powyższych parametrów
    #4. Pobrać wszystkie wpisy z tabeli "odds" dla powyższych parametrów
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
        exact_pred_id = np.argmax(goals_pred) #To ewentualnie TO-DO
 
        # Dodaj do listy zapytań SQL (tylko jeśli predykcja istnieje)
        # Rezultat meczu
        if results_prediction[result_pred_id] > 0:
            event_id = [1, 2, 3][result_pred_id]
            confidence = results_prediction[result_pred_id]
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
        update_db(inserts, conn)

def bet_to_automate(league, season, mode):
    to_automate = 1
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    conn = db_module.db_connect()
    query = "select round from matches where league = {} and season = {} and cast(game_date as date) = current_date order by game_date limit 1".format(league, season)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    if len(results) == 0:
        print("BRAK SPOTKAŃ")
        return
    current_round = results[0][0]
    print("RUNDA: ", current_round)
    if mode == 0:
        generate_predictions(conn, league, season, current_round, to_automate)
    conn.close()    

def main():
    to_automate = 1
    warnings.filterwarnings("ignore", category=UserWarning, message="pandas only supports SQLAlchemy connectable")
    #1. Wybrać dla jakiej ligi, jakiego sezonu i jakiej rundy wygenerować zestawienie
    league = int(sys.argv[1])
    season = int(sys.argv[2])
    current_round = int(sys.argv[3])
    mode = int(sys.argv[4])
    #2. Wyciągnąć wszystkie idki meczów spełniających powyższe wymagania
    conn = db_module.db_connect()
    
    if mode == 0:
        generate_predictions(conn, league, season, current_round, to_automate)
    conn.close()

if __name__ == '__main__':
    main()