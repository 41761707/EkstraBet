import argparse

import automate_odds
import upcoming_scrapper
import update_scraper

def launch_upcoming(links):
    for link in links:
        current = link + 'mecze/'
        print(current)
        args = current.split()
        upcoming_scrapper.to_automate(int(args[0]), int(args[1]), args[2], 0)

def launch_update(links):
    for link in links:
        current = link + 'wyniki/'
        print(current)
        args = current.split()
        print(args)
        update_scraper.to_automate(int(args[0]), int(args[1]), args[2])

def launch_odds(links):
    for current in links:
        print(current)
        args = current.split()
        automate_odds.to_automate(int(args[0]), int(args[1]), args[2])

def main():
    links = [  
        #'1 11 https://www.flashscore.pl/pilka-nozna/polska/pko-bp-ekstraklasa-2024-2025/',
        #'2 11 https://www.flashscore.pl/pilka-nozna/anglia/premier-league-2024-2025/',
        #'3 11 https://www.flashscore.pl/pilka-nozna/francja/ligue-1-2024-2025/',
        #'4 11 https://www.flashscore.pl/pilka-nozna/niemcy/bundesliga-2024-2025/',
        #'5 11 https://www.flashscore.pl/pilka-nozna/wlochy/serie-a-2024-2025/',
        #'6 11 https://www.flashscore.pl/pilka-nozna/hiszpania/laliga-2024-2025/',
        #'7 11 https://www.flashscore.pl/pilka-nozna/portugalia/liga-portugal-2024-2025/',
        #'8 11 https://www.flashscore.pl/pilka-nozna/anglia/championship-2024-2025/',
        #'10 11 https://www.flashscore.pl/pilka-nozna/australia/a-league-2024-2025/',
        #'11 11 https://www.flashscore.pl/pilka-nozna/belgia/jupiler-league-2024-2025/',
        #'12 11 https://www.flashscore.pl/pilka-nozna/czechy/chance-liga-2024-2025/',
        #'13 11 https://www.flashscore.pl/pilka-nozna/francja/ligue-2-2024-2025/',
        #'14 11 https://www.flashscore.pl/pilka-nozna/hiszpania/laliga2-2024-2025/',
        #'15 11 https://www.flashscore.pl/pilka-nozna/korea-poludniowa/k-league-1-2025/',
        #'16 11 https://www.flashscore.pl/pilka-nozna/holandia/eredivisie-2024-2025/',
        #'17 11 https://www.flashscore.pl/pilka-nozna/japonia/j1-league-2025/',
        #'19 11 https://www.flashscore.pl/pilka-nozna/meksyk/liga-mx-2024-2025/',
        #'20 11 https://www.flashscore.pl/pilka-nozna/niemcy/2-bundesliga-2024-2025/',
        #'21 11 https://www.flashscore.pl/pilka-nozna/polska/betclic-1-liga-2024-2025/',
        #'23 11 https://www.flashscore.pl/pilka-nozna/szwajcaria/super-league-2024-2025/',
        #'24 11 https://www.flashscore.pl/pilka-nozna/turcja/super-lig-2024-2025/',
        #'25 11 https://www.flashscore.pl/pilka-nozna/usa/mls-2025/',
        #'26 11 https://www.flashscore.pl/pilka-nozna/wlochy/serie-b-2024-2025/',
        #'29 11 https://www.flashscore.pl/pilka-nozna/austria/bundesliga-2024-2025/',
        #'30 11 https://www.flashscore.pl/pilka-nozna/korea-poludniowa/k-league-2-2025/',
        #'31 11 https://www.flashscore.pl/pilka-nozna/holandia/eerste-divisie-2024-2025/',
        #'32 11 https://www.flashscore.pl/pilka-nozna/japonia/j2-league-2025/',
        #'33 11 https://www.flashscore.pl/pilka-nozna/argentyna/torneo-betano-2025/',
        '34 11 https://www.flashscore.pl/pilka-nozna/brazylia/serie-a-betano-2025/',
        '36 11 https://www.flashscore.pl/pilka-nozna/portugalia/liga-portugal-2-2024-2025/',
        '37 11 https://www.flashscore.pl/pilka-nozna/belgia/challenger-pro-league-2024-2025/',
        '38 11 https://www.flashscore.pl/pilka-nozna/austria/2-liga-2024-2025/',
        '39 11 https://www.flashscore.pl/pilka-nozna/szwajcaria/challenge-league-2024-2025/',
        '40 11 https://www.flashscore.pl/pilka-nozna/turcja/1-lig-2024-2025/',
        #'41 11 https://www.flashscore.pl/pilka-nozna/czechy/dywizja-2-2024-2025/'
    ]
    parser = argparse.ArgumentParser(description="Automatyzacja scrapowania danych.")
    parser.add_argument('mode', choices=['update', 'upcoming', 'odds'], help='Tryb uruchomienia programu')
    args = parser.parse_args()

    if args.mode == 'update':
        launch_update(links)
    elif args.mode == 'upcoming':
        launch_upcoming(links)
    elif args.mode == 'odds':
        launch_odds(links)

if __name__ == '__main__':
    main()