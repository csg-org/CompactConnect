import json
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

from common_test.sign_request import sign_request
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class SignatureTestBase(TstFunction):
    """Base class for tests that require signature authentication setup."""

    def setUp(self):
        super().setUp()
        # Load test keys for signature authentication
        with open('../common/tests/resources/client_private_key.pem') as f:
            self.private_key_pem = f.read()
        with open('../common/tests/resources/client_public_key.pem') as f:
            self.public_key_pem = f.read()

        # Load signature public keys into the compact configuration table for functional testing
        self._setup_signature_keys()

    def _setup_signature_keys(self):
        """Setup signature keys for testing. Override in subclasses to customize key setup."""
        # Default setup - load keys for 'cosm' compact with 'oh' and 'ne' jurisdictions
        self._load_signature_public_key('cosm', 'oh', 'test-key-001', self.public_key_pem)
        self._load_signature_public_key('cosm', 'ne', 'test-key-001', self.public_key_pem)

    def _load_signature_public_key(self, compact: str, jurisdiction: str, key_id: str, public_key_pem: str):
        """Load a signature public key into the compact configuration table."""
        item = {
            'pk': f'{compact}#SIGNATURE_KEYS#{jurisdiction}',
            'sk': f'{compact}#JURISDICTION#{jurisdiction}#{key_id}',
            'publicKey': public_key_pem,
            'compact': compact,
            'jurisdiction': jurisdiction,
            'keyId': key_id,
            'createdAt': '2024-01-01T00:00:00Z',
        }
        self._compact_configuration_table.put_item(Item=item)

    def _create_signed_event(self, event: dict) -> dict:
        """Add signature headers to an event for signature authentication."""
        from cc_common.config import config

        # Generate current timestamp and nonce
        timestamp = config.current_standard_datetime
        nonce = str(uuid4())
        key_id = 'test-key-001'

        # Sign the request
        headers = sign_request(
            method=event['httpMethod'],
            path=event['path'],
            query_params=event.get('queryStringParameters') or {},
            timestamp=timestamp.isoformat(),
            nonce=nonce,
            key_id=key_id,
            private_key_pem=self.private_key_pem,
        )

        # Add signature headers to event
        event['headers'].update(headers)
        return event


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestBulkUploadUrlHandler(SignatureTestBase):
    def _setup_signature_keys(self):
        """Setup signature keys for testing. Only need 'oh' jurisdiction for this test."""

        self._load_signature_public_key('cosm', 'oh', 'test-key-001', self.public_key_pem)

    def test_bulk_upload_url_handler_success(self):
        """Test successful bulk upload URL generation with optional signature authentication."""
        from handlers.state_api import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for cosm/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral oh/cosm.write'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertIn('upload', body)
        upload = body['upload']
        self.assertIn('url', upload)
        self.assertIn('fields', upload)
        self.assertIn('key', upload['fields'])
        self.assertIn('policy', upload['fields'])
        self.assertIn('x-amz-algorithm', upload['fields'])
        self.assertIn('x-amz-credential', upload['fields'])
        self.assertIn('x-amz-date', upload['fields'])
        self.assertIn('x-amz-signature', upload['fields'])

        # Verify the key follows the expected pattern: compact/jurisdiction/uuid
        key = upload['fields']['key']
        self.assertTrue(key.startswith('cosm/oh/'))
        self.assertEqual(len(key.split('/')), 3)

    def test_bulk_upload_url_handler_missing_signature_rejected(self):
        """
        Test that bulk upload URL generation is rejected when signature keys are configured but no signature is
        provided.
        """
        from handlers.state_api import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for cosm/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral oh/cosm.write'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}

        # Do NOT add signature authentication headers - this should cause the request to be rejected
        # since signature keys are configured for this compact/jurisdiction

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(401, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertIn('message', body)
        # The error message should indicate missing required signature authentication headers
        self.assertIn('x-key-id', body['message'].lower())
