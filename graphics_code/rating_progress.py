import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import glob
import argparse

def plot_rating_progress(top_teams=None, csv_path=None):
    """
    Funkcja wczytująca wszystkie pliki ratings_elo_*.csv z określonego folderu
    i przedstawiająca graficznie progres ratingów ELO każdej drużyny w czasie.
    
    Args:
        top_teams (int, optional): Liczba najlepszych drużyn do wyświetlenia. 
                                 Jeśli None, wyświetla wszystkie drużyny.
        csv_path (str, optional): Ścieżka do folderu z plikami CSV.
                                Jeśli None, używa obecnego folderu.
    
    Funkcja:
    1. Wczytuje wszystkie pliki z określonego folderu zaczynające się od 'ratings_elo'
    2. Tworzy listę słowników z danymi drużyn i ich ratingami w poszczególnych datach
    3. Przedstawia graficznie progres każdej drużyny - na osi X daty, na osi Y ratingi
    4. Każda drużyna ma inny kolor, kolejność determinowana przez najnowszy rating
    """
    if csv_path is not None:
        target_dir = os.path.abspath(csv_path)
        if not os.path.exists(target_dir):
            print(f"Błąd: Podana ścieżka nie istnieje: {target_dir}")
            return
        if not os.path.isdir(target_dir):
            print(f"Błąd: Podana ścieżka nie jest folderem: {target_dir}")
            return
    else:
        target_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Szukanie plików CSV w folderze: {target_dir}")
    # Znalezienie wszystkich plików ratings_elo_*.csv
    pattern = os.path.join(target_dir, "ratings_elo_*.csv")
    rating_files = glob.glob(pattern)
    if not rating_files:
        print("Nie znaleziono plików z ratingami!")
        return
    print(f"Znaleziono {len(rating_files)} plików z ratingami")
    all_ratings_data = []
    for file_path in rating_files:
        # Wyciągnięcie daty z nazwy pliku (ratings_elo_2025-07-13.csv -> 2025-07-13)
        filename = os.path.basename(file_path)
        date_str = filename.replace("ratings_elo_", "").replace(".csv", "")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            df = pd.read_csv(file_path)
            # Dodanie danych do listy słowników
            for _, row in df.iterrows():
                rating_data = {
                    'team_name': row['team_name'],
                    'rating': row['rating'],
                    'date': date_obj,
                    'date_str': date_str
                }
                all_ratings_data.append(rating_data)
            print(f"Wczytano dane z pliku: {filename} (data: {date_str})")
        except ValueError as e:
            print(f"Błąd parsowania daty z pliku {filename}: {e}")
            continue
    if not all_ratings_data:
        print("Nie udało się wczytać żadnych danych!")
        return
    df_all = pd.DataFrame(all_ratings_data)
    df_all = df_all.sort_values('date')
    unique_dates = sorted(df_all['date'].unique())
    unique_teams = df_all['team_name'].unique()
    team_order = []
    newest_date = max(unique_dates)
    newest_ratings = df_all[df_all['date'] == newest_date].sort_values('rating', ascending=False)
    team_order = newest_ratings['team_name'].tolist()
    for team in unique_teams:
        if team not in team_order:
            team_order.append(team)
    # Ograniczenie do najlepszych drużyn jeśli określono parametr top_teams
    if top_teams is not None and top_teams > 0:
        team_order = team_order[:top_teams]
        print(f"Wyświetlanie {len(team_order)} najlepszych drużyn z {len(unique_teams)} dostępnych")
    print(f"Kolejność drużyn determinowana przez najnowszy rating ({newest_date.strftime('%Y-%m-%d')}):")
    for i, team in enumerate(team_order[:10]):  # Pokaz pierwszych 10
        newest_rating = newest_ratings[newest_ratings['team_name'] == team]
        if not newest_rating.empty:
            print(f"{i+1}. {team}: {newest_rating.iloc[0]['rating']:.2f}")
    # Tworzenie wykresu
    plt.figure(figsize=(15, 10))
    colors = plt.cm.tab20(range(len(team_order)))  # Użycie palety kolorów tab20
    team_labels = []  # Lista do przechowywania pozycji etykiet
    for i, team in enumerate(team_order):
        team_data = df_all[df_all['team_name'] == team].sort_values('date')
        if len(team_data) > 0:
            dates = team_data['date'].tolist()
            ratings = team_data['rating'].tolist()
            color = colors[i % len(colors)]
            legend_label = f"{i+1}. {team}"
            plt.plot(dates, ratings, 
                    color=color, 
                    marker='o', 
                    linewidth=2, 
                    markersize=4,
                    label=legend_label)
            if len(dates) > 0:
                last_date = dates[-1]
                last_rating = ratings[-1]
                team_labels.append((last_date, last_rating, team, color, i+1))
    # Konfiguracja wykresu
    title_suffix = f" (Top {len(team_order)})" if top_teams is not None else ""
    plt.title(f'Progres Ratingów drużyn w czasie{title_suffix}', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Data', fontsize=12)
    plt.ylabel('Rating', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    # Dodanie etykiet z nazwami drużyn na końcu linii
    if team_labels:
        # Sortowanie etykiet według wartości ratingu (od góry do dołu)
        team_labels.sort(key=lambda x: x[1], reverse=True)
        # Rozszerzenie zakresu osi X żeby zmieścić etykiety
        ax = plt.gca()
        xlim = ax.get_xlim()
        x_range = xlim[1] - xlim[0]
        ax.set_xlim(xlim[0], xlim[1] + x_range * 0.15)  # Dodanie 15% miejsca z prawej strony
        # Dodanie etykiet z nazwami drużyn
        for last_date, last_rating, team_name, color, team_rank in team_labels:
            plt.text(last_date, last_rating, f' {team_rank}. {team_name}', 
                    fontsize=10,
                    color=color,
                    verticalalignment='center',
                    fontweight='bold')
    # Legenda (opcjonalnie można ją wyłączyć jeśli jest za dużo drużyn)
    if len(team_order) <= 21: 
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    else:
        print(f"Za dużo drużyn ({len(team_order)}) do wyświetlenia legendy - używam etykiet na wykresie")
    plt.tight_layout()
    print(f"\nStatystyki:")
    print(f"Liczba drużyn: {len(team_order)}")
    print(f"Liczba dat: {len(unique_dates)}")
    print(f"Zakres dat: {min(unique_dates).strftime('%Y-%m-%d')} - {max(unique_dates).strftime('%Y-%m-%d')}")
    # Najwyższe i najniższe ratingi
    max_rating = df_all.loc[df_all['rating'].idxmax()]
    min_rating = df_all.loc[df_all['rating'].idxmin()]
    print(f"Najwyższy rating: {max_rating['team_name']} - {max_rating['rating']:.2f} ({max_rating['date_str']})")
    print(f"Najniższy rating: {min_rating['team_name']} - {min_rating['rating']:.2f} ({min_rating['date_str']})")
    # Obliczenie największych przyrostów i strat punktowych w całym okresie
    max_gain = {'team': None, 'gain': 0, 'from_date': None, 'to_date': None, 'from_rating': 0, 'to_rating': 0}
    max_loss = {'team': None, 'loss': 0, 'from_date': None, 'to_date': None, 'from_rating': 0, 'to_rating': 0}
    # Sprawdzenie zmian dla każdej drużyny w całym okresie
    for team in unique_teams:
        team_data = df_all[df_all['team_name'] == team].sort_values('date')
        if len(team_data) < 2:  # Drużyna musi mieć przynajmniej 2 pomiary
            continue
        # Znajdź najniższy i najwyższy rating dla danej drużyny
        min_rating_row = team_data.loc[team_data['rating'].idxmin()]
        max_rating_row = team_data.loc[team_data['rating'].idxmax()]
        min_date = min_rating_row['date']
        max_date = max_rating_row['date']       
        # Oblicz różnicę między skrajnymi wartościami
        rating_difference = max_rating_row['rating'] - min_rating_row['rating']
        
        # Jeśli minimum było przed maksimum chronologicznie - to przyrost
        if min_date < max_date:
            if rating_difference > max_gain['gain']:
                max_gain = {
                    'team': team,
                    'gain': rating_difference,
                    'from_date': min_rating_row['date_str'],
                    'to_date': max_rating_row['date_str'],
                    'from_rating': min_rating_row['rating'],
                    'to_rating': max_rating_row['rating']
                }
        # Jeśli maksimum było przed minimum chronologicznie - to strata
        elif max_date < min_date:
            loss_value = -(rating_difference)  # Strata to ujemna wartość
            if loss_value < max_loss['loss']:
                max_loss = {
                    'team': team,
                    'loss': loss_value,
                    'from_date': max_rating_row['date_str'],
                    'to_date': min_rating_row['date_str'],
                    'from_rating': max_rating_row['rating'],
                    'to_rating': min_rating_row['rating']
                }
        # Jeśli daty są takie same, sprawdzamy całą trajektorię drużyny
        else:
            first_rating = team_data.iloc[0]['rating']
            last_rating = team_data.iloc[-1]['rating']
            total_change = last_rating - first_rating
            
            if total_change > max_gain['gain']:
                max_gain = {
                    'team': team,
                    'gain': total_change,
                    'from_date': team_data.iloc[0]['date_str'],
                    'to_date': team_data.iloc[-1]['date_str'],
                    'from_rating': first_rating,
                    'to_rating': last_rating
                }
            elif total_change < max_loss['loss']:
                max_loss = {
                    'team': team,
                    'loss': total_change,
                    'from_date': team_data.iloc[0]['date_str'],
                    'to_date': team_data.iloc[-1]['date_str'],
                    'from_rating': first_rating,
                    'to_rating': last_rating
                }
    if max_gain['team'] is not None:
        print(f"Największy przyrost: {max_gain['team']} - +{max_gain['gain']:.2f} punktów "
              f"({max_gain['from_rating']:.2f} → {max_gain['to_rating']:.2f}) "
              f"w okresie {max_gain['from_date']} → {max_gain['to_date']}")
    
    if max_loss['team'] is not None:
        print(f"Największa strata: {max_loss['team']} - {max_loss['loss']:.2f} punktów "
              f"({max_loss['from_rating']:.2f} → {max_loss['to_rating']:.2f}) "
              f"w okresie {max_loss['from_date']} → {max_loss['to_date']}")
    filename_suffix = f"_top{len(team_order)}" if top_teams is not None else ""
    output_path = os.path.join(target_dir, f'elo_progress_chart{filename_suffix}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Wykres zapisany jako: {output_path}")
    plt.show()
    
    return df_all

def main():
    """Główna funkcja z obsługą argumentów wiersza poleceń"""
    parser = argparse.ArgumentParser(description='Generowanie wykresu progresu ratingów drużyn')
    parser.add_argument('--top', '-t', type=int, default=None,
                       help='Liczba najlepszych drużyn do wyświetlenia (domyślnie: wszystkie)')
    parser.add_argument('--path', '-p', type=str, default=None,
                       help='Ścieżka do folderu z plikami CSV ratings_elo_*.csv (domyślnie: obecny folder)') 
    args = parser.parse_args()
    if args.top is not None and args.top <= 0:
        print("Błąd: Parametr --top musi być liczbą dodatnią!")
        return
    plot_rating_progress(top_teams=args.top, csv_path=args.path)

if __name__ == "__main__":
    main()
