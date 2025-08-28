# ruff: noqa: ARG001 unused-argument
import json
import uuid
from copy import deepcopy
from datetime import UTC, datetime

from common_test.sign_request import sign_request
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestSignatureAuthFunctional(TstFunction):
    """Functional tests for signature authentication using real database interactions."""

    def setUp(self):
        super().setUp()
        self._load_compact_configuration_data()

        with open('tests/resources/api-client-event.json') as f:
            self.base_event = json.load(f)

        # Load test keys
        with open('tests/resources/client_private_key.pem') as f:
            self.private_key_pem = f.read()

        with open('tests/resources/client_public_key.pem') as f:
            self.public_key_pem = f.read()

    def test_required_signature_auth_success_with_public_key_in_database(self):
        """Test successful authentication when public key is in database."""
        from cc_common.signature_auth import required_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @required_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create signed event
        event = self._create_signed_event()

        # Test successful authentication
        result = lambda_handler(event, self.mock_context)
        self.assertEqual({'message': 'OK', 'authenticated': True}, result)

    def test_required_signature_auth_signature_missing_access_denied(self):
        """Test access denied when signature is missing for required signature auth."""
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.signature_auth import required_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @required_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create event without signature headers
        event = deepcopy(self.base_event)

        # Test access denied
        with self.assertRaises(CCUnauthorizedException) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('Missing required X-Key-Id header', str(cm.exception))

    def test_required_signature_auth_public_key_not_in_database_access_denied(self):
        """Test access denied when public key is not in database for required signature auth."""
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.signature_auth import required_signature_auth

        # Don't add public key to database

        @required_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create signed event
        event = self._create_signed_event()

        # Test access denied
        with self.assertRaises(CCUnauthorizedException) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('Public key not found for this compact/jurisdiction/key-id', str(cm.exception))

    def test_required_signature_auth_invalid_signature_access_denied(self):
        """Test access denied with invalid signature."""
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.signature_auth import required_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @required_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create signed event
        event = self._create_signed_event()

        # Corrupt the signature
        event['headers']['X-Signature'] = 'invalid_signature'

        # Test access denied
        with self.assertRaises(CCUnauthorizedException) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('Invalid request signature', str(cm.exception))

    def test_optional_signature_auth_success_with_public_key_in_database(self):
        """Test successful authentication when public key is in database for optional signature auth."""
        from cc_common.signature_auth import optional_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @optional_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create signed event
        event = self._create_signed_event()

        # Test successful authentication
        result = lambda_handler(event, self.mock_context)
        self.assertEqual({'message': 'OK', 'authenticated': True}, result)

    def test_optional_signature_auth_signature_missing_with_public_key_access_denied(self):
        """Test access denied when signature is missing but public key exists for optional signature auth."""
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.signature_auth import optional_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @optional_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create event without signature headers
        event = deepcopy(self.base_event)

        # Test access denied
        with self.assertRaises(CCUnauthorizedException) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('X-Key-Id header required when signature keys are configured', str(cm.exception))

    def test_optional_signature_auth_no_public_key_no_signature_success(self):
        """Test successful access when no public key in database and no signature for optional signature auth."""
        from cc_common.signature_auth import optional_signature_auth

        # Don't add public key to database

        @optional_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': False}

        # Create event without signature headers
        event = deepcopy(self.base_event)

        # Test successful access (no authentication required)
        result = lambda_handler(event, self.mock_context)
        self.assertEqual({'message': 'OK', 'authenticated': False}, result)

    def test_optional_signature_auth_no_public_key_with_signature_success(self):
        """Test successful access when no public key in database but signature provided for optional signature auth."""
        from cc_common.signature_auth import optional_signature_auth

        # Don't add public key to database

        @optional_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': False}

        # Create signed event
        event = self._create_signed_event()

        # Test successful access (no authentication required, signature ignored)
        result = lambda_handler(event, self.mock_context)
        self.assertEqual({'message': 'OK', 'authenticated': False}, result)

    def test_optional_signature_auth_invalid_signature_access_denied(self):
        """Test access denied with invalid signature."""
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.signature_auth import optional_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @optional_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create signed event
        event = self._create_signed_event()

        # Corrupt the signature
        event['headers']['X-Signature'] = 'invalid_signature'

        # Test access denied
        with self.assertRaises(CCUnauthorizedException) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('Invalid request signature', str(cm.exception))

    def test_required_signature_auth_nonce_reuse_rejected(self):
        """Test that nonce reuse is rejected for required signature auth."""
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.signature_auth import required_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @required_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create a signed event
        event = self._create_signed_event()

        # First request should succeed
        result = lambda_handler(event, self.mock_context)
        self.assertEqual({'message': 'OK', 'authenticated': True}, result)

        # Second request with the same nonce should fail (replay attack simulation)
        with self.assertRaises(CCUnauthorizedException) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('Nonce has already been used', str(cm.exception))

    def test_optional_signature_auth_nonce_reuse_rejected(self):
        """Test that nonce reuse is rejected for optional signature auth."""
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.signature_auth import optional_signature_auth

        # Add public key to database
        self._compact_configuration_table.put_item(
            Item={
                'pk': 'aslp#SIGNATURE_KEYS#al',
                'sk': 'aslp#JURISDICTION#al#test-key-001',
                'publicKey': self.public_key_pem,
                'compact': 'aslp',
                'jurisdiction': 'al',
                'keyId': 'test-key-001',
            }
        )

        @optional_signature_auth
        def lambda_handler(event: dict, context):
            return {'message': 'OK', 'authenticated': True}

        # Create a signed event
        event = self._create_signed_event()

        # First request should succeed
        result = lambda_handler(event, self.mock_context)
        self.assertEqual({'message': 'OK', 'authenticated': True}, result)

        # Second request with the same nonce should fail (replay attack simulation)
        with self.assertRaises(CCUnauthorizedException) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('Nonce has already been used', str(cm.exception))

    def _create_signed_event(self) -> dict:
        """Create a properly signed event for testing."""
        # Create base event
        event = deepcopy(self.base_event)

        # Generate current timestamp and nonce
        timestamp = datetime.now(UTC).isoformat()
        nonce = str(uuid.uuid4())
        key_id = 'test-key-001'

        # Import and use the sign_request function
        headers = sign_request(
            method=event['httpMethod'],
            path=event['path'],
            query_params=event.get('queryStringParameters') or {},
            timestamp=timestamp,
            nonce=nonce,
            key_id=key_id,
            private_key_pem=self.private_key_pem,
        )

        # Add signature headers to event
        event['headers'].update(headers)

        return event
