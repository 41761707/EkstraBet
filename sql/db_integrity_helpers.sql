-- =============================================================================
-- Weryfikacja integralności danych dla wskazanej ligi i sezonu
-- =============================================================================
-- Użycie:
--   1. Ustaw parametry poniżej (ID ligi i ID sezonu).
--   2. Uruchom wybrane zapytanie (każde jest niezależne).
--
-- Każde zapytanie zwraca listę konkretnych meczów z brakami — nie liczników.
--
-- Odniesienia do dokumentacji:
--   - matches.result: '0' lub NULL = brak wyniku
--   - leagues.has_player_stats: 1 = liga powinna mieć statystyki zawodników
--   - odds: co najmniej jeden wiersz na mecz oznacza pobrane kursy
--   - statystyki zawodników wg sport_id:
--       1 (piłka nożna)  -> football_player_stats
--       2 (hokej)        -> hockey_match_player_stats
--       3 (koszykówka)   -> basketball_match_player_stats
-- =============================================================================

SET @league_id = 1;   -- ID ligi (leagues.id)
SET @season_id = 1;   -- ID sezonu (seasons.id)


-- -----------------------------------------------------------------------------
-- 1. Mecze rozegrane przed dzisiejszą datą bez uzupełnionego wyniku (result)
-- -----------------------------------------------------------------------------
-- Sprawdzane są mecze z game_date < CURDATE().
-- Brak wyniku: result IS NULL lub result = '0'.
-- -----------------------------------------------------------------------------
SELECT
    m.id AS match_id,
    m.game_date,
    m.round,
    s.years AS season,
    l.name AS league_name,
    ht.name AS home_team,
    at.name AS away_team,
    m.result,
    'brak_wyniku' AS integrity_issue
FROM matches m
JOIN leagues l ON l.id = m.league
JOIN seasons s ON s.id = m.season
JOIN teams ht ON ht.id = m.home_team
JOIN teams at ON at.id = m.away_team
WHERE m.league = @league_id
  AND m.season = @season_id
  AND DATE(m.game_date) < CURDATE()
  AND (m.result IS NULL OR m.result = '0')
ORDER BY m.game_date, m.id;


-- -----------------------------------------------------------------------------
-- 2. Mecze bez pobranych kursów
-- -----------------------------------------------------------------------------
-- Sprawdzane są wszystkie mecze ligi/sezonu (także przyszłe).
-- Mecz uznajemy za mający kursy, gdy istnieje co najmniej jeden wiersz w odds.
-- -----------------------------------------------------------------------------
SELECT
    m.id AS match_id,
    m.game_date,
    m.round,
    s.years AS season,
    l.name AS league_name,
    ht.name AS home_team,
    at.name AS away_team,
    'brak_kursow' AS integrity_issue
FROM matches m
JOIN leagues l ON l.id = m.league
JOIN seasons s ON s.id = m.season
JOIN teams ht ON ht.id = m.home_team
JOIN teams at ON at.id = m.away_team
WHERE m.league = @league_id
  AND m.season = @season_id
  AND NOT EXISTS (
      SELECT 1
      FROM odds o
      WHERE o.match_id = m.id
  )
ORDER BY m.game_date, m.id;


-- -----------------------------------------------------------------------------
-- 3. Mecze z lig ze statystykami zawodników bez pobranych statystyk
-- -----------------------------------------------------------------------------
-- Dotyczy lig z leagues.has_player_stats = 1.
-- Sprawdzane są mecze rozegrane przed dzisiejszą datą (statystyki meczowe
-- nie są oczekiwane dla przyszłych spotkań).
-- -----------------------------------------------------------------------------
SELECT
    m.id AS match_id,
    m.game_date,
    m.round,
    s.years AS season,
    l.name AS league_name,
    sp.name AS sport_name,
    m.sport_id,
    ht.name AS home_team,
    at.name AS away_team,
    CASE m.sport_id
        WHEN 1 THEN 'football_player_stats'
        WHEN 2 THEN 'hockey_match_player_stats'
        WHEN 3 THEN 'basketball_match_player_stats'
        ELSE 'nieznana_tabela_statystyk'
    END AS expected_stats_table,
    'brak_statystyk_zawodnikow' AS integrity_issue
FROM matches m
JOIN leagues l ON l.id = m.league
JOIN seasons s ON s.id = m.season
JOIN sports sp ON sp.id = m.sport_id
JOIN teams ht ON ht.id = m.home_team
JOIN teams at ON at.id = m.away_team
WHERE m.league = @league_id
  AND m.season = @season_id
  AND l.has_player_stats = 1
  AND DATE(m.game_date) < CURDATE()
  AND (
      (m.sport_id = 1 AND NOT EXISTS (
          SELECT 1
          FROM football_player_stats fps
          WHERE fps.match_id = m.id
      ))
      OR (m.sport_id = 2 AND NOT EXISTS (
          SELECT 1
          FROM hockey_match_player_stats hps
          WHERE hps.match_id = m.id
      ))
      OR (m.sport_id = 3 AND NOT EXISTS (
          SELECT 1
          FROM basketball_match_player_stats bps
          WHERE bps.match_id = m.id
      ))
      OR m.sport_id NOT IN (1, 2, 3)
  )
ORDER BY m.game_date, m.id;
