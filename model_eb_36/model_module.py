from tensorflow.keras.layers import Input, LSTM, Dense, Concatenate, Dropout, LeakyReLU, BatchNormalization
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard
from tensorflow.keras.optimizers import Adagrad, Adam
from tensorflow.keras.metrics import Precision, Recall
from tensorflow.keras import backend as K
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime

class ModelModule:
    def __init__(self, train_data, val_data, features, model_type, model_name, window_size):
        self.train_data = train_data
        self.val_data = val_data
        # Parametry
        self.embedding_dim = 8
        self.features = features
        self.model_type = model_type
        self.window_size = window_size
        self.model = None
        self.current_date = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        #self.model_name = f"{self.model_type}_model_{self.current_date}"
        self.model_name = model_name

    def build_lstm_model_from_config(self, config):
        """
        Buduje model na podstawie konfiguracji JSON
        
        Args:
            config (dict): Konfiguracja z config_manager.py
        """
        # Utworzenie warstw wejściowych
        input_home_seq = Input(shape=(self.window_size, self.features), name='home_input')
        input_away_seq = Input(shape=(self.window_size, self.features), name='away_input')
        
        # Budowanie warstw LSTM
        lstm_config = config.model_config["model"]["architecture"]["lstm_layers"]
        
        # Przetwarzanie sekwencji home
        lstm_home = input_home_seq
        for i, layer in enumerate(lstm_config[0]["units"]):
            lstm_home = LSTM(
                units=layer,
                activation=lstm_config[0]["activation"][i],
                return_sequences=lstm_config[0]["return_sequences"][i]
            )(lstm_home)
            
            # Dodaj dropout jeśli jest skonfigurowany
            if "dropout" in lstm_config[0] and lstm_config[0]["dropout"][i]:
                lstm_home = Dropout(lstm_config[0]["dropout"][i])(lstm_home)

            if "batch_normalization" in lstm_config[0] and lstm_config[0]["batch_normalization"][i]:
                lstm_home = BatchNormalization()(lstm_home)
        
        # Przetwarzanie sekwencji away
        lstm_away = input_away_seq
        for i, layer in enumerate(lstm_config[1]["units"]):
            lstm_away = LSTM(
                units=layer,
                activation=lstm_config[1]["activation"][i],
                return_sequences=lstm_config[1]["return_sequences"][i]
            )(lstm_away)
            
            # Dodaj dropout jeśli jest skonfigurowany
            if "dropout" in lstm_config[1] and lstm_config[1]["dropout"][i]:
                lstm_away = Dropout(lstm_config[1]["dropout"][i])(lstm_away)

            if "batch_normalization" in lstm_config[1] and lstm_config[1]["batch_normalization"][i]:
                lstm_away = BatchNormalization()(lstm_away)
        # Połączenie sekwencji
        combined = Concatenate()([lstm_home, lstm_away])
        
        # Budowanie warstw gęstych
        dense_config = config.model_config["model"]["architecture"]["dense_layers"]
        x = combined
        for layer in dense_config:          
            # Dodaj regularyzację jeśli jest skonfigurowana
            if "regularization_l2" in layer and layer["regularization_l2"]:
                x = Dense(
                    units=layer["units"],
                    activation=layer["activation"],
                    kernel_regularizer=l2(layer["regularization_l2"])
                )(x)
            else:
                x = Dense(
                    units=layer["units"],
                    activation=layer["activation"]
                    )(x)
            
            # Dodaj BatchNormalization jeśli jest skonfigurowany
            if "batch_normalization" in layer and layer["batch_normalization"]:
                x = BatchNormalization()(x)
                
            # Dodaj Dropout jeśli jest skonfigurowany
            if "dropout" in layer and layer["dropout"]:
                x = Dropout(layer["dropout"])(x)
        
        # Warstwa wyjściowa
        output_config = config.model_config["model"]["architecture"]["output"]
        output = Dense(
            units=output_config["units"],
            activation=output_config["activation"]
        )(x)
        
        # Tworzenie i kompilacja modelu
        self.model = Model(inputs=[input_home_seq, input_away_seq], outputs=output)
        
        # Konfiguracja optymalizatora
        optimizer_config = config.model_config["model"]["compilation"]["optimizer"]
        if optimizer_config["type"] == "Adam":
            optimizer = Adam(learning_rate=optimizer_config["learning_rate"])
        elif optimizer_config["type"] == "Adagrad":
            optimizer = Adagrad(learning_rate=optimizer_config["learning_rate"])
        
        # Kompilacja modelu
        self.model.compile(
            loss=config.model_config["model"]["compilation"]["loss"],
            optimizer=optimizer,
            metrics=config.model_config["model"]["compilation"]["metrics"]
        )

    #UWAGA: NA TEN MOMENT JEST SPECJALNIE TAK BRZYDKO 
    #ŻE KAŻDY MODEL MA OSOBNĄ FUNKCJĘ I 90% KODU SIĘ POWTARZA
    #BO NA ŚLEPO TESTUJĘ CO BĘDZIE DOBRZE
    #GDY JUŻ ODPOWIEDNIE ARCHITEKTURY ZOSTANĄ USTAWIONE POMYŚLIMY NAD LEPSZYM OKODZENIEM
    def create_winner_model(self):
        # Wejścia
        input_home_seq = Input(shape=(self.window_size, self.features), name='home_input')
        input_away_seq = Input(shape=(self.window_size, self.features), name='away_input')

        # Ulepszone LSTM z Dropout i BatchNorm
        lstm_home = LSTM(256, activation='tanh', return_sequences=True)(input_home_seq)
        lstm_home = BatchNormalization()(lstm_home)
        lstm_home = Dropout(0.2)(lstm_home)
        lstm_home = LSTM(128, return_sequences=True)(lstm_home)
        lstm_home = LSTM(64)(lstm_home)

        lstm_away = LSTM(256, activation='tanh', return_sequences=True)(input_away_seq)
        lstm_away = BatchNormalization()(lstm_away)
        lstm_away = Dropout(0.2)(lstm_away)
        lstm_away = LSTM(128, return_sequences=True)(lstm_away)
        lstm_away = LSTM(64)(lstm_away)

        # Połączenie + warstwy Dense
        combined = Concatenate()([lstm_home, lstm_away])
        dense = Dense(128, activation='relu')(combined)
        dense = Dropout(0.2)(dense)
        dense = Dense(64, activation='relu')(dense)
        output = Dense(3, activation='softmax')(dense)

        # Kompilacja z Adam i LR scheduler
        self.model = Model(inputs=[input_home_seq, input_away_seq], outputs=output)
        self.model.compile(
            loss='categorical_crossentropy',
            optimizer=Adam(learning_rate=0.001),
            metrics=['accuracy', Precision(), Recall()]
        )

    def create_goals_model(self):
        # Wejścia
        input_home_seq = Input(shape=(self.window_size, self.features), name='home_input')
        input_away_seq = Input(shape=(self.window_size, self.features), name='away_input')

        # Ulepszone warstwy LSTM dla każdej sekwencji
        lstm_home = LSTM(128, activation='tanh', return_sequences=True)(input_home_seq)
        lstm_home = LSTM(64)(lstm_home)
        
        lstm_away = LSTM(128, activation='tanh', return_sequences=True)(input_away_seq)
        lstm_away = LSTM(64)(lstm_away)
        # Połączenie sekwencji
        combined = Concatenate()([lstm_home, lstm_away])
        # Rozszerzone warstwy gęste z regularyzacją
        dense1 = Dense(128, kernel_regularizer=l2(0.01))(combined)
        dense1 = LeakyReLU(alpha=0.01)(dense1)  # alpha=0.01 to typowa wartość dla LeakyReLU
        dense1 = BatchNormalization()(dense1)

        dense2 = Dense(64, kernel_regularizer=l2(0.01))(dense1)
        dense2 = LeakyReLU(alpha=0.01)(dense2)
        dense2 = BatchNormalization()(dense2)

        dense3 = Dense(32, kernel_regularizer=l2(0.01))(dense2)
        dense3 = LeakyReLU(alpha=0.01)(dense3)
        dense3 = BatchNormalization()(dense3)

        # Warstwa wyjściowa (softmax dla klasyfikacji wieloklasowej)
        output = Dense(7, activation='softmax')(dense3)

        # Kompilacja modelu z dostosowanymi parametrami
        self.model = Model(inputs=[input_home_seq, input_away_seq], outputs=output)
        self.model.compile(
            loss='categorical_crossentropy',
            optimizer=Adagrad(learning_rate=0.0001),
            metrics=['accuracy']
        )

    def create_btts_model(self):
        # Wejścia
        input_home_seq = Input(shape=(self.window_size, self.features), name='home_input')
        input_away_seq = Input(shape=(self.window_size, self.features), name='away_input')

        # Warstwy LSTM
        lstm_home = LSTM(64, activation='sigmoid')(input_home_seq)
        
        lstm_away = LSTM(64, activation='sigmoid')(input_away_seq)
        
        # Połączenie sekwencji
        combined = Concatenate()([lstm_home, lstm_away])
        
        # Warstwy gęste
        dense1 = Dense(32, activation='tanh')(combined)
        dense2 = Dense(16, activation='tanh')(dense1)
        
        # Warstwa wyjściowa - binarna klasyfikacja
        output = Dense(2, activation='softmax')(dense2)

        # Kompilacja modelu
        self.model = Model(inputs=[input_home_seq, input_away_seq], outputs=output)
        self.model.compile(
            loss='categorical_crossentropy',
            optimizer=Adam(learning_rate=1e-06),
            metrics=['accuracy', Precision(), Recall()]
        )

    def create_exact_model(self):
        # Wejścia
        input_home_seq = Input(shape=(self.window_size, self.features), name='home_input')
        input_away_seq = Input(shape=(self.window_size, self.features), name='away_input')

        # Ulepszone warstwy LSTM dla każdej sekwencji
        lstm_home = LSTM(512, activation='tanh', return_sequences=True)(input_home_seq)
        lstm_home = LSTM(256)(lstm_home)
        
        lstm_away = LSTM(512, activation='tanh', return_sequences=True)(input_away_seq)
        lstm_away = LSTM(256)(lstm_away)
        # Połączenie sekwencji
        combined = Concatenate()([lstm_home, lstm_away])
        # Rozszerzone warstwy gęste z regularyzacją
        dense1 = Dense(1024, activation='relu', kernel_regularizer=l2(0.01))(combined)
        dense2 = Dense(512, activation='relu', kernel_regularizer=l2(0.01))(dense1)
        dense3 = Dense(256, activation='relu', kernel_regularizer=l2(0.01))(dense2)
        output = Dense(100, activation='softmax')(dense3)

        # Kompilacja modelu z dostosowanymi parametrami
        self.model = Model(inputs=[input_home_seq, input_away_seq], outputs=output)
        self.model.compile(
            loss='categorical_crossentropy',
            optimizer=Adagrad(learning_rate=0.0001),
            metrics=['accuracy', Precision(), Recall()]
        )

    def train_model(self):
        (X_home_train, X_away_train, y_train) = self.train_data
        (X_home_val, X_away_val, y_val) = self.val_data
        
        # Ulepszone callbacks
        callbacks = [
            EarlyStopping(
                monitor='accuracy',  
                patience=10,         # Zwiększona cierpliwość
                restore_best_weights=True,
                mode='min'
            ),
            ModelCheckpoint(
                f'model_{self.model_type}_dev/{self.model_name}.h5',
                monitor='accuracy',
                save_best_only=True,
                mode='min'
            ),
            TensorBoard(log_dir='./logs')
        ]
        
        history = self.model.fit(
            x=[X_home_train, X_away_train],
            y=y_train,
            batch_size=32,          # Zwiększony batch size
            epochs=100,             
            validation_data=([X_home_val, X_away_val], y_val),
            callbacks=callbacks,
            #class_weight = {0: 1.5, 1: 1, 2: 1.2},
            shuffle=True
        )
        # Ewaluacja
        evaluation_results = self.model.evaluate(
            [X_home_val, X_away_val],
            y_val
        )
        
        # Get metrics names
        metric_names = self.model.metrics_names
        
        # Print all available metrics
        for name, value in zip(metric_names, evaluation_results):
            if name == 'accuracy':
                print(f'Validation accuracy: {value*100:.2f}%')
            else:
                print(f'Validation {name}: {value:.4f}')

        #Confusion matrix
        #self.confusion_matrix(X_home_val, X_away_val, y_val)
        if self.model_type == 'goals':
            self.confusion_matrix_over_under(X_home_val, X_away_val, y_val)
        #self.print_sample_predictions(X_home_val, X_away_val, y_val)
        # Zapisz ostateczny model
        self.model.save(f'model_dev/{self.model_name}.h5')
        return history, evaluation_results
    
    def confusion_matrix(self, X_home_val, X_away_val, y_val):
        # Uzyskanie przewidywanych wartości (prawdopodobieństwa)
        y_pred_probs = self.model.predict([X_home_val, X_away_val])

        # Konwersja prawdopodobieństw na klasy (wybieramy indeks z najwyższą wartością)
        y_pred= np.argmax(y_pred_probs, axis=1)

        # Konwersja y_val do postaci klasy (jeśli jest one-hot encoded)
        y_true = np.argmax(y_val, axis=1)  # Jeśli y_val jest w formie one-hot

        #for i in range(len(y_pred)):
        #    print(f"MECZ {i}: Y_PRED: {y_pred[i]}, Y_TRUE: {y_true[i]}")
        # Obliczenie confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        print(classification_report(y_true, y_pred))

        # Wizualizacja macierzy błędów
        plt.figure(figsize=(6,5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=[0,1,2], yticklabels=[0,1,2])

        plt.xlabel("Przewidywane")
        plt.ylabel("Prawdziwe")
        plt.title("Confusion Matrix")
        plt.show()

    def confusion_matrix_over_under(self, X_home_val, X_away_val, y_val):
        # Uzyskanie przewidywanych wartości (prawdopodobieństwa)
        y_pred_probs = self.model.predict([X_home_val, X_away_val])

        # Konwersja prawdopodobieństw na klasy (wybieramy indeks z najwyższą wartością)
        y_pred_tmp = np.argmax(y_pred_probs, axis=1) 
        y_pred = np.where(y_pred_tmp < 3, 0, 1)

        # Konwersja y_val do postaci klasy (jeśli jest one-hot encoded)
        y_true_tmp = np.argmax(y_val, axis=1)  # Jeśli y_val jest w formie one-hot
        y_true = np.where(y_true_tmp < 3, 0, 1)

        # Obliczenie confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        print(classification_report(y_true, y_pred))

        # Wizualizacja macierzy błędów
        plt.figure(figsize=(6,5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=[0,1], yticklabels=[0,1])

        plt.xlabel("Przewidywane")
        plt.ylabel("Prawdziwe")
        plt.title("Confusion Matrix")
        plt.show()
    
    def load_predict_model(self, path):
        self.model = load_model(path)
    
    def predict(self, inputs): 
        return self.model.predict(inputs)
    
    def print_sample_predictions(self, X_home_val, X_away_val, y_val, num_samples=10000):
        """
        Prints detailed comparison of predictions vs actual values for a few samples
        """
        # Get predictions
        predictions = self.model.predict([X_home_val, X_away_val])
        
        # Convert to class labels
        y_pred = np.argmax(predictions, axis=1)
        y_true = np.argmax(y_val, axis=1)
        
        print("\n=== Sample Predictions ===")
        for i in range(min(num_samples, len(y_true))):
            prediction = y_pred[i]
            actual = y_true[i]
            
            # Convert numeric labels to readable format
            if self.model_type == 'winner':
                pred_label = ['Draw', 'Home Win', 'Away Win'][prediction]
                true_label = ['Draw', 'Home Win', 'Away Win'][actual]
            elif self.model_type == 'btts':
                pred_label = ['No BTTS', 'BTTS'][prediction]
                true_label = ['No BTTS', 'BTTS'][actual]
            else:  # for goals and exact
                pred_label = str(prediction)
                true_label = str(actual)
            
            result = "WIN" if prediction == actual else "LOSE"
            print(f"\nPrediction #{i+1}:")
            print(f"Expected: {true_label}")
            print(f"Predicted: {pred_label}")
            print(f"Result: {result}")
