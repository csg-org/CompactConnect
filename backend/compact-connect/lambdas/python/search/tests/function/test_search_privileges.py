import json
from unittest.mock import Mock, patch

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestSearchPrivileges(TstFunction):
    """Test suite for search_api_handler - privilege search functionality."""

    def setUp(self):
        super().setUp()

    def _create_api_event(self, compact: str, body: dict = None) -> dict:
        """Create a standard API Gateway event for search_privileges."""
        return {
            'resource': '/v1/compacts/{compact}/privileges/search',
            'path': f'/v1/compacts/{compact}/privileges/search',
            'httpMethod': 'POST',
            'headers': {
                'accept': 'application/json',
                'content-type': 'application/json',
                'Content-Type': 'application/json',
                'origin': 'https://example.org',
                'Host': 'api.test.example.com',
            },
            'multiValueHeaders': {},
            'queryStringParameters': None,
            'pathParameters': {'compact': compact},
            'requestContext': {
                'resourcePath': '/v1/compacts/{compact}/privileges/search',
                'httpMethod': 'POST',
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-id',
                        'cognito:username': 'test-user',
                    }
                },
            },
            'body': json.dumps(body) if body else None,
            'isBase64Encoded': False,
        }

    def _when_testing_mock_opensearch_client(self, mock_opensearch_client, search_response: dict = None):
        """
        Configure the mock OpenSearchClient for testing.

        :param mock_opensearch_client: The patched OpenSearchClient class
        :param search_response: The response to return from the search method
        :return: The mock client instance
        """
        if not search_response:
            search_response = {
                'hits': {
                    'total': {'value': 0, 'relation': 'eq'},
                    'hits': [],
                }
            }

        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.search.return_value = search_response
        return mock_client_instance

    def _create_mock_provider_hit_with_privileges(
        self,
        provider_id: str = '00000000-0000-0000-0000-000000000001',
        compact: str = 'aslp',
        sort_values: list = None,
    ) -> dict:
        """Create a mock OpenSearch hit for a provider document with privileges and licenses."""
        hit = {
            '_index': f'compact_{compact}_providers',
            '_id': provider_id,
            '_score': 1.0,
            '_source': {
                'providerId': provider_id,
                'type': 'provider',
                'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                'compact': compact,
                'licenseJurisdiction': 'oh',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'givenName': 'John',
                'familyName': 'Doe',
                'dateOfExpiration': '2025-12-31',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'birthMonthDay': '06-15',
                'licenses': [
                    {
                        'providerId': provider_id,
                        'type': 'license-home',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'compact': compact,
                        'jurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'licenseStatus': 'active',
                        'compactEligibility': 'eligible',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
                        'givenName': 'John',
                        'familyName': 'Doe',
                        'dateOfIssuance': '2020-01-01',
                        'dateOfRenewal': '2024-01-01',
                        'dateOfExpiration': '2025-12-31',
                        'npi': '1234567890',
                        'licenseNumber': 'AUD-12345',
                    }
                ],
                'privileges': [
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'ky',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-01-15',
                        'dateOfRenewal': '2024-01-15',
                        'dateOfExpiration': '2025-01-15',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'administratorSetStatus': 'active',
                        'privilegeId': 'PRIV-001',
                        'status': 'active',
                    }
                ],
            },
        }
        if sort_values:
            hit['sort'] = sort_values
        return hit

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_search_returns_flattened_privileges(self, mock_opensearch_client):
        """Test that privilege search returns flattened privilege records."""
        from handlers.search import search_api_handler

        # Create a mock response with provider hits containing privileges
        mock_hit = self._create_mock_provider_hit_with_privileges()
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [mock_hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])

        # Verify response structure has 'privileges' instead of 'providers'
        self.assertIn('privileges', body)
        self.assertNotIn('providers', body)
        self.assertEqual(1, len(body['privileges']))

        # Verify the flattened privilege has both privilege and license fields
        privilege = body['privileges'][0]
        self.assertEqual('statePrivilege', privilege['type'])
        self.assertEqual('00000000-0000-0000-0000-000000000001', privilege['providerId'])
        self.assertEqual('ky', privilege['jurisdiction'])
        self.assertEqual('oh', privilege['licenseJurisdiction'])
        self.assertEqual('audiologist', privilege['licenseType'])
        self.assertEqual('PRIV-001', privilege['privilegeId'])
        self.assertEqual('active', privilege['status'])

        # Verify license fields were merged
        self.assertEqual('John', privilege['givenName'])
        self.assertEqual('Doe', privilege['familyName'])
        self.assertEqual('1234567890', privilege['npi'])
        self.assertEqual('AUD-12345', privilege['licenseNumber'])

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_search_with_empty_results(self, mock_opensearch_client):
        """Test that privilege search returns empty array when no results."""
        from handlers.search import search_api_handler

        search_response = {
            'hits': {
                'total': {'value': 0, 'relation': 'eq'},
                'hits': [],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual({'privileges': [], 'total': {'relation': 'eq', 'value': 0}}, body)

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_search_skips_provider_without_privileges(self, mock_opensearch_client):
        """Test that providers without privileges don't add entries."""
        from handlers.search import search_api_handler

        # Create a provider hit without privileges
        hit = {
            '_index': 'compact_aslp_providers',
            '_id': 'provider-1',
            '_score': 1.0,
            '_source': {
                'providerId': 'provider-1',
                'type': 'provider',
                'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                'compact': 'aslp',
                'licenseJurisdiction': 'oh',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'givenName': 'Jane',
                'familyName': 'Smith',
                'dateOfExpiration': '2025-12-31',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'birthMonthDay': '03-20',
                'licenses': [],
                'privileges': [],
            },
        }
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual(0, len(body['privileges']))

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_search_includes_last_sort(self, mock_opensearch_client):
        """Test that lastSort is included in privilege search response."""
        from handlers.search import search_api_handler

        mock_hit = self._create_mock_provider_hit_with_privileges(
            sort_values=['provider-uuid-123', '2024-01-15T10:30:00+00:00']
        )
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [mock_hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': [{'providerId': 'asc'}],
            },
        )

        response = search_api_handler(event, self.mock_context)

        body = json.loads(response['body'])
        self.assertIn('lastSort', body)
        self.assertEqual(['provider-uuid-123', '2024-01-15T10:30:00+00:00'], body['lastSort'])

    def test_unsupported_route_returns_400(self):
        """Test that unsupported routes return a 400 error."""
        from handlers.search import search_api_handler

        # Create event with unsupported route
        event = {
            'resource': '/v1/compacts/{compact}/unknown/search',
            'path': '/v1/compacts/aslp/unknown/search',
            'httpMethod': 'POST',
            'headers': {
                'Content-Type': 'application/json',
                'origin': 'https://example.org',
            },
            'multiValueHeaders': {},
            'queryStringParameters': None,
            'pathParameters': {'compact': 'aslp'},
            'requestContext': {
                'resourcePath': '/v1/compacts/{compact}/unknown/search',
                'httpMethod': 'POST',
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-id',
                        'cognito:username': 'test-user',
                    }
                },
            },
            'body': json.dumps({'query': {'match_all': {}}}),
            'isBase64Encoded': False,
        }

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Unsupported method or resource', body['message'])
