from collections import deque
from tqdm import tqdm
import rating_strategy

# Klasa do obliczania ratingu drużyn na podstawie wyników meczów
class GapRating(rating_strategy.RatingStrategy):
    def __init__(self, matches_df, teams_df, first_tier_leagues, second_tier_leagues, match_attributes):
        self.matches_df = matches_df
        self.teams_df = teams_df
        self.first_tier_leagues = first_tier_leagues
        self.second_tier_leagues = second_tier_leagues
        self.last_five_matches = {}
        self.powers = {}
        # Domyślna konfiguracja jeśli nie podano match_attributes
        self.match_attributes = match_attributes

    def calculate_rating(self):
        for index, row in tqdm(self.matches_df.iterrows(), total=len(self.matches_df), desc="Aktualizacja GapRating"):
            powers = self.calculate_match_rating(row)
            
            # Przypisanie wartości do DataFrame
            self.matches_df.at[index, 'home_home_att_power'] = powers['home_home_att']
            self.matches_df.at[index, 'home_home_def_power'] = powers['home_home_def']
            self.matches_df.at[index, 'home_away_att_power'] = powers['home_away_att']
            self.matches_df.at[index, 'home_away_def_power'] = powers['home_away_def']

            self.matches_df.at[index, 'away_home_att_power'] = powers['away_home_att']
            self.matches_df.at[index, 'away_home_def_power'] = powers['away_home_def']
            self.matches_df.at[index, 'away_away_att_power'] = powers['away_away_att']
            self.matches_df.at[index, 'away_away_def_power'] = powers['away_away_def']

            self.matches_df.at[index, 'home_goals_avg'] = powers['home_goals_avg']
            self.matches_df.at[index, 'away_goals_avg'] = powers['away_goals_avg']

    def calculate_match_rating(self, match):
        # Inicjalizacja powerów dla nowych drużyn
        if match['home_team'] not in self.last_five_matches:
            self.last_five_matches[match['home_team']] = {}
            self.powers["{}h_att".format(match['home_team'])] = 0
            self.powers["{}h_def".format(match['home_team'])] = 0
            self.powers["{}a_att".format(match['home_team'])] = 0
            self.powers["{}a_def".format(match['home_team'])] = 0
        
        if match['away_team'] not in self.last_five_matches:
            self.last_five_matches[match['away_team']] = {}
            self.powers["{}h_att".format(match['away_team'])] = 0
            self.powers["{}h_def".format(match['away_team'])] = 0
            self.powers["{}a_att".format(match['away_team'])] = 0
            self.powers["{}a_def".format(match['away_team'])] = 0

        # Initialize attributes if they don't exist
        for attribute in self.match_attributes:
            if attribute['name'] not in self.last_five_matches[match['home_team']]:
                self.last_five_matches[match['home_team']][attribute['name']] = deque(maxlen=5)
            if attribute['name'] not in self.last_five_matches[match['away_team']]:
                self.last_five_matches[match['away_team']][attribute['name']] = deque(maxlen=5)

        # Calculate averages for the main metric (assuming first attribute is the main one)
        main_attribute = self.match_attributes[0]['name']
        s_h = sum(self.last_five_matches[match['home_team']][main_attribute]) / max(len(self.last_five_matches[match['home_team']][main_attribute]), 1)
        s_a = sum(self.last_five_matches[match['away_team']][main_attribute]) / max(len(self.last_five_matches[match['away_team']][main_attribute]), 1)

        # Pobranie aktualnych powerów
        i_h_att = float(self.powers["{}h_att".format(match['home_team'])])
        i_h_def = float(self.powers["{}h_def".format(match['home_team'])])
        i_a_att = float(self.powers["{}a_att".format(match['home_team'])])
        i_a_def = float(self.powers["{}a_def".format(match['home_team'])])
        j_h_att = float(self.powers["{}h_att".format(match['away_team'])])
        j_h_def = float(self.powers["{}h_def".format(match['away_team'])])
        j_a_att = float(self.powers["{}a_att".format(match['away_team'])])
        j_a_def = float(self.powers["{}a_def".format(match['away_team'])])

        # Aktualizacja powerów
        self.gap_update_home_team(match, i_h_att, i_h_def, i_a_att, j_a_def, j_a_att, i_a_def, s_h, s_a, 0.5, 0.5)
        self.gap_update_away_team(match, j_a_att, j_h_att, j_a_def, j_h_def, i_h_def, i_h_att, s_h, s_a, 0.5, 0.5)

        for attribute in self.match_attributes:
            # Oblicz wartość dla danego atrybutu
            value = attribute['calculator'](match)
            
            # Inicjalizacja słowników dla drużyn, jeśli nie istnieją
            if match['home_team'] not in self.last_five_matches:
                self.last_five_matches[match['home_team']] = {}
            if match['away_team'] not in self.last_five_matches:
                self.last_five_matches[match['away_team']] = {}
            
            # Dla drużyny gospodarzy zapisujemy tylko chances_home
            if 'home' in attribute['name']:
                if attribute['name'] not in self.last_five_matches[match['home_team']]:
                    self.last_five_matches[match['home_team']][attribute['name']] = deque(maxlen=5)
                self.last_five_matches[match['home_team']][attribute['name']].append(value)
            
            # Dla drużyny gości zapisujemy tylko chances_away
            if 'away' in attribute['name']:
                if attribute['name'] not in self.last_five_matches[match['away_team']]:
                    self.last_five_matches[match['away_team']][attribute['name']] = deque(maxlen=5)
                self.last_five_matches[match['away_team']][attribute['name']].append(value)

        #btts = 1 if match['home_team_goals'] > 0 and match['away_team_goals'] > 0 else 0 
        #self.last_five_matches[match['home_team']].append(btts)
        #self.last_five_matches[match['away_team']].append(btts)
        #self.last_five_matches[match['home_team']].append(int(match['home_team_goals'] + match['away_team_goals']))
        #self.last_five_matches[match['away_team']].append(int(match['away_team_goals'] + match['home_team_goals']))

        #Suma rożnych i strzałów
        #value_home = int(match['home_team_ck']) + int(match['home_team_sc'])
        #value_away = int(match['away_team_ck']) + int(match['away_team_sc'])
        #self.last_five_matches[match['home_team']].append(value_home)
        #self.last_five_matches[match['away_team']].append(value_away)

        # Zwracanie słownika z wszystkimi potrzebnymi wartościami
        return {
            'home_home_att': i_h_att,
            'home_home_def': i_h_def,
            'home_away_att': i_a_att,
            'home_away_def': i_a_def,
            'away_home_att': j_h_att,
            'away_home_def': j_h_def,
            'away_away_att': j_a_att,
            'away_away_def': j_a_def,
            'home_goals_avg': s_h,
            'away_goals_avg': s_a
        }

    def gap_update_home_team(self, match, i_h_att, i_h_def, i_a_att, j_a_def, j_a_att, i_a_def, s_h, s_a, l, phi_1):
        i_h_att = max((i_h_att + l * phi_1 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_a_att = max((i_a_att + l * (1 - phi_1) * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        i_h_def = max((i_h_def + l * phi_1 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        i_a_def = max((i_a_def + l * (1 - phi_1) * (s_a - ((j_a_att + i_h_def) / 2))), 0)

        self.powers["{}h_att".format(match['home_team'])] = i_h_att
        self.powers["{}h_def".format(match['home_team'])] = i_h_def
        self.powers["{}a_att".format(match['home_team'])] = i_a_att
        self.powers["{}a_def".format(match['home_team'])] = i_a_def

    def gap_update_away_team(self, match, j_a_att, j_h_att, j_a_def, j_h_def, i_h_def, i_h_att, s_h, s_a, l, phi_2):
        j_a_att = max((j_a_att + l * phi_2 * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_h_att = max((j_h_att + l * (1 - phi_2) * (s_a - ((j_a_att + i_h_def) / 2))), 0)
        j_a_def = max((j_a_def + l * phi_2 * (s_h - ((i_h_att + j_a_def) / 2))), 0)
        j_h_def = max((j_h_def + l * (1 - phi_2) * (s_h - ((i_h_att + j_a_def) / 2))), 0)

        self.powers["{}h_att".format(match['away_team'])] = j_h_att
        self.powers["{}h_def".format(match['away_team'])] = j_h_def
        self.powers["{}a_att".format(match['away_team'])] = j_a_att
        self.powers["{}a_def".format(match['away_team'])] = j_a_def

    def get_rating(self, team_id: int, league: int) -> int:
        #TO-DO Pobranie ratingu gap dla drużyn
        pass
    
    def print_rating(self):
        #TO-DO: Sensowne printowanie ratingu gap dla druzyn
        pass
    
    def get_data(self):
        return self.matches_df, self.teams_df