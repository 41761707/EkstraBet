from tabulate import tabulate

import rating_strategy

class CzechRating:
    def __init__(self, matches_df, teams_df):
        self.matches_df = matches_df
        self.teams_df = teams_df
        self.team_stats = []
        self.init_ratings()

    def init_ratings(self):
        # Initialize current ratings
        for _, team in self.teams_df.iterrows():
            current_dict = {
                'team_id': team['id'],
                'team_name' : team['name'],
                'wins' : 0,
                'draws' : 0,
                'loses' : 0,
                'matches' : 0,
                'goals_scored' : 0,
                'goals_conceded' : 0,
                'win_pct': 0.0,
                'draw_pct': 0.0,
                'gs_avg': 0.0,
                'gc_avg': 0.0,
                'gs_std': 0.0,
                'gc_std': 0.0
               # 'rest': 0
            }
            self.team_stats.append(current_dict)
    
    def calculate_rating(self):
        for index, match in self.matches_df.iterrows():
            # Update statistics for both teams
            #print(f"Gospo: {match['home_team']}, Gosc: {match['away_team']}, Wynik: {match['home_team_goals']} : {match['away_team_goals']}")
            home_stats, away_stats = self.update_team_stats(match)
            self.matches_df.at[index, 'home_team_win_pct'] = home_stats['win_pct']
            self.matches_df.at[index, 'home_team_draw_pct'] = home_stats['draw_pct']
            self.matches_df.at[index, 'home_team_gs_avg'] = home_stats['gs_avg']
            self.matches_df.at[index, 'home_team_gc_avg'] = home_stats['gc_avg']
            self.matches_df.at[index, 'home_team_gs_std'] = home_stats['gs_std']
            self.matches_df.at[index, 'home_team_gc_std'] = home_stats['gc_std']
            
            self.matches_df.at[index, 'away_team_win_pct'] = away_stats['win_pct']
            self.matches_df.at[index, 'away_team_draw_pct'] = away_stats['draw_pct']
            self.matches_df.at[index, 'away_team_gs_avg'] = away_stats['gs_avg']
            self.matches_df.at[index, 'away_team_gc_avg'] = away_stats['gc_avg']
            self.matches_df.at[index, 'away_team_gs_std'] = away_stats['gs_std']
            self.matches_df.at[index, 'away_team_gc_std'] = away_stats['gc_std']

    def update_team_stats(self, match):
        """Helper method to update team statistics for both home and away teams"""
        home_stats = next(team for team in self.team_stats if team['team_id'] == match['home_team'])
        away_stats = next(team for team in self.team_stats if team['team_id'] == match['away_team'])
        #if (match['home_team'] == 3 or match['away_team'] == 3):
        #    print(f"Gospo: {match['home_team']}, Gosc: {match['away_team']}, Wynik: {match['home_team_goals']} : {match['away_team_goals']}")
        # Update match results
        if match['result'] == 1:  # Home win
            #if (match['home_team'] == 3 or match['away_team'] == 3):
            #    print("GOSPO WIN")
            home_stats['wins'] += 1
            away_stats['loses'] += 1
        elif match['result'] == 2:  # Away win
            #if (match['home_team'] == 3 or match['away_team'] == 3):
            #    print("GOSPO LOSE")
            home_stats['loses'] += 1
            away_stats['wins'] += 1
        elif match['result'] == 0:  # Draw
            #if (match['home_team'] == 3 or match['away_team'] == 3):
            #    print("DRAW")
            home_stats['draws'] += 1
            away_stats['draws'] += 1
        else:
            print("Brak danych")
            return
        
        # Update basic stats for home team
        self._update_basic_stats(
            home_stats, 
            match['home_team_goals'], 
            match['away_team_goals']
        )
        
        # Update basic stats for away team
        self._update_basic_stats(
            away_stats, 
            match['away_team_goals'], 
            match['home_team_goals']
        )
        
        # Calculate standard deviations
        self._update_standard_deviations(home_stats, match, is_home=True)
        self._update_standard_deviations(away_stats, match, is_home=False)
        #print(home_stats)
        #print(away_stats)
        return home_stats, away_stats

    def _update_basic_stats(self, stats, goals_scored, goals_conceded):
        """Helper method to update basic statistics"""
        stats['matches'] += 1
        stats['goals_scored'] += goals_scored
        stats['goals_conceded'] += goals_conceded
        
        stats['win_pct'] = round(stats['wins'] * 100 / stats['matches'], 2)
        stats['draw_pct'] = round(stats['draws'] * 100 / stats['matches'], 2)
        stats['gs_avg'] = round(stats['goals_scored'] / stats['matches'], 2)
        stats['gc_avg'] = round(stats['goals_conceded'] / stats['matches'], 2)

    def _update_standard_deviations(self, stats, current_match, is_home):
        """Helper method to calculate standard deviations"""
        team_matches = self.matches_df[
            ((self.matches_df['home_team' if is_home else 'away_team'] == stats['team_id']) &
            (self.matches_df['game_date'] < current_match['game_date']))
        ]
        
        if team_matches.empty:
            stats['gs_std'] = 0.0
            stats['gc_std'] = 0.0
            return
        
        goals_column = 'home_team_goals' if is_home else 'away_team_goals'
        conceded_column = 'away_team_goals' if is_home else 'home_team_goals'
        
        goals_scored_variance = sum((getattr(match, goals_column) - stats['gs_avg']) ** 2 
                                for match in team_matches.itertuples())
        goals_conceded_variance = sum((getattr(match, conceded_column) - stats['gc_avg']) ** 2 
                                    for match in team_matches.itertuples())
        
        stats['gs_std'] = round((goals_scored_variance / len(team_matches)) ** 0.5, 2)
        stats['gc_std'] = round((goals_conceded_variance / len(team_matches)) ** 0.5, 2)

    def print_rating(self):
        """Prints team statistics in a formatted table"""
        # Sort teams by win percentage (descending)
        sorted_stats = sorted(self.team_stats, 
                            key=lambda x: (x['win_pct'], x['gs_avg']), 
                            reverse=True)
        
        # Prepare data for tabulation
        table_data = []
        for team in sorted_stats:
            row = [
                team['team_name'],
                f"{team['matches']}",
                f"{team['wins']}-{team['draws']}-{team['loses']}",
                f"{team['win_pct']}%",
                f"{team['draw_pct']}%",
                f"{team['gs_avg']:.2f}",
                f"{team['gc_avg']:.2f}",
                f"{team['gs_std']:.2f}",
                f"{team['gc_std']:.2f}"
            ]
            table_data.append(row)
        
        # Define headers
        headers = [
            'Team',
            'Matches',
            'W-D-L',
            'Win%',
            'Draw%',
            'GS Avg',
            'GC Avg',
            'GS StD',
            'GC StD'
        ]
        
        # Print the table
        print("\nTeam Ratings:")
        print(tabulate(table_data, 
                    headers=headers, 
                    tablefmt='grid', 
                    numalign='right',
                    floatfmt='.2f'))

    def calculate_match_rating(self):
        pass

    def get_data(self):
        return self.matches_df, self.teams_df