import numpy as np
import pandas as pd
import sys
import db_module

def read_data(goals_txt, winner_txt, btts_txt):
    winner_results = []
    goals_results = []
    btts_results = []
    try:
        with open(goals_txt, 'r', encoding = 'utf-8-sig') as file:
            for line in file:
                # Usunięcie białych znaków (np. nowych linii) z końca linii
                line = line.strip()
                # Podzielenie linii względem separatora ;
                parts = line.split(';')
                array = [parts[0], int(parts[1]), parts[2]]
                # Dodanie wyników do listy
                goals_results.append(array)
    except FileNotFoundError:
        print(f"Plik {goals_txt} nie został znaleziony.")
    except Exception as e:
        print(f"Wystąpił błąd: {e}")
    try:
        with open(winner_txt, 'r', encoding = 'utf-8-sig') as file:
            for line in file:
                # Usunięcie białych znaków (np. nowych linii) z końca linii
                line = line.strip()
                # Podzielenie linii względem separatora ;
                parts = line.split(';')
                # Dodanie wyników do listy
                array = [parts[0], float(parts[1]), float(parts[2]), float(parts[3])]
                winner_results.append(array)
    except FileNotFoundError:
        print(f"Plik {winner_txt} nie został znaleziony.")
    except Exception as e:
        print(f"Wystąpił błąd: {e}")
    try:
        with open(btts_txt, 'r', encoding = 'utf-8-sig') as file:
            for line in file:
                # Usunięcie białych znaków (np. nowych linii) z końca linii
                line = line.strip()
                # Podzielenie linii względem separatora ;
                parts = line.split(';')
                # Dodanie wyników do listy
                array = [int(parts[0]), float(parts[1]), float(parts[2])]
                btts_results.append(array)
    except FileNotFoundError:
        print(f"Plik {winner_txt} nie został znaleziony.")
    except Exception as e:
        print(f"Wystąpił błąd: {e}")

    
    return goals_results, winner_results, btts_results

def main():
    goals_results = []
    winner_results = []
    btts_results = []
    goals_txt = sys.argv[1]
    winner_txt = sys.argv[2]
    btts_txt = sys.argv[3]
    goals_results, winner_results, btts_results = read_data(goals_txt, winner_txt, btts_txt)
    conn = db_module.db_connect()
    #POL1 - 1
    #POL2 - 21
    #ENG1 - 2
    #ENG2 - 8
    #FRA1 - 3
    #FRA2 - 13
    #ITA1 - 5
    #ITA2 - 26
    #ESP1 - 6
    #ESP2 - 14
    #GER1 - 4
    #GER2 - 20
    query = "SELECT m.id, t1.name, t2.name, m.league, m.season, m.home_team_goals, m.away_team_goals, m.result FROM matches m join teams t1 on m.home_team = t1.id join teams t2 on m.away_team = t2.id where game_date > '2024-04-10'  order by game_date"
    upcoming_df = pd.read_sql(query, conn)
    upcoming_np = upcoming_df.to_numpy()
    bookmakers = "SELECT match_id, event, odds FROM ODDS WHERE BOOKMAKER = 4"
    bookmakers_df = pd.read_sql(bookmakers, conn)
    bookmakers_np = bookmakers_df.to_numpy()
    correct_goals = 0
    correct_ou = 0
    correct_winners = 0
    correct_btts = 0
    account_winners = 0
    account_ou = 0
    btts_winner = 0
    size = 0
    goals_results = sorted(goals_results, key=lambda x: x[0])
    winner_results = sorted(winner_results, key=lambda x: x[0])
    btts_results = sorted(btts_results, key=lambda x: x[0])
    print(goals_results[:5])
    print(winner_results[:5])
    print(btts_results[:5])
    for i in range(len(goals_results)):
        for b in range(len(btts_results)):
            if int(goals_results[i][0]) == int(btts_results[b][0]):
                for c in range(len(upcoming_df)):
                    if int(goals_results[i][0]) == int(upcoming_np[c][0]):
                        btts_flag = False
                        btts_winner = btts_winner - 1
                        btts = 1
                        if int(upcoming_np[c][5]) > 0 and int(upcoming_np[c][6]) > 0:
                            btts = 0
                        btts_local = [btts_results[b][1], btts_results[b][2]]
                        max_btts = np.max(btts_local)
                        max_btts_index = btts_local.index(max_btts)
                        if max_btts_index == btts:
                            correct_btts = correct_btts + 1
                            btts_flag = True
                        for d in range(len(bookmakers_np)):
                            if int(goals_results[i][0]) == int(bookmakers_np[d][0]):
                                if int(bookmakers_np[d][1]) == 6 and btts_flag and btts == 0:
                                    print("Mecz: {} vs {} - {}:{}".format(upcoming_np[c][1], upcoming_np[c][2], upcoming_np[c][5], upcoming_np[c][6]))
                                    print("Zdarzenie: BTTS TAK")
                                    print("Kurs: ", bookmakers_np[d][2])
                                    btts_winner = btts_winner + float(bookmakers_np[d][2]) * 0.88
                                elif int(bookmakers_np[d][1]) == 172 and btts_flag and btts == 1:
                                    print("Mecz: {} vs {} - {}:{}".format(upcoming_np[c][1], upcoming_np[c][2], upcoming_np[c][5], upcoming_np[c][6]))
                                    print("Zdarzenie: BTTS NIE")
                                    print("Kurs: ", bookmakers_np[d][2])
                                    btts_winner = btts_winner + float(bookmakers_np[d][2]) * 0.88


        for a in range(len(winner_results)):
            if int(goals_results[i][0]) == int(winner_results[a][0]):
                for j in range(len(upcoming_df)):
                    if int(goals_results[i][0]) == int(upcoming_np[j][0]):
                        size = size + 1
                        account_winners = account_winners - 1
                        account_ou = account_ou - 1
                        correct_winner_flag = False
                        correct_ou_flag = False
                        sum_goals = upcoming_np[j][5] + upcoming_np[j][6]
                        ou = goals_results[i][2]
                        if (sum_goals < 2.5 and ou == 'U') or (sum_goals > 2.5 and ou == 'O'):
                            correct_ou_flag = True
                            correct_ou = correct_ou + 1
                        results = [winner_results[a][1], winner_results[a][2], winner_results[a][3]]
                        #print(results)
                        max_value = np.max(results) 
                        max_index = results.index(max_value) 
                        gen_result = ""
                        real_result = ""
                        if max_index == 0:
                            gen_result = upcoming_np[j][1]
                        elif max_index == 2:
                            gen_result = upcoming_np[j][2]
                        else:
                            gen_result = 'REMIS'

                        if upcoming_np[j][7] == '1':
                            real_result = upcoming_np[j][1]
                        elif upcoming_np[j][7] == '2':
                            real_result = upcoming_np[j][2]
                        else:
                            real_result = 'REMIS'

                        if int(sum_goals) == int(goals_results[i][1]):
                            correct_goals = correct_goals + 1

                        #print("Mecz: {} vs {} - {}:{}".format(upcoming_np[j][1], upcoming_np[j][2], upcoming_np[j][5], upcoming_np[j][6]))
                        #print("Wygenerowany rezultat: {}".format(gen_result))
                        #print(results)
                        #print("Prawdziwy rezultat: {}".format(real_result))
                        #print("Wygenerowana liczba bramek: {}".format(goals_results[i][1]))
                        #print("Prawdziwa liczba bramek: {}".format(sum_goals))
                        #print("{} vs {}".format(ou, "U" if sum_goals < 2.5 else "O"))
                        #print("{} - {} - {}".format(upcoming_np[j][0], max_index, upcoming_np[j][7] ))
                        if max_index == 0 and upcoming_np[j][7] == '1':
                            correct_winner_flag = True
                            correct_winners = correct_winners + 1
                        if max_index == 1 and upcoming_np[j][7] == 'X':
                            correct_winner_flag = True
                            correct_winners = correct_winners + 1
                        if max_index == 2 and upcoming_np[j][7] == '2':
                            correct_winner_flag = True
                            correct_winners = correct_winners + 1
                        for k in range(len(bookmakers_np)):
                            if int(goals_results[i][0]) == int(bookmakers_np[k][0]):
                                if int(bookmakers_np[k][1]) == 1:
                                    #Zwyciestwo gospo
                                    if upcoming_np[j][7] == '1' and correct_winner_flag:
                                        #print("Mecz: {} vs {} - {}:{}".format(upcoming_np[j][1], upcoming_np[j][2], upcoming_np[j][5], upcoming_np[j][6]))
                                        #print("Zdarzenie: Zwycięstwo gospo")
                                        #print("Kurs: ", bookmakers_np[k][2])
                                        account_winners = account_winners + float(bookmakers_np[k][2]) #* 0.88
                                elif int(bookmakers_np[k][1]) == 2:
                                    if upcoming_np[j][7] == 'X' and correct_winner_flag:
                                        #print("Mecz: {} vs {} - {}:{}".format(upcoming_np[j][1], upcoming_np[j][2], upcoming_np[j][5], upcoming_np[j][6]))
                                        #print("Zdarzenie: Remis")
                                        #print("Kurs: ", bookmakers_np[k][2])
                                        account_winners = account_winners + float(bookmakers_np[k][2]) #* 0.88
                                elif int(bookmakers_np[k][1]) == 3:
                                    if upcoming_np[j][7] == '2' and correct_winner_flag:
                                        #print("Mecz: {} vs {} - {}:{}".format(upcoming_np[j][1], upcoming_np[j][2], upcoming_np[j][5], upcoming_np[j][6]))
                                        #print("Zdarzenie: Zwycięstwo gość")
                                        #print("Kurs: ", bookmakers_np[k][2])
                                        account_winners = account_winners + float(bookmakers_np[k][2]) #* 0.88
                                elif int(bookmakers_np[k][1]) == 8:
                                    if sum_goals > 2.5 and correct_ou_flag:
                                        #print(sum_goals)
                                        #print(float(bookmakers_np[k][2]))
                                        #print("Mecz: {} vs {} - {}:{}".format(upcoming_np[j][1], upcoming_np[j][2], upcoming_np[j][5], upcoming_np[j][6]))
                                        #print("Zdarzenie: Under 2.5")
                                        #print("Kurs: ", bookmakers_np[k][2])
                                        account_ou = account_ou + float(bookmakers_np[k][2]) #* 0.88
                                elif int(bookmakers_np[k][1]) == 12:
                                    if sum_goals < 2.5 and correct_ou_flag:
                                        #print("Mecz: {} vs {} - {}:{}".format(upcoming_np[j][1], upcoming_np[j][2], upcoming_np[j][5], upcoming_np[j][6]))
                                        #print("Zdarzenie: Over 2.5")
                                        #print("Kurs: ", bookmakers_np[k][2])
                                        #print(float(bookmakers_np[k][2]))
                                        account_ou = account_ou + float(bookmakers_np[k][2]) #* 0.88
                                else:  
                                    pass
    print("Rozmiar danych: ", size)
    print("Prawidlowe OU: ", correct_ou)
    print("Prawidlowe OU %: ", correct_ou / size)
    print( "Prawidłowy rezultat: ", correct_winners)
    print("Prawidłowy rezultat %: ", correct_winners / size)
    print("Prawidłowa liczba bramek: ", correct_goals)
    print("Prawidłowa liczba bramek %: ", correct_goals / size)
    print("Prawidłowe BTTS: ", correct_btts)
    print("Prawidłowe BTTS %: ", correct_btts / size)
    print("ZYSK Z OU: ", account_ou)
    print("ZYSK Z 1X2: ", account_winners)
    print("ZYSK Z BTTS: ", btts_winner)
    conn.close()

if __name__ == '__main__':
    main()