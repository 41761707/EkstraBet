import db_module

class TestModule:

    def __init__(self, matches_predictions, analized_event, conn, stake = 1):
        self.matches_predictions = matches_predictions
        self.analized_event = analized_event #winner, btts, goals, exact
        self.stake = stake #najczesciej pewnie w unitach, wiec domyslnie 1
        self.conn = conn

    def calculate_predictions_profit(self):
        """
        Oblicza sumaryczny profit na podstawie predykcji, uwzględniając najwyższy dostępny kurs.
        """
        cursor = self.conn.cursor()
        total_profit = 0

        # Mapowanie wyniku meczu na indeks w event_ids
        result_to_index= {'X': 0, '1': 1, '2': 2}

        for pred in self.matches_predictions:
            match_id = pred['match_id']
            event_ids = pred['event_id']
            is_final = pred['is_final']

            if self.analized_event == 'winner':
                # Pobierz rzeczywisty wynik meczu
                cursor.execute("SELECT result FROM matches WHERE id = %s", (match_id,))
                result = cursor.fetchone()
                if not result:
                    print(f"Brak wyniku dla meczu {match_id}!")
                    continue

                match_result = result[0]
                if match_result not in result_to_index:
                    print(f"Nieznany wynik '{match_result}' dla meczu {match_id}!")
                    continue

                event_id = event_ids[result_to_index[match_result]]

                # Pobierz wszystkie kursy dla danego zdarzenia
                cursor.execute(
                    "SELECT bookmaker, odds FROM odds WHERE match_id = %s AND event = %s ORDER BY odds DESC", 
                    (match_id, event_id))
                odds_records = cursor.fetchall()

                if not odds_records:
                    print(f"Brak kursów dla meczu {match_id} i zdarzenia {event_id}!")
                    continue

                # Znajdź najwyższy kurs i odpowiadającego mu bukmachera
                _, best_odds = odds_records[0]  # Bukmacher zachowany na przyszłość!
                total_profit = total_profit - self.stake  # Na początku odejmujemy stawkę (sam fakt postawienia zakładu)
                if is_final[result_to_index[match_result]]:
                    total_profit = total_profit + best_odds

        print(f"Sumaryczny profit dla podanych spotkań: {round(total_profit, 2)}")

        cursor.close()
        return total_profit


    
