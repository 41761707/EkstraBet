import pandas as pd
import numpy as np
from collections import deque

class GoalsRating:
    def __init__(self, matches_df, teams_df):
        # implementacja obliczania rankingu PI
            self.matches_df = matches_df
            self.teams_df = teams_df
            self.teams_dict = {}
            self.ratings = {}
            self.powers = {}
            self.league_features = {}
            self.last_five_matches = {}

    def relax_coef(self, round):
        if round >= 6 :
            return 1
        return (round/6) ** 2
    def form_coef(self, round):
        return 1

    def card_coef(self, card):
        return 1 / (1 + (card)**2)
    def outcome_probability(self, team_a, team_b):
        return 1 / (1 + 10 ** (-(team_a - team_b) / 200))
    
    def update_rating(self, team_rating, win_ppb, team_result, const, round, cards):
        relax = self.relax_coef(round)
        form = self.form_coef(round)
        card = self.card_coef(cards)
        return team_rating + const * (team_result - win_ppb) * relax * form * card
    
    def evaluate_const(self, goal_diff):
        constant = 16
        if goal_diff == 2:
            constant = constant * 3/2
        elif goal_diff == 3:
            constant = constant * 7/4 
        elif goal_diff > 3:
            constant = constant * (7/4 + (goal_diff-3)/8)
        return constant
    
    def main_rating(self, 
                    ratings, 
                    home_team_id, 
                    away_team_id, 
                    result, goal_diff, 
                    cards, 
                    round):
        const = self.evaluate_const(goal_diff)
        home_team_rating = ratings[home_team_id]
        away_team_rating = ratings[away_team_id]
        home_team_ppb = self.outcome_probability(home_team_rating, away_team_rating)
        away_team_ppb = self.outcome_probability(away_team_rating, home_team_rating)
        #assert home_team_ppb + away_team_ppb = 1
        home_team_result = 0
        away_team_result = 0
        if result == 0:
            home_team_result = 0.5
            away_team_result = 0.5
        elif result == 1:
            home_team_result = 1
        else: 
            away_team_result = 1
        home_team_update = self.update_rating(home_team_rating, home_team_ppb, home_team_result, const, round, cards)
        away_team_update = self.update_rating(away_team_rating, away_team_ppb, away_team_result, const, round, cards)
        ratings[home_team_id] = home_team_update
        ratings[away_team_id] = away_team_update
        return home_team_update, away_team_update
    
    def update_home_team(self, i_h_att, i_h_def, i_a_att, j_a_def, j_a_att, i_a_def, s_h, s_a, l, phi_1):
        i_h_att = max((i_h_att + l * phi_1 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_a_att = max((i_a_att + l * (1 - phi_1) * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_h_def = max((i_h_def + l * phi_1 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        i_a_def = max((i_a_def + l * (1 - phi_1) * (s_a - ((j_a_att + i_h_def) / 2))), 0)

        return i_h_att, i_a_att, i_h_def, i_a_def 
    
    def update_away_team(self, j_a_att, j_h_att, j_a_def, j_h_def, i_h_def, i_h_att, s_h, s_a, l,phi_2):
        j_a_att = max((j_a_att + l * phi_2 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_h_att = max((j_h_att + l * (1 - phi_2) * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_a_def = max((j_a_def + l * phi_2 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        j_h_def = max((j_h_def + l * (1 - phi_2) * (s_h - ((i_h_att + j_a_def) / 2))), 0)

        return j_a_att, j_h_att, j_a_def, j_h_def
    
    def rating_wrapper(self):
        starting_rating = 500
        for team in self.teams_df.values:
            if team[0] not in self.ratings:
                self.ratings[team[0]] = starting_rating
                self.last_five_matches[team[0]] = deque(maxlen=5)
                self.powers["{}h_att".format(team[0])] = 0
                self.powers["{}h_def".format(team[0])] = 0
                self.powers["{}a_att".format(team[0])] = 0
                self.powers["{}a_def".format(team[0])] = 0
            if team[1] not in self.teams_dict:
                self.teams_dict[team[0]] = team[1]
        for index, _ in self.matches_df.iterrows():
            self.last_five_matches[self.matches_df.loc[index, 'home_team']].append(int(self.matches_df.loc[index, 'home_team_goals'] + self.matches_df.loc[index, 'away_team_goals']))
            self.last_five_matches[self.matches_df.loc[index, 'away_team']].append(int(self.matches_df.loc[index, 'away_team_goals'] + self.matches_df.loc[index, 'home_team_goals']))
            if "{}_goals".format(self.matches_df.loc[index, 'league']) not in self.league_features:
                self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] = 0
            if "{}_matches".format(self.matches_df.loc[index, 'league']) not in self.league_features:
                self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])] = 0

            self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] += self.matches_df.loc[index, 'home_team_goals'] + self.matches_df.loc[index, 'away_team_goals']
            self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])] += 1
            s_h = sum(self.last_five_matches[self.matches_df.loc[index, 'home_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'home_team']])
            s_a = sum(self.last_five_matches[self.matches_df.loc[index, 'away_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'away_team']])
            i_h_att = float(self.powers["{}h_att".format(self.matches_df.loc[index, 'home_team'])])
            i_h_def = float(self.powers["{}h_def".format(self.matches_df.loc[index, 'home_team'])])
            i_a_att = float(self.powers["{}a_att".format(self.matches_df.loc[index, 'home_team'])])
            i_a_def = float(self.powers["{}a_def".format(self.matches_df.loc[index, 'home_team'])])
            j_h_att = float(self.powers["{}h_att".format(self.matches_df.loc[index, 'away_team'])])
            j_h_def = float(self.powers["{}h_def".format(self.matches_df.loc[index, 'away_team'])])
            j_a_att = float(self.powers["{}a_att".format(self.matches_df.loc[index, 'away_team'])])
            j_a_def = float(self.powers["{}a_def".format(self.matches_df.loc[index, 'away_team'])])
            goal_diff = abs(self.matches_df.loc[index, 'home_team_goals'] - self.matches_df.loc[index, 'away_team_goals'])
            home_rating, away_rating = self.main_rating(self.ratings, 
                                                       self.matches_df.loc[index, 'home_team'], 
                                                       self.matches_df.loc[index, 'away_team'], 
                                                       self.matches_df.loc[index, 'result'], 
                                                       goal_diff,
                                                       int(self.matches_df.loc[index, 'home_team_rc'] + self.matches_df.loc[index, 'away_team_rc']),
                                                       10)
            
            self.matches_df.at[index, 'home_rating'] = home_rating
            self.matches_df.at[index, 'away_rating'] = away_rating

            self.matches_df.at[index, 'home_goals_avg'] = sum(self.last_five_matches[self.matches_df.loc[index, 'home_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'home_team']])
            self.matches_df.at[index, 'away_goals_avg'] = sum(self.last_five_matches[self.matches_df.loc[index, 'away_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'away_team']])
            i_h_att, i_a_att, i_h_def, i_a_def = self.update_home_team(i_h_att, i_h_def, i_a_att, j_a_def, j_a_att, i_a_def, s_h, s_a, 0.5, 0.5)
            j_a_att, j_h_att, j_a_def, j_h_def = self.update_away_team(j_a_att, j_h_att, j_a_def, j_h_def, i_h_def, i_h_att, s_h, s_a, 0.5, 0.5)
            self.matches_df.at[index, 'home_home_att_power'] =i_h_att
            self.matches_df.at[index, 'home_home_def_power'] =i_h_def
            self.matches_df.at[index, 'home_away_att_power'] =i_a_att
            self.matches_df.at[index, 'home_away_def_power'] =i_a_def

            self.matches_df.at[index, 'away_home_att_power'] =j_h_att
            self.matches_df.at[index, 'away_home_def_power'] =j_h_def
            self.matches_df.at[index, 'away_away_att_power'] =j_a_att
            self.matches_df.at[index, 'away_away_def_power'] =j_a_def
            #self.matches_df.at[index, 'league_goals_avg'] = self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] / self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])]
            self.powers["{}h_att".format(self.matches_df.loc[index, 'home_team'])] = i_h_att
            self.powers["{}h_def".format(self.matches_df.loc[index, 'home_team'])] = i_h_def
            self.powers["{}a_att".format(self.matches_df.loc[index, 'home_team'])] = i_a_att
            self.powers["{}a_def".format(self.matches_df.loc[index, 'home_team'])] = i_a_def


            self.powers["{}h_att".format(self.matches_df.loc[index, 'away_team'])] = j_h_att
            self.powers["{}h_def".format(self.matches_df.loc[index, 'away_team'])] = j_h_def
            self.powers["{}a_att".format(self.matches_df.loc[index, 'away_team'])] = j_a_att
            self.powers["{}a_def".format(self.matches_df.loc[index, 'away_team'])] = j_a_def
            #print(self.powers["{}h_att".format(self.matches_df.loc[index, 'home_team'])])
            #print(self.powers["{}h_att".format(self.matches_df.loc[index, 'away_team'])])
        #print(self.powers)
    def get_data(self):
        return self.matches_df, self.teams_df, self.teams_dict, self.powers, self.ratings, self.last_five_matches
    
    def print_ratings(self):
        ratings_list = [(self.teams_dict[k],v) for k,v in self.ratings.items()]
        ratings_list.sort(key=lambda x: x[1], reverse= True)
        for item in ratings_list:
            if item[1] == 1500:
                continue
            print(item[0],": ", item[1])

class WinnerRating:
    def __init__(self, matches_df, teams_df):
            self.matches_df = matches_df
            self.teams_df = teams_df
            self.teams_dict = {}
            self.ratings = {}
            self.powers = {}
            self.league_features = {}
            self.last_five_matches = {}

    def relax_coef(self, round):
        if round >= 6 :
            return 1
        return (round/6) ** 2
    def form_coef(self, round):
        return 1

    def card_coef(self, card):
        return 1 / (1 + (card)**2)
    def outcome_probability(self, team_a, team_b):
        return 1 / (1 + 10 ** (-(team_a - team_b) / 400))
    
    def update_rating(self, team_rating, win_ppb, team_result, const, round, cards):
        relax = self.relax_coef(round)
        form = self.form_coef(round)
        card = self.card_coef(cards)
        return team_rating + const * (team_result - win_ppb) * relax * form * card
    
    def evaluate_const(self, goal_diff):
        constant = 64
        if goal_diff == 2:
            constant = constant * 3/2
        elif goal_diff == 3:
            constant = constant * 7/4 
        elif goal_diff > 3:
            constant = constant * (7/4 + (goal_diff-3)/8)
        return constant
    
    def main_rating(self, 
                    ratings, 
                    home_team_id, 
                    away_team_id, 
                    result, goal_diff, 
                    cards, 
                    round):
        #print("RESULT: ", result)
        const = self.evaluate_const(goal_diff)
        home_team_rating = ratings[home_team_id]
        away_team_rating = ratings[away_team_id]
        home_team_ppb = self.outcome_probability(home_team_rating, away_team_rating)
        away_team_ppb = self.outcome_probability(away_team_rating, home_team_rating)
        #assert home_team_ppb + away_team_ppb = 1
        home_team_result = 0
        away_team_result = 0
        if result == 0:
            home_team_result = 0.5
            away_team_result = 0.5
        elif result == 1:
            home_team_result = 1
        else: 
            away_team_result = 1
        home_team_update = self.update_rating(home_team_rating, home_team_ppb, home_team_result, const, round, cards)
        away_team_update = self.update_rating(away_team_rating, away_team_ppb, away_team_result, const, round, cards)
        ratings[home_team_id] = home_team_update
        ratings[away_team_id] = away_team_update
        return home_team_update, away_team_update
    
    def update_home_team(self, i_h_att, i_h_def, i_a_att, j_a_def, j_a_att, i_a_def, s_h, s_a, l, phi_1):
        i_h_att = max((i_h_att + l * phi_1 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_a_att = max((i_a_att + l * (1 - phi_1) * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_h_def = max((i_h_def + l * phi_1 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        i_a_def = max((i_a_def + l * (1 - phi_1) * (s_a - ((j_a_att + i_h_def) / 2))), 0)

        return i_h_att, i_a_att, i_h_def, i_a_def 
    
    def update_away_team(self, j_a_att, j_h_att, j_a_def, j_h_def, i_h_def, i_h_att, s_h, s_a, l,phi_2):
        j_a_att = max((j_a_att + l * phi_2 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_h_att = max((j_h_att + l * (1 - phi_2) * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_a_def = max((j_a_def + l * phi_2 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        j_h_def = max((j_h_def + l * (1 - phi_2) * (s_h - ((i_h_att + j_a_def) / 2))), 0)

        return j_a_att, j_h_att, j_a_def, j_h_def
    
    def rating_wrapper(self):
        starting_rating = 1500
        for team in self.teams_df.values:
            if team[0] not in self.ratings:
                self.ratings[team[0]] = starting_rating
                self.last_five_matches[team[0]] = deque(maxlen=5)
                '''self.powers["{}h_att".format(team[0])] = 0
                self.powers["{}h_def".format(team[0])] = 0
                self.powers["{}a_att".format(team[0])] = 0
                self.powers["{}a_def".format(team[0])] = 0'''
            if team[1] not in self.teams_dict:
                self.teams_dict[team[0]] = team[1]
        for index, _ in self.matches_df.iterrows():
            #if self.ratings[self.matches_df.loc[index, 'home_team']] == 1500 and self.matches_df.loc[index, 'league'] in (8, 13, 14, 20, 21, 26, 30, 32, 36, 37, 38, 39, 40):
            #    self.ratings[self.matches_df.loc[index, 'home_team']] = 1200
            #    print(self.matches_df.loc[index, 'home_team'])
            #if self.ratings[self.matches_df.loc[index, 'away_team']] == 1500 and self.matches_df.loc[index, 'league'] in (8, 13, 14, 20, 21, 26, 30, 32, 36, 37, 38, 39, 40):
            #    self.ratings[self.matches_df.loc[index, 'away_team']] = 1200
            #    print(self.matches_df.loc[index, 'away_team'])
            if "{}_goals".format(self.matches_df.loc[index, 'league']) not in self.league_features:
                self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] = 0
            if "{}_matches".format(self.matches_df.loc[index, 'league']) not in self.league_features:
                self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])] = 0
            self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] += self.matches_df.loc[index, 'home_team_goals'] + self.matches_df.loc[index, 'away_team_goals']
            self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])] += 1
            goal_diff = abs(self.matches_df.loc[index, 'home_team_goals'] - self.matches_df.loc[index, 'away_team_goals'])
            home_rating, away_rating = self.main_rating(self.ratings, 
                                                        self.matches_df.loc[index, 'home_team'], 
                                                        self.matches_df.loc[index, 'away_team'], 
                                                        self.matches_df.loc[index, 'result'], 
                                                        goal_diff,
                                                        int(self.matches_df.loc[index, 'home_team_rc'] + self.matches_df.loc[index, 'away_team_rc']),
                                                        #int(self.matches_df.loc[index, 'round']))
                                                        10)
            
            self.matches_df.at[index, 'home_rating'] = home_rating
            self.matches_df.at[index, 'away_rating'] = away_rating
        #print(self.powers)

    def get_data(self):
        return self.matches_df, self.teams_df, self.teams_dict, self.powers, self.ratings
    
    def print_ratings(self):
        ratings_list = [(self.teams_dict[k],v) for k,v in self.ratings.items()]
        ratings_list.sort(key=lambda x: x[1], reverse= True)
        for item in ratings_list:
            if item[1] == 1500:
                continue
            print(item[0],": ", item[1])

class BTTSRating:
    def __init__(self, matches_df, teams_df):
            self.matches_df = matches_df
            self.teams_df = teams_df
            self.teams_dict = {}
            self.ratings = {}
            self.powers = {}
            self.league_features = {}
            self.last_five_matches = {}

    def relax_coef(self, round):
        if round >= 6 :
            return 1
        return (round/6) ** 2
    def form_coef(self, round):
        return 1

    def card_coef(self, card):
        return 1 / (1 + (card)**2)
    def outcome_probability(self, team_a, team_b):
        return 1 / (1 + 10 ** (-(team_a - team_b) / 400))
    
    def update_rating(self, team_rating, win_ppb, team_result, const, round, cards):
        relax = self.relax_coef(round)
        form = self.form_coef(round)
        card = self.card_coef(cards)
        return team_rating + const * (team_result - win_ppb) * relax * form * card
    
    def evaluate_const(self, goal_diff):
        constant = 64
        if goal_diff == 2:
            constant = constant * 3/2
        elif goal_diff == 3:
            constant = constant * 7/4 
        elif goal_diff > 3:
            constant = constant * (7/4 + (goal_diff-3)/8)
        return constant
    
    def main_rating(self, 
                    ratings, 
                    home_team_id, 
                    away_team_id, 
                    result, goal_diff, 
                    cards, 
                    round):
        const = self.evaluate_const(goal_diff)
        home_team_rating = ratings[home_team_id]
        away_team_rating = ratings[away_team_id]
        home_team_ppb = self.outcome_probability(home_team_rating, away_team_rating)
        away_team_ppb = self.outcome_probability(away_team_rating, home_team_rating)
        #assert home_team_ppb + away_team_ppb = 1
        home_team_result = 0
        away_team_result = 0
        if result == 0:
            home_team_result = 0.5
            away_team_result = 0.5
        elif result == 1:
            home_team_result = 1
        else: 
            away_team_result = 1
        home_team_update = self.update_rating(home_team_rating, home_team_ppb, home_team_result, const, round, cards)
        away_team_update = self.update_rating(away_team_rating, away_team_ppb, away_team_result, const, round, cards)
        ratings[home_team_id] = home_team_update
        ratings[away_team_id] = away_team_update
        return home_team_update, away_team_update
    
    def update_home_team(self, i_h_att, i_h_def, i_a_att, j_a_def, j_a_att, i_a_def, s_h, s_a, l, phi_1):
        i_h_att = max((i_h_att + l * phi_1 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_a_att = max((i_a_att + l * (1 - phi_1) * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_h_def = max((i_h_def + l * phi_1 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        i_a_def = max((i_a_def + l * (1 - phi_1) * (s_a - ((j_a_att + i_h_def) / 2))), 0)

        return i_h_att, i_a_att, i_h_def, i_a_def 
    
    def update_away_team(self, j_a_att, j_h_att, j_a_def, j_h_def, i_h_def, i_h_att, s_h, s_a, l,phi_2):
        j_a_att = max((j_a_att + l * phi_2 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_h_att = max((j_h_att + l * (1 - phi_2) * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_a_def = max((j_a_def + l * phi_2 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        j_h_def = max((j_h_def + l * (1 - phi_2) * (s_h - ((i_h_att + j_a_def) / 2))), 0)

        return j_a_att, j_h_att, j_a_def, j_h_def
    
    def rating_wrapper(self):
        starting_rating = 1500
        for team in self.teams_df.values:
            if team[0] not in self.ratings:
                self.ratings[team[0]] = starting_rating
                self.last_five_matches[team[0]] = deque(maxlen=5)
                self.powers["{}h_att".format(team[0])] = 0
                self.powers["{}h_def".format(team[0])] = 0
                self.powers["{}a_att".format(team[0])] = 0
                self.powers["{}a_def".format(team[0])] = 0
            if team[1] not in self.teams_dict:
                self.teams_dict[team[0]] = team[1]
        for index, _ in self.matches_df.iterrows():
            self.last_five_matches[self.matches_df.loc[index, 'home_team']].append(int(self.matches_df.loc[index, 'home_team_goals']))
            self.last_five_matches[self.matches_df.loc[index, 'away_team']].append(int(self.matches_df.loc[index, 'away_team_goals']))
            if "{}_goals".format(self.matches_df.loc[index, 'league']) not in self.league_features:
                self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] = 0
            if "{}_matches".format(self.matches_df.loc[index, 'league']) not in self.league_features:
                self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])] = 0
            self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] += self.matches_df.loc[index, 'home_team_goals'] + self.matches_df.loc[index, 'away_team_goals']
            self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])] += 1
            s_h = sum(self.last_five_matches[self.matches_df.loc[index, 'home_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'home_team']])
            s_a = sum(self.last_five_matches[self.matches_df.loc[index, 'away_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'away_team']])
            i_h_att = float(self.powers["{}h_att".format(self.matches_df.loc[index, 'home_team'])])
            i_h_def = float(self.powers["{}h_def".format(self.matches_df.loc[index, 'home_team'])])
            i_a_att = float(self.powers["{}a_att".format(self.matches_df.loc[index, 'home_team'])])
            i_a_def = float(self.powers["{}a_def".format(self.matches_df.loc[index, 'home_team'])])
            j_h_att = float(self.powers["{}h_att".format(self.matches_df.loc[index, 'away_team'])])
            j_h_def = float(self.powers["{}h_def".format(self.matches_df.loc[index, 'away_team'])])
            j_a_att = float(self.powers["{}a_att".format(self.matches_df.loc[index, 'away_team'])])
            j_a_def = float(self.powers["{}a_def".format(self.matches_df.loc[index, 'away_team'])])
            goal_diff = abs(self.matches_df.loc[index, 'home_team_goals'] - self.matches_df.loc[index, 'away_team_goals'])
            home_rating, away_rating = self.main_rating(self.ratings, 
                                                       self.matches_df.loc[index, 'home_team'], 
                                                       self.matches_df.loc[index, 'away_team'], 
                                                       self.matches_df.loc[index, 'result'], 
                                                       goal_diff,
                                                       int(self.matches_df.loc[index, 'home_team_rc'] + self.matches_df.loc[index, 'away_team_rc']),
                                                       self.matches_df.at[index, 'round'])
            
            self.matches_df.at[index, 'home_rating'] = home_rating
            self.matches_df.at[index, 'away_rating'] = away_rating
            self.matches_df.at[index, 'home_goals_avg'] = sum(self.last_five_matches[self.matches_df.loc[index, 'home_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'home_team']])
            self.matches_df.at[index, 'away_goals_avg'] = sum(self.last_five_matches[self.matches_df.loc[index, 'away_team']]) / len(self.last_five_matches[self.matches_df.loc[index, 'away_team']])
            
            i_h_att, i_a_att, i_h_def, i_a_def = self.update_home_team(i_h_att, i_h_def, i_a_att, j_a_def, j_a_att, i_a_def, s_h, s_a, 0.5, 0.5)
            j_a_att, j_h_att, j_a_def, j_h_def = self.update_away_team(j_a_att, j_h_att, j_a_def, j_h_def, i_h_def, i_h_att, s_h, s_a, 0.5, 0.5)
            self.matches_df.at[index, 'home_home_att_power'] =i_h_att
            self.matches_df.at[index, 'home_home_def_power'] =i_h_def
            self.matches_df.at[index, 'home_away_att_power'] =i_a_att
            self.matches_df.at[index, 'home_away_def_power'] =i_a_def

            self.matches_df.at[index, 'away_home_att_power'] =j_h_att
            self.matches_df.at[index, 'away_home_def_power'] =j_h_def
            self.matches_df.at[index, 'away_away_att_power'] =j_a_att
            self.matches_df.at[index, 'away_away_def_power'] =j_a_def
            #self.matches_df.at[index, 'league_goals_avg'] = self.league_features["{}_goals".format(self.matches_df.loc[index, 'league'])] / self.league_features["{}_matches".format(self.matches_df.loc[index, 'league'])]
            self.powers["{}h_att".format(self.matches_df.loc[index, 'home_team'])] = i_h_att
            self.powers["{}h_def".format(self.matches_df.loc[index, 'home_team'])] = i_h_def
            self.powers["{}a_att".format(self.matches_df.loc[index, 'home_team'])] = i_a_att
            self.powers["{}a_def".format(self.matches_df.loc[index, 'home_team'])] = i_a_def


            self.powers["{}h_att".format(self.matches_df.loc[index, 'away_team'])] = j_h_att
            self.powers["{}h_def".format(self.matches_df.loc[index, 'away_team'])] = j_h_def
            self.powers["{}a_att".format(self.matches_df.loc[index, 'away_team'])] = j_a_att
            self.powers["{}a_def".format(self.matches_df.loc[index, 'away_team'])] = j_a_def
    def get_data(self):
        return self.matches_df, self.teams_df, self.teams_dict, self.powers, self.ratings, self.last_five_matches
    
    def print_ratings(self):
        ratings_list = [(self.teams_dict[k],v) for k,v in self.ratings.items()]
        ratings_list.sort(key=lambda x: x[1], reverse= True)
        for item in ratings_list:
            if item[1] == 1500:
                continue
            print(item[0],": ", item[1])
    

class RatingFactory:
    @staticmethod
    def create_rating(method, matches_df, teams_df):
        if method == "GoalsRating":
            return GoalsRating(matches_df, teams_df)
        if method == "WinnerRating":
            return WinnerRating(matches_df, teams_df)
        if method == "BTTSRating":
            return BTTSRating(matches_df, teams_df)

# Użycie fabryki do tworzenia instancji różnych metod obliczania rankingu
#elo_calculator = RatingFactory.create_rating("Elo", <obiekt typu pandas z listą meczów>, <obiekt typu pandas z listą drużyn>)
#berrar_calculator = RatingFactory.create_rating("Berrar", <obiekt typu pandas z listą meczów>, <obiekt typu pandas z listą drużyn>)
#gap_calculator = RatingFactory.create_rating("GAP", <obiekt typu pandas z listą meczów>, <obiekt typu pandas z listą drużyn>)
#pi_calculator = RatingFactory.create_rating("PI", <obiekt typu pandas z listą meczów>, <obiekt typu pandas z listą drużyn>)