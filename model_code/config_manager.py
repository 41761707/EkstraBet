import json
from datetime import datetime, timedelta
from typing import Self
class ConfigManager:
    """
    Klasa zarządzająca konfiguracją aplikacji realizująca wzorzec Singleton.

    Gwarantuje istnienie tylko jednej instancji w całym systemie, zapewniając globalny dostęp
    do ustawień konfiguracyjnych. Chodzi o to, ze nie chcemy mieć przypadkowo paru configów bo będzie lipa

    Przykład użycia:
        config = ConfigManager()
        config.load_from_args(args)
    """
    _instance = None  # Prywatna zmienna klasy przechowująca jedyną instancję

    def __new__(cls) -> Self:
        """
        Metoda tworzenia instancji realizująca wzorzec Singleton.
        
        Zapewnia, że klasa będzie miała tylko jedną instancję w całym cyklu życia aplikacji.
        Przy pierwszym wywołaniu tworzy nową instancję, przy kolejnych zwraca istniejącą.

        Returns:
            ConfigManager: Jedyna instancja klasy ConfigManager

        Przykład:
            manager1 = ConfigManager()
            manager2 = ConfigManager()
            manager1 is manager2  # Zwróci True
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Inicjalizuje domyślne wartości konfiguracyjne dla menedżera."""
        # Typ modelu: 'winner', 'btts', 'goals', 'exact', 'goals-6-classes' - określa rodzaj predykcji
        self.model_type = None

        # Tryb pracy: 'train' (trenowanie) lub 'predict' (predykcja)
        self.model_mode = None

        # Flaga określająca czy ładować wagi modelu: '0' - nie, '1' - tak
        self.load_weights = None

        # Unikalna nazwa modelu używana do zapisu/odczytu plików
        self.model_name = None

        # Nazwa modelu z którego mają być wczytane wagi (używane gdy load_weights == '1')
        self.model_load_name = None

        # Lista ID lig do analizy
        self.leagues = []

        # Lista ID lig dla których generujemy predykcje (używane tylko w trybie predict)
        self.leagues_upcoming = []

        # ID sportu (1 - piłka nożna, 2 - hokej, 3 - koszykówka, 4 - esport)
        self.sport_id = 1

        # Lista krajów do uwzględnienia (pusta - wszystkie kraje)
        self.country = []

        # Rozmiar okna czasowego używany do analizy sekwencji
        self.window_size = 5

        # Lista kolumn z cechami używanymi do trenowania/predykcji
        self.feature_columns = []

        # Typy ratingów używane w modelu: ['elo', 'gap', 'czech']
        self.rating_types = []

        # Lista aktywnych atrybutów meczu używanych w obliczeniach rankingu
        self.match_attributes = []

        # Konfiguracja ścieżek do modeli dla różnych typów ratingów
        self.rating_config = {}

        # Nazwy domyślnie aktywnych atrybutów meczu (wybrane z ALL_MATCH_ATTRIBUTES, GAP rating)
        self.active_match_attributes = []

        # Stałe
        self.MODEL_BASE_PATH = 'model_{}_dev/{}.h5'  # Szablon ścieżki do zapisu modelu
        self.INITIAL_ELO = 1500  # Początkowa wartość rankingu ELO
        self.SECOND_TIER_COEF = 0.8  # Współczynnik dla lig drugiej kategorii
        self.LEARNING_RATE = 0.00001  # Domyślna szybkość uczenia
        self.THRESHOLD_DATE = str(datetime.today())  # Data graniczna dla danych treningowych

    def load_from_args(self, args_dict) -> None:
        """
        Inicjalizuje konfigurację na podstawie słownika argumentów z wiersza poleceń.

        Args:
            args_dict (dict): Słownik argumentów z kluczami:
                - model_type: typ modelu ('winner', 'btts', 'goals', 'exact')
                - mode: tryb pracy ('train', 'predict', 'test')
                - load_weights: flaga ładowania wag (0 - nie, 1 - tak)
                - model_name: nazwa modelu (obowiązkowy)
                - model_load_name: nazwa modelu źródłowego (opcjonalny)
                - prediction_config: ścieżka do pliku z konfiguracją predykcji (opcjonalny)
        """
        # Argumenty obowiązkowe
        self.model_type = args_dict['model_type']
        self.model_mode = args_dict['mode']
        self.load_weights = args_dict['load_weights']
        self.model_name = args_dict['model_name']
        
        # Argumenty opcjonalne
        self.model_load_name = args_dict.get('model_load_name')
        self.prediction_config_path = args_dict.get('prediction_config')
        
        # Konfiguracja typów ratingów w zależności od typu modelu
        if self.model_type in ['winner', 'exact']:
            # Dla modeli winner i exact używamy wszystkich ratingów
            self.rating_types = ['elo', 'gap', 'czech']
        else:
            # Dla pozostałych modeli tylko gap i czech
            self.rating_types = ['gap', 'czech']
        
        # Domyślne atrybuty meczu jeśli rating 'gap' jest aktywny
        if 'gap' in self.rating_types:
            self.active_match_attributes = ['chances_home', 'chances_away']
        
        # Obsługa ładowania wag z istniejącego modelu
        if (self.model_mode == 'train' and self.load_weights == '1') or self.model_mode == 'predict':
            if not self.model_load_name:
                raise ValueError(f"Tryb {self.model_mode} z load_weights={self.load_weights} wymaga model_load_name")
            # Wczytanie pełnej konfiguracji z pliku modelu
            self._setup_configurations_from_model()
        else:
            # Standardowa inicjalizacja konfiguracji
            self._setup_configurations()
        
        # Logowanie załadowanej konfiguracji
        self._log_configuration()

    def _setup_configurations_from_model(self):
        """Wczytuje całą konfigurację modelu z pliku JSON i synchronizuje atrybuty klasy. """
        with open(f'model_{self.model_type}_dev/{self.model_load_name}_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.model_config = config
            # Nadpisz te zmienne zeby znowu nie wpisal danych ze wzorca
            config["model_name"] = self.model_name
            config["model_path"] = f'model_{self.model_type}_dev/{self.model_name}.h5'

            self.window_size = config.get("window_size")
            self.feature_columns = config.get("feature_columns", [])
            self.rating_types = []
            ratings = config.get("ratings", {})
            for rating_type in ["elo", "gap", "czech"]:
                if ratings.get(rating_type, {}).get("enabled"):
                    self.rating_types.append(rating_type)
            # Synchronizacja rating_config
            self.rating_config = {
                'winner': {
                    'rating_type': self.rating_types,
                    'model_path': f'model_winner_dev/{self.model_name}.h5'
                },
                'goals': {
                    'rating_type': self.rating_types,
                    'model_path': f'model_goals_dev/{self.model_name}.h5'
                },
                'goals-6-classes': {
                    'rating_type': self.rating_types,
                    'model_path': f'model_goals_6_classes_dev/{self.model_name}.h5'
                },
                'btts': {
                    'rating_type': self.rating_types,
                    'model_path': f'model_btts_dev/{self.model_name}.h5'
                },
                'exact': {
                    'rating_type': self.rating_types,
                    'model_path': f'model_exact_dev/{self.model_name}.h5'
                }
            }
            # Ustawienia atrybutów meczu (GAP RATING)
            self._setup_match_attributes()
        
        if self.prediction_config_path is not None:
            with open(self.prediction_config_path, 'r', encoding='utf-8') as f:
                training_config = json.load(f)
                self.leagues = training_config.get("leagues", [])
                self.leagues_upcoming = training_config.get("leagues_upcoming", [])
                self.country = training_config.get("country", [])
                self.sport_id = training_config.get("sport_id", 1)
                self.THRESHOLD_DATE = training_config.get("threshold_date", str(datetime.today()))
        else:
            # Optionally, set default values or log a warning
            self.leagues = []
            self.leagues_upcoming = []
            self.country = []
            self.sport_id = 1
            self.THRESHOLD_DATE = str(datetime.today())
    def _setup_configurations(self):
        """Funkcja odpowiedzialna ustawienia wszystkich konfiguracji modelu. """
        # Ustawienia ratingów
        self._setup_rating_columns()
        # Ustawienia cech, na podstawie których odbywa się trening
        self._setup_feature_columns()
        # Ustawienia atrybutów meczu (GAP RATING)
        self._setup_match_attributes()
        # Ustawienia ratingów (które są aktualnie wykorzystywane)
        self._setup_rating_config()
        # Ustawienia głównej konfiguracji modelu
        self._setup_model_config()

    def _setup_rating_columns(self):
        """Definicje kolumn dla różnych typów ratingów."""
        self.elo_columns = ['home_team_elo', 'away_team_elo']

        self.czech_columns = [
            'home_team_home_win_pct', 
            #'home_team_away_win_pct',
            'home_team_home_draw_pct', 
            #'home_team_away_draw_pct',
            'home_team_home_gs_avg', 
            #'home_team_away_gs_avg',
            'home_team_home_gc_avg', 
            #'home_team_away_gc_avg',
            'home_team_home_gs_std', 
            #'home_team_away_gs_std',
            'home_team_home_gc_std', 
            #'home_team_away_gc_std',
            #'away_team_home_win_pct', 
            'away_team_away_win_pct',
            #'away_team_home_draw_pct', 
            'away_team_away_draw_pct',
            #'away_team_home_gs_avg',
            'away_team_away_gs_avg',
            #'away_team_home_gc_avg',
            'away_team_away_gc_avg',
            #'away_team_home_gs_std', 
            'away_team_away_gs_std',
            #'away_team_home_gc_std', 
            'away_team_away_gc_std',
            #'home_team_win_pct_last_5',
            #'home_team_draw_pct_last_5',
            #'home_team_gs_avg_last_5',
            #'home_team_gc_avg_last_5',
            #'home_team_gs_std_last_5',
            #'home_team_gc_std_last_5',
            #'home_team_rest',
        ]
        
        self.gap_columns = [
            'home_home_att_power', 'home_home_def_power',
            'away_away_att_power', 'away_away_def_power',
            'home_goals_avg', 'away_goals_avg'
        ]

    def _setup_feature_columns(self):
        """Dynamiczne tworzenie kolumn features na podstawie wybranych rating_types."""
        self.feature_columns = []

        rating_columns_mapping = {
            'elo': self.elo_columns,
            'gap': self.gap_columns,
            'czech': self.czech_columns
        }

        for rating_type in self.rating_types:
            if rating_type in rating_columns_mapping:
                self.feature_columns.extend(rating_columns_mapping[rating_type])

    def _setup_match_attributes(self, active_attributes=None):
        """
        Konfiguruje atrybuty meczu na podstawie listy aktywnych atrybutów
        Args:
          active_attributes: Lista nazw atrybutów do aktywacji (None = użyj domyślnych)
        """
        # Definicja wszystkich możliwych atrybutów meczu
        all_match_attributes = {
            'chances_home': {
                'calculator': lambda match: int(match['home_team_ck']) + int(match['home_team_sc'])
            },
            'chances_away': {
                'calculator': lambda match: int(match['away_team_ck']) + int(match['away_team_sc'])
            },
            'goals_home': {
                'calculator': lambda match: int(match['home_team_goals'])
            },
            'goals_away': {
                'calculator': lambda match: int(match['away_team_goals'])
            },
            'btts': {
                'calculator': lambda match: 1 if match['home_team_goals'] > 0 and match['away_team_goals'] > 0 else 0
            },
            # MOŻNA ROZSZERZAĆ!
        }
        if active_attributes is None:
            active_attributes = self.active_match_attributes
        self.match_attributes = [
            {
                'name': attr_name,
                'calculator': all_match_attributes[attr_name]['calculator']
            }
            for attr_name in active_attributes
            if attr_name in all_match_attributes
        ]
        print("SELF.MATCH_ATTRIBUTES:", self.match_attributes)

    def _setup_rating_config(self):
        """Konfiguracja ścieżek modeli dla różnych typów ratingów"""
        self.rating_config = {
            'winner': {
                'rating_type': self.rating_types,
                'model_path': f'model_winner_dev/{self.model_name}.h5'
            },
            'goals': {
                'rating_type': self.rating_types,
                'model_path': f'model_goals_dev/{self.model_name}.h5'
            },
            'goals-6-classes': {
                'rating_type': self.rating_types,
                'model_path': f'model_goals_6_classes_dev/{self.model_name}.h5'
            },
            'btts': {
                'rating_type': self.rating_types,
                'model_path': f'model_btts_dev/{self.model_name}.h5'
            },
            'exact': {
                'rating_type': self.rating_types,
                'model_path': f'model_exact_dev/{self.model_name}.h5'
            }
        }

    def _setup_model_config(self):
        """
        Konfiguruje pełną specyfikację modelu deep learning do serializacji JSON.
        
        Tworzy strukturę konfiguracyjną zawierającą:
        - Parametry metryk i ścieżek modelu
        - Architekturę sieci neuronowej
        - Konfigurację procesu treningowego
        - Konfigurację ratingów i cech
        
        Generowana konfiguracja jest używana do:
        - Zapisania pełnej specyfikacji modelu
        - Rekonstrukcji modelu podczas ładowania
        - Śledzenia wersji i parametrów
        """
        
        # --------------------------------------------------------------------------
        # KONFIGURACJA WARSTW LSTM
        # --------------------------------------------------------------------------
        lstm_layers_config = {
            "units": [256, 128, 64],  # Liczba neuronów w kolejnych warstwach
            "activation": ["tanh", "tanh", "tanh"],  # Funkcje aktywacji
            "return_sequences": [True, True, False],  # Czy zwracać pełną sekwencję
            "dropout": [0.2, 0.2, 0.0],  # Współczynniki dropout
            "batch_normalization": [True, True, False]  # Normalizacja batch
        }
        
        # --------------------------------------------------------------------------
        # KONFIGURACJA WARSTW GĘSTYCH
        # --------------------------------------------------------------------------
        dense_layers_config = [
            {
                "units": 128,  # Liczba neuronów
                "activation": "relu",  # Funkcja aktywacji ReLU
                "regularization_l2": None,  # Brak regularyzacji L2
                "dropout": 0.2  # 20% dropout
            },
            {
                "units": 64,
                "activation": "relu",
                "regularization_l2": None
            },
            {
                "units": 16,
                "activation": "linear",  # Liniowa przed softmax
                "regularization_l2": None
            }
        ]
        
        # --------------------------------------------------------------------------
        # KONFIGURACJA WARSTWY WYJŚCIOWEJ
        # --------------------------------------------------------------------------
        output_units_map = {
            'winner': 3,  # 3 klasy wyjściowe (wygrał gospodarz/remis/gość)
            'goals': 7,  # 7 przedziałów bramkowych (0/1/2/3/4/5/6+)
            'goals-6-classes': 6,  # 6 klas (0/1/2/3/4/5+)
            'btts': 2  # 2 klasy (tak/nie dla obu strzelą)
        }
        output_units = output_units_map.get(self.model_type, 3)  # Domyślnie 3 klasy
        
        # --------------------------------------------------------------------------
        # BUDOWA PEŁNEJ KONFIGURACJI MODELU
        # --------------------------------------------------------------------------
        self.model_config = {
            # Sekcja metadanych modelu
            "model_name": self.model_name,  # Unikalna nazwa modelu
            "model_type": self.model_type,  # Typ modelu (winner/goals/btts/exact)
            "window_size": self.window_size,  # Rozmiar okna czasowego

            # Miejsce na metryki treningowe (inicjalizowane zerami)
            "train_accuracy": 0,
            "train_loss": 0,
            "val_accuracy": 0,
            "val_loss": 0,

            # Ścieżka do zapisu/odczytu modelu
            "model_path": self.MODEL_BASE_PATH.format(self.model_type, self.model_name),

            # Lista używanych cech
            "feature_columns": self.feature_columns,

            # Konfiguracja systemów ratingowych
            "ratings": self._get_ratings_config(self.INITIAL_ELO, self.SECOND_TIER_COEF),

            # Szczegółowa architektura modelu
            "model": {
                "type": "LSTM",

                # Architektura sieci
                "architecture": {
                    # Podwójny stos warstw LSTM (dla lepszego uczenia sekwencji)
                    "lstm_layers": [lstm_layers_config, lstm_layers_config.copy()],

                    # Warstwy gęste
                    "dense_layers": dense_layers_config,

                    # Warstwa wyjściowa
                    "output": {
                        "units": output_units,
                        "activation": "softmax"
                    }
                },

                # Konfiguracja kompilacji modelu
                "compilation": {
                    "optimizer": {
                        "type": "Adam",
                        "learning_rate": self.LEARNING_RATE
                    },
                    "loss": "categorical_crossentropy",  # Funkcja straty
                    "metrics": ["accuracy", "Precision", "Recall"]  # Metryki
                }
            },

            # Konfiguracja procesu treningowego
            "training_config": {
                "sport_id": 1,  # ID sportu
                "leagues": self.leagues,  # Lista lig do trenowania/rankingów
                "leagues_upcoming": self.leagues_upcoming,  # Lista lig do predykcji
                "country": self.country,  # Lista krajów
                "load_weights": self.load_weights,  # Czy wagi były ładowane
                "threshold_date": self.THRESHOLD_DATE  # Data graniczna danych
            }
        }

    def _get_ratings_config(self, initial_elo, second_tier_coef):
        """Konfiguracja ratingów dla modelu z optymalizacją outputu JSON
        Args:
            initial_elo (int): Początkowa wartość rankingu ELO
            second_tier_coef (float): Współczynnik dla lig drugiej kategorii
        Returns:
            ratings_config (dict): Słownik z konfiguracją ratingów
        """
        ratings_config = {}

        # Konfiguracja dla elo
        if 'elo' in self.rating_types:
            ratings_config["elo"] = {
                "enabled": True,
                "initial_rating": initial_elo,
                "second_tier_coef": second_tier_coef,
                "columns": self.elo_columns
            }
        else:
            ratings_config["elo"] = {"enabled": False}

        # Konfiguracja dla gap
        if 'gap' in self.rating_types:
            ratings_config['gap'] = {
                "enabled": True,
                "columns": self.gap_columns,
                "match_attributes": [
                    {"name": attr["name"], "calculator": attr["calculator"]}
                    for attr in self.match_attributes
                ]
            }
        else:
            ratings_config["gap"] = {"enabled": False}

        # Konfiguracja dla czech
        if 'czech' in self.rating_types:
            ratings_config["czech"] = {
                "enabled": True,
                "columns": self.czech_columns
            }
        else:
            ratings_config["czech"] = {"enabled": False}

        return ratings_config
    
    def _log_configuration(self) -> None:
        """
        Loguje załadowaną konfigurację do konsoli w stylu Ekstrabet.
        """
        print("=" * 60)
        print("KONFIGURACJA EKSTRABET")
        print("=" * 60)
        print(f"Typ modelu: {self.model_type}")
        print(f"Tryb pracy: {self.model_mode}")
        print(f"Nazwa modelu: {self.model_name}")
        
        if self.model_load_name:
            print(f"Model źródłowy: {self.model_load_name}")
        
        print(f"Ładowanie wag: {'TAK' if self.load_weights == 1 else 'NIE'}")
        print(f"Sport ID: {self.sport_id}")
        print(f"Ligi treningowe: {self.leagues if self.leagues else 'WSZYSTKIE'}")
        print(f"Ligi predykcji: {self.leagues_upcoming if self.leagues_upcoming else 'WSZYSTKIE'}")
        print(f"Data graniczna: {self.THRESHOLD_DATE}")
        print(f"Rozmiar okna: {self.window_size}")
        print(f"Typy ratingów: {self.rating_types}")
        
        if self.prediction_config_path:
            print(f"Konfiguracja predykcji: {self.prediction_config_path}")
        
        print("=" * 60)