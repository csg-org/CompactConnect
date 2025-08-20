# ruff: noqa: ARG001 unused-argument
import json
from datetime import UTC, datetime
from unittest.mock import patch

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestHmacAuthIntegration(TstLambdas):
    """Testing HMAC authentication integration with the existing api_handler decorator."""

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

    def test_hmac_with_api_handler_success(self):
        """Test successful HMAC authentication with api_handler decorator."""
        from cc_common.hmac_auth import hmac_auth_required
        from cc_common.utils import api_handler

        @api_handler
        @hmac_auth_required
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK', 'authenticated': True}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(200, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

            # Parse response body to verify content
            body = json.loads(resp['body'])
            self.assertEqual('OK', body['message'])
            self.assertTrue(body['authenticated'])

    def test_hmac_with_api_handler_unauthorized(self):
        """Test HMAC authentication failure with api_handler decorator returns 401."""
        from cc_common.hmac_auth import hmac_auth_required
        from cc_common.utils import api_handler

        @api_handler
        @hmac_auth_required
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event without HMAC headers
        event = self.base_event.copy()

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(401, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])
        self.assertEqual('{"message": "Unauthorized"}', resp['body'])

    def test_hmac_with_api_handler_invalid_request(self):
        """Test HMAC validation failure with api_handler decorator returns 400."""
        from cc_common.hmac_auth import hmac_auth_required
        from cc_common.utils import api_handler

        @api_handler
        @hmac_auth_required
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with malformed timestamp
        event = self._create_signed_event()
        event['headers']['X-Timestamp'] = 'not-a-timestamp'

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(400, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

        # Parse response body to verify error message
        body = json.loads(resp['body'])
        self.assertIn('Invalid timestamp format', body['message'])

    def test_hmac_with_api_handler_invalid_signature(self):
        """Test invalid signature with api_handler decorator returns 401."""
        from cc_common.hmac_auth import hmac_auth_required
        from cc_common.utils import api_handler

        @api_handler
        @hmac_auth_required
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with invalid signature
        event = self._create_signed_event()
        event['headers']['X-Signature'] = 'invalid-signature'

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(401, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])
            self.assertEqual('{"message": "Unauthorized"}', resp['body'])

    def test_hmac_with_api_handler_public_key_not_found(self):
        """Test public key not found with api_handler decorator returns 401."""
        from cc_common.hmac_auth import hmac_auth_required
        from cc_common.utils import api_handler

        @api_handler
        @hmac_auth_required
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return None (key not found)
        with patch('cc_common.hmac_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = None

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(401, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])
            self.assertEqual('{"message": "Unauthorized"}', resp['body'])

    def test_decorator_order_matters(self):
        """Test that decorator order affects behavior (api_handler should be outermost)."""
        from cc_common.hmac_auth import hmac_auth_required
        from cc_common.utils import api_handler

        # This test demonstrates that api_handler should be the outermost decorator
        # so it can properly handle exceptions from hmac_auth_required

        @hmac_auth_required
        @api_handler
        def lambda_handler_wrong_order(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event without HMAC headers
        event = self.base_event.copy()

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # This should raise an exception directly instead of returning a proper API response
            with self.assertRaises(Exception) as cm:
                lambda_handler_wrong_order(event, self.mock_context)

            self.assertIn('Missing required X-Key-Id header', str(cm.exception))

    def test_hmac_with_api_handler_cors_handling(self):
        """Test that CORS headers are properly handled with HMAC authentication."""
        from cc_common.hmac_auth import hmac_auth_required
        from cc_common.utils import api_handler

        @api_handler
        @hmac_auth_required
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request with localhost origin
        event = self._create_signed_event()
        event['headers']['origin'] = 'http://localhost:1234'

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(200, resp['statusCode'])
            self.assertEqual('http://localhost:1234', resp['headers']['Access-Control-Allow-Origin'])

    def _create_signed_event(self) -> dict:
        """Create a properly signed event for testing."""
        # Create base event
        event = self.base_event.copy()

        # Generate current timestamp and nonce
        timestamp = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        nonce = '550e8400-e29b-41d4-a716-446655440000'

        # Import the sign_request function
        from tests.sign_request import sign_request

        # Sign the request
        headers = sign_request(
            method=event['httpMethod'],
            path=event['path'],
            query_params=event.get('queryStringParameters') or {},
            timestamp=timestamp,
            nonce=nonce,
            key_id='test-key-001',
            private_key_pem=self.private_key_pem,
        )

        # Add HMAC headers to event
        event['headers'].update(headers)

        return event
