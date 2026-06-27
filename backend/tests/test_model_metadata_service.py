"""Unit tests for model metadata service."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from backend.services.model_metadata_service import get_model_details


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


if __name__ == "__main__":
    unittest.main()
