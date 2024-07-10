CREATE TABLE `leagues` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'League ID',
  `name` varchar(45) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT 'League''s name',
  `country` int DEFAULT NULL COMMENT 'Id of league''s country',
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_UNIQUE` (`id`),
  KEY `countryFK_idx` (`country`),
  CONSTRAINT `countryFK` FOREIGN KEY (`country`) REFERENCES `countries` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_polish_ci COMMENT='All leagues considered in model'