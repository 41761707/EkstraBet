import elo_rating
import dataprep_module
import argparse
import db_module
from datetime import datetime

def get_league_details(leagues: list):
    """Pobierz szczegóły ligi na podstawie ID (np. kraj, poziom)
    Args:
        leagues (list): Lista ID lig
    """
    conn = db_module.db_connect()
    # Tworzymy odpowiednią liczbę placeholderów
    placeholders = ','.join(['%s'] * len(leagues))
    query = f"SELECT id, country, tier, sport_id FROM leagues WHERE id in ({placeholders})"
    cursor = conn.cursor()
    cursor.execute(query, tuple(leagues))
    league_details = cursor.fetchall()
    conn.close()
    leagues_details = []
    for league in league_details:
        leagues_details.append({
            "id": league[0],
            "country": league[1],
            "tier": league[2],
            "sport_id": league[3]
        })
    return leagues_details

def get_leagues_by_country(country_id: int):
    """Pobierz ligi na podstawie ID kraju
    Args:
        country_id (int): ID kraju
    """
    conn = db_module.db_connect()
    query = "SELECT id FROM leagues WHERE country = %s"
    cursor = conn.cursor()
    cursor.execute(query, (country_id,))
    leagues = cursor.fetchall()
    conn.close()
    return [league[0] for league in leagues]

def arg_parser():
    parser = argparse.ArgumentParser(description="Funkcja do przeliczania rankingów")
    parser.add_argument("--rating", type=str, help="Rodzaj rankingu (np. 'elo, czech, gap')")
    parser.add_argument("--country", type=int, help="ID kraju")
    parser.add_argument("--date", type=str, help="Data w formacie YYYY-MM-DD")
    parser.add_argument("--csv", action="store_true", help="Czy wygenerować plik CSV")
    args = parser.parse_args()
    return args

def main():
    """Główna funkcja skryptu"""
    #1. Inicjalizacja parametrów
    args = arg_parser()
    #2. Pobierz ligi dla tego kraju
    leagues = get_leagues_by_country(args.country)
    print(leagues)
    #2. Pobierz szczegoly ligi
    leagues_details = get_league_details(leagues)
    print(leagues_details)
    #3. Pobierz mecze
    input_date = args.date if args.date else datetime.today().strftime('%Y-%m-%d') # Data w formacie YYYY-MM-DD
    dataprep = dataprep_module.DataPrep(input_date,
                                        leagues,
                                        leagues_details[0]["sport_id"],
                                        [args.country],
                                        leagues)
    matches_df, teams_df, _, _, _ = dataprep.get_data()
    print(matches_df.head())
    #4. Policz rankingi
    rating_dict = {}
    if args.rating == "elo":
        elo = elo_rating.EloRating(matches_df, 
                                   teams_df,
                                   [league["id"] for league in leagues_details if league["tier"] == 1],
                                   [league["id"] for league in leagues_details if league["tier"] == 2],
                                   initial_elo=1500,
                                   second_tier_coef=0.8)
        elo.calculate_rating()
        rating_dict = elo.get_rating()
    elif args.rating == "czech":
        pass  # TODO: Implement Czech ranking
    elif args.rating == "gap":
        pass  # TODO: Implement GAP ranking
    print(rating_dict)
    #5. Do CSV (opcjonalnie)
    if args.csv:
        import pandas as pd
        df = pd.DataFrame.from_dict(rating_dict, orient='index', columns=['rating'])
        df.to_csv(f"ratings_{args.rating}_{input_date}.csv", index_label='team_name')
        print(f"Ratings saved to ratings_{args.rating}_{input_date}.csv")

if __name__ == "__main__":
    main()