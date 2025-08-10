import db_module
import traceback

def delete_match_by_ids(id_list):
    """
    Usuwa mecze oraz powiązane rekordy z tabel: matches, predictions, odds, bets, final_predictions.
    Args:
        id_list (list): Lista identyfikatorów meczów do usunięcia.
    Returns:
        None
    """
    if not id_list:
        print("Brak przekazanych ID do usunięcia.")
        return
    try:
        conn = db_module.db_connect()
        cursor = conn.cursor()
        # Przygotowanie placeholderów dla zapytań SQL
        placeholders = ','.join(['%s'] * len(id_list))
        # Usuwanie z tabeli final_predictions
        cursor.execute(f"""
            DELETE FROM final_predictions WHERE predictions_id IN (
                SELECT id FROM predictions WHERE match_id IN ({placeholders})
            )
        """, tuple(id_list))
        # Usuwanie z tabeli bets
        cursor.execute(f"DELETE FROM bets WHERE match_id IN ({placeholders})", tuple(id_list))
        # Usuwanie z tabeli odds
        cursor.execute(f"DELETE FROM odds WHERE match_id IN ({placeholders})", tuple(id_list))
        # Usuwanie z tabeli predictions
        cursor.execute(f"DELETE FROM predictions WHERE match_id IN ({placeholders})", tuple(id_list))
        # Usuwanie z tabeli matches
        cursor.execute(f"DELETE FROM matches WHERE id IN ({placeholders})", tuple(id_list))
        conn.commit()
        print(f"Usunięto mecze i powiązane rekordy dla ID: {', '.join(str(i) for i in id_list)}")
    except Exception as e:
        print("Błąd podczas usuwania meczów i powiązanych rekordów:")
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    """
    Funkcja główna do usuwania meczów na podstawie przekazanych ID.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Usuwa mecze i powiązane rekordy na podstawie listy ID.")
    parser.add_argument('--ids', type=str, required=True, help='ID meczów oddzielone przecinkami, np. "123,456,789"')
    args = parser.parse_args()
    # Parsowanie stringa na listę intów z obsługą błędów
    id_list = []
    invalid_ids = []
    for x in args.ids.split(','):
        s = x.strip()
        try:
            id_list.append(int(s))
        except ValueError:
            if s:  # ignore empty strings
                invalid_ids.append(s)
    if invalid_ids:
        print(f"Nieprawidłowe ID meczów: {', '.join(invalid_ids)}. Podaj tylko liczby całkowite.")
    if not id_list:
        print("Nie podano poprawnych ID meczów do usunięcia.")
        return
    delete_match_by_ids(id_list)


if __name__ == "__main__":
    main()
