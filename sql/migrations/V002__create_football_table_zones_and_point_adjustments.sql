-- Strefy miejsc i kary punktowe.
CREATE TABLE `football_table_zones` (
  `id` int NOT NULL AUTO_INCREMENT,
  `league_id` int NOT NULL,
  `season_id` int NOT NULL,
  `position_from` int NOT NULL,
  `position_to` int NOT NULL,
  `zone_kind` varchar(32) NOT NULL,
  `band` varchar(16) NOT NULL,
  `stage` varchar(32) DEFAULT NULL,
  `target_league_id` int DEFAULT NULL,
  `sort_order` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_football_table_zones_position` (`league_id`, `season_id`, `position_from`),
  KEY `idx_football_table_zones_league_season` (`league_id`, `season_id`),
  KEY `fk_ftz_season` (`season_id`),
  KEY `fk_ftz_target_league` (`target_league_id`),
  CONSTRAINT `fk_ftz_league` FOREIGN KEY (`league_id`) REFERENCES `leagues` (`id`),
  CONSTRAINT `fk_ftz_season` FOREIGN KEY (`season_id`) REFERENCES `seasons` (`id`),
  CONSTRAINT `fk_ftz_target_league` FOREIGN KEY (`target_league_id`) REFERENCES `leagues` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_polish_ci;
CREATE TABLE `football_point_adjustments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `league_id` int NOT NULL,
  `season_id` int NOT NULL,
  `team_id` int NOT NULL,
  `points_delta` int NOT NULL,
  `reason` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_football_point_adjustments_league_season` (`league_id`, `season_id`),
  KEY `fk_fpa_season` (`season_id`),
  KEY `fk_fpa_team` (`team_id`),
  CONSTRAINT `fk_fpa_league` FOREIGN KEY (`league_id`) REFERENCES `leagues` (`id`),
  CONSTRAINT `fk_fpa_season` FOREIGN KEY (`season_id`) REFERENCES `seasons` (`id`),
  CONSTRAINT `fk_fpa_team` FOREIGN KEY (`team_id`) REFERENCES `teams` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_polish_ci;
