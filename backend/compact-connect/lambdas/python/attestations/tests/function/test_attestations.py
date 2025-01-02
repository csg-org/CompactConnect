import json

from moto import mock_aws

from cc_common.exceptions import CCNotFoundException
from handlers.attestations import attestations

from . import TstFunction


@mock_aws
class TestGetAttestation(TstFunction):
    """Test suite for attestation endpoints."""

    def test_get_latest_attestation(self):
        """Test getting the latest version of an attestation."""
        event = {
            'httpMethod': 'GET',
            'pathParameters': {
                'compact': 'aslp',
                'attestationType': 'jurisprudence-confirmation',
            },
        }

        response = attestations(event, self.mock_context)
        response_body = json.loads(response['body'])

        # The TstFunction class sets up 4 versions of this attestation, we expect the endpoint to return version 4
        # as it's the latest
        self.assertEqual({
            'version': '4',
            'attestationType': 'jurisprudence-confirmation',
            'compact': 'aslp',
            'required': True,
            'dateCreated': '2024-06-06T23:59:59+00:00',
            'type': 'attestation',
        }, response_body)

    def test_get_nonexistent_attestation(self):
        """Test getting an attestation that doesn't exist."""
        event = {
            'httpMethod': 'GET',
            'pathParameters': {
                'compact': 'aslp',
                'attestationType': 'nonexistent-type',
            },
        }

        with self.assertRaises(CCNotFoundException) as context:
            attestations(event, self.mock_context)

        self.assertEqual(str(context.exception), 'No attestation found for type nonexistent-type')

    def test_invalid_http_method(self):
        """Test that non-GET methods are rejected."""
        event = {
            'httpMethod': 'POST',
            'pathParameters': {
                'compact': 'aslp',
                'attestationType': 'jurisprudence-confirmation',
            },
        }

        with self.assertRaises(Exception) as context:
            attestations(event, self.mock_context)

        self.assertEqual(str(context.exception), 'Invalid HTTP method')
