from typing import Any
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
    def __init__(self, train_data, val_data, features, model_type, model_name, model_load_name, window_size, training_info=None, model_config=None) -> None:
        """ Funkcja inicjalizująca klasę ModelModule
        Args: 
            train_data (tuple): Dane treningowe w formacie (X_home, X_away, y)
            val_data (tuple): Dane walidacyjne w formacie (X_home, X_away, y)
            features (int): Liczba cech wejściowych
            model_type (str): Typ modelu (np. 'goals', 'winner', itp.)
            model_name (str): Nazwa modelu do zapisu
            model_load_name (str): Nazwa modelu do wczytania
            window_size (int): Rozmiar okna czasowego dla sekwencji wejściowych
            training_info (Any, optional): Dodatkowe informacje o treningu. Domyślnie None.
            model_config (dict, optional): Konfiguracja modelu z config_manager.py. Domyślnie None.
        """
        self.train_data = train_data
        self.val_data = val_data
        self.training_info = training_info
        self.model_config = model_config
        self.embedding_dim = 8 #TODO: Magic number
        self.features = features
        self.model_type = model_type
        self.model_load_name = model_load_name
        self.window_size = window_size
        self.model = None
        self.current_date = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
        self.model_name = model_name

    def build_model_from_config(self, config) -> None:
        """
        Buduje model na podstawie konfiguracji JSON
        Args:
            config (dict): Konfiguracja z config_manager.py
        """
        # TODO rozszerzyć może o inne modele niż LSTM
        if config.model_config["architecture_config"]["model"]["type"] == "LSTM":
            self.build_lstm_model(config)

    def build_lstm_model(self, config):
        """ Funkcja tworząca model korzystający z architektury LSTM
        Args: config: konfiguracja struktury modelu
        """
        # Utworzenie warstw wejściowych
        input_home_seq = Input(
            shape=(self.window_size, self.features), name='home_input')
        input_away_seq = Input(
            shape=(self.window_size, self.features), name='away_input')

        # Budowanie warstw LSTM
        lstm_config = config.model_config["architecture_config"]["lstm"]["layers"]

        # Przetwarzanie sekwencji home
        lstm_home = input_home_seq
        for i, layer in enumerate(lstm_config[0]["units"]):
            lstm_home = LSTM(
                units=layer,
                activation=lstm_config[0]["activation"][i],
                return_sequences=lstm_config[0]["return_sequences"][i]
            )(lstm_home)
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
            if "dropout" in lstm_config[1] and lstm_config[1]["dropout"][i]:
                lstm_away = Dropout(lstm_config[1]["dropout"][i])(lstm_away)
            if "batch_normalization" in lstm_config[1] and lstm_config[1]["batch_normalization"][i]:
                lstm_away = BatchNormalization()(lstm_away)
        combined = Concatenate()([lstm_home, lstm_away]) # Połączenie sekwencji

        # Budowanie warstw gęstych
        dense_config = config.model_config["architecture_config"]["dense_layers"]
        x = combined
        for layer in dense_config:
            if "regularization_l2" in layer and layer["regularization_l2"]:
                x = Dense(
                    units=layer["units"],
                    activation=layer["activation"],
                    kernel_regularizer=l2(layer["regularization_l2"]))(x)
            else:
                x = Dense(
                    units=layer["units"],
                    activation=layer["activation"])(x)
            if "batch_normalization" in layer and layer["batch_normalization"]:
                x = BatchNormalization()(x)
            if "dropout" in layer and layer["dropout"]:
                x = Dropout(layer["dropout"])(x)

        # Warstwa wyjściowa
        output_config = config.model_config["architecture_config"]["output"]
        output = Dense(
            units=output_config["units"],
            activation=output_config["activation"])(x)
        
        self.model = Model(
            inputs=[input_home_seq, input_away_seq], outputs=output)
        optimizer_config = config.model_config["architecture_config"]["model"]["compilation"]["optimizer"]
        if optimizer_config["type"] == "Adam":
            optimizer = Adam(learning_rate=optimizer_config["learning_rate"])
        elif optimizer_config["type"] == "Adagrad":
            optimizer = Adagrad(
                learning_rate=optimizer_config["learning_rate"])
        print(config.model_config["architecture_config"]["model"])

        self.model.compile(
            loss=config.model_config["architecture_config"]["model"]["compilation"]["loss"],
            optimizer=optimizer,
            metrics=config.model_config["architecture_config"]["model"]["compilation"]["metrics"])

    def train_model(self) -> tuple:
        """ Funkcja odpowiadająća za trening modelu 
        Returns:
            tuple: Historia treningu oraz wyniki ewaluacji (history, evaluation_results)
            """
        (X_home_train, X_away_train, y_train) = self.train_data
        (X_home_val, X_away_val, y_val) = self.val_data

        callbacks = [
            EarlyStopping(
                monitor='accuracy',
                patience=10,
                restore_best_weights=True,
                mode='min'),
            ModelCheckpoint(
                f'model_dev/{self.model_type}/{self.model_name}.h5',
                monitor='accuracy',
                save_best_only=True,
                mode='min'),
            TensorBoard(log_dir='./logs')]
        history = self.model.fit(
            x=[X_home_train, X_away_train],
            y=y_train,
            batch_size=32, #TODO: Magic number
            epochs=100, #TODO: Magic number
            validation_data=([X_home_val, X_away_val], y_val),
            callbacks=callbacks,
            class_weight=self.model_config.get("compilation", {}).get("class_weights", None),
            shuffle=True)
        evaluation_results = self.model.evaluate(
            [X_home_val, X_away_val],
            y_val
        )
        metric_names = self.model.metrics_names
        for name, value in zip(metric_names, evaluation_results):
            if name == 'accuracy':
                print(f'Validation accuracy: {value*100:.2f}%')
            else:
                print(f'Validation {name}: {value:.4f}')
        self.confusion_matrix(X_home_val, X_away_val, y_val)
        if self.model_type == 'goals':
            self.confusion_matrix_over_under(X_home_val, X_away_val, y_val)
        self.print_detailed_predictions(X_home_val, X_away_val, y_val)
        return history, evaluation_results

    def confusion_matrix(self, X_home_val, X_away_val, y_val):
        """ Funkcja tworząca i wyświetlająca macierz błędów
        Args:
            X_home_val: Dane wejściowe dla drużyn gospodarzy
            X_away_val: Dane wejściowe dla drużyn gości
            y_val: Prawdziwe etykiety
        """
        y_pred_probs = self.model.predict([X_home_val, X_away_val])
        y_pred = np.argmax(y_pred_probs, axis=1)
        y_true = np.argmax(y_val, axis=1)
        cm = confusion_matrix(y_true, y_pred)
        print(classification_report(y_true, y_pred))
        labels = []
        for i in range(len(self.model_config['output_config']['label_mapping'])):
            labels.append(self.model_config['output_config']['label_mapping'][str(i)])
        xticklabels, yticklabels = labels, labels
        # Wizualizacja macierzy błędów
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=xticklabels, yticklabels=yticklabels)
        plt.xlabel("Przewidywane")
        plt.ylabel("Prawdziwe")
        plt.title("Confusion Matrix")
        plt.show()

    def confusion_matrix_over_under(self, X_home_val, X_away_val, y_val):
        """ Funkcja tworząca i wyświetlająca macierz błędów dla klasyfikacji Under/Over 2.5 bramki
        Args:
            X_home_val: Dane wejściowe dla drużyn gospodarzy
            X_away_val: Dane wejściowe dla drużyn gości
            y_val: Prawdziwe etykiety
        """
        y_pred_probs = self.model.predict([X_home_val, X_away_val])
        y_pred_tmp = np.argmax(y_pred_probs, axis=1)
        y_pred = np.where(y_pred_tmp < 3, 0, 1)
        y_true_tmp = np.argmax(y_val, axis=1)
        y_true = np.where(y_true_tmp < 3, 0, 1)

        cm = confusion_matrix(y_true, y_pred)
        print(classification_report(y_true, y_pred))
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                    xticklabels=[0, 1], yticklabels=[0, 1])
        plt.xlabel("Przewidywane")
        plt.ylabel("Prawdziwe")
        plt.title("Confusion Matrix - Klasyfikacja: Under/Over 2.5 (na podstawie argmax)")
        plt.show()

        sum_012 = np.sum(y_pred_probs[:, :3], axis=1)
        sum_3plus = np.sum(y_pred_probs[:, 3:], axis=1)
        y_pred_sum = np.where(sum_012 > sum_3plus, 0, 1)
        y_true_sum = np.where(y_true_tmp < 3, 0, 1)
        cm_sum = confusion_matrix(y_true_sum, y_pred_sum)
        print("\n=== Confusion matrix (sum of probabilities for 0-2 vs 3+ goals) ===")
        print(classification_report(y_true_sum, y_pred_sum))
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm_sum, annot=True, fmt="d", cmap="Greens",
                    xticklabels=["0-2 bramki", "3+ bramki"], yticklabels=["0-2 bramki", "3+ bramki"])
        plt.xlabel("Przewidywane")
        plt.ylabel("Prawdziwe")
        plt.title("Confusion Matrix - Klasyfikacja: Under/Over 2.5 (na podstawie sumy prawdopodobieństw)")
        plt.show()

    def load_predict_model(self, config):
        """ Funkcja ładująca wytrenowany model do predykcji
        Args:
            config (dict): Konfiguracja z config_manager.py
        """
        print(f'model_dev/{config.model_config["model_type"]}/{self.model_load_name}.h5')
        self.model = load_model(
            f'model_dev/{config.model_config["model_type"]}/{self.model_load_name}.h5', compile=False)
        self.model.compile(
            loss=config.model_config["architecture_config"]["model"]["compilation"]["loss"],
            optimizer=config.model_config["architecture_config"]["model"]["compilation"]["optimizer"]["type"],
            metrics=config.model_config["architecture_config"]["model"]["compilation"]["metrics"])

    def predict(self, inputs) -> Any:
        return self.model.predict(inputs)

    def print_sample_predictions(self, X_home_val, X_away_val, y_val, num_samples=10000):
        """
        Wyświetla przykładowe predykcje modelu
        Args:
            X_home_val: Dane wejściowe dla drużyn gospodarzy
            X_away_val: Dane wejściowe dla drużyn gości
            y_val: Prawdziwe etykiety
            num_samples (int): Liczba próbek do wyświetlenia
        """
        predictions = self.model.predict([X_home_val, X_away_val])
        y_pred = np.argmax(predictions, axis=1)
        y_true = np.argmax(y_val, axis=1)
        print("\n=== Przykładowe predykcje ===")
        for i in range(min(num_samples, len(y_true))):
            prediction = y_pred[i]
            actual = y_true[i]

            if self.model_config and 'output_config' in self.model_config and 'label_mapping' in self.model_config['output_config']:
                pred_label = self.model_config['output_config']['label_mapping'][str(prediction)]
                true_label = self.model_config['output_config']['label_mapping'][str(actual)]
            result = "WIN" if prediction == actual else "LOSE"
            print(f"\nPrediction #{i+1}:")
            print(f"Expected: {true_label}")
            print(f"Predicted: {pred_label}")
            print(f"Result: {result}")

    def print_detailed_predictions(self, X_home_val, X_away_val, y_val):
        """
        Wyświetla szczegółowe informacje predykcyjne w formacie CSV
        
        Args:
            X_home_val: Dane wejściowe dla drużyn gospodarzy
            X_away_val: Dane wejściowe dla drużyn gości
            y_val: Prawdziwe etykiety
        """
        print("\n" + "="*80)
        print("SZCZEGÓŁOWE INFORMACJE PREDYKCYJNE - FORMAT CSV")
        print("="*80)

        y_pred_probs = self.model.predict([X_home_val, X_away_val])
        match_ids = []
        if self.training_info and len(self.training_info) > 1:
            # training_info[1] zawiera informacje o próbkach walidacyjnych
            val_info = self.training_info[1]
            match_ids = [info[0] if isinstance(info, list) and len(info) > 0 else f'Mecz_{i+1}' for i, info in enumerate(val_info)]
        else:
            match_ids = [f'Mecz_{i+1}' for i in range(len(y_pred_probs))]
        
        num_classes = y_pred_probs.shape[1]
        prob_headers = [f"prawdopodobieństwo_{i+1}" for i in range(num_classes)]
        header = "id_meczu;" + ";".join(prob_headers)
        print(header)
        for i in range(len(y_pred_probs)):
            match_id = match_ids[i] if i < len(match_ids) else f'Mecz_{i+1}'
            probabilities = [f"{prob:.6f}" for prob in y_pred_probs[i]]
            row = f"{match_id};" + ";".join(probabilities)
            print(row)
        print("="*80)
