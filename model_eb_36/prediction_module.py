def predict_next_games(upcoming_games, model, feature_columns):
    """
    Funkcja przewidująca wyniki nadchodzących meczów na podstawie modelu i cech.
    
    :param upcoming_games: DataFrame z danymi o nadchodzących meczach
    :param model: Wytrenowany model do przewidywania wyników
    :param feature_columns: Lista kolumn cech do użycia w przewidywaniu
    :return: DataFrame z przewidywaniami
    """
    # Przekształcenie danych wejściowych do formatu odpowiedniego dla modelu
    X = upcoming_games[feature_columns]
    
    # Przewidywanie wyników
    predictions = model.predict(X)
    
    # Dodanie przewidywań do DataFrame
    upcoming_games['predictions'] = predictions
    
    return upcoming_games