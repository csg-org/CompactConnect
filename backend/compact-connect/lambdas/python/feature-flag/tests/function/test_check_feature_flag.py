import json
from unittest.mock import MagicMock, patch

import boto3
from moto import mock_aws

from . import TstFunction


@mock_aws
class TestCheckFeatureFlag(TstFunction):
    """Test suite for feature flag endpoint."""

    def setUp(self):
        super().setUp()

        # Set up environment variables for testing
        import os

        os.environ['ENVIRONMENT_NAME'] = 'test'

        # Set up mock secrets manager with StatSig credentials
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        secrets_client.create_secret(
            Name='compact-connect/env/test/statsig/credentials',
            SecretString=json.dumps({'serverKey': 'test-server-key-123'}),
        )

    def tearDown(self):
        """Clean up between tests to ensure test isolation"""
        super().tearDown()
        
        # Reset the module-level feature_flag_client to force recreation in next test
        # without this the client gets cached and cannot be modified
        import sys
        if 'handlers.check_feature_flag' in sys.modules:
            del sys.modules['handlers.check_feature_flag']

    def _generate_test_api_gateway_event(self, body: dict) -> dict:
        """Generate a test API Gateway event"""
        event = self.test_data_generator.generate_test_api_event()
        event['body'] = json.dumps(body)

        return event

    def _setup_mock_statsig(self, mock_statsig, mock_flag_enabled_return: bool = True):
        # Create a mock client instance
        mock_client = MagicMock()
        mock_client.initialize.return_value = MagicMock()
        mock_client.check_gate.return_value = mock_flag_enabled_return
        mock_client.shutdown.return_value = MagicMock()

        # Make the Statsig constructor return our mock client
        mock_statsig.return_value = mock_client

        return mock_client

    @patch('feature_flag_client.Statsig')
    def test_feature_flag_enabled_returns_true(self, mock_statsig):
        """Test that when StatSig returns True, our handler returns enabled: true"""
        self._setup_mock_statsig(mock_statsig, mock_flag_enabled_return=True)
        from handlers.check_feature_flag import check_feature_flag

        # Create test event
        test_body = {
            'flagName': 'test-feature-flag',
            'context': {'userId': 'test-user-123', 'customAttributes': {'region': 'us-east-1'}},
        }
        event = self._generate_test_api_gateway_event(test_body)

        # Call the handler
        result = check_feature_flag(event, self.mock_context)

        # Verify the API Gateway response format
        self.assertEqual(result['statusCode'], 200)

        # Parse and verify the JSON body
        response_body = json.loads(result['body'])
        self.assertEqual({'enabled': True}, response_body)

    @patch('feature_flag_client.Statsig')
    def test_feature_flag_disabled_returns_false(self, mock_statsig):
        """Test that when StatSig returns False, our handler returns enabled: false"""
        # Mock StatSig to return False for flag check
        self._setup_mock_statsig(mock_statsig, mock_flag_enabled_return=False)

        from handlers.check_feature_flag import check_feature_flag

        # Create test event
        test_body = {'flagName': 'disabled-feature-flag', 'context': {'userId': 'test-user-456'}}
        event = self._generate_test_api_gateway_event(test_body)

        # Call the handler
        result = check_feature_flag(event, self.mock_context)

        # Verify the API Gateway response format
        self.assertEqual(result['statusCode'], 200)

        # Parse and verify the JSON body
        response_body = json.loads(result['body'])
        self.assertEqual({'enabled': False}, response_body)

    @patch('feature_flag_client.Statsig')
    def test_feature_flag_with_minimal_context(self, mock_statsig):
        """Test feature flag check with minimal context (no userId or customAttributes)"""
        # Mock StatSig to return True for flag check
        self._setup_mock_statsig(mock_statsig, mock_flag_enabled_return=True)

        from handlers.check_feature_flag import check_feature_flag

        # Create test event with minimal context
        test_body = {'flagName': 'minimal-test-flag', 'context': {}}
        event = self._generate_test_api_gateway_event(test_body)

        # Call the handler
        result = check_feature_flag(event, self.mock_context)

        # Verify the API Gateway response format
        self.assertEqual(result['statusCode'], 200)

        # Parse and verify the JSON body
        response_body = json.loads(result['body'])
        self.assertEqual({'enabled': True}, response_body)
