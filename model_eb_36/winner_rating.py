from abc import ABC, abstractmethod

class WinnerRatingStrategy(ABC):
    @abstractmethod
    def __init__(self, matches_df, teams_df, first_tier_leagues, second_tier_leagues, initial_elo, second_tier_coef):
        pass
    
    @abstractmethod
    def calculate_rating(self):
        pass

    @abstractmethod
    def print_rating(self):
        pass

    @abstractmethod
    def calculate_match_rating(self):
        pass

    @abstractmethod
    def get_data(self):
        pass