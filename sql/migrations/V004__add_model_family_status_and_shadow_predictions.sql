-- Status modelu w rodzinie rynków i predykcje pretendentów poza publikacją.
ALTER TABLE `event_model_families`
  ADD COLUMN `status` varchar(16) DEFAULT NULL,
  ADD COLUMN `status_changed_at` timestamp NULL DEFAULT NULL;
CREATE TABLE `model_shadow_predictions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `match_id` int NOT NULL,
  `event_id` int NOT NULL,
  `model_id` int NOT NULL,
  `value` float NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_model_shadow_predictions` (`match_id`, `event_id`, `model_id`),
  KEY `idx_model_shadow_predictions_model` (`model_id`),
  KEY `fk_msp_event` (`event_id`),
  CONSTRAINT `fk_msp_match` FOREIGN KEY (`match_id`) REFERENCES `matches` (`id`),
  CONSTRAINT `fk_msp_event` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`),
  CONSTRAINT `fk_msp_model` FOREIGN KEY (`model_id`) REFERENCES `models` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_polish_ci;
