import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

## @package Views
# Moduł odpowiedzialny za dostarczanie najważniejszych informacji / ciekawostek
# Ma działać jak widoki w db
# Może byc istotny z persepktywy potencjalnego GUI
class Views:
    def __init__(self, matches_df, teams_df):
        self.matches_df = matches_df
        self.teams_df = teams_df

    def graph_goals(self, input):
        results = []
        all_matches = 0
        exact_correct = 0
        ou_correct = 0
        with open(input, 'r') as file:
            for line in file:
                parts = line.strip().split(';')
                if int(parts[5]) < 20:
                    continue
                results.append([parts[0], float(parts[1]), float(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])])
                ou_correct = ou_correct + int(parts[4]) + 1
                exact_correct = exact_correct + int(parts[3]) + 1
                all_matches = all_matches + int(parts[5])
        best_exacts = sorted(results, key=lambda x: x[1])
        best_ou = sorted(results, key=lambda x: x[2])

        print("Wszystkie mecze: {}".format(all_matches))
        print("Liczba poprawnie wywnioskowanych wyników: {}, {:.2f}%".format(exact_correct, exact_correct / all_matches * 100))
        print("Liczba poprawnie wywnioskowanych OU: {}, {}%".format(ou_correct,  ou_correct / all_matches * 100))
        print("Najlepsze przewidywania dokładnych wyników: ")
        for best in best_exacts[:20]:
            print('{} - {}'.format(best[0], best[1]))
        print("Najlepsze przewidywania Over/Under: ")
        for best in best_ou[:20]:
            print('{} - {}'.format(best[0], best[2]))

    def graph_winners(self, input):
        results = []
        all_matches = 0
        exact_correct = 0
        with open(input, 'r') as file:
            for line in file:
                parts = line.strip().split(';')
                if int(parts[2]) < 20:
                    continue
                results.append([parts[0], float(parts[1]), int(parts[2])])
                exact_correct += int(float(parts[1]) * int(parts[2]) + 1)
                all_matches = all_matches + int(parts[2])
        best_exacts = sorted(results, key=lambda x: x[1])

        print("Wszystkie mecze: {}".format(all_matches))
        print("Liczba poprawnie wywnioskowanych wyników: {}, {:.2f}%".format(exact_correct, exact_correct / all_matches * 100))
        print("Najlepsze przewidywania dokładnych wyników: ")
        for best in best_exacts[:20]:
            print('{} - {}'.format(best[0], best[1]))

    def league_view(self, league_id):
        pass 
    
    def season_view(self, season_id):
        pass 

    def league_season_view(self, league_id, season_id):
        pass

    def country_view(self, country_id):
        pass

def main():
    graphs = Views([], [])
    #graphs.graph_goals(sys.argv[1])
    graphs.graph_winners(sys.argv[1])

if __name__ == '__main__':
    main()

