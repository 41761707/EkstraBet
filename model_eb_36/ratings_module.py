import pandas as pd
import numpy as np
from collections import deque

import elo_rating
import gap_rating
import pi_rating

class RatingFactory:
    @staticmethod
    def create_rating(rating_types=None, **kwargs):
        if not rating_types:
            raise ValueError("Nie podano typów rankingów")
            
        matches_df = kwargs.get('matches_df')
        teams_df = kwargs.get('teams_df')
        first_tier_leagues = kwargs.get('first_tier_leagues')
        second_tier_leagues = kwargs.get('second_tier_leagues')
        inital_rating = kwargs.get('initial_rating')
        second_tier_coef = kwargs.get('second_tier_coef')
        match_attributes = kwargs.get('match_attributes')
        
        ratings = []
        
        for rating_type in rating_types:
            if rating_type == "elo":
                ratings.append(elo_rating.EloRating(
                    matches_df, 
                    teams_df, 
                    first_tier_leagues, 
                    second_tier_leagues, 
                    inital_rating, 
                    second_tier_coef
                ))
            elif rating_type == "gap":
                ratings.append(gap_rating.GapRating(
                    matches_df, 
                    teams_df, 
                    first_tier_leagues, 
                    second_tier_leagues, 
                    match_attributes
                ))
            elif rating_type == "pi_rating":
                ratings.append(pi_rating.PiRating())
            else:
                raise ValueError(f"Nieznany typ rankingu: {rating_type}")
                
        return ratings