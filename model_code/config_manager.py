import json
class ConfigManager:
    """
    Klasa zarządzająca konfiguracją aplikacji realizująca wzorzec Singleton.

    Gwarantuje istnienie tylko jednej instancji w całym systemie, zapewniając globalny dostęp
    do ustawień konfiguracyjnych. Chodzi o to, ze nie chcemy mieć przypadkowo paru configów bo będzie lipa

    Przykład użycia:
        config = ConfigManager()
        config.load_from_args(args)
    """
    _instance = None  #: Prywatna zmienna klasy przechowująca jedyną instancję
    
    def __new__(cls):
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
    
    def _initialize(self):
        """Inicjalizuje domyślne wartości konfiguracyjne dla menedżera."""
        # Typ modelu: 'winner', 'btts', 'goals' lub 'exact' - określa rodzaj predykcji
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
        self.leagues = [34, 35, 15, 30, 17, 32, 25]
        
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
        
    def load_from_args(self, args):
        """
        Inicjalizuje konfigurację na podstawie argumentów wiersza poleceń.

        Args:
            args (list): Lista argumentów przekazanych z wiersza poleceń w kolejności:
                [0] - nazwa skryptu
                [1] - typ modelu
                [2] - tryb pracy
                [3] - flaga ładowania wag (0 - nie ładuj, 1 - załaduj)
                [4] - nazwa modelu (jeżeli tryb pracy to predict to tutaj nazwa modelu, z którego wczytujemy wagi do predykcji) (lekka niespójność)
                [5] - (opcjonalnie) nazwa modelu źródłowego do ładowania wag ([3] musi byc na 1)
        """
        # Typ modelu: 'winner', 'btts', 'goals' lub 'exact'
        self.model_type = args[1]
        
        # Tryb pracy: 'train' (trenowanie) / 'predict' (predykcja) / 'test' (testowanie)
        self.model_mode = args[2]
        
        # Flaga ładowania wag: '0' - nie, '1' - tak
        self.load_weights = args[3]
        
        # Nazwa modelu (dla nowego modelu) lub modelu do predykcji
        self.model_name = args[4]
        
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
            # Nazwa modelu źródłowego do ładowania wag (argument opcjonalny)
            self.model_load_name = args[5]
            # Wczytanie pełnej konfiguracji z pliku modelu
            self._setup_configurations_from_model()
        else:
            # Standardowa inicjalizacja konfiguracji
            self._setup_configurations()

    def _setup_configurations_from_model(self):
        """
        Wczytuje całą konfigurację modelu z pliku JSON i synchronizuje atrybuty klasy.
        """
        with open(f'model_{self.model_type}_dev/{self.model_load_name}_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            self.model_config = config
            self.model_name = config.get("model_name")
            self.model_type = config.get("model_type")
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
                'btts': {
                    'rating_type': self.rating_types,
                    'model_path': f'model_btts_dev/{self.model_name}.h5'
                },
                'exact': {
                    'rating_type': self.rating_types,
                    'model_path': f'model_exact_dev/{self.model_name}.h5'
                }
            }
            #Ustawienia atrybutów meczu (GAP RATING)
            self._setup_match_attributes()

    def _setup_configurations(self):
        ''' Funkcja odpowiedzialna ustawienia wszystkich konfiguracji modelu '''
        #Ustawienia ratingów
        self._setup_rating_columns()
        #Ustawienia cech, na podstawie których odbywa się trening
        self._setup_feature_columns()
        #Ustawienia atrybutów meczu (GAP RATING)
        self._setup_match_attributes()
        #Ustawienia ratingów (które są aktualnie wykorzystywane)
        self._setup_rating_config()
        #Ustawienia głównej konfiguracji modelu!
        self._setup_model_config()

    def _setup_rating_columns(self):
        """Definicje kolumn dla różnych typów ratingów"""
        self.elo_columns = ['home_team_elo', 'away_team_elo']
        
        self.czech_columns = [
            'home_team_home_win_pct', 'home_team_away_win_pct',
            'home_team_home_draw_pct', 'home_team_away_draw_pct',
            'home_team_home_gs_avg', 'home_team_away_gs_avg',
            'home_team_home_gc_avg', 'home_team_away_gc_avg',
            'home_team_home_gs_std', 'home_team_away_gs_std',
            'home_team_home_gc_std', 'home_team_away_gc_std',
            'away_team_home_win_pct', 'away_team_away_win_pct',
            'away_team_home_draw_pct', 'away_team_away_draw_pct',
            'away_team_home_gs_avg', 'away_team_away_gs_avg',
            'away_team_home_gc_avg', 'away_team_away_gc_avg',
            'away_team_home_gs_std', 'away_team_away_gs_std',
            'away_team_home_gc_std', 'away_team_away_gc_std',
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
        """Dynamiczne tworzenie kolumn features na podstawie wybranych rating_types"""
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
        ALL_MATCH_ATTRIBUTES = {
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
                'calculator': ALL_MATCH_ATTRIBUTES[attr_name]['calculator']
            }
            for attr_name in active_attributes
            if attr_name in ALL_MATCH_ATTRIBUTES
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
        # STAŁE KONFIGURACYJNE
        # --------------------------------------------------------------------------
        MODEL_BASE_PATH = 'model_{}_dev/{}.h5'  # Szablon ścieżki do zapisu modelu
        INITIAL_ELO = 1500                     # Początkowa wartość rankingu ELO
        SECOND_TIER_COEF = 0.8                 # Współczynnik dla lig drugiej kategorii
        LEARNING_RATE = 0.00001                # Domyślna szybkość uczenia
        THRESHOLD_DATE = "2025-07-04"          # Data graniczna dla danych treningowych
        
        # --------------------------------------------------------------------------
        # KONFIGURACJA WARSTW LSTM
        # --------------------------------------------------------------------------
        lstm_layers_config = {
            "units": [256, 128, 64],           # Liczba neuronów w kolejnych warstwach
            "activation": ["tanh", "tanh", "tanh"],  # Funkcje aktywacji
            "return_sequences": [True, True, False], # Czy zwracać pełną sekwencję
            "dropout": [0.2, 0.2, 0.0],        # Współczynniki dropout
            "batch_normalization": [True, True, False]  # Normalizacja batch
        }
        
        # --------------------------------------------------------------------------
        # KONFIGURACJA WARSTW GĘSTYCH
        # --------------------------------------------------------------------------
        dense_layers_config = [
            {   # Pierwsza warstwa gęsta
                "units": 128,                  # Liczba neuronów
                "activation": "relu",          # Funkcja aktywacji ReLU
                "regularization_l2": None,     # Brak regularyzacji L2
                "dropout": 0.2                 # 20% dropout
            },
            {   # Druga warstwa gęsta
                "units": 64,
                "activation": "relu",
                "regularization_l2": None
            },
            {   # Warstwa wyjściowa pre-softmax
                "units": 16,
                "activation": "linear",        # Liniowa przed softmax
                "regularization_l2": None
            }
        ]
        
        # --------------------------------------------------------------------------
        # KONFIGURACJA WARSTWY WYJŚCIOWEJ
        # --------------------------------------------------------------------------
        output_units_map = {
            'winner': 3,    # 3 klasy wyjściowe (wygrał gospodarz/remis/gość)
            'goals': 7,     # 7 przedziałów bramkowych (0/1/2/3/4/5/6+)
            'btts': 2       # 2 klasy (tak/nie dla obu strzelą)
        }
        output_units = output_units_map.get(self.model_type, 3)  # Domyślnie 3 klasy
        
        # --------------------------------------------------------------------------
        # BUDOWA PEŁNEJ KONFIGURACJI MODELU
        # --------------------------------------------------------------------------
        self.model_config = {
            # Sekcja metadanych modelu
            "model_name": self.model_name,     # Unikalna nazwa modelu
            "model_type": self.model_type,     # Typ modelu (winner/goals/btts/exact)
            "window_size": self.window_size,   # Rozmiar okna czasowego
            
            # Miejsce na metryki treningowe (inicjalizowane zerami)
            "train_accuracy": 0,
            "train_loss": 0,
            "val_accuracy": 0,
            "val_loss": 0,
            
            # Ścieżka do zapisu/odczytu modelu
            "model_path": MODEL_BASE_PATH.format(self.model_type, self.model_name),
            
            # Lista używanych cech
            "feature_columns": self.feature_columns,
            
            # Konfiguracja systemów ratingowych
            "ratings": self._get_ratings_config(INITIAL_ELO, SECOND_TIER_COEF),
            
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
                        "learning_rate": LEARNING_RATE
                    },
                    "loss": "categorical_crossentropy",  # Funkcja straty
                    "metrics": ["accuracy", "Precision", "Recall"]  # Metryki
                }
            },
            
            # Konfiguracja procesu treningowego
            "training_config": {
                "sport_id": 1,                  # ID sportu
                "leagues": self.leagues,        # Lista lig
                "country": self.country,        # Lista krajów
                "load_weights": self.load_weights,  # Czy wagi były ładowane
                "threshold_date": THRESHOLD_DATE # Data graniczna danych
            }
        }

    def _get_ratings_config(self, initial_elo, second_tier_coef):
        """Konfiguracja ratingów dla modelu z optymalizacją outputu JSON"""
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