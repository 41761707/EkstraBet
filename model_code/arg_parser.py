import argparse
from datetime import datetime
from typing import Any

def create_argument_parser() -> argparse.ArgumentParser:
    """
    Tworzy parser argumentów wiersza poleceń dla systemu Ekstrabet.
    
    Returns:
        argparse.ArgumentParser: Skonfigurowany parser argumentów
    """
    parser = argparse.ArgumentParser(
        description='System predykcji sportowych Ekstrabet',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  # Trenowanie z konfiguracją treningu
  python main.py --mode train --model_config btts_model.json --training_config training_config.json
  
  # Predykcja z konfiguracją predykcji
  python main.py --mode predict --model_config btts_model.json --prediction_config prediction_config.json

Argumenty nazwane:
  --mode: tryb pracy (train, predict) - wymagany
  --model_config: ścieżka do pliku JSON z konfiguracją modelu - wymagany
  --training_config: ścieżka do pliku JSON z konfiguracją treningu - opcjonalny
  --prediction_config: ścieżka do pliku JSON z konfiguracją predykcji - opcjonalny
        """
    )
    
    # Argumenty nazwane (wymagane)
    parser.add_argument(
        '--mode', 
        required=True,
        choices=['train', 'predict'],
        help='Tryb pracy aplikacji (wymagany)'
    )
    
    parser.add_argument(
        '--model_config',
        required=True,
        type=str,
        help='Ścieżka do pliku JSON z konfiguracją modelu (wymagany)'
    )
    
    # Argumenty nazwane (opcjonalne)
    parser.add_argument(
        '--training_config',
        type=str,
        help='Ścieżka do pliku JSON z konfiguracją treningu (opcjonalny)'
    )
    
    parser.add_argument(
        '--prediction_config',
        type=str,
        help='Ścieżka do pliku JSON z konfiguracją predykcji (opcjonalny)'
    )

    # Dodatkowe argumenty opcjonalne
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
    validate_arguments(args_dict)
    
    return args_dict

def validate_arguments(args_dict):
    """
    Waliduje argumenty i sprawdza ich poprawność zgodnie z logiką Ekstrabet.
    
    Args:
        args_dict (dict): Słownik z argumentami do walidacji
        
    Raises:
        ValueError: W przypadku niepoprawnych argumentów
    """
    mode = args_dict.get('mode')
    model_config = args_dict.get('model_config')
    
    # Sprawdzenie czy plik konfiguracji modelu istnieje
    if not model_config:
        raise ValueError("[ERROR] Konfiguracja modelu jest wymagana")

    # Walidacja dla trybu trenowania
    if mode == 'train':
        if 'training_config' not in args_dict:
            raise ValueError("[ERROR] Dla trybu 'train' wymagany jest argument --training_config")
        print(f"[OK] Tryb trenowania: konfiguracja modelu - {model_config}")
        print(f"[OK] Konfiguracja treningu: {args_dict['training_config']}")

    # Walidacja dla trybu predykcji
    elif mode == 'predict':
        if 'prediction_config' not in args_dict:
            raise ValueError("[ERROR] Dla trybu 'predict' wymagany jest argument --prediction_config")
        print(f"[OK] Tryb predykcji: konfiguracja modelu - {model_config}")
        print(f"[OK] Konfiguracja predykcji: {args_dict['prediction_config']}")