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
        self.model_config = None 
        self.training_config = None
        self.prediction_config = None
        self.feature_columns = []
        self.threshold_date = datetime.now()
        self.leagues = []
        self.sport_id = -1
        self.country = []
        self.leagues_upcoming = []
        self.load_weights = 0
        self.model_load_name = ""

    def load_from_args(self, args_dict) -> None:
        """
        Inicjalizuje konfigurację na podstawie słownika argumentów z wiersza poleceń.

        Args:
            args_dict (dict): Słownik argumentów z kluczami:
                - model_config: ścieżka do pliku JSON z konfiguracją modelu (wymagany)
                - mode: tryb pracy ('train', 'predict', 'test') (wymagany)
                - training_config: ścieżka do pliku JSON z konfiguracją treningu (wymagany dla mode='train')
                - prediction_config: ścieżka do pliku JSON z konfiguracją predykcji (wymagany dla mode='predict')
                
        Raises:
            KeyError: Jeśli brakuje wymaganych kluczy w args_dict
            ValueError: Jeśli tryb pracy jest nieznany
        """
        # Ładowanie konfiguracji modelu (zawsze wymagane)
        self.model_config = self.load_config(args_dict['model_config'])
        
        # Ładowanie konfiguracji specyficznej dla trybu
        mode = args_dict['mode']
        if mode == 'train':
            self.training_config = self.load_config(args_dict['training_config'])
            self.parse_training_config(self.training_config)
        elif mode == 'predict':
            self.prediction_config = self.load_config(args_dict['prediction_config'])
            self.parse_prediction_config(self.prediction_config)
            self.model_load_name = self.model_config["model_name"]
        else:
            raise ValueError(f"Nieznany tryb pracy: {mode}. Dostępne tryby: 'train', 'predict'")
        
        # Generowanie kolumn cech na podstawie konfiguracji modelu
        self.feature_columns = self.get_feature_columns()

    def parse_training_config(self, config: dict) -> None:
        """
        Ładuje parametry z konfiguracji treningu lub predykcji do instancji klasy.
        
        Args:
            config (dict): Słownik z konfiguracją zawierający parametry do załadowania
            
        Raises:
            KeyError: Jeśli brakuje wymaganych kluczy w konfiguracji
            ValueError: Jeśli format daty jest niepoprawny
        """
        try:
            self.threshold_date = datetime.strptime(config["threshold_date"], "%Y-%m-%d")
            self.leagues = config.get("leagues", [])
            self.sport_id = config.get("sport_id", 1)
            self.country = config.get("country", [])
            self.leagues_upcoming = config.get("leagues_upcoming", [])
            self.load_weights = config.get("load_weights", 0)
            self.model_load_name = config.get("model_load_name", "")
        except KeyError as e:
            raise KeyError(f"Brak wymaganego klucza w konfiguracji: {e}")
        except ValueError as e:
            raise ValueError(f"Niepoprawny format daty threshold_date (oczekiwany YYYY-MM-DD): {e}")
        
    def parse_prediction_config(self, config: dict) -> None:
        """
        Ładuje parametry z konfiguracji predykcji do instancji klasy.
        Args:
            config (dict): Słownik z konfiguracją zawierający parametry do załadowania
        Raises:
            KeyError: Jeśli brakuje wymaganych kluczy w konfiguracji
            ValueError: Jeśli format daty jest niepoprawny
        """
        try:
            self.threshold_date = datetime.strptime(config["threshold_date"], "%Y-%m-%d")
            self.leagues = config.get("leagues", [])
            self.sport_id = config.get("sport_id", 1)
            self.country = config.get("country", [])
            self.leagues_upcoming = config.get("leagues_upcoming", [])
        except KeyError as e:
            raise KeyError(f"Brak wymaganego klucza w konfiguracji: {e}")
        except ValueError as e:
            raise ValueError(f"Niepoprawny format daty threshold_date (oczekiwany YYYY-MM-DD): {e}")

    def load_config(self, path: str) -> dict:
        """
        Wczytuje konfigurację modelu z pliku JSON.

        Args:
            path (str): Ścieżka do pliku JSON z konfiguracją modelu

        Returns:
            dict: Słownik z konfiguracją modelu

        Raises:
            FileNotFoundError: Jeśli plik nie istnieje
            json.JSONDecodeError: Jeśli plik nie jest poprawnym JSON-em
        """
        with open(path, 'r', encoding='utf-8') as file:
            config = json.load(file)
        return config

    def get_feature_columns(self) -> list[str]:
        """
        Tworzy listę kolumn cech (feature_columns) na podstawie włączonych ratingów w konfiguracji modelu.
        
        Przegląda sekcję "supported_ratings" w konfiguracji modelu i łączy wszystkie kolumny
        z ratingów, które mają ustawione enabled=true.
        
        Returns:
            list[str]: Lista nazw kolumn cech do wykorzystania w modelu
            
        Raises:
            ValueError: Jeśli konfiguracja modelu nie została załadowana
            KeyError: Jeśli brakuje wymaganych kluczy w konfiguracji
            
        Przykład:
            config = ConfigManager()
            config.load_from_args(args)
            features = config.get_feature_columns()
            # features = ['home_team_elo', 'away_team_elo', 'home_home_att_power', ...]
        """
        if self.model_config is None:
            raise ValueError("Konfiguracja modelu nie została załadowana. Użyj load_from_args() lub load_model_config() najpierw.")
        
        if 'supported_ratings' not in self.model_config:
            raise KeyError("Brak sekcji 'supported_ratings' w konfiguracji modelu")
        
        feature_columns = []
        supported_ratings = self.model_config['supported_ratings']
        
        for rating_name, rating_config in supported_ratings.items():
            # Sprawdź czy rating jest włączony
            print(rating_name, rating_config.get('enabled', False))
            if rating_config.get('enabled', False) != False:
                # Dodaj kolumny z tego ratingu do listy cech
                if 'columns' in rating_config:
                    feature_columns.extend(rating_config['columns'])
                else:
                    print(f"[WARNING]: Rating '{rating_name}' jest włączony ale nie ma zdefiniowanych kolumn")
        
        return feature_columns