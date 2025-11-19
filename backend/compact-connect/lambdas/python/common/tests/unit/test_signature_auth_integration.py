# ruff: noqa: ARG001 unused-argument
import json
from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestSignatureAuthIntegration(TstLambdas):
    """Testing signature authentication integration with the existing api_handler decorator."""

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

    def test_signature_with_api_handler_success(self):
        """Test successful signature authentication with api_handler decorator."""
        from cc_common.signature_auth import required_signature_auth
        from cc_common.utils import api_handler

        @api_handler
        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK', 'authenticated': True}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # Mock the rate limiting table for nonce storage
            with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                mock_table.put_item.return_value = None

                resp = lambda_handler(event, self.mock_context)

                self.assertEqual(200, resp['statusCode'])
                self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

                # Parse response body to verify content
                body = json.loads(resp['body'])
                self.assertEqual('OK', body['message'])
                self.assertTrue(body['authenticated'])

    def test_signature_with_api_handler_unauthorized(self):
        """Test signature authentication failure with api_handler decorator returns 401."""
        from cc_common.signature_auth import required_signature_auth
        from cc_common.utils import api_handler

        @api_handler
        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event without signature headers
        event = deepcopy(self.base_event)

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(401, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])
        self.assertEqual('{"message": "Missing required X-Key-Id header"}', resp['body'])

    def test_signature_with_api_handler_invalid_request(self):
        """Test signature validation failure with api_handler decorator returns 400."""
        from cc_common.signature_auth import required_signature_auth
        from cc_common.utils import api_handler

        @api_handler
        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with malformed timestamp
        event = self._create_signed_event()
        event['headers']['X-Timestamp'] = 'not-a-timestamp'

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(401, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])
            self.assertEqual({'message': 'Invalid timestamp format'}, json.loads(resp['body']))

    def test_signature_with_api_handler_invalid_signature(self):
        """Test invalid signature with api_handler decorator returns 401."""
        from cc_common.signature_auth import required_signature_auth
        from cc_common.utils import api_handler

        @api_handler
        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with invalid signature
        event = self._create_signed_event()
        event['headers']['X-Signature'] = 'invalid-signature'

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            resp = lambda_handler(event, self.mock_context)

        self.assertEqual(401, resp['statusCode'])
        self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])
        self.assertEqual({'message': 'Invalid request signature'}, json.loads(resp['body']))

    def test_signature_with_api_handler_public_key_not_found(self):
        """Test public key not found with api_handler decorator returns 401."""
        from cc_common.signature_auth import required_signature_auth
        from cc_common.utils import api_handler

        @api_handler
        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request
        event = self._create_signed_event()

        # Mock DynamoDB to return None (key not found)
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = None

            resp = lambda_handler(event, self.mock_context)

            self.assertEqual(401, resp['statusCode'])
            self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])
            self.assertEqual(
                {'message': 'Public key not found for this compact/jurisdiction/key-id'}, json.loads(resp['body'])
            )

    def test_decorator_order_matters(self):
        """Test that decorator order affects behavior (api_handler should be outermost)."""
        from cc_common.signature_auth import required_signature_auth
        from cc_common.utils import api_handler

        # This test demonstrates that api_handler should be the outermost decorator
        # so it can properly handle exceptions from signature_auth_required

        @required_signature_auth
        @api_handler
        def lambda_handler_wrong_order(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event without signature headers
        event = deepcopy(self.base_event)

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # This should raise an exception directly instead of returning a proper API response
            with self.assertRaises(Exception) as cm:
                lambda_handler_wrong_order(event, self.mock_context)

            self.assertIn('Missing required X-Key-Id header', str(cm.exception))

    def test_signature_with_api_handler_cors_handling(self):
        """Test that CORS headers are properly handled with signature authentication."""
        from cc_common.signature_auth import required_signature_auth
        from cc_common.utils import api_handler

        @api_handler
        @required_signature_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create a properly signed request with localhost origin
        event = self._create_signed_event()
        event['headers']['origin'] = 'http://localhost:1234'

        # Mock DynamoDB to return the public key
        with patch('cc_common.signature_auth._get_public_key_from_dynamodb') as mock_get_key:
            mock_get_key.return_value = self.public_key_pem

            # Mock the rate limiting table for nonce storage
            with patch('cc_common.config._Config.rate_limiting_table') as mock_table:
                mock_table.put_item.return_value = None

                resp = lambda_handler(event, self.mock_context)

                self.assertEqual(200, resp['statusCode'])
                self.assertEqual('http://localhost:1234', resp['headers']['Access-Control-Allow-Origin'])

    def _create_signed_event(self) -> dict:
        """Create a properly signed event for testing."""
        # Create base event
        event = deepcopy(self.base_event)

        # Generate current timestamp and nonce
        timestamp = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        nonce = '550e8400-e29b-41d4-a716-446655440000'

        # Import the sign_request function
        from common_test.sign_request import sign_request

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

        # Add signature headers to event
        event['headers'].update(headers)

        return event


class TestSignatureAuthSigner(TstLambdas):
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Load test keys
        with open('tests/resources/client_private_key.pem') as f:
            self.private_key_pem = f.read()

    def test_string_to_sign(self):
        from common_test.sign_request import get_string_to_sign
        # Generate current timestamp and nonce
        timestamp = '2025-11-11T19:09:53Z'
        nonce = '54ebdc56-4eae-4627-94e1-11ff27a3ec88'

        string_to_sign = get_string_to_sign(
            method='POST',
            path='/path',
            query_params={
                'a': '1',
                'b': 'value two',
            },
            timestamp=timestamp,
            nonce=nonce,
            key_id='eLicenseKey'
        )
        expected = (
            'POST\n/path\na=1&b=value%20two\n2025-11-11T19:09:53Z\n'
            '54ebdc56-4eae-4627-94e1-11ff27a3ec88\neLicenseKey'
        )
        self.assertEqual(string_to_sign, expected)

    def test_generate_signature_examples(self):
        """Generate example HTTP requests with signature authentication for client documentation."""
        import base64
        from datetime import UTC, datetime
        from urllib.parse import quote

        from common_test.sign_request import get_string_to_sign, sign_request

        # Define four example requests with varying methods, paths, and query parameters
        examples = [
            {
                'method': 'GET',
                'path': '/v1/compacts/aslp/jurisdictions/al/providers/query',
                'query_params': {'limit': '10', 'offset': '0', 'status': 'active'},
                'host': 'api.example.com',
                'key_id': 'test-key-001',
            },
            {
                'method': 'POST',
                'path': '/v1/compacts/aslp/jurisdictions/al/providers',
                'query_params': {'validate': 'true'},
                'host': 'api.example.com',
                'key_id': 'test-key-002',
            },
            {
                'method': 'GET',
                'path': '/v1/compacts/aslp/jurisdictions/al/providers/12345',
                'query_params': {},
                'host': 'api.example.com',
                'key_id': 'test-key-003',
            },
            {
                'method': 'POST',
                'path': '/path',
                'query_params': {'a': '1', 'b': 'value two'},
                'host': 'api.example.com',
                'key_id': 'eLicenseKey',
                'timestamp': '2025-11-11T19:09:53Z',
                'nonce': '54ebdc56-4eae-4627-94e1-11ff27a3ec88',
            },
        ]

        output_lines = []
        output_lines.append('=' * 80)
        output_lines.append('Signature Authentication Examples')
        output_lines.append('=' * 80)
        output_lines.append('')
        output_lines.append('This document provides example HTTP requests demonstrating the')
        output_lines.append('CompactConnect signature authentication scheme.')
        output_lines.append('')
        output_lines.append('Each example includes:')
        output_lines.append('  1. The raw HTTP request with signature headers')
        output_lines.append('  2. The plaintext string that was signed')
        output_lines.append('  3. The base64-encoded string that was signed')
        output_lines.append('')
        output_lines.append('=' * 80)
        output_lines.append('')

        for idx, example in enumerate(examples, 1):
            # Generate timestamp and nonce for this example (use provided values if available)
            timestamp = example.get('timestamp') or datetime.now(UTC).isoformat().replace('+00:00', 'Z')
            nonce = example.get('nonce') or uuid4().hex

            # Get the string to sign
            string_to_sign = get_string_to_sign(
                method=example['method'],
                path=example['path'],
                query_params=example['query_params'],
                timestamp=timestamp,
                nonce=nonce,
                key_id=example['key_id'],
            )

            # Sign the request
            signature_headers = sign_request(
                method=example['method'],
                path=example['path'],
                query_params=example['query_params'],
                timestamp=timestamp,
                nonce=nonce,
                key_id=example['key_id'],
                private_key_pem=self.private_key_pem,
            )

            # Build the query string for the HTTP request (using same format as signature)
            if example['query_params']:
                sorted_params = '&'.join(
                    f'{quote(str(k), safe="")}={quote(str(v), safe="")}'
                    for k, v in sorted(example['query_params'].items())
                )
                query_string = '?' + sorted_params
            else:
                query_string = ''

            # Format the raw HTTP request
            output_lines.append(f'Example {idx}: {example["method"]} {example["path"]}')
            output_lines.append('-' * 80)
            output_lines.append('')
            output_lines.append('Raw HTTP Request:')
            output_lines.append('')
            output_lines.append(f'{example["method"]} {example["path"]}{query_string} HTTP/1.1')
            output_lines.append(f'Host: {example["host"]}')
            output_lines.append('Content-Type: application/json')
            output_lines.append('User-Agent: CompactConnect-Client/1.0')
            output_lines.append(f'X-Algorithm: {signature_headers["X-Algorithm"]}')
            output_lines.append(f'X-Timestamp: {signature_headers["X-Timestamp"]}')
            output_lines.append(f'X-Nonce: {signature_headers["X-Nonce"]}')
            output_lines.append(f'X-Key-Id: {signature_headers["X-Key-Id"]}')
            output_lines.append(f'X-Signature: {signature_headers["X-Signature"]}')
            output_lines.append('')
            output_lines.append('')

            # Add the plaintext string to sign
            output_lines.append('Plaintext String to Sign:')
            output_lines.append('')
            output_lines.append(string_to_sign)
            output_lines.append('')
            output_lines.append('')

            # Add the base64-encoded string to sign
            string_to_sign_b64 = base64.b64encode(string_to_sign.encode()).decode()
            output_lines.append('Base64-Encoded String to Sign:')
            output_lines.append('')
            output_lines.append(string_to_sign_b64)
            output_lines.append('')
            output_lines.append('')
            output_lines.append('=' * 80)
            output_lines.append('')

        # Write to file
        output_file = 'tests/resources/signature_auth_examples.txt'
        with open(output_file, 'w') as f:
            f.write('\n'.join(output_lines))

        # Verify the file was created and has content
        with open(output_file) as f:
            content = f.read()
            self.assertGreater(len(content), 0)
            self.assertIn('Example 1:', content)
            self.assertIn('Example 2:', content)
            self.assertIn('Example 3:', content)
            self.assertIn('Example 4:', content)
            self.assertIn('Raw HTTP Request:', content)
            self.assertIn('Plaintext String to Sign:', content)
            self.assertIn('Base64-Encoded String to Sign:', content)
