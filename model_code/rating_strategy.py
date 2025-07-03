from abc import ABC, abstractmethod

class RatingStrategy(ABC):
    
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