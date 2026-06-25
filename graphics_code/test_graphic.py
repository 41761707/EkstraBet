import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image
import os
import db_module
import pandas as pd
def draw_match_row(ax, y_offset, match, bar_width=0.6):
    # Pasek z prawdopodobieństwami
    probs = match['probs']
    max_prob = max([p for p in probs if p is not None])
    max_idx = probs.index(max_prob)

    base_colors = ['#A5D6A7', '#FFF59D', '#EF9A9A']  # home, draw, away (jasne)
    winner_colors = ['#1B5E20', '#FFD600', '#B71C1C']  # home, draw, away (ciemne)

    # Ustal kolory paska
    if max_idx == 0:  # Wygrywa gospodarz
        colors = [winner_colors[0], base_colors[1], base_colors[2]]
        home_color = winner_colors[0]
        away_color = 'black'
    elif max_idx == 2:  # Wygrywa gość
        colors = [base_colors[0], base_colors[1], winner_colors[2]]
        home_color = 'black'
        away_color = winner_colors[2]
    else:  # Remis
        colors = [winner_colors[1], winner_colors[1], winner_colors[1]]
        home_color = 'black'
        away_color = 'black'

    widths = [p / 100 for p in probs]
    labels = [f"{p}%" for p in probs]

    start = 0
    for width, color, label in zip(widths, colors, labels):
        rect = Rectangle((start, y_offset), width, bar_width, facecolor=color, edgecolor='black', linewidth=1.5)
        ax.add_patch(rect)
        ax.text(start + width / 2, y_offset + bar_width / 2, label, ha='center', va='center',
                fontsize=10, fontweight='bold', color='black')
        start += width

    # Nazwy drużyn z odpowiednim kolorem (kolor tylko dla zwycięzcy, przegrany czarny)
    if max_idx == 0:  # Wygrywa gospodarz
        ax.text(-0.05, y_offset + bar_width / 2, match['home_team'], ha='right', va='center',
                fontsize=10, fontweight='bold', color=home_color)
        ax.text(1.05, y_offset + bar_width / 2, match['away_team'], ha='left', va='center',
                fontsize=10, fontweight='bold', color='black')
    elif max_idx == 2:  # Wygrywa gość
        ax.text(-0.05, y_offset + bar_width / 2, match['home_team'], ha='right', va='center',
                fontsize=10, fontweight='bold', color='black')
        ax.text(1.05, y_offset + bar_width / 2, match['away_team'], ha='left', va='center',
                fontsize=10, fontweight='bold', color=away_color)
    else:  # Remis
        ax.text(-0.05, y_offset + bar_width / 2, match['home_team'], ha='right', va='center',
                fontsize=10, fontweight='bold', color='black')
        ax.text(1.05, y_offset + bar_width / 2, match['away_team'], ha='left', va='center',
                fontsize=10, fontweight='bold', color='black')

def generate_infographic(matches, output_path='match_infographic.png'):
    num_matches = len(matches)
    fig_height = max(2, 0.7 * num_matches)

    fig, ax = plt.subplots(figsize=(10, fig_height))
    ax.set_xlim(-0.2, 1.2)
    ax.set_ylim(0, num_matches)
    ax.axis('off')

    for idx, match in enumerate(matches):
        y = num_matches - idx - 1
        draw_match_row(ax, y, match)

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Infografika zapisana do pliku: {output_path}")

def main(): 
    conn = db_module.db_connect()
    query = """
    SELECT 
        m.id AS match_id,
        t1.name AS home_team,
        t2.name AS away_team,
        p1.value AS home_win_prob,
        p2.value AS draw_prob,
        p3.value AS away_win_prob
    FROM matches m
    JOIN teams t1 ON m.home_team = t1.id
    JOIN teams t2 ON m.away_team = t2.id
    JOIN predictions p1 ON p1.match_id = m.id AND p1.event_id = 1
    JOIN predictions p2 ON p2.match_id = m.id AND p2.event_id = 2
    JOIN predictions p3 ON p3.match_id = m.id AND p3.event_id = 3
    WHERE m.league = 1 and m.season = 12 and m.game_date >= '2025-08-22'
    ORDER BY m.game_date"""
    matches_df = pd.read_sql(query, conn)
    conn.close()
    if matches_df.empty:
        print("Brak meczów w bazie danych dla podanej ligi i sezonu.")
        return
    matches = []
    for _, row in matches_df.iterrows():
        match = {
            'home_team': row['home_team'],
            'away_team': row['away_team'],
            'probs': [round(row['home_win_prob'] * 100, 2), round(row['draw_prob'] * 100, 2), round(row['away_win_prob'] * 100, 2)]
        }
        matches.append(match)
    matches.sort(key=lambda m: m['probs'][0], reverse=True)
    generate_infographic(matches)
    
if __name__ == "__main__":
    main()
