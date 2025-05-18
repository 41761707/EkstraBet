import time
import sys

import odds_scraper
import bet_all

def to_automate(league, season, games, mode):
    odds_scraper.odds_to_automate(league, season, games, mode)
    print("Pobieranie kursów ukończone")
    #bet_all.bet_to_automate(league, season, 0)
    #print("Generowanie zakładów zakończone")

def main():
    league = int(sys.argv[1])
    season = int(sys.argv[2])
    games = sys.argv[3]
    to_automate(league, season, games)

if __name__ == '__main__':
    main()
