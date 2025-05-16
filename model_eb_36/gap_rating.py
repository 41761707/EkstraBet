from collections import deque

# Klasa do obliczania ratingu drużyn na podstawie wyników meczów
class GapRating:
    def __init__(self, matches_df, teams_df, first_tier_leagues, second_tier_leagues, initial_elo, second_tier_coef):
        self.matches_df = matches_df
        self.teams_df = teams_df
        self.first_tier_leagues = first_tier_leagues
        self.second_tier_leagues = second_tier_leagues
        self.last_five_matches = {}
        self.powers = {}

    def calculate_rating(self):
        for index, row in self.matches_df.iterrows():
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
            self.last_five_matches[match['home_team']] = deque(maxlen=5)
            self.powers["{}h_att".format(match['home_team'])] = 0
            self.powers["{}h_def".format(match['home_team'])] = 0
            self.powers["{}a_att".format(match['home_team'])] = 0
            self.powers["{}a_def".format(match['home_team'])] = 0
        
        if match['away_team'] not in self.last_five_matches:
            self.last_five_matches[match['away_team']] = deque(maxlen=5)
            self.powers["{}h_att".format(match['away_team'])] = 0
            self.powers["{}h_def".format(match['away_team'])] = 0
            self.powers["{}a_att".format(match['away_team'])] = 0
            self.powers["{}a_def".format(match['away_team'])] = 0

        # Obliczenie średnich goli
        s_h = sum(self.last_five_matches[match['home_team']]) / max(len(self.last_five_matches[match['home_team']]), 1)
        s_a = sum(self.last_five_matches[match['away_team']]) / max(len(self.last_five_matches[match['away_team']]), 1)

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

        # Aktualizacja ostatnich 5 meczów
        self.last_five_matches[match['home_team']].append(int(match['home_team_goals'] + match['away_team_goals']))
        self.last_five_matches[match['away_team']].append(int(match['away_team_goals'] + match['home_team_goals']))

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