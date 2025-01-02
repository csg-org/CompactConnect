import json

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestGetAttestation(TstFunction):
    """Test suite for attestation endpoints."""

    def _generate_test_event(self, method: str, attestation_type: str) -> dict:
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['httpMethod'] = method
            event['pathParameters'] = {
                'compact': 'aslp',
                'attestationId': attestation_type,
            }

        return event


    def test_get_latest_attestation(self):
        """Test getting the latest version of an attestation."""
        from handlers.attestations import attestations

        event = self._generate_test_event('GET', 'jurisprudence-confirmation')

        response = attestations(event, self.mock_context)
        response_body = json.loads(response['body'])

        # The TstFunction class sets up 4 versions of this attestation, we expect the endpoint to return version 4
        # as it's the latest
        self.assertEqual({'attestationId': 'jurisprudence-confirmation',
                     'compact': 'aslp',
                     'dateCreated': '2024-06-06T23:59:59+00:00',
                     'dateOfUpdate': '2024-06-06T23:59:59+00:00',
                     'description': 'For displaying the jurisprudence confirmation',
                     'displayName': 'Jurisprudence Confirmation',
                     'required': True,
                     'text': 'You attest that you have read and understand the jurisprudence '
                             'requirements for all states you are purchasing privileges for.',
                     'type': 'attestation',
                     'version': '4'
        }, response_body)

    def test_get_nonexistent_attestation(self):
        """Test getting an attestation that doesn't exist."""
        from handlers.attestations import attestations

        event = self._generate_test_event('GET', 'nonexistent-type')

        response = attestations(event, self.mock_context)
        self.assertEqual(404, response['statusCode'])

    def test_invalid_http_method(self):
        """Test that non-GET methods are rejected."""
        from handlers.attestations import attestations

        event = self._generate_test_event('POST', 'jurisprudence-confirmation')

        response = attestations(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
