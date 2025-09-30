import json
from unittest.mock import MagicMock, patch

from feature_flag_client import (
    FeatureFlagException,
    FeatureFlagRequest,
    FeatureFlagValidationException,
    StatSigFeatureFlagClient,
)
from moto import mock_aws
from statsig_python_core import StatsigOptions

from . import TstFunction

MOCK_SERVER_KEY = 'test-server-key-123'


@mock_aws
class TestStatSigClient(TstFunction):
    """Test suite for StatSig feature flag client."""

    def setUp(self):
        super().setUp()

        # Set up mock secrets manager with StatSig credentials
        secrets_client = self.create_mock_secrets_manager()
        secrets_client.create_secret(
            Name='compact-connect/env/test/statsig/credentials', SecretString=json.dumps({'serverKey': MOCK_SERVER_KEY})
        )

    def create_mock_secrets_manager(self):
        """Create a mock secrets manager client"""
        import boto3

        return boto3.client('secretsmanager', region_name='us-east-1')

    def _setup_mock_statsig(self, mock_statsig, mock_flag_enabled_return: bool = True):
        # Create a mock client instance
        mock_client = MagicMock()
        mock_client.initialize.return_value = MagicMock()
        mock_client.check_gate.return_value = mock_flag_enabled_return
        mock_client.shutdown.return_value = MagicMock()

        # Make the Statsig constructor return our mock client
        mock_statsig.return_value = mock_client

        return mock_client

    def test_client_initialization_missing_secret(self):
        """Test that client initialization fails when secret is missing"""
        with self.assertRaises(FeatureFlagException) as context:
            StatSigFeatureFlagClient(environment='nonexistent')

        self.assertIn(
            "Failed to retrieve secret 'compact-connect/env/nonexistent/statsig/credentials'", str(context.exception)
        )

    @patch('feature_flag_client.Statsig')
    def test_validate_request_success(self, mock_statsig):
        """Test request validation with valid data"""
        self._setup_mock_statsig(mock_statsig)

        client = StatSigFeatureFlagClient(environment='test')

        # Valid request data
        request_data = {
            'flagName': 'test-flag',
            'context': {'userId': 'user123', 'customAttributes': {'region': 'us-east-1'}},
        }

        # Should validate successfully
        client.validate_request(request_data)

    @patch('feature_flag_client.Statsig')
    def test_validate_request_minimal_data(self, mock_statsig):
        """Test request validation with minimal valid data"""
        self._setup_mock_statsig(mock_statsig)
        mock_statsig.initialize.return_value = MagicMock()

        client = StatSigFeatureFlagClient(environment='test')

        # Minimal valid request data
        request_data = {'flagName': 'test-flag'}

        # Should validate successfully with defaults
        validated = client.validate_request(request_data)

        self.assertEqual(validated['flagName'], 'test-flag')
        self.assertEqual(validated['context'], {})  # Default empty context

    @patch('feature_flag_client.Statsig')
    def test_validate_request_missing_flag_name(self, mock_statsig):
        """Test request validation fails when flagName is missing"""
        self._setup_mock_statsig(mock_statsig)

        client = StatSigFeatureFlagClient(environment='test')

        # Invalid request data - missing flagName
        request_data = {'context': {'userId': 'user123'}}

        with self.assertRaises(FeatureFlagValidationException):
            client.validate_request(request_data)

    @patch('feature_flag_client.Statsig')
    def test_validate_request_invalid_flag_name(self, mock_statsig):
        """Test request validation fails when flagName is empty"""
        self._setup_mock_statsig(mock_statsig)

        client = StatSigFeatureFlagClient(environment='test')

        # Invalid request data - empty flagName
        request_data = {'flagName': '', 'context': {}}

        with self.assertRaises(FeatureFlagValidationException):
            client.validate_request(request_data)

    @patch('feature_flag_client.Statsig')
    def test_check_flag_enabled(self, mock_statsig):
        """Test check_flag returns enabled=True when StatSig returns True"""
        mock_statsig_client = self._setup_mock_statsig(mock_statsig)

        client = StatSigFeatureFlagClient(environment='test')

        # Create request
        request = FeatureFlagRequest(flagName='enabled-flag', context={'userId': 'user123'})

        # Check flag
        result = client.check_flag(request)

        # Verify result
        self.assertTrue(result.enabled)
        self.assertEqual(result.flag_name, 'enabled-flag')

        # Verify StatSig was called correctly
        mock_statsig_client.check_gate.assert_called_once()
        call_args = mock_statsig_client.check_gate.call_args
        statsig_user = call_args[0][0]
        flag_name = call_args[0][1]

        self.assertEqual(statsig_user.user_id, 'user123')
        self.assertEqual(flag_name, 'enabled-flag')

    @patch('feature_flag_client.Statsig')
    def test_check_flag_disabled(self, mock_statsig):
        """Test check_flag returns enabled=False when StatSig returns False"""
        self._setup_mock_statsig(mock_statsig, mock_flag_enabled_return=False)

        client = StatSigFeatureFlagClient(environment='test')

        # Create request
        request = FeatureFlagRequest(flagName='disabled-flag', context={'userId': 'user456'})

        # Check flag
        result = client.check_flag(request)

        # Verify result
        self.assertFalse(result.enabled)
        self.assertEqual(result.flag_name, 'disabled-flag')

    @patch('feature_flag_client.Statsig')
    def test_check_flag_with_custom_attributes(self, mock_statsig):
        """Test check_flag properly handles custom attributes"""
        mock_statsig_client = self._setup_mock_statsig(mock_statsig)

        client = StatSigFeatureFlagClient(environment='test')

        # Create request with custom attributes
        request = FeatureFlagRequest(
            flagName='custom-flag',
            context={
                'userId': 'user789',
                'customAttributes': {'foo': 'bar'},
            },
        )

        # Check flag
        result = client.check_flag(request)

        # Verify result
        self.assertTrue(result.enabled)

        # Verify StatSig user was created with custom attributes
        call_args = mock_statsig_client.check_gate.call_args
        statsig_user = call_args[0][0]
        flag_name = call_args[0][1]

        self.assertEqual('user789', statsig_user.user_id)
        self.assertEqual({'foo': 'bar'}, statsig_user.custom)
        self.assertEqual('custom-flag', flag_name)

    @patch('feature_flag_client.Statsig')
    def test_check_flag_default_user(self, mock_statsig):
        """Test check_flag uses default user when no userId provided"""
        mock_statsig_client = self._setup_mock_statsig(mock_statsig)

        client = StatSigFeatureFlagClient(environment='test')

        # Create request without userId
        request = FeatureFlagRequest(flagName='default-user-flag', context={})

        # Check flag
        result = client.check_flag(request)

        # Verify result
        self.assertTrue(result.enabled)

        # Verify default user was used
        call_args = mock_statsig_client.check_gate.call_args
        statsig_user = call_args[0][0]

        self.assertEqual(statsig_user.user_id, 'default_cc_user')

    @patch('feature_flag_client.Statsig')
    def test_environment_tier_mapping(self, mock_statsig):
        """Test that different environments map to correct StatSig tiers"""
        self._setup_mock_statsig(mock_statsig)

        # Test different environments
        test_cases = [
            ('test', 'development'),
            ('beta', 'staging'),
            ('prod', 'production'),
            ('sandbox', 'development'),  # Unknown environments default to development
        ]

        for cc_env, expected_tier in test_cases:
            # Set up secret for this environment
            secrets_client = self.create_mock_secrets_manager()
            # note that the test environment secret is created as part of setup, so we don't add that here
            if cc_env != 'test':
                secrets_client.create_secret(
                    Name=f'compact-connect/env/{cc_env}/statsig/credentials',
                    SecretString=json.dumps({'serverKey': MOCK_SERVER_KEY}),
                )

            # Create client
            StatSigFeatureFlagClient(environment=cc_env)

            # Verify StatSig was called correctly
            mock_statsig.assert_called_once()
            call_args = mock_statsig.call_args
            server_key = call_args[0][0]
            options: StatsigOptions = call_args.kwargs['options']

            self.assertEqual(MOCK_SERVER_KEY, server_key)
            self.assertEqual(expected_tier, options.environment)

            mock_statsig.reset_mock()
