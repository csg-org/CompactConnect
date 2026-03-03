"""
Unit tests for _Config, including live_compact_jurisdictions cache.

Tests mock the compact configuration client (DynamoDB/table) responses.
"""

import os
from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestConfigLiveCompactJurisdictions(TestCase):
    """Tests for _Config.live_compact_jurisdictions cached_property."""

    def test_returns_dict_of_compact_to_list_of_jurisdiction_codes(self):
        """live_compact_jurisdictions returns dict[str, list[str]] (postal abbreviations)."""
        mock_jurisdictions = ['al', 'ky']
        with patch.dict(os.environ, {'COMPACTS': '["cosm"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_live_compact_jurisdictions.return_value = mock_jurisdictions
            config.compact_configuration_client = mock_client

            result = config.live_compact_jurisdictions

            self.assertIsInstance(result, dict)
            self.assertIn('cosm', result)
            self.assertIsInstance(result['cosm'], list)
            self.assertEqual(result['cosm'], mock_jurisdictions)

    def test_calls_get_live_compact_jurisdictions_for_each_compact(self):
        """For each compact in compacts, calls get_live_compact_jurisdictions(compact)."""
        with patch.dict(os.environ, {'COMPACTS': '["cosm", "other"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_live_compact_jurisdictions.side_effect = [
                ['al', 'oh'],
                ['tx'],
            ]
            config.compact_configuration_client = mock_client

            result = config.live_compact_jurisdictions

            self.assertEqual(mock_client.get_live_compact_jurisdictions.call_count, 2)
            mock_client.get_live_compact_jurisdictions.assert_any_call('cosm')
            mock_client.get_live_compact_jurisdictions.assert_any_call('other')
            self.assertEqual(result['cosm'], ['al', 'oh'])
            self.assertEqual(result['other'], ['tx'])

    def test_on_exception_logs_error_and_reraises(self):
        """On exception from get_live_compact_jurisdictions, log error and re-raise."""
        with patch.dict(os.environ, {'COMPACTS': '["cosm", "failing"]'}, clear=False):
            with patch('cc_common.config.logger') as mock_logger:
                from cc_common.config import _Config

                config = _Config()
                mock_client = MagicMock()
                config.compact_configuration_client = mock_client
                mock_client.get_live_compact_jurisdictions.side_effect = [
                    ['al', 'oh'],
                    Exception('Table not found'),
                ]

                with self.assertRaises(Exception) as ctx:
                    _ = config.live_compact_jurisdictions

                self.assertEqual(str(ctx.exception), 'Table not found')
                mock_logger.error.assert_called_once()
                self.assertIn('live jurisdictions', str(mock_logger.error.call_args).lower())

    def test_value_is_cached_after_first_access(self):
        """live_compact_jurisdictions is cached; second access does not call client again."""
        with patch.dict(os.environ, {'COMPACTS': '["cosm"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_live_compact_jurisdictions.return_value = ['al', 'oh']
            config.compact_configuration_client = mock_client

            first = config.live_compact_jurisdictions
            second = config.live_compact_jurisdictions

            self.assertEqual(first, second)
            mock_client.get_live_compact_jurisdictions.assert_called_once_with('cosm')
