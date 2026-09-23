# ruff: noqa: ARG001 unused-argument
import base64
import json
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import patch

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestSignatureAuth(TstLambdas):
    """Testing that the signature_auth_required decorator is working as expected."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Load test keys
        with open('tests/resources/client_private_key.pem') as f:
            self.private_key_pem = f.read()

        with open('tests/resources/client_public_key.pem') as f:
            self.public_key_pem = f.read()

        # Load test event
        with open('tests/resources/api-client-event.json') as f:
            self.base_event = json.load(f)

    def test_happy_path(self):
        """Test successful signature authentication."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # Mock the rate limiting table for nonce storage
            with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                mock_table.put_item.return_value = None

                resp = lambda_handler(event, self.mock_context)

                # The decorator returns the raw function result, not an API Gateway response
                self.assertEqual({'message': 'OK'}, resp)

    def test_missing_headers(self):
        """Test authentication failure when required headers are missing."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event without signature headers
        event = deepcopy(self.base_event)

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Missing required X-Key-Id header', str(cm.exception))

    def test_unsupported_algorithm(self):
        """Test authentication failure with unsupported algorithm."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with wrong algorithm
        event = self._create_signed_event()
        event['headers']['X-Algorithm'] = 'RSA-SHA256'

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Unsupported signature algorithm', str(cm.exception))

    def test_invalid_timestamp(self):
        """Test authentication failure with invalid timestamp."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with old timestamp
        event = self._create_signed_event()
        event['headers']['X-Timestamp'] = '2020-01-01T00:00:00Z'

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Request timestamp is too old or too far in the future', str(cm.exception))

    def test_malformed_timestamp(self):
        """Test authentication failure with malformed timestamp."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with malformed timestamp
        event = self._create_signed_event()
        event['headers']['X-Timestamp'] = 'not-a-timestamp'

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Invalid timestamp format', str(cm.exception))

    def test_timestamp_format_compatibility(self):
        """Test that both timestamp formats work with the same signature validation."""
        from cc_common.signature_auth import _build_signature_string, _verify_signature, required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Test both timestamp formats
        timestamp_formats = [
            datetime.now(UTC).isoformat(),  # '+00:00' format
            datetime.now(UTC).isoformat().replace('+00:00', 'Z'),  # 'Z' format
        ]

        for timestamp in timestamp_formats:
            with self.subTest(timestamp_format=timestamp):
                # Create event with current timestamp format
                event = deepcopy(self.base_event)
                nonce = '550e8400-e29b-41d4-a716-446655440000'

                # Import and use the sign_request function
                from common_test.sign_request import sign_request

                headers = sign_request(
                    method=event['httpMethod'],
                    path=event['path'],
                    query_params=event.get('queryStringParameters') or {},
                    timestamp=timestamp,
                    nonce=nonce,
                    key_id='test-key-001',
                    private_key_pem=self.private_key_pem,
                )

                event['headers'].update(headers)

                # Verify that the signature string can be built and verified
                signature_string = _build_signature_string(event)
                is_valid = _verify_signature(signature_string, headers['X-Signature'], self.public_key_pem)
                self.assertTrue(is_valid)

                # Mock DynamoDB to return the public key
                with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
                    mock_get_key.return_value = self.public_key_pem

                    # Mock the rate limiting table for nonce storage
                    with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                        mock_table.put_item.return_value = None

                        resp = lambda_handler(event, self.mock_context)
                    self.assertEqual({'message': 'OK'}, resp)

    def test_missing_path_parameters(self):
        """Test authentication failure when compact/jurisdiction are missing."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event without path parameters
        event = self._create_signed_event()
        event['pathParameters'] = {}

        with self.assertRaises(Exception) as cm:
            lambda_handler(event, self.mock_context)

        self.assertIn('Missing compact or jurisdiction parameters', str(cm.exception))

    def test_public_key_not_found(self):
        """Test authentication failure when public key is not found in DynamoDB."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return None (key not found)
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = None

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Public key not found for this compact/jurisdiction', str(cm.exception))

    def test_invalid_signature(self):
        """Test authentication failure with invalid signature."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with invalid signature
        event = self._create_signed_event()
        event['headers']['X-Signature'] = 'invalid-signature'

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Invalid request signature', str(cm.exception))

    def test_sign_request_utility_function(self):
        """Test the sign_request utility function works correctly."""
        # Test data
        method = 'POST'
        path = '/v1/compacts/aslp/jurisdictions/al/providers/query'
        query_params = {'pageSize': '50', 'startDateTime': '2024-01-01T00:00:00Z'}
        timestamp = '2024-01-15T10:30:00Z'
        nonce = '550e8400-e29b-41d4-a716-446655440000'

        # Import and use the sign_request function
        from common_test.sign_request import sign_request

        headers = sign_request(method, path, query_params, timestamp, nonce, 'test-key-001', self.private_key_pem)

        # Verify headers are present
        self.assertEqual('ECDSA-SHA256', headers['X-Algorithm'])
        self.assertEqual(timestamp, headers['X-Timestamp'])
        self.assertEqual(nonce, headers['X-Nonce'])
        self.assertIn('X-Key-Id', headers)
        self.assertIn('X-Signature', headers)

        # Verify signature can be decoded
        signature_bytes = base64.b64decode(headers['X-Signature'])
        self.assertIsInstance(signature_bytes, bytes)
        self.assertGreater(len(signature_bytes), 0)

    def test_sign_request_with_url_encoded_parameters(self):
        """Test that sign_request properly URL-encodes query parameters."""
        # Test data with special characters
        method = 'GET'
        path = '/v1/compacts/aslp/jurisdictions/al/providers/query'
        query_params = {
            'search': 'test value with spaces',
            'filter': 'status=active&type=provider',
            'special': '!@#$%^&*()',
        }
        timestamp = '2024-01-15T10:30:00Z'
        nonce = '550e8400-e29b-41d4-a716-446655440000'

        # Import and use the sign_request function
        from common_test.sign_request import sign_request

        headers = sign_request(method, path, query_params, timestamp, nonce, 'test-key-001', self.private_key_pem)

        # Verify headers are present
        self.assertEqual('ECDSA-SHA256', headers['X-Algorithm'])
        self.assertEqual(timestamp, headers['X-Timestamp'])
        self.assertEqual(nonce, headers['X-Nonce'])
        self.assertIn('X-Key-Id', headers)
        self.assertIn('X-Signature', headers)

        # Verify signature can be decoded
        signature_bytes = base64.b64decode(headers['X-Signature'])
        self.assertIsInstance(signature_bytes, bytes)
        self.assertGreater(len(signature_bytes), 0)

        # Verify that the signature string includes URL-encoded parameters
        # The signature string should be: GET\n/path\nfilter=status%3Dactive%26type%3Dprovider&
        # search=test%20value%20with%20spaces&special=%21%40%23%24%25%5E%26%2A%28%29\n...
        # We can't directly verify the signature string, but we can verify the signature is valid
        # by creating a test event and validating it
        from cc_common.signature_auth import _build_signature_string, _verify_signature

        test_event = {'httpMethod': method, 'path': path, 'queryStringParameters': query_params, 'headers': headers}

        signature_string = _build_signature_string(test_event)
        is_valid = _verify_signature(signature_string, headers['X-Signature'], self.public_key_pem)
        self.assertTrue(is_valid)

    def test_signature_string_construction(self):
        """Test that signature string is constructed correctly."""
        from cc_common.signature_auth import _build_signature_string

        # Create event with specific components
        event = {
            'httpMethod': 'POST',
            'path': '/v1/compacts/aslp/jurisdictions/al/providers/query',
            'queryStringParameters': {'pageSize': '50', 'startDateTime': '2024-01-01T00:00:00Z'},
            'headers': {
                'X-Timestamp': '2024-01-15T10:30:00Z',
                'X-Nonce': '550e8400-e29b-41d4-a716-446655440000',
                'X-Key-Id': 'test-key-001',
            },
        }

        signature_string = _build_signature_string(event)

        expected = (
            'POST\n'
            '/v1/compacts/aslp/jurisdictions/al/providers/query\n'
            'pageSize=50&startDateTime=2024-01-01T00%3A00%3A00Z\n'
            '2024-01-15T10:30:00Z\n'
            '550e8400-e29b-41d4-a716-446655440000\n'
            'test-key-001'
        )

        self.assertEqual(expected, signature_string)

    def test_query_parameters_sorting(self):
        """Test that query parameters are sorted correctly in signature string."""
        from cc_common.signature_auth import _build_signature_string

        # Create event with unsorted query parameters
        event = {
            'httpMethod': 'GET',
            'path': '/v1/compacts/aslp/jurisdictions/al/providers/query',
            'queryStringParameters': {'zebra': 'last', 'alpha': 'first', 'beta': 'second'},
            'headers': {
                'X-Timestamp': '2024-01-15T10:30:00Z',
                'X-Nonce': '550e8400-e29b-41d4-a716-446655440000',
                'X-Key-Id': 'test-key-001',
            },
        }

        signature_string = _build_signature_string(event)

        # Verify parameters are sorted alphabetically and URL-encoded
        expected = (
            'GET\n'
            '/v1/compacts/aslp/jurisdictions/al/providers/query\n'
            'alpha=first&beta=second&zebra=last\n'
            '2024-01-15T10:30:00Z\n'
            '550e8400-e29b-41d4-a716-446655440000\n'
            'test-key-001'
        )

        self.assertEqual(expected, signature_string)

    def test_empty_query_parameters(self):
        """Test signature string construction with no query parameters."""
        from cc_common.signature_auth import _build_signature_string

        event = {
            'httpMethod': 'GET',
            'path': '/v1/compacts/aslp/jurisdictions/al/providers',
            'queryStringParameters': None,
            'headers': {
                'X-Timestamp': '2024-01-15T10:30:00Z',
                'X-Nonce': '550e8400-e29b-41d4-a716-446655440000',
                'X-Key-Id': 'test-key-001',
            },
        }

        signature_string = _build_signature_string(event)

        expected = (
            'GET\n'
            '/v1/compacts/aslp/jurisdictions/al/providers\n'
            '\n'
            '2024-01-15T10:30:00Z\n'
            '550e8400-e29b-41d4-a716-446655440000\n'
            'test-key-001'
        )

        self.assertEqual(expected, signature_string)

    def test_url_encoded_query_parameters(self):
        """Test that query parameters are properly URL-encoded in signature string."""
        from cc_common.signature_auth import _build_signature_string

        event = {
            'httpMethod': 'GET',
            'path': '/v1/compacts/aslp/jurisdictions/al/providers/query',
            'queryStringParameters': {
                'search': 'test value with spaces',
                'filter': 'status=active&type=provider',
                'special': '!@#$%^&*()',
                'unicode': 'café résumé',
            },
            'headers': {
                'X-Timestamp': '2024-01-15T10:30:00Z',
                'X-Nonce': '550e8400-e29b-41d4-a716-446655440000',
                'X-Key-Id': 'test-key-001',
            },
        }

        signature_string = _build_signature_string(event)

        # Verify that parameters are sorted alphabetically and URL-encoded
        expected = (
            'GET\n'
            '/v1/compacts/aslp/jurisdictions/al/providers/query\n'
            'filter=status%3Dactive%26type%3Dprovider&search=test%20value%20with%20spaces&special=%21%40%23%24%25%5E%26%2A%28%29&unicode=caf%C3%A9%20r%C3%A9sum%C3%A9\n'
            '2024-01-15T10:30:00Z\n'
            '550e8400-e29b-41d4-a716-446655440000\n'
            'test-key-001'
        )

        self.assertEqual(expected, signature_string)

    def test_case_insensitive_headers(self):
        """Test that header extraction is case insensitive using CaseInsensitiveDict."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed event first
        event = self._create_signed_event()

        # Now create a new event with mixed case headers but keep the original signature
        # This tests that CaseInsensitiveDict can handle different header cases
        mixed_case_event = deepcopy(self.base_event)
        mixed_case_event['headers'] = {
            'x-algorithm': event['headers']['X-Algorithm'],
            'X-Timestamp': event['headers']['X-Timestamp'],
            'x-nonce': event['headers']['X-Nonce'],
            'x-key-id': event['headers']['X-Key-Id'],
            'X-Signature': event['headers']['X-Signature'],
        }

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # Mock the rate limiting table for nonce storage
            with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                mock_table.put_item.return_value = None

                resp = lambda_handler(mixed_case_event, self.mock_context)

                # The decorator returns the raw function result, not an API Gateway response
                self.assertEqual({'message': 'OK'}, resp)

    def _create_signed_event(self) -> dict:
        """Create a properly signed event for testing."""
        # Create base event
        event = deepcopy(self.base_event)

        # Generate current timestamp and nonce
        timestamp = datetime.now(UTC).isoformat()
        nonce = '550e8400-e29b-41d4-a716-446655440000'
        key_id = 'test-key-001'

        # Import and use the sign_request function
        from common_test.sign_request import sign_request

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

    def _create_signed_event_with_nonce(self, nonce: str) -> dict:
        """Create a properly signed event with a specific nonce for testing."""
        # Create base event
        event = deepcopy(self.base_event)

        # Generate current timestamp
        timestamp = datetime.now(UTC).isoformat()
        key_id = 'test-key-001'

        # Import and use the sign_request function
        from common_test.sign_request import sign_request

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

    def test_nonce_reuse_prevention(self):
        """Test that nonce reuse is prevented."""
        from botocore.exceptions import ClientError
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # Mock the rate limiting table for the first call (successful nonce storage)
            with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                # First call should succeed (nonce doesn't exist)
                mock_table.put_item.return_value = None

                # First request should succeed
                resp = lambda_handler(event, self.mock_context)
                self.assertEqual({'message': 'OK'}, resp)

                # Verify the nonce was stored
                mock_table.put_item.assert_called_once()
                call_args = mock_table.put_item.call_args
                self.assertEqual('NONCE#aslp#JURISDICTION#al', call_args[1]['Item']['pk'])
                self.assertEqual(f'NONCE#{event["headers"]["X-Nonce"]}', call_args[1]['Item']['sk'])

                # Reset the mock for the second call
                mock_table.put_item.reset_mock()

                # Mock the second call to simulate nonce already exists
                error_response = {
                    'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'The conditional request failed'}
                }
                mock_table.put_item.side_effect = ClientError(error_response, 'PutItem')

                # Second request with same nonce should fail
                with self.assertRaises(Exception) as cm:
                    lambda_handler(event, self.mock_context)

                self.assertIn('Nonce has already been used', str(cm.exception))

    def test_nonce_storage_failure(self):
        """Test handling of nonce storage failures."""
        from botocore.exceptions import ClientError
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # Mock the rate limiting table to simulate a different error
            with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                error_response = {
                    'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Rate exceeded'}
                }
                mock_table.put_item.side_effect = ClientError(error_response, 'PutItem')

                # Request should fail with nonce validation error
                with self.assertRaises(Exception) as cm:
                    lambda_handler(event, self.mock_context)

                self.assertIn('Failed to validate nonce', str(cm.exception))

    def test_nonce_format_validation_empty_nonce(self):
        """Test that empty nonces are rejected."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with empty nonce
        event = self._create_signed_event()
        event['headers']['X-Nonce'] = ''

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            # Empty nonce is caught by the missing headers check
            self.assertIn('Missing required signature authentication headers', str(cm.exception))

    def test_nonce_format_validation_too_long_nonce(self):
        """Test that nonces longer than 256 characters are rejected."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with nonce that's too long
        event = self._create_signed_event()
        event['headers']['X-Nonce'] = 'a' * 257  # 257 characters

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            with self.assertRaises(Exception) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Nonce cannot be longer than 256 characters', str(cm.exception))

    def test_nonce_format_validation_invalid_characters(self):
        """Test that nonces with invalid characters are rejected."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Test various invalid characters
        invalid_nonces = [
            'test@nonce',  # @ symbol
            'test nonce',  # space
            'test_nonce',  # underscore
            'test.nonce',  # period
            'test+nonce',  # plus
            'test=nonce',  # equals
            'test/nonce',  # slash
            'test\\nonce',  # backslash
            'test(nonce)',  # parentheses
            'test[nonce]',  # brackets
            'test{nonce}',  # braces
            'test#nonce',  # hash
            'test$nonce',  # dollar
            'test%nonce',  # percent
            'test^nonce',  # caret
            'test&nonce',  # ampersand
            'test*nonce',  # asterisk
            'test|nonce',  # pipe
            'test~nonce',  # tilde
            'test`nonce',  # backtick
            'test;nonce',  # semicolon
            'test:nonce',  # colon
            'test"nonce',  # quote
            "test'nonce",  # single quote
            'test<nonce',  # less than
            'test>nonce',  # greater than
            'test,nonce',  # comma
            'test?nonce',  # question mark
            'test!nonce',  # exclamation
        ]

        for invalid_nonce in invalid_nonces:
            with self.subTest(nonce=invalid_nonce):
                # Create event with invalid nonce
                event = self._create_signed_event()
                event['headers']['X-Nonce'] = invalid_nonce

                # Mock DynamoDB to return the public key
                with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
                    mock_get_key.return_value = self.public_key_pem

                    with self.assertRaises(Exception) as cm:
                        lambda_handler(event, self.mock_context)

                    self.assertIn('Nonce can only contain alphanumeric characters and hyphens', str(cm.exception))

    def test_nonce_format_validation_valid_characters(self):
        """Test that nonces with valid characters are accepted."""
        from cc_common.signature_auth import required_signature_auth

        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Test various valid nonces
        valid_nonces = [
            'test-nonce',  # hyphen
            'test123',  # numbers
            'TEST123',  # uppercase
            'test123-nonce',  # mixed alphanumeric with hyphen
            'a',  # single character
            'a' * 256,  # exactly 256 characters
            '1234567890',  # all numbers
            'abcdefghijklmnopqrstuvwxyz',  # all lowercase
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ',  # all uppercase
            'a1b2c3-d4e5f6',  # mixed with hyphens
        ]

        for valid_nonce in valid_nonces:
            with self.subTest(nonce=valid_nonce):
                # Create event with valid nonce and recalculate signature
                event = self._create_signed_event_with_nonce(valid_nonce)

                # Mock DynamoDB to return the public key
                with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
                    mock_get_key.return_value = self.public_key_pem

                    # Mock the rate limiting table for nonce storage
                    with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                        mock_table.put_item.return_value = None

                        # Should succeed
                        resp = lambda_handler(event, self.mock_context)
                        self.assertEqual({'message': 'OK'}, resp)
