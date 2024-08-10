import mysql.connector
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
from sklearn.metrics import accuracy_score
from tensorflow.keras.optimizers import Adagrad
from tensorflow.keras.models import load_model
from tensorflow.keras import layers, backend
from tensorflow.keras.losses import SparseCategoricalCrossentropy
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
import random

class Model:
    def __init__(self, model_type, matches_df, model_columns_df, entries, features, create_model):
        self.model_columns_df = model_columns_df
        self.matches_df = matches_df
        self.model_type = model_type
        self.model = ''
        self.entries = entries
        self.features = features
        self.create_model = create_model
        self.window_helper = []
        self.window_df = []
        self.indexes = []
        self.X = []
        self.y = []
        self.indexes_train = []
        self.X_train = []
        self.y_train = []
        self.indexes_val = []
        self.X_val = []
        self.y_val = []
        self.indexes_test = []
        self.X_test = []
        self.y_test = []
        self.test_predictions = []
        self.mean_y = 0
        self.mean_rank = 0
        self.norm_y = 0
        self.norm_rank = 0
    
    def normalize_rank(self, data):
        data_np = np.array(data)

        # Znalezienie minimalnej i maksymalnej wartości w całej tablicy
        min_val = np.min(data_np)
        max_val = np.max(data_np)

        # Normalizacja tablicy
        normalized_data = (data_np - min_val) / (max_val - min_val)

        # Konwersja znormalizowanej tablicy z powrotem do listy (opcjonalnie)
        normalized_data_list = normalized_data.tolist()

        return normalized_data_list

    '''def create_window(self):
        model_tolist = self.model_columns_df.values.tolist()
        iter = 0
        while True:
            self.window_helper.append({'id' : model_tolist[iter+8][0], 
                                       'Match-8' : model_tolist[iter][1:], 
                                       'Match-7' : model_tolist[iter+1][1:], 
                                       'Match-6' : model_tolist[iter+2][1:], 
                                       'Match-5' : model_tolist[iter+3][1:], 
                                       'Match-4' : model_tolist[iter+4][1:], 
                                       'Match-3' : model_tolist[iter+5][1:], 
                                       'Match-2' : model_tolist[iter+6][1:],
                                       'Match-1' : model_tolist[iter+7][1:],
                                       'Match-CURR' : model_tolist[iter+8][1:]})
            iter = iter + 1
            if iter > len(self.model_columns_df)-self.entries:
                break
        self.window_df = pd.DataFrame(self.window_helper)
        #self.window_df = self.window_df.drop(columns=['id'])'''
    
    def get_last_matches(self, team_id, game_date, amount):
        filtered_rows = self.matches_df[((self.matches_df['home_team'] == int(team_id)) | 
                                        (self.matches_df['away_team'] == int(team_id))) & 
                                        (self.matches_df['game_date'] < game_date)].tail(int(amount))
        return filtered_rows
    
    def turn_match_into_numpy_winner(self, match):
        result = match['result']
        results = [1, 0, 0] if result == 1 else [0, 1, 0] if result == 0 else [0, 0, 1]
        return [match['home_rating'], 
                match['away_rating'], 
                results[0],
                results[1],
                results[2]
                ]
    def turn_match_into_numpy_btts(self, match):
        home_goals = int(match['home_team_goals'])
        away_goals = int(match['away_team_goals'])
        results = [1, 0] if home_goals > 0 and away_goals > 0 else [0, 1]
        return [match['home_home_att_power'],
                match['home_home_def_power'],
                match['away_away_att_power'],
                match['away_away_def_power'],
                match['home_goals_avg'],
                match['away_goals_avg'],
                results[0],
                results[1]
                ]
    def turn_match_into_numpy_ou(self, match):
        total_goals = int(match['home_team_goals']) + int(match['away_team_goals'])
        results = [0, 1] if total_goals > 2.5 else [1, 0]
        return [match['home_home_att_power'],
                match['home_home_def_power'],
                match['away_away_att_power'],
                match['away_away_def_power'],
                match['home_goals_avg'],
                match['away_goals_avg'],
                results[0],
                results[1]
                ]
    
    def turn_match_into_numpy_goals_ppb(self, match):
        total_goals = int(match['home_team_goals']) + int(match['away_team_goals'])
        results = [0] * 7
        results[min(total_goals, 6)] = 1
        return [match['home_home_att_power'],
                match['home_home_def_power'],
                match['away_away_att_power'],
                match['away_away_def_power'],
                match['home_goals_avg'],
                match['away_goals_avg'],
                results[0], results[1], results[2], results[3], results[4], results[5], results[6]
                ]
    
    def turn_match_into_numpy_goals_total(self, match):
        goals = int(match['home_team_goals']) + int(match['away_team_goals'])
        return [match['home_home_att_power'],
                match['home_home_def_power'],
                match['away_away_att_power'],
                match['away_away_def_power'],
                match['home_goals_avg'],
                match['away_goals_avg'],
                goals
                ]
    
    def create_window(self):
        model_tolist = self.model_columns_df.values.tolist()
        for i in range(len(model_tolist)):
            home_matches = self.get_last_matches(model_tolist[i][1], model_tolist[i][3], 4)
            away_matches = self.get_last_matches(model_tolist[i][2], model_tolist[i][3], 4)
            if len(home_matches) == 4 and len(away_matches) == 4:
                home_team_matches = []
                away_team_matches = []
                if self.model_type == 'winner':
                    for _, match in home_matches.iterrows():
                        home_team_matches.append(self.turn_match_into_numpy_winner(match))
                    for _, match in away_matches.iterrows():
                        away_team_matches.append(self.turn_match_into_numpy_winner(match))
                elif self.model_type == 'btts':
                    for _, match in home_matches.iterrows():
                        home_team_matches.append(self.turn_match_into_numpy_btts(match))
                    for _, match in away_matches.iterrows():
                        away_team_matches.append(self.turn_match_into_numpy_btts(match))
                elif self.model_type == 'goals_ou':
                    for _, match in home_matches.iterrows():
                        home_team_matches.append(self.turn_match_into_numpy_ou(match))
                    for _, match in away_matches.iterrows():
                        away_team_matches.append(self.turn_match_into_numpy_ou(match)) 
                elif self.model_type == 'goals_ppb':
                    for _, match in home_matches.iterrows():
                        home_team_matches.append(self.turn_match_into_numpy_goals_ppb(match))
                    for _, match in away_matches.iterrows():
                        away_team_matches.append(self.turn_match_into_numpy_goals_ppb(match)) 
                elif self.model_type == 'goals_total':
                    for _, match in home_matches.iterrows():
                        home_team_matches.append(self.turn_match_into_numpy_goals_total(match))
                    for _, match in away_matches.iterrows():
                        away_team_matches.append(self.turn_match_into_numpy_goals_total(match)) 
                else:
                    print("Błędny argument")
                self.window_helper.append({'id' : model_tolist[i][0], 
                                            'Match-8' : home_team_matches[0], 
                                            'Match-7' : away_team_matches[0], 
                                            'Match-6' : home_team_matches[1], 
                                            'Match-5' : away_team_matches[1], 
                                            'Match-4' : home_team_matches[2], 
                                            'Match-3' : away_team_matches[2], 
                                            'Match-2' : home_team_matches[3],
                                            'Match-1' : away_team_matches[3],
                                            'Match-CURR' : model_tolist[i][4:]})
            else:
                continue
        self.window_df = pd.DataFrame(self.window_helper)
        

    def remade(self, labels):
        new_self_x = []
        for list in self.X:
            row = []
            for inner_list in list:
                for inner_inner in inner_list:
                    row.append(inner_inner[0:-1 * labels])
            new_self_x.append(row)
        return new_self_x

        
    def window_to_numpy(self, labels):
        df_as_np = self.window_df.to_numpy()
        #for element in df_as_np:
        #    print(element)
        #self.indexes = list(range(1, len(df_as_np) + 1)) 
        self.indexes = df_as_np[:, 0]
        mid = df_as_np[:, 1:]
        tmp_y = df_as_np[:, -1]
        for element in tmp_y:
            self.y.append(element[(-1) * labels :])
        self.X = mid.reshape((len(self.indexes), mid.shape[1], 1))
        self.X = self.remade(labels)



    def divide_set(self):
        first = int(len(self.indexes) * 0.9)
        second = int(len(self.indexes) * 0.95)
        self.indexes_train, self.X_train, self.y_train = self.indexes[:first], self.X[:first], self.y[:first]
        self.indexes_val, self.X_val, self.y_val = self.indexes[first:second], self.X[first:second], self.y[first:second]
        self.indexes_test, self.X_test, self.y_test = self.indexes[second:], self.X[second:], self.y[second:]
        print("ROZMIAR TEST: ", len(self.indexes_test))
        #print("SELF.X_TRAIN: ", self.X_train[0])

    def make_goals_predictions(self, tests):
        test_prediction = self.model.predict(tests).flatten().astype(int)
        test_prediction = np.clip(test_prediction, 0, 6)
        return test_prediction
    
    def make_winner_predictions(self, tests):
        test_prediction = self.model.predict(tests)
        #test_prediction = np.argmax(test_prediction, axis=1)
        return test_prediction
    
    def make_goals_ppb_predictions(self, tests):
        test_prediction = self.model.predict(tests)
        #test_prediction = np.argmax(test_prediction, axis=1)
        return test_prediction
    
    def make_btts_predictions(self, tests):
        test_prediction = self.model.predict(tests)
        #test_prediction = np.argmax(test_prediction, axis=1)
        return test_prediction

    def graph_team_goals(self, team_name):
        test_predictions = self.model.predict(self.X_test).flatten().astype(int)
        test_predictions = np.clip(test_predictions, 0, 6)
        plt.plot([x for x in range(len(test_predictions))], test_predictions)
        plt.plot([x for x in range(len(test_predictions))], self.y_test)
        plt.legend(['Predykcje', 'Obserwacje'])
        plt.savefig('graphs/goals/{}_goals_total.png'.format(team_name))
        plt.close()
        ou_accuracy = 0
        exact_accuracy = 0
        for i in range(len(test_predictions)):
            generated_ou = "U" if test_predictions[i] < 2.5 else "O"
            real_ou = "U" if self.y_test[i][0] < 2.5 else "O"
            if generated_ou == real_ou:
                ou_accuracy = ou_accuracy + 1
            if test_predictions[i] == self.y_test[i][0]:
                exact_accuracy = exact_accuracy + 1
        return exact_accuracy / len(test_predictions), ou_accuracy / len(test_predictions), exact_accuracy, ou_accuracy, len(test_predictions)
    
    def graph_team_btts(self, team_name):
        test_predictions = self.model.predict(self.X_test)
        np_array = np.array(self.y_test)
        test_max = np.argmax(np_array, axis=1)
        predict_max = np.argmax(test_predictions, axis = 1)
        plt.plot([x for x in range(len(predict_max))], predict_max)
        plt.plot([x for x in range(len(predict_max))], test_max)
        plt.legend(['Predykcje', 'Obserwacje'], loc='upper left')
        plt.savefig('graphs/btts/{}_winner.png'.format(team_name))
        plt.close()
        print(test_max)
        print(predict_max)
        return np.sum(test_max  == predict_max ) / len(test_max), len(test_max)
    
    def graph_team_winner(self, team_name):
        test_predictions = self.model.predict(self.X_test)
        np_array = np.array(self.y_test)
        test_max = np.argmax(np_array, axis=1)
        predict_max = np.argmax(test_predictions, axis = 1)
        plt.plot([x for x in range(len(predict_max))], predict_max)
        plt.plot([x for x in range(len(predict_max))], test_max)
        plt.legend(['Predykcje', 'Obserwacje'], loc='upper left')
        plt.savefig('graphs/winners/{}_winner.png'.format(team_name))
        plt.close()
        print(test_max)
        print(predict_max)
        return np.sum(test_max  == predict_max ) / len(test_max), len(test_max)
    
    def train_goals_total_model(self):
        if self.create_model == 'new':
            self.model = Sequential([layers.Input((int(self.entries), self.features)),
                    layers.LSTM(64, activation = 'relu'),
                    layers.Dense(32, activation = 'relu'),
                    layers.Dense(16, activation = 'relu'),
                    layers.Dense(1)])
            cp = ModelCheckpoint('model_goals/', save_best_only = True)
            es = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)
            self.model.load_weights('model_goals/model_weights.h5')
            self.model.compile(loss='mse', 
                optimizer=Adagrad(learning_rate=0.001),
                metrics=['accuracy'])
            self.model.fit(self.X_train, self.y_train, validation_data=(self.X_val, self.y_val), epochs=15, batch_size = 32, callbacks = [cp, es])
            #print(self.model.summary())
        else:
            self.model = load_model('model_goals/')
            self.model.save_weights('model_goals/model_weights.h5')

    def train_goals_ppb_model(self):
        if self.create_model == 'new':
            self.model = Sequential([layers.Input((int(self.entries), self.features)),
                    layers.LSTM(64, activation = 'relu'),
                    layers.Dense(32, activation = 'relu'),
                    layers.Dense(16, activation = 'relu'),
                    layers.Dense(7, activation = 'softmax')])
            cp = ModelCheckpoint('model_goals_ppb/', save_best_only = True)
            es = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)
            #self.model.load_weights('model_goals/model_weights.h5')
            self.model.compile(loss='categorical_crossentropy', 
                optimizer=Adagrad(learning_rate=0.001),
                metrics=['accuracy'])
            self.model.fit(self.X_train, self.y_train, validation_data=(self.X_val, self.y_val), epochs=15, batch_size = 32, callbacks = [cp, es])
            #print(self.model.summary())
        else:
            self.model = load_model('model_goals_ppb/')
            self.model.save_weights('model_goals_ppb/model_weights.h5')

    def train_winner_model(self):
        if self.create_model == 'new':
            self.model = Sequential([layers.Input((int(self.entries), self.features)),
                    layers.LSTM(64, activation = 'relu'),
                    layers.Dense(32, activation = 'relu'),
                    layers.Dense(16, activation = 'relu'),
                    layers.Dense(3, activation = 'softmax')])
            cp = ModelCheckpoint('model_winner/', save_best_only = True)
            es = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)
            self.model.load_weights('model_winner/model_weights.h5')
            self.model.compile(loss='categorical_crossentropy', 
                optimizer=Adagrad(learning_rate=0.001),
                metrics=['accuracy'])

            self.model.fit(self.X_train, self.y_train, validation_data=(self.X_val, self.y_val), epochs=15, batch_size = 32, callbacks = [cp, es])
            print(self.model.summary())
        else:
            self.model = load_model('model_winner/')
            self.model.save_weights('model_winner/model_weights.h5')

    def train_btts_model(self):
        if self.create_model == 'new':
            self.model = Sequential([layers.Input((int(self.entries), self.features)),
                    layers.LSTM(64, activation = 'sigmoid'),
                    layers.Dense(32, activation = 'relu'),
                    layers.Dense(16, activation = 'relu'),
                    layers.Dense(2, activation = 'softmax')])
            cp = ModelCheckpoint('model_btts/', save_best_only = True)
            es = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)
            #self.model.load_weights('model_btts/model_weights.h5')
            self.model.compile(loss='categorical_crossentropy', 
            #self.model.compile(loss=self.ranked_probability_score, 
                optimizer=Adagrad(learning_rate=0.001),
                metrics=['accuracy'])

            self.model.fit(self.X_train, self.y_train, validation_data=(self.X_val, self.y_val), epochs=15, batch_size = 32, callbacks = [cp, es])
            print(self.model.summary())
        else:
            self.model = load_model('model_btts/')
            self.model.save_weights('model_btts/model_weights.h5')

    def train_ou_model(self):
        if self.create_model == 'new':
            self.model = Sequential([layers.Input((int(self.entries), self.features)),
                    layers.LSTM(64, activation = 'sigmoid'),
                    layers.Dense(32, activation = 'relu'),
                    layers.Dense(16, activation = 'relu'),
                    layers.Dense(2, activation = 'softmax')])
            cp = ModelCheckpoint('model_ou/', save_best_only = True)
            es = EarlyStopping(monitor='val_loss', patience=2, restore_best_weights=True)
            self.model.compile(loss='categorical_crossentropy',  
                optimizer=Adagrad(learning_rate=0.001),
                metrics=['accuracy'])

            self.model.fit(self.X_train, self.y_train, validation_data=(self.X_val, self.y_val), epochs=15, batch_size = 32, callbacks = [cp, es])
            print(self.model.summary())
        else:
            self.model = load_model('model_ou/')
            self.model.save_weights('model_ou/model_weights.h5')

    def goals_total_test(self):
        test_predictions = self.model.predict(self.X_test).flatten().astype(int)
        accuracy = accuracy_score(test_predictions, self.y_test)
        test_predictions = np.clip(test_predictions, 0, 6)
        ou_predictions = 0
        for i in range(len(test_predictions)):
            if (self.y_test[i][0] < 2.5 and test_predictions[i] < 2.5) or (self.y_test[i][0] > 2.5 and test_predictions[i] > 2.5):
                ou_predictions += 1
        print("Liczba meczów: {}".format(len(self.X_test)))
        print("Accuracy:", accuracy)
        print("OU accuracy: ", ou_predictions / len(test_predictions))
        #for i in range(len(self.X_test)):
        #    generated_ou = "U" if test_predictions[i] < 2.5 else "O"
        #    print("{};{};{}".format(self.indexes_test[i], test_predictions[i], generated_ou))
        #graph_indexes = [x for x in range(1,51)]
        #plt.plot(graph_indexes, test_predictions[-50:])
        #plt.plot(graph_indexes, self.y_test[-50:])
        #plt.legend(['Predykcje', 'Obserwacje'])
        #plt.show()

    def goals_ppb_test(self):
        test_predictions = self.model.predict(self.X_test)
        np_array = np.array(self.y_test)
        test_max = np.argmax(np_array, axis=1)
        predict_max = np.argmax(test_predictions, axis = 1)
        ou_predictions = 0
        for i in range(len(test_predictions)):
            #print("Indeks meczu: {}".format(self.indexes_test[i]))
            #print("Zaobserwowana liczba bramek: {}".format(test_max[i]))
            #print("Przewidywana liczba bramek: {}".format(predict_max[i]))
            if (test_max[i] < 2.5 and predict_max[i] < 2.5) or (test_max[i] > 2.5 and predict_max[i] > 2.5):
                ou_predictions += 1
        print("Liczba meczów: {}".format(len(self.X_test)))
        print("Skuteczność: {}".format(np.sum(test_max  == predict_max ) / len(test_max)))
        print("OU skuteczność: {}".format(ou_predictions / len(test_predictions)))

    
    def test_winner_model(self):
        test_predictions = self.model.predict(self.X_test)
        np_array = np.array(self.y_test)
        test_max = np.argmax(np_array, axis=1)
        predict_max = np.argmax(test_predictions, axis = 1)
        print("Liczba meczów: {}".format(len(self.X_test)))
        print("Liczba poprawnych: {}".format(np.sum(test_max  == predict_max )))
        print("Skuteczność: {}".format(np.sum(test_max  == predict_max ) / len(test_max)))
        #for i in range(len(self.X_test)):
        #    percentages = np.round(test_predictions[i] * 100, 2)
        #    print("{};{:.2f};{:.2f};{:.2f}".format(self.indexes_test[i], percentages[0], percentages[1], percentages[2]))
        #    print("{};{};{}".format(self.indexes_test[i], predict_max[i], test_max[i]))

    def test_btts_model(self):
        test_predictions = self.model.predict(self.X_test)
        np_array = np.array(self.y_test)
        test_max = np.argmax(np_array, axis=1)
        predict_max = np.argmax(test_predictions, axis = 1)
        print("Liczba meczów: {}".format(len(self.X_test)))
        print("Liczba poprawnych: {}".format(np.sum(test_max  == predict_max )))
        print("Skuteczność: {}".format(np.sum(test_max  == predict_max ) / len(test_max)))
        #for i in range(len(self.X_test)):
        #    percentages = np.round(test_predictions[i] * 100, 2)
        #    print("{};{:.2f};{:.2f};".format(self.indexes_test[i], percentages[0], percentages[1]))
        #     print("{};{};{}".format(int(self.indexes_test[i]), 'TAK' if predict_max[i] == 0 else 'NIE', 'TAK' if test_max[i] == 0 else 'NIE'))
        #    print("{};{}".format(int(self.indexes_test[i]), 'TAK' if predict_max[i] == 0 else 'NIE'))

    def test_ou_model(self):
        test_predictions = self.model.predict(self.X_test)
        np_array = np.array(self.y_test)
        test_max = np.argmax(np_array, axis=1)
        predict_max = np.argmax(test_predictions, axis = 1)
        print("Liczba meczów: {}".format(len(self.X_test)))
        print("Liczba poprawnych: {}".format(np.sum(test_max  == predict_max )))
        print("Skuteczność: {}".format(np.sum(test_max  == predict_max ) / len(test_max)))
        #for i in range(len(self.X_test)):
        #    percentages = np.round(test_predictions[i] * 100, 2)
        #    print("{};{:.2f};{:.2f};".format(self.indexes_test[i], percentages[0], percentages[1]))
        #     print("{};{};{}".format(int(self.indexes_test[i]), 'TAK' if predict_max[i] == 0 else 'NIE', 'TAK' if test_max[i] == 0 else 'NIE'))
        #    print("{};{}".format(int(self.indexes_test[i]), 'TAK' if predict_max[i] == 0 else 'NIE'))

