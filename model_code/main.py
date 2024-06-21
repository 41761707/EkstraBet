import mysql.connector
import pandas as pd
import numpy as np
import sys
import random

#Moduły
import ratings_module
import model_module 
import dataprep_module
import views_module
import league_module
import bet_module
import db_module
## @package main
# Moduł main zawiera funkcje i procedury odpowiedzialne za interakcję z użytkownikiem 
# oraz inicjalizację jak i poprawny przepływ działania programu.

##
# Funkcja odpowiadająca za pobranie informacji z bazy danych
def get_values():
    conn = db_module.db_connect()
    query = "SELECT * FROM matches where game_date < '2024-06-06' order by game_date"
    matches_df = pd.read_sql(query, conn)
    query = "SELECT id, name FROM teams"
    teams_df = pd.read_sql(query, conn)
    matches_df['result'] = matches_df['result'].replace({'X': 0, '1' : 1, '2' : -1}) # 0 - remis, 1 - zwyciestwo gosp. -1 - zwyciestwo goscia
    matches_df.set_index('id', inplace=True)
    query = "SELECT id, home_team, away_team, league, season FROM matches where game_date >= '2024-04-10' order by game_date"
    upcoming_df = pd.read_sql(query, conn)
    #upcoming_df.set_index('id', inplace=True)
    conn.close()
    return matches_df, teams_df, upcoming_df

def accuracy_test_goals(matches_df, teams_dict, teams_df, upcoming_df, key):
    filtered_matches_df = matches_df.loc[(matches_df['home_team'] == key) | (matches_df['away_team'] == key)]
    model_type = 'goals_total'
    data = dataprep_module.DataPrep(filtered_matches_df , teams_df, upcoming_df)
    data.prepare_predict_goals()

    _, _, _, model_columns_df = data.get_data() 
    predict_model = model_module.Model(model_type, model_columns_df, 9, 6, 'old')
    predict_model.create_window()
    predict_model.window_to_numpy(1)
    predict_model.divide_set()
    predict_model.train_goals_total_model()
    exact_accuracy, ou_accuracy, exact, ou, predictions = predict_model.graph_team_goals(teams_dict[key])
    print("{};{};{};{};{};{}".format(key,
                                     exact_accuracy,
                                     ou_accuracy,
                                     exact, 
                                     ou, 
                                     predictions))
    
def accuracy_test_winner(matches_df, teams_dict, teams_df, upcoming_df, key):
    filtered_matches_df = matches_df.loc[(matches_df['home_team'] == key) | (matches_df['away_team'] == key)]
    model_type = 'winner'
    data = dataprep_module.DataPrep(filtered_matches_df , teams_df, upcoming_df)
    data.prepare_predict_winner()

    _, _, _, model_columns_df = data.get_data() 
    predict_model = model_module.Model(model_type, model_columns_df, 9, 2, 'old')
    predict_model.create_window()
    predict_model.window_to_numpy(3)
    predict_model.divide_set()
    predict_model.train_winner_model()
    accuracy, predictions = predict_model.graph_team_winner(teams_dict[key])
    print("{};{};{}".format(key,
                                     accuracy,
                                     predictions))
    

def accuracy_test_btts(matches_df, teams_dict, teams_df, upcoming_df, key):
    filtered_matches_df = matches_df.loc[(matches_df['home_team'] == key) | (matches_df['away_team'] == key)]
    model_type = 'btts'
    data = dataprep_module.DataPrep(filtered_matches_df , teams_df, upcoming_df)
    data.prepare_predict_btts()

    _, _, _, model_columns_df = data.get_data() 
    predict_model = model_module.Model(model_type, model_columns_df, 9, 6, 'old')
    predict_model.create_window()
    predict_model.window_to_numpy(2)
    predict_model.divide_set()
    predict_model.train_btts_model()
    accuracy, predictions = predict_model.graph_team_btts(teams_dict[key])
    print("{};{};{}".format(key,
                                     accuracy,
                                     predictions))

def predict_chosen_matches_goals(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df):
    external_tests = data.generate_goals_test(schedule, ratings, powers, last_five_matches)
    external_tests_np = np.array(external_tests)
    predictions = predict_model.make_goals_predictions(external_tests_np)
    for i in range(len(predictions)):
        #record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1]) & (upcoming_df['season'] == 1)]
        #id = record.iloc[0]['id']
        generated_ou = "U" if predictions[i] < 2.5 else "O"
        #print("{};{};{}".format(id, predictions[i], generated_ou))
        print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
        print("Rankingi druzyny domowej {} - {} - {} - {}".format(
                                                    powers["{}h_att".format(schedule[i][0])],
                                                    powers["{}h_def".format(schedule[i][0])], 
                                                    powers["{}a_att".format(schedule[i][0])],
                                                    powers["{}a_def".format(schedule[i][0])] ,
        ))
        print("Rankingi druzyny wyjazdowej {} - {} - {} - {}".format(
                                                    powers["{}h_att".format(schedule[i][1])],
                                                    powers["{}h_def".format(schedule[i][1])], 
                                                    powers["{}a_att".format(schedule[i][1])],
                                                    powers["{}a_def".format(schedule[i][1])] ,
        ))
        print("Wygenerowana liczba bramek w spotkaniu: {} - O/U: {}".format(predictions[i], generated_ou))

def predict_chosen_matches_winner(data, schedule, predict_model, teams_dict, ratings, upcoming_df):
    external_tests = data.generate_winner_test(schedule, ratings)
    external_tests_np = np.array(external_tests)
    #print(external_tests_np[0])
    predictions = predict_model.make_winner_predictions(external_tests_np)
    for i in range(len(predictions)):
        #record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1]) & (upcoming_df['season'] == 1)]
        #id = record.iloc[0]['id']
        #print(external_tests_np[i][8])
        percentages = np.round(predictions[i] * 100, 2)
        #print("{};{:.2f};{:.2f};{:.2f}".format(id, percentages[0], percentages[1], percentages[2]))
        print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
        print("Rankingi: {} - {}".format(ratings[schedule[i][0]], ratings[schedule[i][1]]))
        print(percentages)

def predict_chosen_matches_btts(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df):
    external_tests = data.generate_btts_test(schedule, ratings, powers, last_five_matches)
    external_tests_np = np.array(external_tests)
    predictions = predict_model.make_btts_predictions(external_tests_np)
    for i in range(len(predictions)):
        #record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1]) & (upcoming_df['season'] == 1)]
        #id = record.iloc[0]['id']
        percentages = np.round(predictions[i] * 100, 2)
        #print("{};{:.2f};{:.2f}".format(id, percentages[0],percentages[1]))
        print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
        print("{:.2f}, {:.2f}".format(percentages[0], percentages[1]))


def predict_chosen_matches_winner_one(data, schedule, predict_model, my_rating, ratings, matches_df, teams_dict, upcoming_df):
    #schedule =  [[home_team, away_team, game_date], [...], ...]
    team_table = {
        198: 0,
        199: 0,
        200: 0,
        201: 0,
        202: 0,
        203: 0,
        204: 0,
        205: 0,
        206: 0,
        207: 0,
        208: 0,
        209: 0,
        210: 0,
        211: 0,
        212: 0,
        213: 0,
        218: 0,
        215: 0,
        219: 0,
        226: 0
    }
    predictions = []
    winners = []
    for match in schedule:
        #record = upcoming_df.loc[(upcoming_df['home_team'] == match[0]) & (upcoming_df['away_team'] == match[1]) & (upcoming_df['season'] == 1)]
        #id = record.iloc[0]['id']
        match_array = data.generate_winner_test_one(match,ratings, matches_df)
        match_array_np = np.array(match_array)
        #print(match_array)
        match_predict = predict_model.make_winner_predictions(match_array_np)
        #print(match_predict)
        winner = np.argmax(match_predict, axis=1)[0]
        winner_prob = random.uniform(0,1)
        #print(winner_prob)
        if match_predict[0][0] >= winner_prob:
            winner = 0
            team_table[match[0]] += 3
        elif match_predict[0][1] >= winner_prob:
            winner = 1
            team_table[match[0]] += 1
            team_table[match[1]] += 1
        else:
            winner = 2
            team_table[match[1]] += 3
        predictions.append(match_predict)
        winners.append(winner)
        #print("WINNER: ", winner)
        #Aktualizacja rankingu
        elo_winner = -1
        if winner == 0:
            elo_winner = 1
        elif winner == 1:
            elo_winner = 0
        old_home_rating, old_away_rating = ratings[match[0]], ratings[match[1]]

        new_home_rating, new_away_rating = my_rating.main_rating(ratings, match[0], match[1], elo_winner, 1, 0, 10)
        #print(new_home_rating, new_away_rating)
        results= []
        if winner == 0:
            #print(winner)
            results = [1, 0, 0]
        elif winner == 1:
            results = [0, 1, 0]
        else:
            results= [0, 0, 1]
        new_record = {'home_team': match[0], 
                      'away_team': match[1], 
                      'home_rating' : new_home_rating,
                      'away_rating' : new_away_rating,
                      'results_home' : results[0],
                      'results_draw' : results[1],
                      'results_away' : results[2] }
        matches_df = matches_df._append(new_record, ignore_index = True)
        percentages = np.round(match_predict[0] * 100, 2)
        #print("{};{:.2f};{:.2f};{:.2f}".format(id, percentages[0], percentages[1], percentages[2]))
        print("Spotkanie: {} - {}".format(teams_dict[match[0]], teams_dict[match[1]]))
        print("Rezultat: ", winner)
        print("Ranking przed: {} - {}".format(old_home_rating, old_away_rating ))
        print(percentages)
        print("Ranking po: {} - {}".format(new_home_rating, new_away_rating ))
    print("TABELA NA KONIEC: ")
    sorted_team_table = dict(sorted(team_table.items(), key=lambda item: item[1]))
    print(sorted_team_table)
    #for i in range(len(predictions)):
    #    percentages = np.round(predictions[i] * 100, 2)
    #    print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
    #    print(percentages)




##
# Funkcja odpowiedzialna za rozruch oraz kontrolowanie przepływu programu
def main():
    model_type = sys.argv[1]
    model_mode = sys.argv[2]
    matches_df, teams_df, upcoming_df = get_values()
    rating_factory = ratings_module.RatingFactory()
    my_rating = ""
    if model_type == 'goals_total':
        my_rating = rating_factory.create_rating("GoalsRating", matches_df, teams_df)
        my_rating.rating_wrapper()
        matches_df, _, teams_dict , powers, ratings, last_five_matches = my_rating.get_data()
        #my_rating.print_ratings()
    if model_type == 'winner':
        my_rating = rating_factory.create_rating("WinnerRating", matches_df, teams_df)
        my_rating.rating_wrapper()
        matches_df, _, teams_dict , _, ratings = my_rating.get_data()
        my_rating.print_ratings()
    if model_type == 'btts':
        my_rating = rating_factory.create_rating("BTTSRating", matches_df, teams_df)
        my_rating.rating_wrapper()
        matches_df, _, teams_dict , powers, ratings, last_five_matches = my_rating.get_data()
        #my_rating.print_ratings()

    data = dataprep_module.DataPrep(matches_df, teams_df, upcoming_df)
    if sys.argv[3] != '-1':
        if model_type == 'goals_total':
            accuracy_test_goals(matches_df, teams_dict, teams_df, upcoming_df, int(sys.argv[3]))
        if model_type == 'winner':
            accuracy_test_winner(matches_df, teams_dict, teams_df, upcoming_df, int(sys.argv[3]))
        if model_type == 'btts':
            accuracy_test_btts(matches_df, teams_dict, teams_df, upcoming_df, int(sys.argv[3]))
    #team_id = int(sys.argv[3])
    #accuracy_test_goals(matches_df, teams_dict, teams_df, upcoming_df, int(sys.argv[3]))
    else:
        if model_type == 'goals_total':
            data.prepare_predict_goals()
            _, _, _, model_columns_df = data.get_data() 
            predict_model = model_module.Model(model_type, model_columns_df, 9, 6, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(1)
            predict_model.divide_set()
            predict_model.train_goals_total_model()
            predict_model.goals_total_test()

        if model_type == 'winner':
            data.prepare_predict_winner()
            _, _, _, model_columns_df = data.get_data()
            predict_model = model_module.Model(model_type, model_columns_df, 9, 2, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(3)
            predict_model.divide_set()
            predict_model.train_winner_model()
            predict_model.test_winner_model()
        
        if model_type =='btts':
            data.prepare_predict_btts()
            _, _, _, model_columns_df = data.get_data()
            predict_model = model_module.Model(model_type, model_columns_df, 9, 6, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(2)
            predict_model.divide_set()
            predict_model.train_btts_model()
            predict_model.test_btts_model()
        '''schedule = [
            [15,16], [6, 17], [11, 12], [14, 3], [4, 5], [18, 10], [2, 13], [7, 1], [9, 8], #Ekstralasa kolejka 28
            [16, 10], [4, 7], [6, 9], [17, 12], [8, 2], [13, 14], [18, 3], [5, 1], [15, 11], #Ekstralasa kolejka 29
            [9, 15], [2, 6], [7, 18], [1, 17], [12, 4], [10, 8], [11, 5], [3, 13], [14, 16], #Ekstralasa kolejka 30
            [13, 7], [17, 3], [18, 1], [8, 4], [11, 2], [15, 12], [16, 9], [5, 10], [6, 14], #Ekstralasa kolejka 31
            [28, 23], [318, 27], [34, 30], [32, 35], [19, 24], [31, 21], [20, 22], [48, 33], [26, 319], #Fortuna 1 Liga kolejka 27
            [319, 28], [30, 26], [48, 24], [33, 34], [23, 20], [35, 31], [27, 19], [21, 318], [22, 32], #Fortuna 1 Liga kolejka 28
            [26, 33], [28, 30], [34, 24], [19, 21], [48, 27], [20, 319], [22, 35], [318, 31], [32, 23], #Fortuna 1 Liga kolejka 29
            [24, 26], [30, 20], [33, 28], [27, 34], [21, 48], [319, 32], [23, 22], [31, 19], [35, 318], #Fortuna 1 Liga kolejka 30
            [58, 55], [65, 70], [74, 59], [52, 68], [67, 60], [63, 56], [51, 64], [57, 62], [53, 54], [61, 66], #Premier League kolejka 33
            [59, 61], [68, 65], [56, 58], [70, 74], [60, 53], [66, 67], [54, 63], [64, 57], [62,51], [55, 52], #Premier League kolejka 34
            [57, 51], [62, 64], [56, 74], [58, 70], [60, 68], [66, 65], [54, 61], [63, 59], [55, 53], [67, 52], #Premier League kolejka 35
            [68, 66], [53, 63], [65, 62], [59, 54], [74, 58], [70, 67], [52, 60], [61, 57], [51, 55], [64, 56], #Premier League kolejka 36
            [320, 71], [72, 86], [90, 85], [89, 79], [82, 92], [102, 84], [87, 78], [88, 76], [100, 81], [73, 75], [80, 91], [77, 83], # Championship kolejka 43
            [71, 77], [78, 73], [79, 80], [76, 89], [91, 90], [81, 320], [83, 87], [75, 82], [92, 88], [86, 100], [84, 72], [85, 102], # Championship kolejka 44
            [92, 72], [86, 85], [89, 91], [78, 84], [79, 90], [87, 320], [76, 80], [100, 77], [73, 81], [75, 83], [82, 102], [88, 71], # Championship kolejka 45
            [90, 76], [85, 92], [102, 79], [72, 73], [71, 86], [84, 75], [320, 82], [91, 78], [81, 89], [83, 100], [80, 87], [77, 88], # Championship kolejka 46
            [199, 212], [213, 211], [207, 204], [206, 208], [198, 226], [210, 201], [209, 203], [200, 218], [205, 219], [202, 215], #Seria A kolejka 32
            [219, 199], [218, 204], [211, 198], [215, 209], [210, 213], [207, 226], [212, 205], [208, 202], [203, 206], [201, 200], #Seria A kolejka 33
            [202, 211], [206, 209], [205, 210], [226, 212], [219, 218], [200, 207], [204, 201], [199, 215], [213, 208], [198, 203], #Seria A kolejka 34
            [201, 219], [203, 204], [218, 213], [211, 226], [208, 199], [212, 202], [210, 200], [207, 206], [209, 198], [215, 205], #Seria A kolejka 35
            [233, 323], [238, 235], [236, 230], [216, 237], [234, 324], [217, 231], [239, 228], [325, 244], [223, 214], [220, 224], #Seria B kolejka 33
            [228, 223], [244, 239], [235, 233], [230, 234], [224, 237], [324, 236], [323, 216], [325, 220], [214, 217], [231, 238], #Seria B kolejka 34
            [234, 323], [220, 216], [224, 214], [233, 231], [223, 325], [237, 235], [238, 324], [239, 230], [228, 244], [217, 236], #Seria B kolejka 35
            [216, 234], [235, 239], [323, 220], [236, 238], [214, 228], [231, 237], [230, 223], [324, 224], [325, 217], [244, 233], #Seria B kolejka 36
            [262, 269], [259, 266], [267, 271], [265, 258], [270, 257], [284, 268], [277, 279], [264, 261], [260, 273], [263, 272], #LaLiga kolejka 31
            [264, 277], [269, 284], [267, 263], [272, 262], [266, 270], [271, 260], [273, 261], [279, 259], [258, 257], [268, 265], #LaLiga kolejka 32
            [273, 271], [257, 272], [279, 269], [259, 264], [260, 258], [270, 265], [277, 263], [261, 267], [262, 268], [284, 266], #LaLiga kolejka 33
            [271, 264], [260, 284], [258, 270], [266, 257], [265, 259], [263, 262], [269, 261], [272, 279], [268, 277], [267, 273], #LaLiga kolejka 34
            [282, 275], [286, 290], [274, 327], [278, 300], [289, 295], [287, 291], [288, 281], [292, 293], [294, 276], [326, 280], [303, 296], #LaLiga 2 kolejka 35
            [291, 282], [300, 274], [293, 278], [296, 326], [276, 286], [280, 294], [275, 288], [281, 303], [327, 287], [295, 292], [290, 289], #LaLiga 2 kolejka 36
            [288, 293], [292, 300], [282, 294], [276, 275], [286, 296], [303, 327], [289, 291], [278, 290], [274, 280], [287, 281], [326, 295], #LaLiga 2 kolejka 37
            [296, 278], [295, 274], [280, 289], [293, 276], [290, 303], [281, 300], [288, 287], [275, 286], [327, 282], [294, 292], [291, 326], #LaLiga 2 kolejka 38
            [126, 106], [119, 115], [108, 117], [136, 120], [112, 116], [111, 118], [114, 105], [110, 109], [107, 113], #Ligue 1 kolejka 29 
            [113, 114], [120, 108], [106, 112], [136, 126], [109, 119], [115, 116], [118, 110], [117, 107], [105, 111], #Ligue 1 kolejka 30
            [116, 120], [105, 136], [126, 109], [112, 115], [114, 117], [119, 113], [108, 118], [111, 110], [107, 106], #Ligue 1 kolejka 31
            [118, 120], [136, 119], [106, 114], [109, 111], [126, 108], [110, 112], [113, 105], [115, 107], [117, 116], #Ligue 1 kolejka 32
            [122, 125], [127, 138], [134, 141], [321, 133], [147, 135], [142, 144], [139, 121], [123, 129], [143, 140], [132, 124], #Ligue 2 kolejka 32
            [141, 121], [122, 134], [133, 147], [124, 123], [144, 132], [321, 139], [135, 138], [129, 143], [140, 142], [125, 127], #Ligue 2 kolejka 33
            [121, 142], [138, 321], [127, 147], [134, 144], [132, 125], [135, 124], [139, 133], [141, 129], [123, 140], [143, 122], #Ligue 2 kolejka 34
            [125, 134], [122, 139], [133, 123], [144, 138], [321, 141], [142, 127], [129, 124], [140, 135], [143, 132], [147, 121], #Ligue 2 kolejka 35
            [168, 157], [162, 165], [163, 155], [154, 164], [167, 183], [156, 161], [169, 160], [180, 158], [159, 166],  #Bundesliga kolejka 29
            [160, 168], [164, 180], [183, 156], [165, 163], [161, 167], [157, 154], [166, 169], [155, 159], [158, 162],  #Bundesliga kolejka 30
            [167, 165], [154, 160], [168, 166], [156, 155], [158, 161], [159, 169], [163, 157], [162, 164], [180, 183],  #Bundesliga kolejka 31
            [165, 156], [155, 168], [169, 154], [161, 180], [166, 163], [164, 158], [157, 167], [160, 159], [183, 162],  #Bundesliga kolejka 32
            [173, 187], [171, 189], [182, 194], [175, 186], [184, 174], [170, 177], [181, 176], [188, 178], [185, 322],  #2. Bundesliga kolejka 29 
            [177, 175], [322, 170], [174, 173], [187, 184], [194, 181], [178, 182], [176, 185], [186, 171], [189, 188],  #2. Bundesliga kolejka 30
            [171, 176], [185, 189], [181, 178], [182, 187], [175, 322], [170, 174], [177, 186], [188, 194], [184, 173],  #2. Bundesliga kolejka 31
            [174, 177], [178, 185], [173, 181], [194, 170], [189, 186], [187, 188], [322, 171], [176, 175], [184, 182],  #2. Bundesliga kolejka 32
        ]'''
        schedule = [
            [490, 488], [475, 477], [483, 485], [484, 486], [476, 492], [481, 487], [480, 489], [491, 482], #SERIE A BRASIL
            [384, 376], [378, 381], [380, 383], [372, 375], [377, 382], [373, 379], [362, 361], 
            [369, 359], [365, 366], [371, 358], [368, 363], [360, 374], [370, 367] #MLS
        ]
        if model_type == 'winner':
            predict_chosen_matches_winner(data, schedule, predict_model, teams_dict, ratings, upcoming_df)
        if model_type == 'goals_total':
            predict_chosen_matches_goals(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df)
        if model_type == 'btts':
            predict_chosen_matches_btts(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df)
        #Mock testing
        #predict_chosen_matches_winner_one(data, schedule, predict_model, my_rating, ratings, matches_df, teams_dict, upcoming_df)

if __name__ == '__main__':
    main()