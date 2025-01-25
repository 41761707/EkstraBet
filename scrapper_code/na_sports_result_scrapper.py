import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from datetime import datetime

def get_match_links(games, driver):
    links = []
    driver.get(games)
    time.sleep(15)
    game_divs = driver.find_elements(By.CLASS_NAME, "event__match")
    for element in game_divs:
        id = element.get_attribute('id').split('_')[2]
        links.append('https://www.flashscore.pl/mecz/{}'.format(id))
    return links

def hockey_scrapper():
    #Jednak robimy hokeja też z flashscora
    #W api nie ma fajnej dokumentacji odnośnie rosterów, a na flashscorze wszystko jest
    #class smv__verticalSections section <- sekcja z przebiegiem meczu
    #class lf__lineUp <- sekcja ze składami

    
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging']) # Here
    driver = webdriver.Chrome(options=options)
    league_id = int(sys.argv[1])
    season_id = int(sys.argv[2])
    games = sys.argv[3]
    links = get_match_links(games, driver)

def main():
    pass
if __name__ == '__main__':
    main()