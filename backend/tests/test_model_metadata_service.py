"""Unit tests for model metadata service."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.services.model_metadata_service import (
    get_model_details,
    get_sport_market_families)


class TestModelMetadataService(unittest.TestCase):
    """Tests for model metadata aggregation."""

    @patch(
        "backend.services.model_metadata_service.model_metadata_repository"
        ".fetch_model_by_id",
        return_value=pd.DataFrame())
    def test_get_model_details_returns_none_for_missing_model(
        self,
        _mock_fetch: unittest.mock.MagicMock) -> None:
        self.assertIsNone(get_model_details(999999))

    @patch(
        "backend.services.model_metadata_service.model_metadata_repository"
        ".fetch_model_supported_events")
    @patch(
        "backend.services.model_metadata_service.model_metadata_repository"
        ".fetch_model_event_families")
    @patch(
        "backend.services.model_metadata_service.model_metadata_repository"
        ".fetch_model_by_id")
    def test_get_model_details_aggregates_families_and_events(
        self,
        mock_fetch_model: unittest.mock.MagicMock,
        mock_fetch_families: unittest.mock.MagicMock,
        mock_fetch_events: unittest.mock.MagicMock) -> None:
        mock_fetch_model.return_value = pd.DataFrame([{
            "id": 3,
            "name": "Model A",
            "active": 1,
            "sport_id": 1,
            "sport_name": "Football",
        }])
        mock_fetch_families.return_value = pd.DataFrame([{
            "id": 2,
            "sport_id": 1,
            "name": "REZULTAT",
        }])
        mock_fetch_events.return_value = pd.DataFrame([{
            "id": 5,
            "name": "1",
            "family_id": 2,
            "family_name": "REZULTAT",
        }])
        details = get_model_details(3)
        assert details is not None
        self.assertEqual(details["name"], "Model A")
        self.assertEqual(len(details["event_families"]), 1)
        self.assertEqual(details["total_events"], 1)

    @patch(
        "backend.services.model_metadata_service.model_metadata_repository"
        ".fetch_sport_family_events")
    def test_get_sport_market_families_groups_events(
        self,
        mock_fetch: unittest.mock.MagicMock) -> None:
        mock_fetch.return_value = pd.DataFrame([
            {
                "family_id": 7,
                "family_name": "HOCKEY_ML",
                "description": "Zwycięzca",
                "event_id": 234,
                "event_name": "Gospodarz"
            },
            {
                "family_id": 7,
                "family_name": "HOCKEY_ML",
                "description": "Zwycięzca",
                "event_id": 235,
                "event_name": "Gość"
            }
        ])
        families = get_sport_market_families(2)
        self.assertEqual(len(families), 1)
        self.assertEqual(families[0]["name"], "HOCKEY_ML")
        self.assertEqual(
            [event["event_id"] for event in families[0]["events"]],
            [234, 235])


if __name__ == "__main__":
    unittest.main()
