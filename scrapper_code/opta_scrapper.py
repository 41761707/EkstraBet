import csv
from bs4 import BeautifulSoup
import pandas as pd
import argparse
import db_module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from tqdm import tqdm
from utils import setup_chrome_driver


def parse_arguments():
    """Funkcja do parsowania argumentów wiersza poleceń."""
    parser = argparse.ArgumentParser(
        description="""Scraper statystyk Opta - pobiera dane ze strony i zapisuje do bazy danych.
        Przykład użycia: python .\opta_scrapper.py --bulk --automate 1 3 https://optaplayerstats.statsperform.com/en_GB/soccer/ekstraklasa-2021-2022/3yted6kra6v27o4jyr87n3m6s/results""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('league', type=int, help='ID ligi (liczba całkowita)')
    parser.add_argument('season', type=int,
                        help='Rok sezonu (liczba całkowita, np. 2024)')
    parser.add_argument(
        'url', type=str, help='URL strony z tabelą statystyk Opta do pobrania')
    parser.add_argument('--automate', action='store_true',
                        help='Automatyczne dodawanie wpisów do bazy danych')
    parser.add_argument(
        '--round', type=int, help='Numer rundy, dla której tworzymy wpisów (opcjonalny)')
    parser.add_argument('--bulk', action='store_true',
                        help='Tryb masowego pobierania wszystkich kolejek')
    parser.add_argument('--csv', action='store_true',
                        help='Zapisz dane do pliku CSV zamiast bazy danych')

    return parser.parse_args()


def check_if_in_db(home_team: str, away_team: str, round_num: str, season: int, conn) -> int:
    """Sprawdza, czy mecz jest już w bazie danych.
    Args:
        home_team (str): Nazwa drużyny gospodarzy.
        away_team (str): Nazwa drużyny gości.
        round_num (str): Numer kolejki
        season (int): ID sezonu
        conn: Połączenie do bazy danych.
    Returns:
        int: ID meczu, jeśli istnieje, -1 w przeciwnym razie.
    """
    cursor = conn.cursor()
    try:
        # Wyszukiwanie według kolejki i sezonu (taki mecz powinien być unikalny)
        query = """
            SELECT m.id 
            FROM matches m 
            JOIN teams t1 on t1.id = m.home_team
            JOIN teams t2 on t2.id = m.away_team
            WHERE t1.opta_name = %s AND t2.opta_name = %s AND m.round = %s AND m.season = %s
        """
        cursor.execute(query, (home_team, away_team, round_num, season))
        result = cursor.fetchall()
        if len(result) > 1:
            print(
                f"Znaleziono {len(result)} meczów dla {home_team} vs {away_team} w kolejce {round_num} sezonie {season}")
            return -1
        else:
            return result[0][0] if result else -1
    finally:
        cursor.close()


def check_if_player_in_db(player_common_name: str, conn):
    """Sprawdza, czy zawodnik jest już w bazie danych.
    Args:
        player_common_name (str): Powszechna nazwa zawodnika.
        conn: Połączenie do bazy danych.
    Returns:
        int: ID zawodnika, jeśli istnieje, -1 w przeciwnym razie.
    """
    cursor = conn.cursor()
    try:
        query = """
            SELECT id FROM players WHERE common_name = %s
        """
        cursor.execute(query, (player_common_name,))
        result = cursor.fetchone()
        return result[0] if result else -1
    finally:
        cursor.close()


def insert_new_player(player_common_name: str, conn):
    """Wstawia nowego zawodnika do bazy danych.
    Args:
        player_common_name (str): Powszechna nazwa zawodnika.
        conn: Połączenie do bazy danych.
    Returns:
        int: ID nowo wstawionego zawodnika lub -1 w przypadku błędu.
    """
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO players (common_name, sports_id) VALUES (%s, 1)
        """
        cursor.execute(query, (player_common_name,))
        player_id = cursor.lastrowid  # Pobierz ID ostatnio wstawionego rekordu
        conn.commit()
        return player_id
    except Exception as e:
        print(
            f"Błąd podczas wstawiania nowego zawodnika '{player_common_name}': {e}")
        conn.rollback()
        return -1
    finally:
        cursor.close()


def save_player_stats_to_db(all_match_data, conn, automate=False):
    """Zapisuje statystyki zawodników do bazy danych lub wyświetla przykładowe zapytania.
    Args:
        all_match_data (pd.DataFrame): Wszystkie dane meczów.
        conn: Połączenie do bazy danych.
        automate (bool): Czy automatycznie zapisywać do bazy danych.
    """
    if all_match_data.empty:
        print("Brak danych do zapisania")
        return

    for _, row in all_match_data.iterrows():
        # Pobierz team_id na podstawie nazwy drużyny i match_id
        team_id = get_team_id_by_name_and_match(
            row['Team'], row['Match'], conn)

        if automate:
            # Zapisz do bazy danych
            cursor = conn.cursor()
            try:
                # Sprawdź czy już istnieje rekord dla tego zawodnika w tym meczu
                check_query = """
                    SELECT id FROM football_player_stats 
                    WHERE player_id = %s AND match_id = %s AND team_id = %s
                """
                cursor.execute(
                    check_query, (row['Player'], row['Match'], team_id))
                existing = cursor.fetchone()

                if existing:
                    continue

                # Przygotuj dane do wstawienia z mapowaniem kolumn
                stats_data = prepare_stats_data_for_insert(row, team_id)

                # Wstawianie statystyk zawodnika
                query = """
                    INSERT INTO football_player_stats (
                        player_id, match_id, team_id, goals, assists, red_cards, yellow_cards,
                        corners_won, shots, shots_on_target, blocked_shots, passes, crosses, 
                        tackles, offsides, fouls_conceded, fouls_won, saves
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, stats_data)
                conn.commit()

            except Exception as e:
                print(
                    f"Błąd podczas zapisywania statystyk zawodnika ID {row['Player']}: {e}")
                conn.rollback()
            finally:
                cursor.close()
        else:
            # Wyświetl przykładowe zapytanie INSERT
            stats_data = prepare_stats_data_for_insert(row, team_id)
            query = """INSERT INTO football_player_stats (
    player_id, match_id, team_id, goals, assists, red_cards, yellow_cards,
    corners_won, shots, shots_on_target, blocked_shots, passes, crosses, 
    tackles, offsides, fouls_conceded, fouls_won, saves
) VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {});""".format(*stats_data)

            print(
                f"-- Statystyki dla zawodnika: {row.get('Player_Common_Name', 'N/A')}")
            print(query)
            print()


def get_team_id_by_name_and_match(team_name, match_id, conn):
    """Pobiera team_id na podstawie nazwy drużyny i match_id.
    Args:
        team_name (str): Nazwa drużyny z Opta.
        match_id (int): ID meczu.
        conn: Połączenie do bazy danych.
    Returns:
        int: ID drużyny lub -1 w przypadku błędu.
    """
    cursor = conn.cursor()
    try:
        query = """
            SELECT CASE 
                WHEN t1.opta_name = %s THEN m.home_team
                WHEN t2.opta_name = %s THEN m.away_team
                ELSE -1
            END as team_id
            FROM matches m
            JOIN teams t1 ON t1.id = m.home_team
            JOIN teams t2 ON t2.id = m.away_team
            WHERE m.id = %s
        """
        cursor.execute(query, (team_name, team_name, match_id))
        result = cursor.fetchone()
        return result[0] if result and result[0] != -1 else -1
    except Exception as e:
        print(
            f"Błąd podczas pobierania team_id dla drużyny '{team_name}': {e}")
        return -1
    finally:
        cursor.close()
        
def prepare_stats_data_for_insert(row, team_id):
    """Przygotowuje dane statystyk do wstawienia do bazy danych.
    Args:
        row: Wiersz z DataFrame zawierający statystyki zawodnika.
        team_id (int): ID drużyny.
    Returns:
        tuple: Krotka z danymi do wstawienia.
    """
    # Zwracamy dane w kolejności zgodnej z bazą danych
    return (
        int(row['Player']),  # player_id
        int(row['Match']),   # match_id
        int(team_id),        # team_id
        int(row['Goals']),           # goals
        int(row['Assists']),        # assists
        int(row['Red cards']),       # red_cards
        int(row['Yellow cards']),    # yellow_cards
        int(row['Corners won']),     # corners_won
        int(row['Shots']),           # shots
        int(row['Shots on target']),  # shots_on_target
        int(row['Blocked shots']),   # blocked_shots
        int(row['Passes']),          # passes
        int(row['Crosses']),         # crosses
        int(row['Tackles']),         # tackles
        int(row['Offsides']),        # offsides
        int(row['Fouls conceded']),  # fouls_conceded
        int(row['Fouls won']),       # fouls_won
        int(row['Saves'])            # saves
    )


def extract_match_list_from_results_page(driver, base_url):
    """Wyciąga listę wszystkich meczów ze strony results.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
        base_url (str): Bazowy URL (bez /results na końcu).
    Returns:
        list: Lista słowników z matchday i match_url.
    """
    matches_list = []

    try:
        # Pobierz HTML strony
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        # Znajdź główny kontener z kolejkami
        tabbed_content = soup.find('ul', class_='Opta-TabbedContent')
        # Przejdź przez wszystkie li (kolejki)
        li_elements = tabbed_content.find_all('li')
        for i, li in enumerate(li_elements):
            try:
                # Znajdź nagłówek z numerem kolejki
                h3_element = li.find('h3', class_='Opta-Exp')
                span_element = h3_element.find('span')
                matchday_text = span_element.get_text(strip=True)
                matchday_number = extract_matchday_number_from_text(
                    matchday_text)
                # Znajdź wszystkie mecze w tej kolejce
                tbody_elements = li.find_all('tbody', class_='Opta-result')
                # Dla każdego meczu wyciągnij data-match i stwórz URL
                for j, tbody in enumerate(tbody_elements):
                    try:
                        match_id = tbody.get('data-match')
                        # Stwórz URL meczu
                        match_url = f"{base_url}/match/view/{match_id}/match-summary"
                        matches_list.append({
                            'matchday': matchday_number,
                            'match_url': match_url,
                            'match_id': match_id
                        })

                    except Exception as e:
                        print(
                            f"Błąd podczas przetwarzania meczu {j+1} w kolejce {matchday_number}: {e}")
                        continue

            except Exception as e:
                print(f"Błąd podczas przetwarzania kolejki {i+1}: {e}")
                continue

        print(f"\nŁącznie znaleziono {len(matches_list)} meczów")

    except Exception as e:
        print(f"Błąd podczas wyciągania listy meczów: {e}")
        import traceback
        traceback.print_exc()

    return matches_list


def extract_matchday_number_from_text(matchday_text):
    """Wyciąga numer kolejki z tekstu typu 'Matchday 3' lub 'Matchday 15'.
    Args:
        matchday_text (str): Tekst zawierający numer kolejki.
    Returns:
        int: Numer kolejki lub None w przypadku błędu.
    """
    try:
        # Split względem spacji i weź drugi element
        parts = matchday_text.strip().split()
        if len(parts) >= 2:
            # Spróbuj skonwertować na int
            matchday_number = int(parts[1])
            return matchday_number
        else:
            print(f"Nieoczekiwany format tekstu kolejki: '{matchday_text}'")
            return None
    except (ValueError, IndexError) as e:
        print(
            f"Błąd podczas parsowania numeru kolejki z '{matchday_text}': {e}")
        return None


def get_team_names(driver):
    """Pobiera nazwy drużyn z listy i zwraca słownik z nazwami."""
    team_list = driver.find_element(By.CSS_SELECTOR, 'ul.Opta-Cf')
    team_items = team_list.find_elements(By.TAG_NAME, 'li')

    if len(team_items) < 3:  # ALL + 2 drużyny
        raise ValueError(
            "Nie znaleziono odpowiedniej liczby elementów w liście drużyn")
    return {
        'home': team_items[1].text.strip(),
        'away': team_items[2].text.strip()
    }


def parse_opta_stats_from_html(html, team_name='', match_id='', matchday_number='', conn=None, automate=False) -> pd.DataFrame:
    '''Parsuje statystyki Opta z HTML i dodaje informację o drużynie i kolejce.
    Args:
        html (str): Kod HTML do przetworzenia.
        team_name (str): Nazwa drużyny.
        match_id (str): ID meczu.
        matchday_number (str): Numer kolejki.
        conn: Połączenie do bazy danych.
        automate (bool): Czy automatycznie dodawać nowych zawodników do bazy.
    Returns:
        pd.DataFrame: DataFrame z danymi statystyk.
    '''
    soup = BeautifulSoup(html, 'html.parser')

    # Najpierw znajdź kontener z zakładkami
    tabbed_content = soup.find('ul', class_='Opta-TabbedContent')
    if not tabbed_content:
        raise ValueError("Nie znaleziono kontenera ul.Opta-TabbedContent")

    # Znajdź aktywną zakładkę (li.Opta-On)
    active_tab = tabbed_content.find('li', class_='Opta-On')
    if not active_tab:
        raise ValueError("Nie znaleziono aktywnej zakładki li.Opta-On")

    # Znajdź tabelę w aktywnej zakładce
    table = active_tab.find('table', class_='Opta-Striped')
    if not table:
        raise ValueError(
            "Nie znaleziono tabeli z klasą 'Opta-Striped' w aktywnej zakładce")
    headers = []
    for th in table.thead.find_all('th'):
        abbr = th.find('abbr')
        if abbr:
            headers.append(abbr['title'])
        else:
            headers.append(th.get_text(strip=True))
    rows = []
    for tr in table.tbody.find_all('tr'):
        player_data = {}
        player_name = tr.find(
            'th', {'class': 'Opta-Player'}).get_text(strip=True)
        total = tr.find('th', {'class': 'Opta-Total'}).get_text(
            strip=True) if tr.find('th', {'class': 'Opta-Total'}) else ''
        if total:
            continue  # Pomijamy wiersze z klasą Opta-Total
        player_id = check_if_player_in_db(player_name, conn)
        if player_id == -1:
            if automate:
                player_id = insert_new_player(player_name, conn)
            else:
                print(
                    f"INSERT INTO players (common_name, sports_id) VALUES ('{player_name}', 1); -- Zawodnik: {player_name}")
        player_data['Player'] = player_id  # ID zawodnika
        # Powszechna nazwa zawodnika
        player_data['Player_Common_Name'] = player_name
        player_data['Team'] = team_name  # Faktyczna nazwa drużyny
        player_data['Match'] = match_id  # ID meczu
        player_data['Round'] = matchday_number  # Numer kolejki
        stats = tr.find_all('td', {'class': 'Opta-Stat'})
        for i, stat in enumerate(stats):
            player_data[headers[i+1]
                        ] = stat.get('data-srt', stat.get_text(strip=True))
        rows.append(player_data)

    return pd.DataFrame(rows)


def switch_to_team(driver, team_index):
    """Przełącza widok na drużynę o podanym indeksie (1 - gospodarz, 2 - gość).
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
        team_index (int): Indeks drużyny do przełączenia (1 - gospodarz, 2 - gość).
    """
    team_list = driver.find_element(By.CSS_SELECTOR, 'ul.Opta-Cf')
    team_items = team_list.find_elements(By.TAG_NAME, 'li')

    if len(team_items) < 3:
        raise ValueError(
            "Nie znaleziono odpowiedniej liczby elementów w liście drużyn")

    team_items[team_index].click()
    time.sleep(3)


def extract_matchday_number(driver):
    """Wyciąga numer kolejki z nagłówka h3.Opta-Exp.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
    Returns:
        str: Numer kolejki.
    """
    try:
        header = driver.find_element(By.CSS_SELECTOR, 'h3.Opta-Exp')
        header_text = header.text.strip()  # np. "Matchday 3"
        return header_text.split()[1]  # zwraca "3"
    except (NoSuchElementException, IndexError):
        return ''


def get_matchday_list(driver):
    """Pobiera listę wszystkich dostępnych kolejek.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
    Returns:
        list: Lista elementów kolejek (od najstarszej do najnowszej).
    """
    try:
        wait = WebDriverWait(driver, 10)
        matchday_list = driver.find_element(By.CSS_SELECTOR, 'ul.Opta-Cf')
        matchday_items = matchday_list.find_elements(By.TAG_NAME, 'li')
        return list(reversed(matchday_items))

    except NoSuchElementException:
        print("Błąd: Nie znaleziono listy kolejek (ul.Opta-Cf)")
        return []
    except Exception as e:
        print(f"Błąd podczas pobierania listy kolejek: {e}")
        return []


def get_matches_from_matchday(driver):
    """Pobiera wszystkie mecze z aktualnie wybranej kolejki.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
    Returns:
        list: Lista elementów meczów (tbody.Opta-result).
    """
    try:
        wait = WebDriverWait(driver, 10)
        # Czekaj na załadowanie meczów
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'tbody.Opta-result')))

        matches = driver.find_elements(By.CSS_SELECTOR, 'tbody.Opta-result')
        return matches
    except TimeoutException:
        print("Błąd: Timeout przy oczekiwaniu na mecze")
        return []
    except NoSuchElementException:
        print("Błąd: Nie znaleziono meczów (tbody.Opta-result)")
        return []


def process_match_stats(driver, matchday_number, season, conn, automate=False):
    """Przetwarza statystyki dla aktualnie wybranego meczu.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
        matchday_number (str): Numer kolejki.
        season: Sezon rozgrywkowy.
        conn: Połączenie do bazy danych.
        automate (bool): Czy automatycznie dodawać nowych zawodników do bazy.
    Returns:
        pd.DataFrame: DataFrame z danymi statystyk dla obu drużyn.
    """
    match_data = pd.DataFrame()

    try:
        # Pobierz nazwy drużyn
        teams = get_team_names(driver)
        match_id = check_if_in_db(
            teams['home'], teams['away'], matchday_number, season, conn)
        if match_id == -1:
            print(
                f"Brak meczu między {teams['home']} a {teams['away']} w kolejce {matchday_number} w bazie danych")
            return
        # Dane dla gospodarza
        switch_to_team(driver, 1)
        html = driver.page_source
        home_stats = parse_opta_stats_from_html(
            html, team_name=teams['home'], match_id=match_id, matchday_number=matchday_number, conn=conn, automate=automate)
        match_data = pd.concat([match_data, home_stats], ignore_index=True)

        # Dane dla gościa
        switch_to_team(driver, 2)
        html = driver.page_source
        away_stats = parse_opta_stats_from_html(
            html, team_name=teams['away'], match_id=match_id, matchday_number=matchday_number, conn=conn, automate=automate)
        match_data = pd.concat([match_data, away_stats], ignore_index=True)

    except Exception as e:
        print(
            f"Błąd podczas przetwarzania meczu w kolejce {matchday_number}: {e}")

    return match_data


def get_match_stats_from_url(driver, match_url, matchday_number, match_id, season, conn, automate=False):
    """Pobiera statystyki z pojedynczego meczu.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
        match_url (str): URL meczu.
        matchday_number (int): Numer kolejki.
        match_id (str): ID meczu.
        season: Sezon rozgrywkowy.
        conn: Połączenie do bazy danych.
        automate (bool): Czy automatycznie dodawać nowych zawodników do bazy.
    Returns:
        pd.DataFrame: DataFrame z danymi statystyk dla obu drużyn.
    """
    match_stats = pd.DataFrame()
    driver.get(match_url)
    time.sleep(3)
    match_stats = process_match_stats(driver, str(
        matchday_number), season, conn, automate)
    return match_stats


def save_to_csv_file(all_match_data, args):
    """Zapisuje dane do pliku CSV.
    Args:
        all_match_data (pd.DataFrame): Wszystkie dane meczów.
        args: Argumenty z parsera.
    """
    # Zapisz wszystkie dane
    if not all_match_data.empty:
        filename = f"opta_stats_new_bulk_liga_{args.league}_sezon_{args.season}.csv"
        all_match_data.to_csv(filename, index=False, encoding='utf-8')
        print(
            f"\nZapisano {len(all_match_data)} rekordów do pliku: {filename}")
        print(f"Mecze z {all_match_data['Round'].nunique()} różnych kolejek")
        if 'Match_ID' in all_match_data.columns:
            print(f"Unikalne mecze: {all_match_data['Match_ID'].nunique()}")
    else:
        print("Nie pobrano żadnych danych statystyk")


def main_bulk(args, driver, conn):
    """Nowa funkcja do masowego pobierania danych - podejście przez listę meczów.
    Args:
        args: Argumenty z parsera.
        driver: Obiekt sterownika Selenium.
        conn: Połączenie do bazy danych.
    """
    print("===TRYB MASOWEGO POBIERANIA ===")
    print(f"Liga: {args.league}, Sezon: {args.season}")
    # Pobierz stronę z wynikami
    driver.get(args.url)
    time.sleep(5)

    # Wygeneruj bazowy URL
    base_url = args.url[:-8]  # usuń '/results'
    print(f"Bazowy URL: {base_url}")

    # Wyciągnij listę wszystkich meczów
    matches_list = extract_match_list_from_results_page(driver, base_url)

    if not matches_list:
        print("Nie znaleziono żadnych meczów do przetworzenia")
        return

    all_match_data = pd.DataFrame()

    if args.round:
        matches_list = [m for m in matches_list if m['matchday'] == args.round]
    print(
        f"\n=== ROZPOCZYNAM POBIERANIE STATYSTYK Z {len(matches_list)} MECZÓW ===")
    # Przetwarzaj każdy mecz
    for i, match_info in enumerate(tqdm(matches_list, desc="Pobieranie statystyk", unit="mecz")):
        match_data = get_match_stats_from_url(
            driver,
            match_info['match_url'],
            match_info['matchday'],
            match_info['match_id'],
            args.season,
            conn,
            args.automate
        )
        if not match_data.empty:
            save_player_stats_to_db(match_data, conn, args.automate)
            all_match_data = pd.concat(
                [all_match_data, match_data], ignore_index=True)
    if args.csv:
        save_to_csv_file(all_match_data, args)


def main() -> None:
    """Główna funkcja skryptu, która pobiera dane z podanego URL i przetwarza je."""
    args = parse_arguments()
    driver = setup_chrome_driver()
    conn = db_module.db_connect()
    try:
        if args.bulk:
            # Tryb masowego pobierania
            main_bulk(args, driver, conn)
        else:
            # Tryb pojedynczego meczu (oryginalny)
            all_data = pd.DataFrame()
            driver.get(args.url)
            time.sleep(5)
            matchday_number = extract_matchday_number(driver)
            all_data = process_match_stats(
                driver, matchday_number, args.season, conn, args.automate)
            save_player_stats_to_db(all_data, conn, args.automate)
            if args.csv:
                save_to_csv_file(all_data, args)

    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania danych: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        conn.close()


if __name__ == "__main__":
    main()
