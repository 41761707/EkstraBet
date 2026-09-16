SET @league_id = 1;    -- 1=Ekstraklasa, 2=Premier League, 6=LaLiga
SET @season_id = 13;   -- 13 = 2026/27
-- 1) Podgląd
SELECT
    COUNT(*) AS schedule_rows,
    SUM(s.match_id IS NOT NULL) AS already_linked,
    SUM(s.match_id IS NULL AND m.id IS NOT NULL) AS will_link,
    SUM(s.match_id IS NULL AND m.id IS NOT NULL AND m.result <> '0') AS will_be_fixed_in_from_now,
    SUM(s.match_id IS NULL AND m.id IS NULL) AS still_no_match_row
FROM schedule s
LEFT JOIN matches m
  ON m.league = s.league
 AND m.season = s.season
 AND m.home_team = s.home_team
 AND m.away_team = s.away_team
 AND m.round = s.round
 AND m.round < 900
WHERE s.league = @league_id
  AND s.season = @season_id
  AND s.round < 900;
BEGIN;
UPDATE schedule s
INNER JOIN matches m
  ON m.league = s.league
 AND m.season = s.season
 AND m.home_team = s.home_team
 AND m.away_team = s.away_team
 AND m.round = s.round
SET s.match_id = m.id
WHERE s.league = @league_id
  AND s.season = @season_id
  AND s.round < 900
  AND s.match_id IS NULL;
COMMIT;
-- 2) Weryfikacja po COMMIT
SELECT
    COUNT(*) AS linked,
    SUM(m.result <> '0') AS fixed_in_from_now,
    SUM(m.result = '0' OR m.result IS NULL) AS linked_but_still_simulated
FROM schedule s
LEFT JOIN matches m ON m.id = s.match_id
WHERE s.league = @league_id
  AND s.season = @season_id
  AND s.round < 900
  AND s.match_id IS NOT NULL;
  
  
models\scripts\run_future_events.bat simulate-season --league-id @league_id --season-id @season_id --mode from_now --trials 2000 --seed 42