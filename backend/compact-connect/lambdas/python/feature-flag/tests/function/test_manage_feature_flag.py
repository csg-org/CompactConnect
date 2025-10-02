import json
from unittest.mock import MagicMock, patch

from moto import mock_aws

from . import TstFunction

MOCK_SERVER_KEY = 'test-server-key-123'
MOCK_CONSOLE_KEY = 'test-console-key-456'


@mock_aws
class TestManageFeatureFlagHandler(TstFunction):
    """Test suite for ManageFeatureFlagHandler custom resource."""

    def setUp(self):
        super().setUp()

        # Set up mock secrets manager with StatSig credentials
        secrets_client = self.create_mock_secrets_manager()
        secrets_client.create_secret(
            Name='compact-connect/env/test/statsig/credentials',
            SecretString=json.dumps({
                'serverKey': MOCK_SERVER_KEY,
                'consoleKey': MOCK_CONSOLE_KEY
            })
        )

    def create_mock_secrets_manager(self):
        """Create a mock secrets manager client"""
        import boto3
        return boto3.client('secretsmanager', region_name='us-east-1')

    @patch('handlers.manage_feature_flag.StatSigFeatureFlagClient')
    def test_on_create_calls_upsert_flag_with_correct_params(self, mock_client_class):
        """Test that on_create calls upsert_flag with the correct parameters"""
        from handlers.manage_feature_flag import ManageFeatureFlagHandler

        # Set up mock client instance
        mock_client = MagicMock()
        mock_client.upsert_flag.return_value = {'id': 'gate-123', 'name': 'test-flag'}
        mock_client_class.return_value = mock_client
        
        handler = ManageFeatureFlagHandler()
        properties = {
            'flagName': 'test-flag',
            'autoEnable': True,
            'customAttributes': {'region': 'us-east-1', 'feature': 'new'}
        }
        
        result = handler.on_create(properties)
        
        # Verify upsert_flag was called with correct parameters
        mock_client.upsert_flag.assert_called_once_with(
            'test-flag',
            True,
            {'region': 'us-east-1', 'feature': 'new'}
        )
        
        # Verify response
        self.assertEqual(result['PhysicalResourceId'], 'feature-flag-test-flag-test')
        self.assertEqual(result['Data']['gateId'], 'gate-123')

    @patch('handlers.manage_feature_flag.StatSigFeatureFlagClient')
    def test_on_create_with_minimal_properties(self, mock_client_class):
        """Test on_create with minimal required properties"""
        from handlers.manage_feature_flag import ManageFeatureFlagHandler
        # Set up mock client instance
        mock_client = MagicMock()
        mock_client.upsert_flag.return_value = {'id': 'gate-456', 'name': 'minimal-flag'}
        mock_client_class.return_value = mock_client
        
        handler = ManageFeatureFlagHandler()
        properties = {'flagName': 'minimal-flag'}
        
        result = handler.on_create(properties)
        
        # Verify upsert_flag was called with defaults
        mock_client.upsert_flag.assert_called_once_with('minimal-flag', False, None)
        
        # Verify response
        self.assertEqual(result['PhysicalResourceId'], 'feature-flag-minimal-flag-test')
        self.assertEqual(result['Data']['gateId'], 'gate-456')

    @patch('handlers.manage_feature_flag.StatSigFeatureFlagClient')
    def test_on_update_calls_upsert_flag_with_correct_params(self, mock_client_class):
        from handlers.manage_feature_flag import ManageFeatureFlagHandler
        """Test that on_update calls upsert_flag with the correct parameters"""
        # Set up mock client instance
        mock_client = MagicMock()
        mock_client.upsert_flag.return_value = {'id': 'gate-789', 'name': 'update-flag'}
        mock_client_class.return_value = mock_client
        
        handler = ManageFeatureFlagHandler()
        properties = {
            'flagName': 'update-flag',
            'autoEnable': False,
            'customAttributes': {'version': '2.0'}
        }
        
        result = handler.on_update(properties)
        
        # Verify client was initialized with correct environment
        mock_client_class.assert_called_once_with(environment='test')
        
        # Verify upsert_flag was called with correct parameters
        mock_client.upsert_flag.assert_called_once_with(
            'update-flag',
            False,
            {'version': '2.0'}
        )

        # Verify response
        self.assertEqual(result['PhysicalResourceId'], 'feature-flag-update-flag-test')
        self.assertEqual(result['Data']['gateId'], 'gate-789')

    @patch('handlers.manage_feature_flag.StatSigFeatureFlagClient')
    def test_on_update_raises_error_when_no_flag_returned(self, mock_client_class):
        """Test on_update raises RuntimeError when upsert_flag returns empty dict"""
        from handlers.manage_feature_flag import ManageFeatureFlagHandler
        # Set up mock client instance
        mock_client = MagicMock()
        mock_client.upsert_flag.return_value = {}  # Empty dict means no action taken
        mock_client_class.return_value = mock_client
        
        handler = ManageFeatureFlagHandler()
        properties = {'flagName': 'failed-update-flag'}
        
        with self.assertRaises(RuntimeError) as context:
            handler.on_update(properties)
        
        self.assertIn("Feature gate 'failed-update-flag' could not be updated", str(context.exception))

    @patch('handlers.manage_feature_flag.StatSigFeatureFlagClient')
    def test_on_delete_calls_delete_flag_with_correct_params(self, mock_client_class):
        """Test that on_delete calls delete_flag with the correct parameters"""
        from handlers.manage_feature_flag import ManageFeatureFlagHandler
        # Set up mock client instance
        mock_client = MagicMock()
        mock_client.delete_flag.return_value = True  # Flag fully deleted
        mock_client_class.return_value = mock_client
        
        handler = ManageFeatureFlagHandler()
        properties = {'flagName': 'delete-flag'}
        
        result = handler.on_delete(properties)
        
        # Verify client was initialized with correct environment
        mock_client_class.assert_called_once_with(environment='test')
        
        # Verify delete_flag was called with correct parameters
        mock_client.delete_flag.assert_called_once_with('delete-flag')
        
        # Should return None (successful deletion)
        self.assertIsNone(result)
