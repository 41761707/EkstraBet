import pandas as pd
import numpy as np
from collections import deque

import elo_rating
import btts_rating
import gap_rating


class RatingFactory:
    @staticmethod
    def create_rating(method, rating_types=None, **kwargs):
        matches_df = kwargs.get('matches_df')
        teams_df = kwargs.get('teams_df')
        first_tier_leagues = kwargs.get('first_tier_leagues')
        second_tier_leagues = kwargs.get('second_tier_leagues')
        inital_rating = kwargs.get('initial_rating')
        second_tier_coef = kwargs.get('second_tier_coef')
        if not rating_types:
            raise ValueError("Nie podano typów rankingów")
        ratings = [] 

        if method == "winner":
            for rating_type in rating_types:
                if rating_type == "elo":
                    ratings.append(elo_rating.EloRating(matches_df, 
                                                    teams_df, 
                                                    first_tier_leagues, 
                                                    second_tier_leagues, 
                                                    inital_rating, 
                                                    second_tier_coef))
                elif rating_type == "gap":
                    #ratings.append(GapWinnerRating(matches_df, teams_df, first_tier_leagues, second_tier_leagues))
                    pass
                elif rating_type == "berrar":
                    #ratings.append(BerrarWinnerRating(matches_df, teams_df, first_tier_leagues, second_tier_leagues))
                    pass
                else:
                    raise ValueError(f"Nieznany typ rankingu zwycięzcy: {rating_type}")
                    
        elif method == "goals":
            for rating_type in rating_types:
                if rating_type == "elo":
                    ratings.append(elo_rating.EloRating(matches_df, 
                                                    teams_df, 
                                                    first_tier_leagues, 
                                                    second_tier_leagues, 
                                                    inital_rating, 
                                                    second_tier_coef))
                elif rating_type == "gap":
                    ratings.append(gap_rating.GapRating(matches_df, 
                                                              teams_df, 
                                                              first_tier_leagues, 
                                                              second_tier_leagues, 
                                                              inital_rating, 
                                                              second_tier_coef))
                    pass
                elif rating_type == "berrar":
                    #ratings.append(BerrarGoalsRating(matches_df, teams_df, first_tier_leagues, second_tier_leagues))
                    pass
                else:
                    raise ValueError(f"Nieznany typ rankingu goli: {rating_type}")
                    
        elif method == "btts":
            for rating_type in rating_types:
                if rating_type == "elo":
                    ratings.append(elo_rating.EloRating(matches_df, 
                                                        teams_df, 
                                                        first_tier_leagues, 
                                                        second_tier_leagues, 
                                                        inital_rating, 
                                                        second_tier_coef))
                elif rating_type == "gap":
                    ratings.append(gap_rating.GapRating(matches_df, 
                                                              teams_df, 
                                                              first_tier_leagues, 
                                                              second_tier_leagues, 
                                                              inital_rating, 
                                                              second_tier_coef))
                    pass
                elif rating_type == "berrar":
                    #ratings.append(BerrarGoalsRating(matches_df, teams_df, first_tier_leagues, second_tier_leagues))
                    pass
                else:
                    raise ValueError(f"Nieznany typ rankingu btts: {rating_type}")
        elif method == "exact":
            for rating_type in rating_types:
                if rating_type == "elo":
                    ratings.append(elo_rating.EloRating(matches_df, 
                                                        teams_df, 
                                                        first_tier_leagues, 
                                                        second_tier_leagues, 
                                                        inital_rating, 
                                                        second_tier_coef))
                elif rating_type == "gap":
                    ratings.append(gap_rating.GapRating(matches_df, 
                                                              teams_df, 
                                                              first_tier_leagues, 
                                                              second_tier_leagues, 
                                                              inital_rating, 
                                                              second_tier_coef))
                    pass
                elif rating_type == "berrar":
                    #ratings.append(BerrarGoalsRating(matches_df, teams_df, first_tier_leagues, second_tier_leagues))
                    pass
                else:
                    raise ValueError(f"Nieznany typ rankingu btts: {rating_type}")
        else:
            raise ValueError(f"Nieznany typ ratingu: {method}")
            
        return ratings