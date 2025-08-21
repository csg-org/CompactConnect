# ruff: noqa: ARG001 unused-argument
"""
Tests for the optional HMAC authentication decorator.

This module tests the optional_hmac_auth decorator which allows endpoints to
support both authenticated and unauthenticated access based on whether a
public key is configured for the compact/state combination.
"""

import json
from datetime import UTC, datetime
from unittest.mock import patch

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.exceptions import CCInvalidRequestException, CCUnauthorizedException

from tests import TstLambdas


class TestOptionalHmacAuth(TstLambdas):
    """Test the optional_hmac_auth decorator."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Load test keys
        with open('tests/resources/client_private_key.pem') as f:
            self.private_key_pem = f.read()

        with open('tests/resources/client_public_key.pem') as f:
            self.public_key_pem = f.read()

        # Load base event
        with open('tests/resources/api-client-event.json') as f:
            self.base_event = json.load(f)

    def test_no_public_key_configured_allows_request(self):
        """Test that requests proceed when no public key is configured."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK', 'authenticated': False}

        # Mock DynamoDB to return empty dict (no public key configured)
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {}

            resp = lambda_handler(self.base_event, self.mock_context)

            # Should proceed without HMAC validation
            self.assertEqual({'message': 'OK', 'authenticated': False}, resp)

    def test_public_key_configured_enforces_hmac_validation(self):
        """Test that HMAC validation is enforced when public key is configured."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK', 'authenticated': True}

        # Create a properly signed event
        event = self._create_signed_event()

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {'test-key-001': self.public_key_pem}

            resp = lambda_handler(event, self.mock_context)

            # Should validate HMAC and proceed
            self.assertEqual({'message': 'OK', 'authenticated': True}, resp)

    def test_public_key_configured_missing_headers_rejected(self):
        """Test that missing HMAC headers are rejected when public key is configured."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Mock DynamoDB to return True (keys configured)
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {'test-key-001': self.public_key_pem}

            with self.assertRaises(CCUnauthorizedException) as cm:
                lambda_handler(self.base_event, self.mock_context)

            self.assertIn('X-Key-Id header required when HMAC keys are configured', str(cm.exception))

    def test_public_key_configured_invalid_signature_rejected(self):
        """Test that invalid signatures are rejected when public key is configured."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with invalid signature
        event = self._create_signed_event()
        event['headers']['X-Signature'] = 'invalid-signature'

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {'test-key-001': self.public_key_pem}

            with self.assertRaises(CCUnauthorizedException) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Invalid request signature', str(cm.exception))

    def test_missing_path_parameters_rejected(self):
        """Test that missing path parameters are rejected regardless of public key configuration."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event without path parameters
        event = self.base_event.copy()
        event['pathParameters'] = {}

        # Should be rejected even if no public key is configured
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {}

            with self.assertRaises(CCInvalidRequestException) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Missing compact or jurisdiction parameters', str(cm.exception))

    def test_public_key_configured_invalid_timestamp_rejected(self):
        """Test that invalid timestamps are rejected when public key is configured."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with old timestamp
        event = self._create_signed_event()
        event['headers']['X-Timestamp'] = '2020-01-01T00:00:00Z'

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {'test-key-001': self.public_key_pem}

            with self.assertRaises(CCUnauthorizedException) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Request timestamp is too old or in the future', str(cm.exception))

    def test_public_key_configured_malformed_timestamp_rejected(self):
        """Test that malformed timestamps are rejected when public key is configured."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with malformed timestamp
        event = self._create_signed_event()
        event['headers']['X-Timestamp'] = 'not-a-timestamp'

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {'test-key-001': self.public_key_pem}

            with self.assertRaises(CCInvalidRequestException) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Invalid timestamp format', str(cm.exception))

    def test_public_key_configured_unsupported_algorithm_rejected(self):
        """Test that unsupported algorithms are rejected when public key is configured."""
        from cc_common.hmac_auth import optional_hmac_auth

        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        # Create event with unsupported algorithm
        event = self._create_signed_event()
        event['headers']['X-Algorithm'] = 'RSA-SHA256'

        # Mock DynamoDB to return the public key
        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {'test-key-001': self.public_key_pem}

            with self.assertRaises(CCUnauthorizedException) as cm:
                lambda_handler(event, self.mock_context)

            self.assertIn('Unsupported signature algorithm', str(cm.exception))

    def test_integration_with_api_handler(self):
        """Test that optional_hmac_auth works correctly with api_handler decorator."""
        from cc_common.hmac_auth import optional_hmac_auth
        from cc_common.utils import api_handler

        @api_handler
        @optional_hmac_auth
        def lambda_handler(event: dict, context: LambdaContext):
            # Check if we have HMAC headers to determine if authenticated
            headers = event.get('headers') or {}
            has_hmac_headers = all(
                [
                    headers.get('X-Algorithm'),
                    headers.get('X-Timestamp'),
                    headers.get('X-Nonce'),
                    headers.get('X-Signature'),
                ]
            )
            return {'message': 'OK', 'authenticated': has_hmac_headers}

            # Test with no public key configured

        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {}

            resp = lambda_handler(self.base_event, self.mock_context)

            # Should return API Gateway response format
            self.assertEqual(200, resp['statusCode'])
            self.assertEqual('{"message": "OK", "authenticated": false}', resp['body'])

        # Test with public key configured and valid signature
        event = self._create_signed_event()

        with patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction') as mock_get_keys:
            mock_get_keys.return_value = {'test-key-001': self.public_key_pem}

            resp = lambda_handler(event, self.mock_context)

            # Should return API Gateway response format
            self.assertEqual(200, resp['statusCode'])
            self.assertEqual('{"message": "OK", "authenticated": true}', resp['body'])

    def _create_signed_event(self) -> dict:
        """Create a properly signed event for testing."""
        # Create base event
        event = self.base_event.copy()

        # Generate current timestamp and nonce
        timestamp = datetime.now(UTC).isoformat()
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

        # Add HMAC headers to event
        event['headers'].update(headers)

        return event
