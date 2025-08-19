import argparse

import odds_scrapper
import upcoming_scrapper
import update_scraper
import scrapper
import bet_all


def launch_historic(links) -> None:
    """Uruchamia scrapowanie historycznych wyników.
    Args:
        links (list): Lista linków do lig, które mają być przetwarzane.
    """
    for link in links:
        current = link + 'wyniki/'
        print(f"# {current}")
        args = current.split()
        print(f"# {args}")
        scrapper.to_automate(int(args[0]), int(
            args[1]), args[2], single_match=False, automate=True)


def launch_upcoming(links) -> None:
    """Uruchamia scrapowanie nadchodzących meczów.
    Args:
        links (list): Lista linków do lig, które mają być przetwarzane.
    """
    for link in links:
        current = link + 'mecze/'
        print(f"# {current}")
        args = current.split()
        upcoming_scrapper.to_automate(int(args[0]), int(args[1]), args[2], 0, single_match=False, automate=True)


def launch_update(links) -> None:
    """Uruchamia aktualizację meczów do dzisiejszej daty.
    Args:
        links (list): Lista linków do lig, które mają być przetwarzane.
    """
    for link in links:
        current = link + 'wyniki/'
        print(f"# {current}")
        args = current.split()
        print(f"# {args}")
        update_scraper.to_automate(int(args[0]), int(
            args[1]), args[2], single_match=False, automate=True)


def launch_odds(links) -> None:
    """Uruchamia scrapowanie kursów bukmacherskich.
    Args:
        links (list): Lista linków do lig, które mają być przetwarzane.
    """
    for current in links:
        print(f"# {current}")
        args = current.split()
        odds_scrapper.odds_to_automate(int(args[0]), int(
            args[1]), args[2], 'daily', skip=0, automate=True)


def launch_bet(links) -> None:
    """Uruchamia generowanie zakładów.
    Args:
        links (list): Lista linków do lig, które mają być przetwarzane.
    """
    for current in links:
        print(f"# {current}")
        args = current.split()
        bet_all.bet_to_automate('today',
                                int(args[0]),
                                int(args[1]),
                                round_num=None,
                                date_from=None,
                                date_to=None,
                                match_id=None,
                                automate=True)


def main() -> None:
    links = [
        '1 12 https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2025-2026/',
        '2 12 https://www.flashscore.pl/pilka-nozna/anglia/premier-league-2025-2026/',
        '3 12 https://www.flashscore.pl/pilka-nozna/francja/ligue-1-2025-2026/',
        '4 12 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2025-2026/',
        '5 12 https://www.flashscore.pl/pilka-nozna/wlochy/serie-a-2025-2026/',
        '6 12 https://www.flashscore.pl/pilka-nozna/hiszpania/laliga-2025-2026/',
        '7 12 https://www.flashscore.pl/pilka-nozna/portugalia/liga-portugal-2025-2026/',
        '8 12 https://www.flashscore.pl/pilka-nozna/anglia/championship-2025-2026/',
        # '10 11 https://www.flashscore.pl/pilka-nozna/australia/a-league-2024-2025/', #koniec ligi
        '11 12 https://www.flashscore.pl/pilka-nozna/belgia/jupiler-league-2025-2026/',
        '12 12 https://www.flashscore.pl/pilka-nozna/czechy/chance-liga-2025-2026/',
        '13 12 https://www.flashscore.pl/pilka-nozna/francja/ligue-2-2025-2026/',
        '14 12 https://www.flashscore.pl/pilka-nozna/hiszpania/laliga2-2025-2026/',
        '15 11 https://www.flashscore.pl/pilka-nozna/korea-poludniowa/k-league-1-2025/',
        '16 12 https://www.flashscore.pl/pilka-nozna/holandia/eredivisie-2025-2026/',
        '17 11 https://www.flashscore.pl/pilka-nozna/japonia/j1-league-2025/',
        '19 12 https://www.flashscore.pl/pilka-nozna/meksyk/liga-mx-2025-2026/',
        '20 12 https://www.flashscore.pl/pilka-nozna/niemcy/2-bundesliga-2025-2026/',
        '21 12 https://www.flashscore.pl/pilka-nozna/polska/betclic-1-liga-2025-2026/',
        '23 12 https://www.flashscore.pl/pilka-nozna/szwajcaria/super-league-2025-2026/',
        '24 12 https://www.flashscore.pl/pilka-nozna/turcja/super-lig-2025-2026/',
        '25 11 https://www.flashscore.pl/pilka-nozna/usa/mls-2025/',
        '26 12 https://www.flashscore.pl/pilka-nozna/wlochy/serie-b-2025-2026/',
        '29 12 https://www.flashscore.pl/pilka-nozna/austria/bundesliga-2025-2026/',
        '30 11 https://www.flashscore.pl/pilka-nozna/korea-poludniowa/k-league-2-2025/',
        '31 12 https://www.flashscore.pl/pilka-nozna/holandia/eerste-divisie-2025-2026/',
        '32 11 https://www.flashscore.pl/pilka-nozna/japonia/j2-league-2025/',
        '33 11 https://www.flashscore.pl/pilka-nozna/argentyna/torneo-betano-2025/',
        '34 11 https://www.flashscore.pl/pilka-nozna/brazylia/serie-a-betano-2025/',
        '35 11 https://www.flashscore.pl/pilka-nozna/brazylia/serie-b-2025/',
        '36 12 https://www.flashscore.pl/pilka-nozna/portugalia/liga-portugal-2-2025-2026/',
        '37 12 https://www.flashscore.pl/pilka-nozna/belgia/challenger-pro-league-2025-2026/',
        '38 12 https://www.flashscore.pl/pilka-nozna/austria/2-liga-2025-2026/',
        '39 12 https://www.flashscore.pl/pilka-nozna/szwajcaria/challenge-league-2025-2026/',
        '40 12 https://www.flashscore.pl/pilka-nozna/turcja/1-lig-2025-2026/',
        '41 12 https://www.flashscore.pl/pilka-nozna/czechy/dywizja-2-2025-2026/'
    ]
    parser = argparse.ArgumentParser(
        description="Automatyzacja scrapowania danych.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'mode',
        choices=['update', 'upcoming', 'odds', 'historic', 'bet'],
        help="Tryb działania programu:\n"
        "update   - Aktualizuje wszystkie mecze do dzisiejszej daty\n"
        "upcoming - Pobiera nadchodzące mecze (max 7 dni wprzód)\n"
        "odds     - Pobiera kursy bukmacherskie\n"
        "historic - Pobiera historyczne wyniki\n"
        "bet      - Generuje zakłady"
    )
    args = parser.parse_args()
    options = {
        'update': launch_update,
        'upcoming': launch_upcoming,
        'odds': launch_odds,
        'historic': launch_historic,
        'bet': launch_bet
    }
    if args.mode in options:
        launch_function = options[args.mode]
        launch_function(links)


if __name__ == '__main__':
    main()
