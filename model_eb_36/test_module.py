import db_module

def get_matches(cursor, leagues_str, seasons_str):
    matches_query = f"""
            SELECT m.id, m.home_team_goals, m.away_team_goals, m.result,
                    t1.name as home_team, t2.name as away_team, m.game_date
            FROM matches m 
            JOIN teams t1 ON m.home_team = t1.id
            JOIN teams t2 ON m.away_team = t2.id
            WHERE m.league IN ({leagues_str}) 
            AND m.season IN ({seasons_str})
            ORDER BY m.game_date DESC
        """
    cursor.execute(matches_query)
    matches = cursor.fetchall()    
    return matches

def get_odds_for_match(cursor, match_id, events_str):
    odds_query = f"""
            SELECT event, odds 
            FROM odds 
            WHERE bookmaker = 2 
            AND match_id = {match_id} 
            AND event IN ({events_str})
        """
    cursor.execute(odds_query)
    odds_data = cursor.fetchall()
    return odds_data

def generate_entry(odds_data, event_ids, match, match_id):
    # Create dictionary of odds for this match
    match_odds = {event: odds for event, odds in odds_data}
    # 3. Find lowest odds and corresponding event
    lowest_odds = float('inf')  # Start with infinity to find minimum
    lowest_odds_event = None
    
    for event_id in event_ids:
        if event_id in match_odds:
            if match_odds[event_id] < lowest_odds:
                lowest_odds = match_odds[event_id]
                lowest_odds_event = event_id
    
    # Prepare result entry
    result_entry = {
        'match_id': match_id,
        'home_team': match[4],
        'away_team': match[5],
        'game_date': match[6],
        'result': match[3],
        'home_goals': match[1],
        'away_goals': match[2],
        'has_odds': len(odds_data) > 0,
        'lowest_odds_event': lowest_odds_event,  # Changed from highest to lowest
        'lowest_odds': lowest_odds if lowest_odds != float('inf') else None,  # Changed from highest to lowest
        'odds_data': match_odds
    }

    return result_entry

def print_each_match_info(event_name, results):
    print(f"\n=== Bookmaker Accuracy Analysis for {event_name} ===")
    print("-" * 80)
    
    for entry in results:
        print(f"Match: {entry['home_team']} vs {entry['away_team']} ({entry['game_date']})")
        print(f"Result: {entry['result']} ({entry['home_goals']}:{entry['away_goals']})")
        
        if entry['has_odds']:
            print(f"Lowest odds: {entry['lowest_odds']} (Event ID: {entry['lowest_odds_event']})")
            if event_name.lower() == "winner":
                print(f"Prediction correct: {entry['prediction_correct']}")
            print("All odds:", {event: odds for event, odds in entry['odds_data'].items()})
        else:
            print("No odds data available")
        print("-" * 80)

def print_summary(event_name, total_matches_with_odds, correct_predictions):
    if event_name.lower() == "winner" and total_matches_with_odds > 0:
        accuracy = (correct_predictions / total_matches_with_odds) * 100
        print(f"\nSummary Statistics:")
        print(f"Total matches with odds: {total_matches_with_odds}")
        print(f"Correct predictions: {correct_predictions}")
        print(f"Accuracy: {accuracy:.2f}%")

def print_total_profit(results):
    total_profit = 0
    bets_placed = 0
    winning_bets = 0
    
    for entry in results:
        if entry['has_odds']:
            bets_placed += 1
            # Check if prediction was correct
            is_winner = False
            if (entry['result'] == '1' and entry['lowest_odds_event'] == 1) or \
               (entry['result'] == 'X' and entry['lowest_odds_event'] == 2) or \
               (entry['result'] == '2' and entry['lowest_odds_event'] == 3):
                # Win: add (odds - 1) as profit
                total_profit += (entry['lowest_odds'] - 1)
                winning_bets += 1
                is_winner = True
            else:
                # Loss: subtract stake (1)
                total_profit -= 1

    # Print results
    print("\n=== Betting Profit Analysis ===")
    print("-" * 80)
    print(f"Total bets placed: {bets_placed}")
    print(f"Winning bets: {winning_bets}")
    print(f"Losing bets: {bets_placed - winning_bets}")
    print(f"Hit rate: {(winning_bets/bets_placed*100):.2f}% " if bets_placed > 0 else "Hit rate: N/A")
    print(f"Total profit: {total_profit:.2f} u")
    print(f"ROI: {(total_profit/bets_placed*100):.2f}% " if bets_placed > 0 else "ROI: N/A")
    print("-" * 80)

def bookmaker_accuracy(event_name, event_ids, league_ids, season_ids):
    """
    Analyze bookmaker accuracy for given events, leagues and seasons
    
    Args:
        event_name (str): Name of the event type being analyzed
        event_ids (list): List of event IDs to check
        league_ids (list): List of league IDs to analyze
        season_ids (list): List of season IDs to analyze
    """
    # Convert lists to comma-separated strings for SQL queries
    leagues_str = ','.join(map(str, league_ids))
    seasons_str = ','.join(map(str, season_ids))
    events_str = ','.join(map(str, event_ids))
    # Connect to database
    conn = db_module.db_connect()
    cursor = conn.cursor()
    # 1. Get all matches for given leagues and seasons
    matches = get_matches(cursor, leagues_str, seasons_str)
    
    total_matches_with_odds = 0
    correct_predictions = 0
    results = []
    for match in matches:
        match_id = match[0]
        odds_data = get_odds_for_match(cursor, match_id, events_str)
        result_entry = generate_entry(odds_data, event_ids, match, match_id)
        # Add prediction accuracy check for winner events
        if event_name.lower() == "winner" and result_entry['has_odds']:
            total_matches_with_odds += 1
            is_correct = False
            if result_entry['result'] == '1' and result_entry['lowest_odds_event'] == 1:
                is_correct = True
            elif result_entry['result'] == 'X' and result_entry['lowest_odds_event'] == 2:
                is_correct = True
            elif result_entry['result'] == '2' and result_entry['lowest_odds_event'] == 3:
                is_correct = True
            if is_correct:
                correct_predictions += 1
            result_entry['prediction_correct'] = is_correct 
        results.append(result_entry)
    print_each_match_info(event_name, results)
    print_summary(event_name, total_matches_with_odds, correct_predictions) 
    print_total_profit(results)
    cursor.close()
    conn.close()
    return results


def main():
    bookmaker_accuracy("winner", [1,2,3], [2], [11])
if __name__ == '__main__':
    main()
