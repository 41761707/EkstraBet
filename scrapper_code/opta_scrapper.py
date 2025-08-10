import csv
from bs4 import BeautifulSoup
import pandas as pd
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from utils import setup_chrome_driver

def parse_arguments():
    """Funkcja do parsowania argumentów wiersza poleceń."""
    parser = argparse.ArgumentParser(
        description='Scraper statystyk Opta - pobiera dane ze strony i zapisuje do pliku CSV.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('league', type=int, help='ID ligi (liczba całkowita)')
    parser.add_argument('season', type=int, help='Rok sezonu (liczba całkowita, np. 2024)')
    parser.add_argument('url', type=str, help='URL strony z tabelą statystyk Opta do pobrania')
    parser.add_argument('--automate', action='store_true', help='Automatyczne dodawanie wpisów do bazy danych')
    parser.add_argument('--round', type=int, help='Numer rundy, dla której tworzymy wpisów (opcjonalny)')
    parser.add_argument('--bulk', action='store_true', help='Tryb masowego pobierania wszystkich kolejek')
    
    return parser.parse_args()

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
        if not tabbed_content:
            print("Błąd: Nie znaleziono kontenera ul.Opta-TabbedContent")
            return matches_list
        
        # Przejdź przez wszystkie li (kolejki)
        li_elements = tabbed_content.find_all('li')
        print(f"Znaleziono {len(li_elements)} kolejek do przetworzenia")
        
        for i, li in enumerate(li_elements):
            try:
                # Znajdź nagłówek z numerem kolejki
                h3_element = li.find('h3', class_='Opta-Exp')
                if not h3_element:
                    print(f"Ostrzeżenie: Brak nagłówka h3 w kolejce {i+1}")
                    continue
                
                # Wyciągnij numer kolejki z pierwszego span
                span_element = h3_element.find('span')
                if not span_element:
                    print(f"Ostrzeżenie: Brak span z numerem kolejki w {i+1}")
                    continue
                
                matchday_text = span_element.get_text(strip=True)
                matchday_number = extract_matchday_number_from_text(matchday_text)
                
                if not matchday_number:
                    print(f"Ostrzeżenie: Nie udało się wyciągnąć numeru kolejki z '{matchday_text}'")
                    continue
                
                print(f"Przetwarzanie kolejki {matchday_number}")
                
                # Znajdź wszystkie mecze w tej kolejce
                tbody_elements = li.find_all('tbody', class_='Opta-result')
                
                if not tbody_elements:
                    print(f"Brak meczów w kolejce {matchday_number}")
                    continue
                
                print(f"Znaleziono {len(tbody_elements)} meczów w kolejce {matchday_number}")
                
                # Dla każdego meczu wyciągnij data-match i stwórz URL
                for j, tbody in enumerate(tbody_elements):
                    try:
                        match_id = tbody.get('data-match')
                        if not match_id:
                            print(f"Ostrzeżenie: Brak data-match w meczu {j+1} kolejki {matchday_number}")
                            continue
                        
                        # Stwórz URL meczu
                        match_url = f"{base_url}/match/view/{match_id}/match-summary"
                        
                        matches_list.append({
                            'matchday': matchday_number,
                            'match_url': match_url,
                            'match_id': match_id
                        })
                        
                        print(f"Dodano mecz {match_id} z kolejki {matchday_number}")
                        
                    except Exception as e:
                        print(f"Błąd podczas przetwarzania meczu {j+1} w kolejce {matchday_number}: {e}")
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
        print(f"Błąd podczas parsowania numeru kolejki z '{matchday_text}': {e}")
        return None

def get_team_names(driver):
    """Pobiera nazwy drużyn z listy i zwraca słownik z nazwami."""
    team_list = driver.find_element(By.CSS_SELECTOR, 'ul.Opta-Cf')
    team_items = team_list.find_elements(By.TAG_NAME, 'li')
    
    if len(team_items) < 3:  # ALL + 2 drużyny
        raise ValueError("Nie znaleziono odpowiedniej liczby elementów w liście drużyn")
    
    return {
        'home': team_items[1].text.strip(),
        'away': team_items[2].text.strip()
    }

def parse_opta_stats_from_html(html, team_name='', matchday_number='') -> pd.DataFrame:
    '''Parsuje statystyki Opta z HTML i dodaje informację o drużynie i kolejce.
    Args:
        html (str): Kod HTML do przetworzenia.
        team_name (str): Nazwa drużyny.
        matchday_number (str): Numer kolejki.
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
        raise ValueError("Nie znaleziono tabeli z klasą 'Opta-Striped' w aktywnej zakładce")
    
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
        player_name = tr.find('th', {'class': 'Opta-Player'}).get_text(strip=True)
        total = tr.find('th', {'class': 'Opta-Total'}).get_text(strip=True) if tr.find('th', {'class': 'Opta-Total'}) else ''
        if total:
            continue  # Pomijamy wiersze z klasą Opta-Total
        player_data['Player'] = player_name
        player_data['Team'] = team_name  # Faktyczna nazwa drużyny
        player_data['Matchday'] = matchday_number  # Numer kolejki
        
        stats = tr.find_all('td', {'class': 'Opta-Stat'})
        for i, stat in enumerate(stats):
            player_data[headers[i+1]] = stat.get('data-srt', stat.get_text(strip=True))
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
        raise ValueError("Nie znaleziono odpowiedniej liczby elementów w liście drużyn")
    
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
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'tbody.Opta-result')))
        
        matches = driver.find_elements(By.CSS_SELECTOR, 'tbody.Opta-result')
        return matches
    except TimeoutException:
        print("Błąd: Timeout przy oczekiwaniu na mecze")
        return []
    except NoSuchElementException:
        print("Błąd: Nie znaleziono meczów (tbody.Opta-result)")
        return []

def process_match_stats(driver, matchday_number):
    """Przetwarza statystyki dla aktualnie wybranego meczu.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
        matchday_number (str): Numer kolejki.
    Returns:
        pd.DataFrame: DataFrame z danymi statystyk dla obu drużyn.
    """
    match_data = pd.DataFrame()
    
    try:
        # Pobierz nazwy drużyn
        teams = get_team_names(driver)
        
        # Dane dla gospodarza
        switch_to_team(driver, 1)
        html = driver.page_source
        home_stats = parse_opta_stats_from_html(html, team_name=teams['home'], matchday_number=matchday_number)
        match_data = pd.concat([match_data, home_stats], ignore_index=True)
        
        # Dane dla gościa
        switch_to_team(driver, 2)
        html = driver.page_source
        away_stats = parse_opta_stats_from_html(html, team_name=teams['away'], matchday_number=matchday_number)
        match_data = pd.concat([match_data, away_stats], ignore_index=True)
        
        print(f"Pobrano dane dla meczu: {teams['home']} vs {teams['away']} (kolejka {matchday_number})")
        
    except Exception as e:
        print(f"Błąd podczas przetwarzania meczu w kolejce {matchday_number}: {e}")
    
    return match_data

def process_all_matchdays(driver):
    """Przetwarza wszystkie kolejki i mecze, zbierając dane statystyk.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
    Returns:
        pd.DataFrame: DataFrame z danymi ze wszystkich meczów.
    """
    all_data = pd.DataFrame()
    
    # Pobierz listę kolejek
    matchday_items = get_matchday_list(driver)
    
    if not matchday_items:
        print("Nie znaleziono żadnych kolejek do przetworzenia")
        return all_data
    
    print(matchday_items)
    print(f"Znaleziono {len(matchday_items)} kolejek do przetworzenia")
    
    for i, matchday_item in enumerate(matchday_items):
        try:
            # Kliknij w kolejkę
            matchday_item.click()
            time.sleep(3)
            
            # Pobierz numer kolejki z nagłówka
            matchday_number = extract_matchday_number(driver)
            print(f"\n--- Przetwarzanie kolejki {matchday_number} ({i+1}/{len(matchday_items)}) ---")
            
            # Pobierz mecze z tej kolejki
            matches = get_matches_from_matchday(driver)
            
            if not matches:
                print(f"Brak meczów w kolejce {matchday_number}")
                continue
            
            print(f"Znaleziono {len(matches)} meczów w kolejce {matchday_number}")
            
            # Przetwórz każdy mecz
            for j, match in enumerate(matches):
                try:
                    print(f"Przetwarzanie meczu {j+1}/{len(matches)}...")
                    match.click()
                    time.sleep(3)
                    
                    # Pobierz statystyki dla meczu
                    match_stats = process_match_stats(driver, matchday_number)
                    all_data = pd.concat([all_data, match_stats], ignore_index=True)
                    
                    # Wróć do listy meczów
                    driver.back()
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Błąd podczas przetwarzania meczu {j+1} w kolejce {matchday_number}: {e}")
                    # Spróbuj wrócić do poprzedniej strony
                    try:
                        driver.back()
                        time.sleep(2)
                    except:
                        pass
                    continue
            
        except Exception as e:
            print(f"Błąd podczas przetwarzania kolejki {i+1}: {e}")
            continue
    
    return all_data

def get_match_stats_from_url(driver, match_url, matchday_number, match_id):
    """Pobiera statystyki z pojedynczego meczu.
    Args:
        driver (webdriver.Chrome): Obiekt sterownika Selenium.
        match_url (str): URL meczu.
        matchday_number (int): Numer kolejki.
        match_id (str): ID meczu.
    Returns:
        pd.DataFrame: DataFrame z danymi statystyk dla obu drużyn.
    """
    match_data = pd.DataFrame()
    
    try:
        print(f"Pobieranie danych z meczu {match_id} (kolejka {matchday_number})...")
        driver.get(match_url)
        time.sleep(3)
        
        # Pobierz statystyki dla meczu (używając istniejącej funkcji)
        match_stats = process_match_stats(driver, str(matchday_number))
        
        # Dodaj ID meczu do danych
        if not match_stats.empty:
            match_stats['Match_ID'] = match_id
        
        return match_stats
        
    except Exception as e:
        print(f"Błąd podczas pobierania danych z meczu {match_id}: {e}")
        return pd.DataFrame()

def main_bulk(args, driver):
    """Nowa funkcja do masowego pobierania danych - podejście przez listę meczów.
    Args:
        args: Argumenty z parsera.
        driver: Obiekt sterownika Selenium.
    """
    print("===TRYB MASOWEGO POBIERANIA ===")
    print(f"Liga: {args.league}, Sezon: {args.season}")
    
    try:
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
        
        print(f"\n=== ROZPOCZYNAM POBIERANIE STATYSTYK Z {len(matches_list)} MECZÓW ===")
        
        all_match_data = pd.DataFrame()
        
        if args.round:
            matches_list = [m for m in matches_list if m['matchday'] == args.round]
        # Przetwarzaj każdy mecz
        for i, match_info in enumerate(matches_list):
            try:
                match_data = get_match_stats_from_url(
                    driver, 
                    match_info['match_url'], 
                    match_info['matchday'], 
                    match_info['match_id']
                )
                
                if not match_data.empty:
                    all_match_data = pd.concat([all_match_data, match_data], ignore_index=True)
                    print(f"Mecz {i+1}/{len(matches_list)} - dodano {len(match_data)} rekordów")
                else:
                    print(f"Mecz {i+1}/{len(matches_list)} - brak danych")
                
            except Exception as e:
                print(f"Błąd podczas przetwarzania meczu {i+1}/{len(matches_list)}: {e}")
                continue
        
        # Zapisz wszystkie dane
        if not all_match_data.empty:
            filename = f"opta_stats_new_bulk_liga_{args.league}_sezon_{args.season}.csv"
            all_match_data.to_csv(filename, index=False, encoding='utf-8')
            print(f"\nZapisano {len(all_match_data)} rekordów do pliku: {filename}")
            print(f"Mecze z {all_match_data['Matchday'].nunique()} różnych kolejek")
            if 'Match_ID' in all_match_data.columns:
                print(f"Unikalne mecze: {all_match_data['Match_ID'].nunique()}")
        else:
            print("Nie pobrano żadnych danych statystyk")
        
    except Exception as e:
        print(f"Wystąpił błąd podczas nowego masowego pobierania: {e}")
        import traceback
        traceback.print_exc()

def main() -> None:
    """Główna funkcja skryptu, która pobiera dane z podanego URL i przetwarza je."""
    args = parse_arguments()
    driver = setup_chrome_driver()

    try:
        if args.bulk:
            # Tryb masowego pobierania
            main_bulk(args, driver)
        else:
            # Tryb pojedynczego meczu (oryginalny)
            all_data = pd.DataFrame()
            
            driver.get(args.url)
            time.sleep(5)
            
            # Pobierz numer kolejki z nagłówka (jeśli dostępny)
            matchday_number = extract_matchday_number(driver)
            
            # Pobierz nazwy drużyn
            teams = get_team_names(driver)
            
            # Dane dla gospodarza
            switch_to_team(driver, 1)
            html = driver.page_source
            home_stats = parse_opta_stats_from_html(html, team_name=teams['home'], matchday_number=matchday_number)
            all_data = pd.concat([all_data, home_stats], ignore_index=True)
            
            # Dane dla gościa
            switch_to_team(driver, 2)
            html = driver.page_source
            away_stats = parse_opta_stats_from_html(html, team_name=teams['away'], matchday_number=matchday_number)
            all_data = pd.concat([all_data, away_stats], ignore_index=True)
            
            print(all_data)
            
            # Opcjonalnie zapisz do pliku CSV
            if not all_data.empty:
                filename = f"opta_stats_liga_{args.league}_sezon_{args.season}_kolejka_{matchday_number}.csv"
                all_data.to_csv(filename, index=False, encoding='utf-8')
                print(f"Zapisano dane do pliku: {filename}")
        
    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania danych: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    main()