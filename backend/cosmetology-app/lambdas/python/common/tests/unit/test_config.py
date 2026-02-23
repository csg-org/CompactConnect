"""
Unit tests for _Config, including active_compact_jurisdictions cache.

Tests mock the compact configuration client (DynamoDB/table) responses.
"""

import os
from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestConfigActiveCompactJurisdictions(TestCase):
    """Tests for _Config.active_compact_jurisdictions cached_property."""

    def test_returns_dict_of_compact_to_list_of_jurisdiction_dicts(self):
        """active_compact_jurisdictions returns dict[str, list[dict]]."""
        mock_jurisdictions = [
            {'postalAbbreviation': 'al', 'jurisdictionName': 'Alabama', 'compact': 'cosm'},
            {'postalAbbreviation': 'ky', 'jurisdictionName': 'Kentucky', 'compact': 'cosm'},
        ]
        with patch.dict(os.environ, {'COMPACTS': '["cosm"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_active_compact_jurisdictions.return_value = mock_jurisdictions
            config.compact_configuration_client = mock_client

            result = config.active_compact_jurisdictions

            self.assertIsInstance(result, dict)
            self.assertIn('cosm', result)
            self.assertIsInstance(result['cosm'], list)
            self.assertEqual(result['cosm'], mock_jurisdictions)

    def test_calls_get_active_compact_jurisdictions_for_each_compact(self):
        """For each compact in compacts, calls compact_configuration_client.get_active_compact_jurisdictions(compact)."""
        with patch.dict(os.environ, {'COMPACTS': '["cosm", "other"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_active_compact_jurisdictions.side_effect = [
                [{'postalAbbreviation': 'al', 'compact': 'cosm'}],
                [{'postalAbbreviation': 'tx', 'compact': 'other'}],
            ]
            config.compact_configuration_client = mock_client

            result = config.active_compact_jurisdictions

            self.assertEqual(mock_client.get_active_compact_jurisdictions.call_count, 2)
            mock_client.get_active_compact_jurisdictions.assert_any_call('cosm')
            mock_client.get_active_compact_jurisdictions.assert_any_call('other')
            self.assertEqual(result['cosm'], [{'postalAbbreviation': 'al', 'compact': 'cosm'}])
            self.assertEqual(result['other'], [{'postalAbbreviation': 'tx', 'compact': 'other'}])

    def test_on_exception_logs_warning_and_uses_empty_list_for_that_compact(self):
        """On exception from get_active_compact_jurisdictions, log warning and use empty list for that compact."""
        with patch.dict(os.environ, {'COMPACTS': '["cosm", "failing"]'}, clear=False):
            with patch('cc_common.config.logger') as mock_logger:
                from cc_common.config import _Config

                config = _Config()
                mock_client = MagicMock()
                config.compact_configuration_client = mock_client
                mock_client.get_active_compact_jurisdictions.side_effect = [
                    [{'postalAbbreviation': 'al', 'compact': 'cosm'}],
                    Exception('Table not found'),
                ]

                result = config.active_compact_jurisdictions

                self.assertEqual(result['cosm'], [{'postalAbbreviation': 'al', 'compact': 'cosm'}])
                self.assertEqual(result['failing'], [])
                mock_logger.warning.assert_called_once()
                self.assertIn('failing', str(mock_logger.warning.call_args) or 'failing')

    def test_value_is_cached_after_first_access(self):
        """active_compact_jurisdictions is cached; second access does not call client again."""
        with patch.dict(os.environ, {'COMPACTS': '["cosm"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_active_compact_jurisdictions.return_value = [
                {'postalAbbreviation': 'al', 'compact': 'cosm'},
            ]
            config.compact_configuration_client = mock_client

            first = config.active_compact_jurisdictions
            second = config.active_compact_jurisdictions

            self.assertEqual(first, second)
            mock_client.get_active_compact_jurisdictions.assert_called_once_with('cosm')
