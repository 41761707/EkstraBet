from tabulate import tabulate
from tqdm import tqdm
import rating_strategy

class CzechRating(rating_strategy.RatingStrategy):
    def __init__(self, matches_df, teams_df):
        self.matches_df = matches_df
        self.teams_df = teams_df
        self.team_stats = []
        self.init_ratings()

    def init_ratings(self):
        # Initialize current ratings
        for _, team in self.teams_df.iterrows():
            current_dict = {
                'team_id': team['id'],      # ID drużyny
                'team_name' : team['name'], # Nazwa drużyny
                'home_wins' : 0,            # Liczba zwycięstw w spotkania domowych (sumaryczna)
                'away_wins' : 0,            # Liczba zwycięstw w spotkania wyjazdowych (sumaryczna)
                'home_draws' : 0,           # Liczba remisów w spotkaniach domowych (sumaryczna)
                'away_draws' : 0,           # Liczba remisów w spotkaniach wyjazdowych (sumaryczna)
                'home_loses' : 0,           # Liczba porażek w spotkaniach domowych (sumaryczna)
                'away_loses' : 0,           # Liczba porażek w spotkaniach wyjazdowych (sumaryczna)
                'matches' : 0,              # Liczba rozegranych meczów (sumaryczna)
                'home_goals_scored' : 0,    # Liczba zdobytych bramek w meczach domowych (sumaryczna)
                'home_goals_scored_sq' : 0, # Suma kwadratów zdobytych bramek w meczach domowych (sumaryczna)
                'away_goals_scored' : 0,    # Liczba zdobytych bramek w meczach wyjazdowych (sumaryczna)
                'away_goals_scored_sq' : 0, # Suma kwadratów zdobytych bramek w meczach wyjazdowych (sumaryczna)
                'home_goals_conceded' : 0,       # Liczba straconych bramek w meczach domowych (sumaryczna)
                'home_goals_conceded_sq' : 0,    # Suma kwadratów straconych bramek w meczach domowych (sumaryczna)
                'away_goals_conceded' : 0,       # Liczba straconych bramek w meczach wyjazdowych (sumaryczna)
                'away_goals_conceded_sq' : 0,    # Suma kwadratów straconych bramek w meczach wyjazdowych (sumaryczna)
                'home_win_pct': 0.0,             # Procent zwycięstw w meczach domowych
                'away_win_pct': 0.0,             # Procent zwycięstw w meczach wyjazdowych
                'home_draw_pct': 0.0,            # Procent remisów w meczach domowych
                'away_draw_pct': 0.0,            # Procent remisów w meczach wyjazdowych
                'home_gs_avg': 0.0,              # Średnia zdobytych bramek w meczach domowych
                'away_gs_avg': 0.0,              # Średnia zdobytych bramek w meczach wyjazdowych
                'home_gc_avg': 0.0,              # Średnia straconych bramek w meczach domowych
                'away_gc_avg': 0.0,              # Średnia straconych bramek w meczach wyjazdowych
                'home_gs_std': 0.0,              # Odchylenie standardowe zdobytych bramek w meczach domowych
                'away_gs_std': 0.0,              # Odchylenie standardowe zdobytych bramek w meczach wyjazdowych
                'home_gc_std': 0.0,              # Odchylenie standardowe straconych bramek w meczach domowych
                'away_gc_std': 0.0,              # Odchylenie standardowe straconych bramek w meczach wyjazdowych
                'last_game_date': None,     # Data ostatniego meczu
                'rest': 0,                  # Liczba dni odpoczynku od ostatniego meczu
                'win_pct_last_5' : 0.0,       # Procent zwycięstw w ostatnich 5 meczach
                'draw_pct_last_5' : 0.0,      # Procent remisów w ostatnich 5 meczach
                'gs_avg_last_5' : 0.0,      # Średnia zdobytych bramek w ostatnich 5 meczach
                'gc_avg_last_5' : 0.0,      # Średnia straconych bramek w ostatnich 5 meczach
                'gs_std_last_5' : 0.0,      # Odchylenie standardowe zdobytych bramek w ostatnich 5 meczach
                'gc_std_last_5' : 0.0,      # Odchylenie standardowe straconych bramek w ostatnich 5 meczach
            }
            self.team_stats.append(current_dict)
    
    def calculate_rating(self) -> None:
        """
        Oblicza i aktualizuje statystyki drużyn dla wszystkich meczów w DataFrame.
        
        Dla każdego meczu w matches_df:
        1. Pobiera aktualne statystyki drużyn (gospodarza i gościa)
        2. Aktualizuje wartości statystyk w DataFrame
        3. Uwzględnia różne wskaźniki jak procent wygranych, średnie bramki, odchylenia standardowe
        
        Statystyki są obliczane osobno dla:
        - występów gospodarza u siebie
        - występów gościa na wyjeździe
        - ostatnich 5 meczów drużyny
        
        Argumenty:
            self - instancja klasy zawierająca matches_df z danymi meczowymi
        
        Zwraca:
            None - funkcja modyfikuje bezpośrednio matches_df dodając kolumny ze statystykami
        """
        
        # Stałe z nazwami kolumn do aktualizacji
        STAT_COLUMNS = [
            'home_win_pct', 'away_win_pct', 'home_draw_pct', 'away_draw_pct',
            'home_gs_avg', 'away_gs_avg', 'home_gc_avg', 'away_gc_avg',
            'home_gs_std', 'away_gs_std', 'home_gc_std', 'away_gc_std',
            'win_pct_last_5', 'draw_pct_last_5', 'gs_avg_last_5', 'gc_avg_last_5',
            'gs_std_last_5', 'gc_std_last_5', 'rest'
        ]
        
        # Przygotowanie słowników do przechowywania wyników
        home_updates = {f'home_team_{col}': [] for col in STAT_COLUMNS}
        away_updates = {f'away_team_{col}': [] for col in STAT_COLUMNS}
        
        # Iteracja przez wszystkie mecze
        for _, match in tqdm(self.matches_df.iterrows(), total=len(self.matches_df), desc="Aktualizacja CzechRating"):
            # Pobranie aktualnych statystyk drużyn
            home_stats, away_stats = self.update_team_stats(match)
            
            # Zbieranie statystyk gospodarza
            for col in STAT_COLUMNS:
                home_updates[f'home_team_{col}'].append(home_stats[col])
            
            # Zbieranie statystyk gościa
            for col in STAT_COLUMNS:
                away_updates[f'away_team_{col}'].append(away_stats[col])
        
        # Aktualizacja DataFrame
        for col, values in home_updates.items():
            self.matches_df[col] = values
            
        for col, values in away_updates.items():
            self.matches_df[col] = values

    def update_team_stats(self, match) -> tuple[dict, dict]:
        """
        Kompleksowo aktualizuje statystyki drużyn na podstawie wyniku meczu.
        
        Parametry:
            match : pd.Series
                Dane meczu zawierające:
                - home_team: ID gospodarza
                - away_team: ID gościa
                - result: wynik (1=gospodarz, 0=remis, 2=gość)
                - home_team_goals: bramki gospodarza
                - away_team_goals: bramki gościa
                - date: data meczu
        
        Zwraca:
            tuple[dict, dict]: Zaktualizowane statystyki (gospodarz, gość)
        """
        home_stats = next(t for t in self.team_stats if t['team_id'] == match['home_team'])
        away_stats = next(t for t in self.team_stats if t['team_id'] == match['away_team'])
        
        # Wspólna aktualizacja podstawowych statystyk
        home_stats['matches'] += 1
        away_stats['matches'] += 1
        
        # Aktualizacja zintegrowana - wyniki i bramki
        if match['result'] == 1:  # Zwycięstwo gospodarza
            self._update_combined_stats(
                home_stats, away_stats,
                home_goals=match['home_team_goals'],
                away_goals=match['away_team_goals'],
                home_result='win',
                away_result='lose'
            )
        elif match['result'] == 2:  # Zwycięstwo gościa
            self._update_combined_stats(
                home_stats, away_stats,
                home_goals=match['home_team_goals'],
                away_goals=match['away_team_goals'],
                home_result='lose',
                away_result='win'
            )
        elif match['result'] == 0:  # Remis
            self._update_combined_stats(
                home_stats, away_stats,
                home_goals=match['home_team_goals'],
                away_goals=match['away_team_goals'],
                home_result='draw',
                away_result='draw'
            )
        
        # Obliczenie statystyk pochodnych
        self.update_standard_deviations(home_stats)
        self.update_standard_deviations(away_stats)
        # Aktualizacja daty i odpoczynku
        return home_stats, away_stats

    def _update_combined_stats(self, home_stats: dict, away_stats: dict, 
                            home_goals: int, away_goals: int,
                            home_result: str, away_result: str) -> None:
        """
        Kompleksowa aktualizacja statystyk meczowych w jednej operacji.
        
        Parametry:
            home_stats: statystyki gospodarza
            away_stats: statystyki gościa
            home_goals: bramki gospodarza
            away_goals: bramki gościa
            home_result: wynik gospodarza ('win'/'lose'/'draw')
            away_result: wynik gościa ('win'/'lose'/'draw')
        """
        # Aktualizacja wyników
        if home_result == 'win':
            home_stats['home_wins'] += 1
            away_stats['away_loses'] += 1
        elif home_result == 'lose':
            home_stats['home_loses'] += 1
            away_stats['away_wins'] += 1
        else:  # remis
            home_stats['home_draws'] += 1
            away_stats['away_draws'] += 1
        
        # Aktualizacja statystyk bramkowych gospodarza (mecz domowy)
        home_stats['home_goals_scored'] += home_goals
        home_stats['home_goals_scored_sq'] += home_goals ** 2
        home_stats['home_goals_conceded'] += away_goals
        home_stats['home_goals_conceded_sq'] += away_goals ** 2
        
        # Aktualizacja statystyk bramkowych gościa (mecz wyjazdowy)
        away_stats['away_goals_scored'] += away_goals
        away_stats['away_goals_scored_sq'] += away_goals ** 2
        away_stats['away_goals_conceded'] += home_goals
        away_stats['away_goals_conceded_sq'] += home_goals ** 2

        # Uzupełnianie średnich bramek w słowniku stats
        home_matches = home_stats['home_wins'] + home_stats['home_draws'] + home_stats['home_loses']
        away_matches = away_stats['away_wins'] + away_stats['away_draws'] + away_stats['away_loses']

        # Obliczanie średnich bramek zdobytych i straconych
        home_stats['home_gs_avg'] = home_stats['home_goals_scored'] / home_matches if home_matches > 0 else 0.0
        home_stats['home_gc_avg'] = home_stats['home_goals_conceded'] / home_matches if home_matches > 0 else 0.0
        away_stats['away_gs_avg'] = away_stats['away_goals_scored'] / away_matches if away_matches > 0 else 0.0
        away_stats['away_gc_avg'] = away_stats['away_goals_conceded'] / away_matches if away_matches > 0 else 0.0

    def update_standard_deviations(self, stats):
        """
        Oblicza odchylenia standardowe dla bramek zdobytych i straconych
        w meczach domowych i wyjazdowych.
        Args:
            stats: dict - słownik zawierający statystyki drużyny
        """
        # Obliczenia dla meczów domowych - bez zbędnego sprawdzania n>0
        home_matches = stats['home_wins'] + stats['home_draws'] + stats['home_loses']
        stats['home_gs_std'] = self._calculate_single_std(
            stats['home_goals_scored'],
            stats['home_goals_scored_sq'],
            home_matches
        )
        stats['home_gc_std'] = self._calculate_single_std(
            stats['home_goals_conceded'],
            stats['home_goals_conceded_sq'],
            home_matches
        )

        # Obliczenia dla meczów wyjazdowych - analogicznie
        away_matches = stats['away_wins'] + stats['away_draws'] + stats['away_loses']
        stats['away_gs_std'] = self._calculate_single_std(
            stats['away_goals_scored'],
            stats['away_goals_scored_sq'],
            away_matches
        )
        stats['away_gc_std'] = self._calculate_single_std(
            stats['away_goals_conceded'],
            stats['away_goals_conceded_sq'],
            away_matches
        )

    def _calculate_single_std(self, total_goals, total_goals_sq, matches):
        """
        Oblicza odchylenie standardowe dla pojedynczego typu meczu (domowy/wyjazdowy).
        
        Args:
            total_goals: int - suma zdobytych bramek
            total_goals_sq: int - suma kwadratów zdobytych bramek
            matches: int - liczba rozegranych meczów
        
        Returns:
            float - odchylenie standardowe
        """
        if matches > 0:
            mean = total_goals / matches
            variance = (total_goals_sq / matches) - (mean ** 2)
            return variance ** 0.5
        return 0.0

    def print_rating(self) -> None:
        """
        Wyświetla ranking drużyn w sformatowanej tabeli, uwzględniając:
        - statystyki ogólne
        - podział na mecze domowe i wyjazdowe (zarówno GS jak i GC)
        
        Dane sortowane są malejąco według:
        1. Procentu zwycięstw ogółem
        2. Średniej zdobytych bramek
        """
        # Sortowanie drużyn według skuteczności
        sorted_stats = sorted(
            self.team_stats,
            key=lambda x: (
                (x['home_wins'] + x['away_wins']) / max(1, x['matches']),  # Całkowity win_pct
                (x['home_goals_scored'] + x['away_goals_scored']) / max(1, x['matches'])  # Całkowity gs_avg
            ),
            reverse=True
        )
        
        # Przygotowanie danych do tabeli
        table_data = []
        for idx, team in enumerate(sorted_stats, 1):
            if team['matches'] == 0:
                continue
                
            # Obliczenia statystyk ogólnych
            total_wins = team['home_wins'] + team['away_wins']
            total_draws = team['home_draws'] + team['away_draws']
            total_losses = team['home_loses'] + team['away_loses']
            total_gs = team['home_goals_scored'] + team['away_goals_scored']
            total_gc = team['home_goals_conceded'] + team['away_goals_conceded']
            
            # Formatowanie wiersza
            row = [
                f"{idx}. {team['team_name']}",
                f"{team['matches']}",
                f"{total_wins}-{total_draws}-{total_losses}",
                f"{(total_wins / team['matches']) * 100:.1f}%",
                f"{(total_draws / team['matches']) * 100:.1f}%",
                f"{total_gs / team['matches']:.2f}",
                f"{total_gc / team['matches']:.2f}",
                # Statystyki domowe
                f"{team['home_wins']}-{team['home_draws']}-{team['home_loses']}",
                f"{team['home_gs_avg']:.2f}",
                f"{team['home_gc_avg']:.2f}",  # Dodane GC domowe
                # Statystyki wyjazdowe
                f"{team['away_wins']}-{team['away_draws']}-{team['away_loses']}",
                f"{team['away_gs_avg']:.2f}",
                f"{team['away_gc_avg']:.2f}",  # Dodane GC wyjazdowe
            ]
            table_data.append(row)
        
        # Nagłówki tabeli
        headers = [
            'Team', 'M', 'W-D-L', 'Win%', 'Draw%', 'GS Avg', 'GC Avg',
            'Home W-D-L', 'Home GS AVG', 'Home GC AVG',  # Dodany Home GC
            'Away W-D-L', 'Away GS AVG', 'Away GC AVG'   # Dodany Away GC
        ]
        
        # Wyświetlenie tabeli
        print("\nTeam Ratings Summary:")
        print(tabulate(
            table_data,
            headers=headers,
            tablefmt='grid',
            stralign='left',
            numalign='right',
            floatfmt='.2f'
        ))
        
    def calculate_match_rating(self):
        pass

    def get_data(self):
        return self.matches_df, self.teams_df