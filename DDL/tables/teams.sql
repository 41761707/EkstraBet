CREATE TABLE `teams` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'id of a team',
  `country` int DEFAULT NULL COMMENT 'id of  team''s country',
  `name` varchar(50) COLLATE utf8mb3_polish_ci DEFAULT NULL COMMENT 'Name of a team',
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_UNIQUE` (`id`),
  KEY `CountryFK3_idx` (`country`),
  CONSTRAINT `COUNTRY_FK3` FOREIGN KEY (`id`) REFERENCES `countries` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=138 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_polish_ci COMMENT='Table contains all teams considered in tests'