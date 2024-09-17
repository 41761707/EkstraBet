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
import bet_module
import db_module
## @package main
# Moduł main zawiera funkcje i procedury odpowiedzialne za interakcję z użytkownikiem 
# oraz inicjalizację jak i poprawny przepływ działania programu.

##
# Funkcja odpowiadająca za pobranie informacji z bazy danych
def get_values():
    conn = db_module.db_connect()
    query = "SELECT * FROM matches where game_date < '2024-09-12' and league in (29, 38) and result != '0' order by game_date"
    matches_df = pd.read_sql(query, conn)
    query = "SELECT id, name FROM teams where country = 23"
    teams_df = pd.read_sql(query, conn)
    matches_df['result'] = matches_df['result'].replace({'X': 0, '1' : 1, '2' : -1}) # 0 - remis, 1 - zwyciestwo gosp. -1 - zwyciestwo goscia
    matches_df.set_index('id', inplace=True)
    query = "SELECT id, home_team, away_team, league, season FROM matches where game_date >= '2024-09-12' and league in (29, 38) and home_team not in (845, 852, 853, 857) and away_team not in (845, 852, 853, 857) order by game_date"
    upcoming_df = pd.read_sql(query, conn)
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

def predict_chosen_matches_goals(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print):
    external_tests = data.generate_goals_test(schedule, ratings, powers, last_five_matches)
    external_tests_np = np.array(external_tests)
    predictions = predict_model.make_goals_predictions(external_tests_np)
    for i in range(len(predictions)):
        record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1])]
        id = record.iloc[0]['id']
        generated_ou = "U" if predictions[i] < 2.5 else "O"
        if pretty_print == 'pretty':

            #print("{};{};{}".format(id, predictions[i], generated_ou))
            print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
            print("Wygenerowana liczba bramek w spotkaniu: {} - O/U: {}".format(predictions[i], generated_ou))
            '''print("Rankingi druzyny domowej {} - {} - {} - {}".format(
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
            ))'''
        else:
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 173 , {:.2f});".format(id, predictions[i]))

def predict_chosen_matches_winner(data, schedule, predict_model, teams_dict, ratings, upcoming_df, pretty_print):
    external_tests = data.generate_winner_test(schedule, ratings)
    external_tests_np = np.array(external_tests)
    #print(external_tests_np[0])
    predictions = predict_model.make_winner_predictions(external_tests_np)
    for i in range(len(predictions)):
        record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1])]
        id = record.iloc[0]['id']
        #print(external_tests_np[i][8])
        percentages = np.round(predictions[i] * 100, 2)
        if pretty_print == "pretty":
            print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
            print("Rankingi: {:.2f} - {:.2f}".format(ratings[schedule[i][0]], ratings[schedule[i][1]]))
            print("Gospo: {:.2f}, Remis: {:.2f}, Gość: {:.2f}".format(percentages[0], percentages[1], percentages[2]))
        else:
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 1 , {:.2f});".format(id, percentages[0]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 2 , {:.2f});".format(id, percentages[1]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 3 , {:.2f});".format(id, percentages[2]))
    

def predict_chosen_matches_btts(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print):
    external_tests = data.generate_btts_test(schedule, ratings, powers, last_five_matches)
    external_tests_np = np.array(external_tests)
    predictions = predict_model.make_btts_predictions(external_tests_np)
    for i in range(len(predictions)):
        record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1])]
        id = record.iloc[0]['id']
        percentages = np.round(predictions[i] * 100, 2)
        if pretty_print == "pretty":
            print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
            print("Tak: {:.2f}, Nie: {:.2f}".format(percentages[0], percentages[1]))
        else:
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 6 , {:.2f});".format(id, percentages[0]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 172 , {:.2f});".format(id, percentages[1]))

def predict_chosen_matches_goals_ou(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print):
    external_tests = data.generate_btts_test(schedule, ratings, powers, last_five_matches)
    external_tests_np = np.array(external_tests)
    predictions = predict_model.make_btts_predictions(external_tests_np)
    for i in range(len(predictions)):
        record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1])]
        id = record.iloc[0]['id']
        percentages = np.round(predictions[i] * 100, 2)
        if pretty_print == "pretty":
            print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
            print("Under: {:.2f}, Over: {:.2f}".format(percentages[0], percentages[1]))
        else:
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 12 , {:.2f});".format(id, percentages[0]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 8 , {:.2f});".format(id, percentages[1]))

def predict_chosen_matches_goals_ppb(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print):
    external_tests = data.generate_goals_test(schedule, ratings, powers, last_five_matches)
    external_tests_np = np.array(external_tests)
    predictions = predict_model.make_goals_ppb_predictions(external_tests_np)
    for i in range(len(predictions)):
        record = upcoming_df.loc[(upcoming_df['home_team'] == schedule[i][0]) & (upcoming_df['away_team'] == schedule[i][1])]
        id = record.iloc[0]['id']
        percentages = np.round(predictions[i] * 100, 2)
        under_2_5 = percentages[0] + percentages[1] + percentages[2]
        over_2_5 = percentages[3] + percentages[4] + percentages[5] + percentages[6]

        #print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
        #for i in range(len(percentages)):
        #    print("Ppb {} bramek: {}".format(i, percentages[i]))
        #print("{:.2f}, {:.2f}".format(percentages[0], percentages[1]))
        if pretty_print == 'pretty':
            print("Spotkanie: {} - {}".format(teams_dict[schedule[i][0]], teams_dict[schedule[i][1]]))
            print("Under: {:.2f}, Over: {:.2f}".format(under_2_5, over_2_5))
            for i in range(len(percentages)):
                print("Ppb {} bramek: {}".format(i, percentages[i]))
        else:
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 174 , {:.2f});".format(id, percentages[0]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 175 , {:.2f});".format(id, percentages[1]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 176 , {:.2f});".format(id, percentages[2]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 177 , {:.2f});".format(id, percentages[3]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 178 , {:.2f});".format(id, percentages[4]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 179 , {:.2f});".format(id, percentages[5]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 180 , {:.2f});".format(id, percentages[6]))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 8 , {:.2f});".format(id, over_2_5))
            print("INSERT INTO predictions(match_id, event_id, value) VALUES({}, 12 , {:.2f});".format(id, under_2_5))


def predict_whole_season(data, schedule, predict_model, my_rating, ratings, matches_df, teams_dict, upcoming_df):
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


def generate_schedule(upcoming_df):
    schedule = []
    for _, row in upcoming_df.iterrows():
        schedule.append([row['home_team'], row['away_team']])
    return schedule
##
# Funkcja odpowiedzialna za rozruch oraz kontrolowanie przepływu programu
def main():
    model_type = sys.argv[1]
    model_mode = sys.argv[2]

    pretty_print = sys.argv[4]
    matches_df, teams_df, upcoming_df = get_values()
    rating_factory = ratings_module.RatingFactory()
    my_rating = ""
    if model_type == 'goals_total' or model_type == 'goals_ppb' or model_type == 'goals_ou':
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
        #if model_type == 'goals_ppb':
        #    accuracy_test_goals_ppb(matches_df, teams_dict, teams_df, upcoming_df, int(sys.argv[3]))
        if model_type == 'winner':
            accuracy_test_winner(matches_df, teams_dict, teams_df, upcoming_df, int(sys.argv[3]))
        if model_type == 'btts':
            accuracy_test_btts(matches_df, teams_dict, teams_df, upcoming_df, int(sys.argv[3]))
    else:
        if model_type == 'goals_total':
            data.prepare_predict_goals()
            _, _, _, model_columns_df = data.get_data() 
            predict_model = model_module.Model(model_type, matches_df, model_columns_df, 9, 6, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(1)
            predict_model.divide_set()
            predict_model.train_goals_total_model()
            predict_model.goals_total_test()

        if model_type == 'goals_ppb':
            data.prepare_predict_goals_ppb()
            _, _, _, model_columns_df = data.get_data() 
            predict_model = model_module.Model(model_type, matches_df, model_columns_df, 9, 6, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(7)
            predict_model.divide_set()
            predict_model.train_goals_ppb_model()
            predict_model.goals_ppb_test()

        if model_type =='goals_ou':
            data.prepare_predict_ou()
            _, _, _, model_columns_df = data.get_data()
            predict_model = model_module.Model(model_type, matches_df, model_columns_df, 9, 6, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(2)
            predict_model.divide_set()
            predict_model.train_ou_model()
            predict_model.test_btts_model()

        if model_type == 'winner':
            data.prepare_predict_winner()
            _, _, _, model_columns_df = data.get_data()
            predict_model = model_module.Model(model_type, matches_df, model_columns_df, 9, 2, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(3)
            predict_model.divide_set()
            predict_model.train_winner_model()
            predict_model.test_winner_model()
        
        if model_type =='btts':
            data.prepare_predict_btts()
            _, _, _, model_columns_df = data.get_data()
            predict_model = model_module.Model(model_type, matches_df, model_columns_df, 9, 6, model_mode)
            predict_model.create_window()
            predict_model.window_to_numpy(2)
            predict_model.divide_set()
            predict_model.train_btts_model()
            predict_model.test_btts_model()

        schedule = generate_schedule(upcoming_df)
        #print(schedule)
        if model_type == 'winner':
            predict_chosen_matches_winner(data, schedule, predict_model, teams_dict, ratings, upcoming_df, pretty_print)
        if model_type == 'goals_ppb':
            predict_chosen_matches_goals_ppb(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print)
        if model_type == 'goals_total':
            predict_chosen_matches_goals(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print)
        if model_type == 'goals_ou':
            predict_chosen_matches_goals_ou(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print)
        if model_type == 'btts':
            predict_chosen_matches_btts(data, schedule, predict_model, teams_dict, ratings, powers, last_five_matches, upcoming_df, pretty_print)
        #Mock testing
        #predict_whole_season(data, schedule, predict_model, my_rating, ratings, matches_df, teams_dict, upcoming_df)

if __name__ == '__main__':
    main()