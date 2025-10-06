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
MOCK_CONSOLE_KEY = 'test-console-key-456'

STATSIG_API_BASE_URL = 'https://statsigapi.net/console/v1'
STATSIG_API_VERSION = '20240601'


@mock_aws
class TestStatSigClient(TstFunction):
    """Test suite for StatSig feature flag client."""

    def setUp(self):
        super().setUp()

        # Set up mock secrets manager with StatSig credentials
        secrets_client = self.create_mock_secrets_manager()
        for env in ['test', 'beta', 'prod']:
            secrets_client.create_secret(
                Name=f'compact-connect/env/{env}/statsig/credentials',
                SecretString=json.dumps({'serverKey': MOCK_SERVER_KEY, 'consoleKey': MOCK_CONSOLE_KEY}),
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
                    SecretString=json.dumps({'serverKey': MOCK_SERVER_KEY, 'consoleKey': MOCK_CONSOLE_KEY}),
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

    def _create_mock_response(self, status_code: int, json_data: dict = None):
        """Create a mock requests response"""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        mock_response.text = json.dumps(json_data) if json_data else ''
        return mock_response

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_create_new_in_test_environment(self, mock_requests, mock_statsig):
        """Test creating a new flag in test environment with auto_enable=true (passPercentage=100 for dev)"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        # Mock POST request (create flag)
        created_flag = {'id': 'gate-123', 'name': 'new-test-flag', 'data': {'id': 'gate-123'}}
        mock_requests.post.return_value = self._create_mock_response(201, created_flag)

        client = StatSigFeatureFlagClient(environment='test')

        result = client.upsert_flag('new-test-flag', auto_enable=True, custom_attributes={'region': 'us-east-1'})

        # Verify result
        self.assertEqual(result['id'], 'gate-123')
        self.assertEqual(result['name'], 'new-test-flag')

        # Verify API calls
        mock_requests.get.assert_called_once()
        # Verify POST payload - test environment always gets passPercentage=100 regardless of auto_enable
        mock_requests.post.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'name': 'new-test-flag',
                'description': 'Feature gate managed by CDK for new-test-flag feature',
                'isEnabled': True,
                'rules': [
                    {
                        'name': 'test-rule',
                        'conditions': [
                            {
                                'type': 'custom_field',
                                'targetValue': ['us-east-1'],
                                'field': 'region',
                                'operator': 'any',
                            }
                        ],
                        'environments': ['development'],
                        'passPercentage': 100,  # Always 100 for test environment
                    }
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_create_new_in_test_environment_no_attributes(self, mock_requests, mock_statsig):
        """Test creating a new flag in test environment without custom attributes"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        # Mock POST request (create flag)
        created_flag = {'id': 'gate-456', 'name': 'simple-flag', 'data': {'id': 'gate-456'}}
        mock_requests.post.return_value = self._create_mock_response(201, created_flag)

        client = StatSigFeatureFlagClient(environment='test')

        result = client.upsert_flag('simple-flag')

        # Verify result
        self.assertEqual(result['id'], 'gate-456')

        # Verify API calls
        mock_requests.get.assert_called_once()
        mock_requests.post.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'name': 'simple-flag',
                'description': 'Feature gate managed by CDK for simple-flag feature',
                'isEnabled': True,
                'rules': [
                    {
                        'name': 'test-rule',
                        'conditions': [],
                        'environments': ['development'],
                        'passPercentage': 0,
                    }
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_does_not_update_existing_rule(self, mock_requests, mock_statsig):
        """Test updating an existing flag in test environment (test-rule already exists, no modifications in test)"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-789',
            'name': 'existing-flag',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [{'field': 'old_attr', 'targetValue': ['old_value']}],
                    'environments': ['development'],
                    'passPercentage': 100,
                }
            ],
        }

        # Mock GET request (flag exists with test-rule)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})
        # Mock PATCH request (update test-rule)
        mock_requests.patch.return_value = self._create_mock_response(200)

        client = StatSigFeatureFlagClient(environment='test')

        result = client.upsert_flag('existing-flag', auto_enable=False, custom_attributes={'new_attr': 'new_value'})

        # Verify result - no modification happens in test when rule already exists
        self.assertEqual(result['id'], 'gate-789')

        # Verify API calls - no PATCH since test environment doesn't modify existing rules
        self.assertEqual(1, mock_requests.get.call_count)
        mock_requests.patch.assert_not_called()

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_prod_environment_auto_enable_false_no_existing_flag(self, mock_requests, mock_statsig):
        """Test upsert in prod environment with autoEnable=False and no existing flag - creates with passPercentage=0"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        # Mock POST request (create flag with passPercentage=0)
        created_flag = {'id': 'gate-prod-disabled', 'name': 'prod-flag', 'data': {'id': 'gate-prod-disabled'}}
        mock_requests.post.return_value = self._create_mock_response(201, created_flag)

        client = StatSigFeatureFlagClient(environment='prod')

        result = client.upsert_flag('prod-flag', auto_enable=False)

        # Verify result
        self.assertEqual(result['id'], 'gate-prod-disabled')

        # Verify API calls
        mock_requests.get.assert_called_once()
        mock_requests.post.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'name': 'prod-flag',
                'description': 'Feature gate managed by CDK for prod-flag feature',
                'isEnabled': True,
                'rules': [
                    {
                        'name': 'prod-rule',
                        'conditions': [],
                        'environments': ['production'],
                        'passPercentage': 0,  # Disabled in prod when auto_enable=False
                    }
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_prod_environment_auto_enable_true_no_existing_flag(self, mock_requests, mock_statsig):
        """Test upsert in prod environment with autoEnable=True and no existing flag"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        # Mock POST request (create flag)
        created_flag = {'id': 'gate-prod', 'name': 'prod-flag', 'data': {'id': 'gate-prod'}}
        mock_requests.post.return_value = self._create_mock_response(201, created_flag)

        client = StatSigFeatureFlagClient(environment='prod')

        result = client.upsert_flag('prod-flag', auto_enable=True)

        # Verify result
        self.assertEqual(result['id'], 'gate-prod')

        # Verify API calls
        mock_requests.get.assert_called_once()
        mock_requests.post.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'name': 'prod-flag',
                'description': 'Feature gate managed by CDK for prod-flag feature',
                'isEnabled': True,
                'rules': [
                    {
                        'name': 'prod-rule',
                        'conditions': [],
                        'environments': ['production'],
                        'passPercentage': 100,
                    }
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_beta_environment_auto_enable_false_no_existing_rule_create_rule(
        self, mock_requests, mock_statsig
    ):
        """Test upsert in prod environment with autoEnable=True and no existing flag"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'existing-flag',
            'name': 'existing-flag',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [{'field': 'old_attr', 'targetValue': ['old_value']}],
                    'environments': ['development'],
                    'passPercentage': 100,
                }
            ],
        }

        # Mock GET request (flag exists with test-rule)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        mock_requests.patch.return_value = self._create_mock_response(200)

        client = StatSigFeatureFlagClient(environment='beta')

        result = client.upsert_flag('existing-flag', auto_enable=False)

        # Verify result
        self.assertEqual(result['id'], 'existing-flag')

        # Verify API calls
        mock_requests.get.assert_called_once()
        mock_requests.patch.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates/existing-flag',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'id': 'existing-flag',
                'name': 'existing-flag',
                'rules': [
                    {
                        'name': 'test-rule',
                        'conditions': [{'field': 'old_attr', 'targetValue': ['old_value']}],
                        'environments': ['development'],
                        'passPercentage': 100,
                    },
                    {
                        'name': 'beta-rule',
                        'conditions': [],
                        'environments': ['staging'],
                        'passPercentage': 0,
                    },
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_prod_environment_existing_flag_auto_enable_true(self, mock_requests, mock_statsig):
        """Test upsert in prod environment with existing flag (no prod-rule yet) and autoEnable=True - adds prod-rule"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-existing-prod',
            'name': 'existing-prod-flag',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [],
                    'environments': ['development'],
                    'passPercentage': 100,
                }
            ],
        }

        # Mock GET requests (flag exists, then return updated flag)
        mock_requests.get.side_effect = [
            self._create_mock_response(200, {'data': [existing_flag]}),  # First call to check existence
        ]

        # Mock PATCH request (add prod-rule)
        mock_requests.patch.return_value = self._create_mock_response(200)

        client = StatSigFeatureFlagClient(environment='prod')

        result = client.upsert_flag('existing-prod-flag', auto_enable=True, custom_attributes={'example': 'value'})

        # Verify result
        self.assertEqual(result['id'], 'gate-existing-prod')

        # Verify API calls - adds prod-rule to existing flag
        self.assertEqual(1, mock_requests.get.call_count)
        mock_requests.patch.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates/gate-existing-prod',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'id': 'gate-existing-prod',
                'name': 'existing-prod-flag',
                'rules': [
                    {
                        'name': 'test-rule',
                        'conditions': [],
                        'environments': ['development'],
                        'passPercentage': 100,
                    },
                    {
                        'name': 'prod-rule',
                        'conditions': [
                            {
                                'type': 'custom_field',
                                'targetValue': ['value'],
                                'field': 'example',
                                'operator': 'any',
                            }
                        ],
                        'environments': ['production'],
                        'passPercentage': 100,
                    },
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_prod_environment_existing_flag_auto_enable_false_should_not_update_flag(
        self, mock_requests, mock_statsig
    ):
        """Test upsert in prod environment with existing prod-rule and autoEnable=False - no modification"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-existing-prod-2',
            'name': 'existing-prod-flag-2',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [],
                    'environments': ['development'],
                    'passPercentage': 100,
                },
                {
                    'name': 'prod-rule',
                    'conditions': [{'field': 'old', 'targetValue': ['value']}],
                    'environments': ['production'],
                    'passPercentage': 0,
                },
            ],
        }

        # Mock GET request (flag exists with prod-rule)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        client = StatSigFeatureFlagClient(environment='prod')

        result = client.upsert_flag('existing-prod-flag-2', auto_enable=False, custom_attributes={'new': 'attr'})

        # Verify result - no modification when auto_enable=False and rule exists
        self.assertEqual(result['id'], 'gate-existing-prod-2')

        # Verify API calls - no PATCH since auto_enable=False
        self.assertEqual(mock_requests.get.call_count, 1)
        mock_requests.patch.assert_not_called()

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_api_error_handling(self, mock_requests, mock_statsig):
        """Test error handling when StatSig API returns errors"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request failure
        mock_requests.get.return_value = self._create_mock_response(500, {'error': 'Internal server error'})

        client = StatSigFeatureFlagClient(environment='test')

        with self.assertRaises(FeatureFlagException) as context:
            client.upsert_flag('error-flag')

        self.assertIn('Failed to fetch gates', str(context.exception))

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_create_api_error_raises_exception(self, mock_requests, mock_statsig):
        """Test error handling when flag creation fails"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        # Mock POST request failure
        mock_requests.post.return_value = self._create_mock_response(400, {'error': 'Bad request'})

        client = StatSigFeatureFlagClient(environment='test')

        with self.assertRaises(FeatureFlagException) as context:
            client.upsert_flag('create-error-flag')

        self.assertIn('Failed to create feature gate', str(context.exception))

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_update_api_error_raises_exception(self, mock_requests, mock_statsig):
        """Test error handling when flag update fails"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-update-error',
            'name': 'update-error-flag',
            'rules': [{'name': 'environment_toggle', 'conditions': [], 'environments': ['development']}],
        }

        # Mock GET request (flag exists)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        # Mock PATCH request failure
        mock_requests.patch.return_value = self._create_mock_response(403, {'error': 'Forbidden'})

        client = StatSigFeatureFlagClient(environment='test')

        with self.assertRaises(FeatureFlagException) as context:
            client.upsert_flag('update-error-flag', custom_attributes={'test': 'value'})

        self.assertIn('Failed to update feature gate', str(context.exception))

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_delete_flag_not_found(self, mock_requests, mock_statsig):
        """Test delete_flag when flag doesn't exist"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        client = StatSigFeatureFlagClient(environment='test')

        result = client.delete_flag('nonexistent-flag')

        # Should return None (flag doesn't exist)
        self.assertIsNone(result)

        # Should only call GET, not DELETE or PATCH
        mock_requests.get.assert_called_once()
        mock_requests.delete.assert_not_called()
        mock_requests.patch.assert_not_called()

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_delete_flag_last_rule_deletes_entire_flag(self, mock_requests, mock_statsig):
        """Test delete_flag when test-rule is the only rule - should delete entire flag"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-delete-last',
            'name': 'delete-last-flag',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [],
                    'environments': ['development'],
                    'passPercentage': 100,
                }
            ],
        }

        # Mock GET request (flag exists with only test-rule)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        # Mock DELETE request (delete entire flag)
        mock_requests.delete.return_value = self._create_mock_response(200)

        client = StatSigFeatureFlagClient(environment='test')

        result = client.delete_flag('delete-last-flag')

        # Should return True (flag fully deleted)
        self.assertTrue(result)

        # Verify API calls
        mock_requests.get.assert_called_once()
        mock_requests.delete.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates/gate-delete-last',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            timeout=30,
        )
        mock_requests.patch.assert_not_called()

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_delete_flag_multiple_rules_removes_current_rule_only(self, mock_requests, mock_statsig):
        """Test delete_flag when flag has multiple rules - should only remove test-rule"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-delete-multi',
            'name': 'delete-multi-flag',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [],
                    'environments': ['development'],
                    'passPercentage': 100,
                },
                {
                    'name': 'beta-rule',
                    'conditions': [],
                    'environments': ['staging'],
                    'passPercentage': 100,
                },
                {
                    'name': 'prod-rule',
                    'conditions': [],
                    'environments': ['production'],
                    'passPercentage': 100,
                },
            ],
        }

        # Mock GET request (flag exists with multiple rules)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        # Mock PATCH request (remove test-rule)
        mock_requests.patch.return_value = self._create_mock_response(200)

        client = StatSigFeatureFlagClient(environment='test')

        result = client.delete_flag('delete-multi-flag')

        # Should return False (rule removed, not full deletion)
        self.assertFalse(result)

        # Verify API calls
        mock_requests.get.assert_called_once()
        mock_requests.patch.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates/gate-delete-multi',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'id': 'gate-delete-multi',
                'name': 'delete-multi-flag',
                'rules': [
                    {
                        'name': 'beta-rule',
                        'conditions': [],
                        'environments': ['staging'],
                        'passPercentage': 100,
                    },
                    {
                        'name': 'prod-rule',
                        'conditions': [],
                        'environments': ['production'],
                        'passPercentage': 100,
                    },
                ],
            },
            timeout=30,
        )
        mock_requests.delete.assert_not_called()

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_delete_flag_prod_environment_last_rule(self, mock_requests, mock_statsig):
        """Test delete_flag in prod environment when prod-rule is the only rule"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-delete-prod',
            'name': 'delete-prod-flag',
            'rules': [
                {
                    'name': 'prod-rule',
                    'conditions': [],
                    'environments': ['production'],
                    'passPercentage': 100,
                }
            ],
        }

        # Mock GET request (flag exists with only prod-rule)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        # Mock DELETE request (delete entire flag)
        mock_requests.delete.return_value = self._create_mock_response(200)

        client = StatSigFeatureFlagClient(environment='prod')

        result = client.delete_flag('delete-prod-flag')

        # Should return True (flag fully deleted)
        self.assertTrue(result)

        # Verify API calls
        mock_requests.get.assert_called_once()
        mock_requests.delete.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates/gate-delete-prod',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_delete_flag_current_rule_not_present(self, mock_requests, mock_statsig):
        """Test delete_flag when current environment rule is not in the flag"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-delete-not-present',
            'name': 'delete-not-present-flag',
            'rules': [
                {
                    'name': 'beta-rule',
                    'conditions': [],
                    'environments': ['staging'],
                    'passPercentage': 100,
                },
                {
                    'name': 'prod-rule',
                    'conditions': [],
                    'environments': ['production'],
                    'passPercentage': 100,
                },
            ],
        }

        # Mock GET request (flag exists but test-rule not present)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        client = StatSigFeatureFlagClient(environment='test')

        result = client.delete_flag('delete-not-present-flag')

        # Should return False (no rule removed since it wasn't there)
        self.assertFalse(result)

        # Should not call PATCH or DELETE since rule wasn't present
        mock_requests.get.assert_called_once()
        mock_requests.patch.assert_not_called()
        mock_requests.delete.assert_not_called()

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_delete_flag_api_error_on_delete_raises_exception(self, mock_requests, mock_statsig):
        """Test delete_flag error handling when DELETE request fails"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-delete-error',
            'name': 'delete-error-flag',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [],
                    'environments': ['development'],
                    'passPercentage': 100,
                }
            ],
        }

        # Mock GET request (flag exists)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        # Mock DELETE request failure
        mock_requests.delete.return_value = self._create_mock_response(403, {'error': 'Forbidden'})

        client = StatSigFeatureFlagClient(environment='test')

        with self.assertRaises(FeatureFlagException) as context:
            client.delete_flag('delete-error-flag')

        self.assertIn('Failed to delete feature gate', str(context.exception))

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_delete_flag_api_error_on_patch_raises_exception(self, mock_requests, mock_statsig):
        """Test delete_flag error handling when PATCH request fails"""
        self._setup_mock_statsig(mock_statsig)

        existing_flag = {
            'id': 'gate-patch-error',
            'name': 'patch-error-flag',
            'rules': [
                {
                    'name': 'test-rule',
                    'conditions': [],
                    'environments': ['development'],
                    'passPercentage': 100,
                },
                {
                    'name': 'beta-rule',
                    'conditions': [],
                    'environments': ['staging'],
                    'passPercentage': 100,
                },
            ],
        }

        # Mock GET request (flag exists)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': [existing_flag]})

        # Mock PATCH request failure
        mock_requests.patch.return_value = self._create_mock_response(400, {'error': 'Bad request'})

        client = StatSigFeatureFlagClient(environment='test')

        with self.assertRaises(FeatureFlagException) as context:
            client.delete_flag('patch-error-flag')

        self.assertIn('Failed to update feature gate', str(context.exception))

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_custom_attributes_as_string(self, mock_requests, mock_statsig):
        """Test upsert_flag with custom attributes as string values - development environment always enabled"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        # Mock POST request (create flag)
        created_flag = {'id': 'gate-string-attrs', 'name': 'string-attrs-flag', 'data': {'id': 'gate-string-attrs'}}
        mock_requests.post.return_value = self._create_mock_response(201, created_flag)

        client = StatSigFeatureFlagClient(environment='test')

        result = client.upsert_flag(
            'string-attrs-flag', auto_enable=False, custom_attributes={'region': 'us-east-1', 'feature': 'new'}
        )

        # Verify result
        self.assertEqual(result['id'], 'gate-string-attrs')

        # Verify API calls - string values should be converted to lists, no conditions when auto_enable=False in test
        mock_requests.post.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'name': 'string-attrs-flag',
                'description': 'Feature gate managed by CDK for string-attrs-flag feature',
                'isEnabled': True,
                'rules': [
                    {
                        'name': 'test-rule',
                        'conditions': [
                            {
                                'type': 'custom_field',
                                'targetValue': ['us-east-1'],
                                'field': 'region',
                                'operator': 'any',
                            },
                            {'type': 'custom_field', 'targetValue': ['new'], 'field': 'feature', 'operator': 'any'},
                        ],
                        'environments': ['development'],
                        'passPercentage': 0,  # 0 since auto_enabled is false
                    }
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_custom_attributes_as_list(self, mock_requests, mock_statsig):
        """Test upsert_flag with custom attributes as list values - no conditions for test when auto_enable=False"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        # Mock POST request (create flag)
        created_flag = {'id': 'gate-list-attrs', 'name': 'list-attrs-flag', 'data': {'id': 'gate-list-attrs'}}
        mock_requests.post.return_value = self._create_mock_response(201, created_flag)

        client = StatSigFeatureFlagClient(environment='test')

        result = client.upsert_flag(
            'list-attrs-flag', auto_enable=False, custom_attributes={'licenseType': ['slp', 'audiologist']}
        )

        # Verify result
        self.assertEqual(result['id'], 'gate-list-attrs')

        # Verify API calls - list values preserved but no conditions when auto_enable=False
        mock_requests.post.assert_called_once_with(
            f'{STATSIG_API_BASE_URL}/gates',
            headers={
                'STATSIG-API-KEY': MOCK_CONSOLE_KEY,
                'STATSIG-API-VERSION': STATSIG_API_VERSION,
                'Content-Type': 'application/json',
            },
            json={
                'name': 'list-attrs-flag',
                'description': 'Feature gate managed by CDK for list-attrs-flag feature',
                'isEnabled': True,
                'rules': [
                    {
                        'name': 'test-rule',
                        'conditions': [
                            {
                                'type': 'custom_field',
                                'targetValue': ['slp', 'audiologist'],
                                'field': 'licenseType',
                                'operator': 'any',
                            }
                        ],
                        'environments': ['development'],
                        'passPercentage': 0,
                    }
                ],
            },
            timeout=30,
        )

    @patch('feature_flag_client.Statsig')
    @patch('feature_flag_client.requests')
    def test_upsert_flag_custom_attributes_invalid_type_raises_exception(self, mock_requests, mock_statsig):
        """Test upsert_flag with custom attributes as invalid type (dict) raises exception"""
        self._setup_mock_statsig(mock_statsig)

        # Mock GET request (flag doesn't exist)
        mock_requests.get.return_value = self._create_mock_response(200, {'data': []})

        client = StatSigFeatureFlagClient(environment='prod')

        # Try to create flag with invalid custom attribute type (dict) when auto_enable=True
        with self.assertRaises(FeatureFlagException) as context:
            client.upsert_flag(
                'invalid-attrs-flag',
                auto_enable=True,
                custom_attributes={
                    'invalid_attr': {'nested': 'dict'}  # This should raise an exception
                },
            )

        self.assertIn('Custom attribute value must be a string or list', str(context.exception))
