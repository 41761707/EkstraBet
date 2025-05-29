import rating_strategy
# Klasa do obliczania rankingu drużyn na podstawie wyników meczów, wykorzystywana jest metdologia ELO


class EloRating(rating_strategy.RatingStrategy):
    def __init__(self, matches_df, teams_df, first_tier_leagues, second_tier_leagues, initial_elo, second_tier_coef):
        self.matches_df = matches_df
        self.teams_df = teams_df
        self.first_tier_leagues = first_tier_leagues
        self.second_tier_leagues = second_tier_leagues
        self.initial_elo = initial_elo
        self.second_tier_coef = second_tier_coef
        self.elo_dict = {}  # {team_id: aktualne ELO}

    def calculate_rating(self):
        for index, row in self.matches_df.iterrows():
            new_elo = self.calculate_match_rating(row)
            self.matches_df.at[index, 'home_team_elo'] = new_elo['home_team_elo']
            self.matches_df.at[index, 'away_team_elo'] = new_elo['away_team_elo']

    def calculate_match_rating(self, match):
        home_team_elo = self.get_elo(match['home_team'], match['league'])
        away_team_elo = self.get_elo(match['away_team'], match['league'])

        # print(match)
        self.update_elo(home_team_elo,
                        away_team_elo,
                        match['home_team'],
                        match['away_team'],
                        match['home_team_goals'],
                        match['away_team_goals'],
                        match['result'])
        return {
            'home_team_elo': self.elo_dict[match['home_team']],
            'away_team_elo': self.elo_dict[match['away_team']]
        }

    def evaluate_const(self, goal_diff):
        constant = 64
        if goal_diff == 2:
            constant = constant * 3/2
        elif goal_diff == 3:
            constant = constant * 7/4
        elif goal_diff > 3:
            constant = constant * (7/4 + (goal_diff-3)/8)
        return constant

    def update_elo(self,
                   home_elo: float,
                   away_elo: float,
                   home_team: int,
                   away_team: int,
                   home_team_goals: int,
                   away_team_goals: int,
                   result: int):
        """
        Aktualizuje ELO po meczu.
        result: 1 (home win), 0 (remis), 2 (away win)
        """
        # Pobierz aktualne ELO

        # Oblicz oczekiwaną skuteczność
        expected_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
        expected_away = 1 - expected_home

        # Określ rzeczywisty wynik
        if result == 1:
            actual_home, actual_away = 1, 0
        elif result == 2:
            actual_home, actual_away = 0, 1
        else:
            actual_home, actual_away = 0.5, 0.5

        # Aktualizuj ELO
        k_factor = self.evaluate_const(home_team_goals - away_team_goals)
        new_home_elo = round(home_elo + k_factor *
                             (actual_home - expected_home), 2)
        new_away_elo = round(away_elo + k_factor *
                             (actual_away - expected_away), 2)

        self.elo_dict[home_team] = new_home_elo
        self.elo_dict[away_team] = new_away_elo

    def get_elo(self, team_id: int, league: int) -> int:
        if team_id not in self.elo_dict:
            if league in self.second_tier_leagues:  # mechanizm wolniejszego startu dla drużyn z niższych lig
                inital_elo = self.initial_elo * self.second_tier_coef
            else:
                inital_elo = self.initial_elo
            self.elo_dict[team_id] = inital_elo
        return self.elo_dict[team_id]

    def print_rating(self):
        elo_list = list(self.elo_dict.items())
        elo_list.sort(key=lambda x: x[1], reverse=True)
        for element in elo_list:
            print(
                f"{self.teams_df.loc[self.teams_df['id'] == element[0]]['name'].values[0]}: {element[1]}")

    def get_data(self):
        return self.matches_df, self.teams_df
