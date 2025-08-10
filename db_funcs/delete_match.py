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
        # Zamiana listy na string do zapytania SQL
        ids_str = ','.join(str(i) for i in id_list)
        # Usuwanie z tabeli final_predictions
        cursor.execute(f"""
            DELETE FROM final_predictions WHERE predictions_id IN (
                SELECT id FROM predictions WHERE match_id IN ({ids_str})
            )
        """)
        # Usuwanie z tabeli bets
        cursor.execute(f"DELETE FROM bets WHERE match_id IN ({ids_str})")
        # Usuwanie z tabeli odds
        cursor.execute(f"DELETE FROM odds WHERE match_id IN ({ids_str})")
        # Usuwanie z tabeli predictions
        cursor.execute(f"DELETE FROM predictions WHERE match_id IN ({ids_str})")
        # Usuwanie z tabeli matches
        cursor.execute(f"DELETE FROM matches WHERE id IN ({ids_str})")
        conn.commit()
        print(f"Usunięto mecze i powiązane rekordy dla ID: {ids_str}")
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
    # Parsowanie stringa na listę intów
    id_list = [int(x.strip()) for x in args.ids.split(',') if x.strip().isdigit()]
    if not id_list:
        print("Nie podano poprawnych ID meczów do usunięcia.")
        return
    delete_match_by_ids(id_list)


if __name__ == "__main__":
    main()
