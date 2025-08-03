import argparse
from datetime import datetime
from typing import Any

def create_argument_parser() -> argparse.ArgumentParser:
    """
    Tworzy parser argumentów wiersza poleceń dla systemu Ekstrabet.
    Kolejność argumentów:
    [0] - nazwa skryptu (automatyczne)
    [1] - typ modelu (wymagany)
    [2] - tryb pracy (wymagany) 
    [3] - flaga ładowania wag (wymagany)
    [4] - nazwa modelu (wymagany)
    [5] - nazwa modelu źródłowego (OPCJONALNY)
    [6] - ścieżka do pliku konfiguracji predykcji (OPCJONALNY - tylko jako --prediction_config)
    [7] - flaga automatyzacji predykcji (OPCJONALNY - tylko jako --prediction_automate)
    
    Returns:
        argparse.ArgumentParser: Skonfigurowany parser argumentów
    """
    parser = argparse.ArgumentParser(
        description='System predykcji sportowych Ekstrabet',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  # Trenowanie nowego modelu
  python main.py winner train 0 alpha_v1
  
  # Trenowanie z ładowaniem wag (argument 5 - model źródłowy)
  python main.py winner train 1 alpha_v2 alpha_v1
  
  # Predykcja z domyślną konfiguracją (argument 5 - model źródłowy)
  python main.py winner predict 1 predictions_serie_a serie_b_model
  
  # Predykcja z niestandardową konfiguracją (argument 6 - opcjonalny)
  python main.py winner predict 1 predictions_serie_a serie_b_model --prediction_config configs/serie_a.json
  
  # Testowanie modelu
  python main.py winner test 1 test_run alpha_v1

Argumenty pozycyjne (w kolejności):
  1. model_type: typ modelu (winner, btts, goals, exact)
  2. mode: tryb pracy (train, predict, test)
  3. load_weights: flaga ładowania wag (0 lub 1)
  4. model_name: nazwa modelu

Argumenty nazwane (opcjonalne):
  --model_load_name: nazwa modelu źródłowego do wczytania wag
  --prediction_config: ścieżka do pliku JSON z konfiguracją predykcji
        """
    )
    
    # Argumenty pozycyjne (wymagane)
    parser.add_argument(
        'model_type', 
        choices=['winner', 'btts', 'goals', 'exact'],
        help='Typ modelu do trenowania/predykcji'
    )
    
    parser.add_argument(
        'mode', 
        choices=['train', 'predict', 'test'],
        help='Tryb pracy aplikacji'
    )
    
    parser.add_argument(
        'load_weights',
        type=int,
        choices=[0, 1],
        help='Flaga ładowania wag (0 - nie ładuj, 1 - załaduj)'
    )
    
    parser.add_argument(
        'model_name',
        type=str,
        help='Nazwa modelu do zapisania (train) lub nazwa wynikowa (predict)'
    )
    
    # Argumenty opcjonalne pozycyjne
    parser.add_argument(
        '--model_load_name',
        type=str,
        help='Nazwa modelu źródłowego do wczytania wag'
    )
    
    # Argumenty opcjonalne nazwane
    parser.add_argument(
        '--prediction_config', 
        type=str,
        help='Ścieżka do pliku JSON z konfiguracją predykcji'
    )

    parser.add_argument(
        '--prediction_automate',
        action='store_true',
        help='Jeśli ustawione, predykcje będą automatycznie zapisywane do bazy danych (domyślnie: False, czyli tylko podgląd wyników)'
    )
    return parser

def parse_arguments() -> dict[str, Any]:
    """
    Parsuje argumenty wiersza poleceń i zwraca słownik z parametrami.
    
    Returns:
        dict: Słownik z parametrami konfiguracyjnymi
        
    Raises:
        ValueError: W przypadku niepoprawnych argumentów
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Konwersja na słownik z usunięciem wartości None
    args_dict = {k: v for k, v in vars(args).items() if v is not None}
    
    # Walidacja argumentów
    _validate_arguments(args_dict)
    
    return args_dict

def _validate_arguments(args_dict):
    """
    Waliduje argumenty i sprawdza ich poprawność zgodnie z logiką Ekstrabet.
    
    Args:
        args_dict (dict): Słownik z argumentami do walidacji
        
    Raises:
        ValueError: W przypadku niepoprawnych argumentów
    """
    mode = args_dict.get('mode')
    load_weights = args_dict.get('load_weights')
    
    # Walidacja dla trybu trenowania
    if mode == 'train':
        if load_weights == 1 and 'model_load_name' not in args_dict:
            raise ValueError("Flaga load_weights=1 wymaga podania model_load_name")
    
    # Walidacja dla trybu predykcji
    elif mode == 'predict':
        if 'model_load_name' not in args_dict:
            raise ValueError("Tryb 'predict' wymaga podania model_load_name")
    
    # Walidacja dla trybu testowania
    elif mode == 'test':
        if 'model_load_name' not in args_dict:
            raise ValueError("Tryb 'test' wymaga podania model_load_name")
    
    print(f"Walidacja argumentów zakończona pomyślnie. Tryb: {mode}")