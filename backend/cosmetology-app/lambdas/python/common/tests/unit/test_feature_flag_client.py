from unittest.mock import MagicMock, patch

from cc_common.feature_flag_enum import FeatureFlagEnum

from tests import TstLambdas


class TestFeatureFlagClient(TstLambdas):
    def test_is_feature_enabled_returns_true_when_flag_enabled(self):
        """Test that is_feature_enabled returns True when the API returns enabled=true."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock successful API response with enabled=True
        mock_response = MagicMock()
        mock_response.json.return_value = {'enabled': True}

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response) as mock_post:
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG)

            # Verify the result
            self.assertTrue(result)

            # Verify the API was called correctly
            mock_post.assert_called_once_with(
                'https://api.example.com/v1/flags/test-flag/check',
                json={},
                timeout=5,
                headers={'Content-Type': 'application/json'},
            )

    def test_is_feature_enabled_returns_false_when_flag_disabled(self):
        """Test that is_feature_enabled returns False when the API returns enabled=false."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock successful API response with enabled=False
        mock_response = MagicMock()
        mock_response.json.return_value = {'enabled': False}

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG)

            # Verify the result
            self.assertFalse(result)

    def test_is_feature_enabled_with_context(self):
        """Test that is_feature_enabled correctly passes context to the API."""
        from cc_common.feature_flag_client import FeatureFlagContext, is_feature_enabled

        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {'enabled': True}

        context = FeatureFlagContext(user_id='user123', custom_attributes={'licenseType': 'lpc'})

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response) as mock_post:
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, context=context)

            # Verify the result
            self.assertTrue(result)

            # Verify the API was called with the context
            mock_post.assert_called_once_with(
                'https://api.example.com/v1/flags/test-flag/check',
                json={
                    'context': {'userId': 'user123', 'customAttributes': {'licenseType': 'lpc'}},
                },
                timeout=5,
                headers={'Content-Type': 'application/json'},
            )

    def test_is_feature_enabled_fail_closed_on_timeout(self):
        """Test that is_feature_enabled returns False (fail closed) on timeout."""
        from cc_common.feature_flag_client import is_feature_enabled

        with patch('cc_common.feature_flag_client.requests.post', side_effect=Exception('Timeout')):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=False)

            # Verify it fails closed (returns False)
            self.assertFalse(result)

    def test_is_feature_enabled_fail_open_on_timeout(self):
        """Test that is_feature_enabled returns True (fail open) on timeout."""
        from cc_common.feature_flag_client import is_feature_enabled

        with patch('cc_common.feature_flag_client.requests.post', side_effect=Exception('Timeout')):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=True)

            # Verify it fails open (returns True)
            self.assertTrue(result)

    def test_is_feature_enabled_fail_closed_on_http_error(self):
        """Test that is_feature_enabled returns False (fail closed) on HTTP error."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception('500 Server Error')

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=False)

            # Verify it fails closed (returns False)
            self.assertFalse(result)

    def test_is_feature_enabled_fail_open_on_http_error(self):
        """Test that is_feature_enabled returns True (fail open) on HTTP error."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception('500 Server Error')

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=True)

            # Verify it fails open (returns True)
            self.assertTrue(result)

    def test_is_feature_enabled_fail_closed_on_invalid_response(self):
        """Test that is_feature_enabled returns False (fail closed) when response missing 'enabled' field."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock response with missing 'enabled' field
        mock_response = MagicMock()
        mock_response.json.return_value = {'some_other_field': 'value'}
        mock_response.raise_for_status = MagicMock()

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=False)

            # Verify it fails closed (returns False)
            self.assertFalse(result)

    def test_is_feature_enabled_fail_open_on_invalid_response(self):
        """Test that is_feature_enabled returns True (fail open) when response missing 'enabled' field."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock response with missing 'enabled' field
        mock_response = MagicMock()
        mock_response.json.return_value = {'some_other_field': 'value'}
        mock_response.raise_for_status = MagicMock()

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=True)

            # Verify it fails open (returns True)
            self.assertTrue(result)

    def test_is_feature_enabled_fail_closed_on_json_parse_error(self):
        """Test that is_feature_enabled returns False (fail closed) when JSON parsing fails."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_response.raise_for_status = MagicMock()

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=False)

            # Verify it fails closed (returns False)
            self.assertFalse(result)

    def test_is_feature_enabled_fail_open_on_json_parse_error(self):
        """Test that is_feature_enabled returns True (fail open) when JSON parsing fails."""
        from cc_common.feature_flag_client import is_feature_enabled

        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError('Invalid JSON')

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response):
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, fail_default=True)

            # Verify it fails open (returns True)
            self.assertTrue(result)

    def test_feature_flag_context_with_user_id_only(self):
        """Test FeatureFlagContext to_dict with only user_id."""
        from cc_common.feature_flag_client import FeatureFlagContext

        context = FeatureFlagContext(user_id='user123')
        result = context.to_dict()

        self.assertEqual(result, {'userId': 'user123'})

    def test_feature_flag_context_with_custom_attributes_only(self):
        """Test FeatureFlagContext to_dict with only custom_attributes."""
        from cc_common.feature_flag_client import FeatureFlagContext

        context = FeatureFlagContext(custom_attributes={'licenseType': 'lpc', 'jurisdiction': 'oh'})
        result = context.to_dict()

        self.assertEqual(result, {'customAttributes': {'licenseType': 'lpc', 'jurisdiction': 'oh'}})

    def test_feature_flag_context_with_both_fields(self):
        """Test FeatureFlagContext to_dict with both user_id and custom_attributes."""
        from cc_common.feature_flag_client import FeatureFlagContext

        context = FeatureFlagContext(user_id='user456', custom_attributes={'licenseType': 'physician'})
        result = context.to_dict()

        self.assertEqual(result, {'userId': 'user456', 'customAttributes': {'licenseType': 'physician'}})

    def test_feature_flag_context_empty(self):
        """Test FeatureFlagContext to_dict with no fields set."""
        from cc_common.feature_flag_client import FeatureFlagContext

        context = FeatureFlagContext()
        result = context.to_dict()

        self.assertEqual(result, {})

    def test_is_feature_enabled_with_context_user_id_only(self):
        """Test that is_feature_enabled works with context containing only user_id."""
        from cc_common.feature_flag_client import FeatureFlagContext, is_feature_enabled

        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {'enabled': True}

        context = FeatureFlagContext(user_id='user789')

        with patch('cc_common.feature_flag_client.requests.post', return_value=mock_response) as mock_post:
            result = is_feature_enabled(FeatureFlagEnum.TEST_FLAG, context=context)

            # Verify the result
            self.assertTrue(result)

            # Verify the API was called with only userId in context
            mock_post.assert_called_once_with(
                'https://api.example.com/v1/flags/test-flag/check',
                json={'context': {'userId': 'user789'}},
                timeout=5,
                headers={'Content-Type': 'application/json'},
            )
