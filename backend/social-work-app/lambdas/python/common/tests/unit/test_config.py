"""
Unit tests for _Config, including live jurisdiction cache.

Tests mock the compact configuration client (DynamoDB/table) responses.
"""

import os
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, patch

LIVE_AT = datetime.fromisoformat('2024-01-15T00:00:00+00:00')


def _live_state(postal_abbreviation: str, date_of_live: datetime | None = None) -> dict:
    state = {'postalAbbreviation': postal_abbreviation, 'isLive': True}
    if date_of_live is not None:
        state['dateOfLive'] = date_of_live
    return state


class TestConfigLiveCompactJurisdictions(TestCase):
    """Tests for the cached live-jurisdiction list and go-live timestamps."""

    def test_returns_abbreviations_and_recorded_live_dates_from_one_read(self):
        """Both caches are filled from get_live_configured_states, and a missing date is omitted."""
        with patch.dict(os.environ, {'COMPACTS': '["socw"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_live_configured_states.return_value = [
                _live_state('al', LIVE_AT),
                _live_state('oh'),
            ]
            config.compact_configuration_client = mock_client

            abbreviations = config.live_compact_jurisdictions
            dates = config.live_compact_jurisdiction_dates

            self.assertEqual(['al', 'oh'], abbreviations['socw'])
            self.assertEqual(LIVE_AT, dates['socw']['al'])
            self.assertNotIn('oh', dates['socw'])
            mock_client.get_live_configured_states.assert_called_once_with('socw')

    def test_calls_get_live_configured_states_for_each_compact(self):
        """For each compact in compacts, calls get_live_configured_states(compact)."""
        with patch.dict(os.environ, {'COMPACTS': '["socw", "other"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_live_configured_states.side_effect = [
                [_live_state('al', LIVE_AT), _live_state('oh')],
                [_live_state('tx', datetime.fromisoformat('2023-05-01T00:00:00+00:00'))],
            ]
            config.compact_configuration_client = mock_client

            abbreviations = config.live_compact_jurisdictions
            dates = config.live_compact_jurisdiction_dates

            self.assertEqual(mock_client.get_live_configured_states.call_count, 2)
            mock_client.get_live_configured_states.assert_any_call('socw')
            mock_client.get_live_configured_states.assert_any_call('other')
            self.assertEqual(abbreviations['socw'], ['al', 'oh'])
            self.assertEqual(abbreviations['other'], ['tx'])
            self.assertEqual(dates['other']['tx'], datetime.fromisoformat('2023-05-01T00:00:00+00:00'))

    def test_on_exception_logs_error_and_reraises(self):
        """On exception from get_live_configured_states, log error and re-raise."""
        with patch.dict(os.environ, {'COMPACTS': '["socw", "failing"]'}, clear=False):
            with patch('cc_common.config.logger') as mock_logger:
                from cc_common.config import _Config

                config = _Config()
                mock_client = MagicMock()
                config.compact_configuration_client = mock_client
                mock_client.get_live_configured_states.side_effect = [
                    [_live_state('al')],
                    Exception('Table not found'),
                ]

                with self.assertRaises(Exception) as ctx:
                    _ = config.live_compact_jurisdictions

                self.assertEqual(str(ctx.exception), 'Table not found')
                mock_logger.error.assert_called_once()
                self.assertIn('live jurisdictions', str(mock_logger.error.call_args).lower())

    def test_value_is_cached_after_first_access(self):
        """Reading either cache loads once; a second access does not call the client again."""
        with patch.dict(os.environ, {'COMPACTS': '["socw"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            mock_client = MagicMock()
            mock_client.get_live_configured_states.return_value = [_live_state('al', LIVE_AT)]
            config.compact_configuration_client = mock_client

            first = config.live_compact_jurisdictions
            second = config.live_compact_jurisdictions
            dates = config.live_compact_jurisdiction_dates

            self.assertEqual(first, second)
            self.assertEqual(LIVE_AT, dates['socw']['al'])
            mock_client.get_live_configured_states.assert_called_once_with('socw')

    def test_loading_dates_does_not_replace_an_existing_abbreviation_cache(self):
        """A preset jurisdiction list stays in place when go-live dates are loaded."""
        with patch.dict(os.environ, {'COMPACTS': '["socw"]'}, clear=False):
            from cc_common.config import _Config

            config = _Config()
            config.live_compact_jurisdictions = {'socw': ['ne']}
            mock_client = MagicMock()
            mock_client.get_live_configured_states.return_value = [_live_state('al', LIVE_AT)]
            config.compact_configuration_client = mock_client

            dates = config.live_compact_jurisdiction_dates

            self.assertEqual({'socw': ['ne']}, config.live_compact_jurisdictions)
            self.assertEqual(LIVE_AT, dates['socw']['al'])
            mock_client.get_live_configured_states.assert_called_once_with('socw')
