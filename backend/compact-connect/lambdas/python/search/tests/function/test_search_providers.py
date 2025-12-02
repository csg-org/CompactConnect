import json
from unittest.mock import Mock, patch

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestSearchProviders(TstFunction):
    """Test suite for search_providers handler."""

    def setUp(self):
        super().setUp()

    def _create_api_event(self, compact: str, body: dict = None) -> dict:
        """Create a standard API Gateway event for search_providers."""
        return {
            'resource': f'/v1/compacts/{compact}/providers/search',
            'path': f'/v1/compacts/{compact}/providers/search',
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
                'resourcePath': f'/v1/compacts/{compact}/providers/search',
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

    def _create_mock_provider_hit(
        self,
        provider_id: str = '00000000-0000-0000-0000-000000000001',
        compact: str = 'aslp',
        sort_values: list = None,
    ) -> dict:
        """Create a mock OpenSearch hit for a provider document."""
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
            },
        }
        if sort_values:
            hit['sort'] = sort_values
        return hit

    @patch('handlers.search_providers.OpenSearchClient')
    def test_basic_search_with_match_all_query(self, mock_opensearch_client):
        """Test that a basic search with no query uses match_all."""
        from handlers.search_providers import search_providers

        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create event with minimal body - just the required query field
        event = self._create_api_event(compact='aslp', body={'query': {'match_all': {}}})

        response = search_providers(event, self.mock_context)

        # Verify OpenSearchClient was instantiated and search was called
        mock_opensearch_client.assert_called_once()
        mock_client_instance.search.assert_called_once()

        # Verify the search was called with correct parameters
        mock_client_instance.search.assert_called_once_with(
            index_name='compact_aslp_providers', body={'query': {'match_all': {}}, 'size': 10}
        )

        # Verify response structure
        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual({'providers': [], 'total': {'relation': 'eq', 'value': 0}}, body)

    @patch('handlers.search_providers.OpenSearchClient')
    def test_search_with_custom_query(self, mock_opensearch_client):
        """Test that a custom OpenSearch query is passed through correctly."""
        from handlers.search_providers import search_providers

        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create a custom bool query
        custom_query = {
            'bool': {
                'must': [
                    {'match': {'givenName': 'John'}},
                    {'term': {'licenseStatus': 'active'}},
                ]
            }
        }
        event = self._create_api_event('aslp', body={'query': custom_query, 'from': 20})

        search_providers(event, self.mock_context)

        # Verify the custom query was passed through
        mock_client_instance.search.assert_called_once_with(
            index_name='compact_aslp_providers',
            body={
                'query': {'bool': {'must': [{'match': {'givenName': 'John'}}, {'term': {'licenseStatus': 'active'}}]}},
                'size': 10,
                'from': 20,
            },
        )

    @patch('handlers.search_providers.OpenSearchClient')
    def test_search_size_capped_at_max(self, mock_opensearch_client):
        """Test that size parameter is capped at MAX_SIZE (100)."""
        from handlers.search_providers import search_providers

        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Request size larger than MAX_SIZE
        event = self._create_api_event('aslp', body={'query': {'match_all': {}}, 'size': 500})

        search_providers(event, self.mock_context)

        call_args = mock_client_instance.search.call_args
        search_body = call_args.kwargs['body']
        self.assertEqual(100, search_body['size'])  # Capped at MAX_SIZE

    @patch('handlers.search_providers.OpenSearchClient')
    def test_search_with_sort_parameter(self, mock_opensearch_client):
        """Test that sort parameter is included in the search body."""
        from handlers.search_providers import search_providers

        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        sort_config = [{'providerId': 'asc'}, {'dateOfUpdate': 'desc'}]
        search_after_values = ['provider-uuid-123']
        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': sort_config,
                'search_after': search_after_values,
            },
        )

        search_providers(event, self.mock_context)

        mock_client_instance.search.assert_called_once_with(
            index_name='compact_aslp_providers',
            body={
                'query': {'match_all': {}},
                'size': 10,
                'sort': sort_config,
                'search_after': search_after_values,
            },
        )

    @patch('handlers.search_providers.OpenSearchClient')
    def test_search_after_without_sort_returns_400(self, mock_opensearch_client):
        """Test that search_after without sort raises an error."""
        from handlers.search_providers import search_providers

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # search_after without sort should fail
        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'search_after': ['provider-uuid-123'],
            },
        )

        response = search_providers(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('sort is required when using search_after pagination', body['message'])

    def test_invalid_request_body_returns_400(self):
        """Test that an invalid request body returns a 400 error."""
        from handlers.search_providers import search_providers

        # Create event with missing required 'query' field
        event = self._create_api_event('aslp', body={'size': 10})

        response = search_providers(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Invalid request', body['message'])

    @patch('handlers.search_providers.OpenSearchClient')
    def test_search_returns_sanitized_providers(self, mock_opensearch_client):
        """Test that provider records are sanitized through ProviderGeneralResponseSchema."""
        from handlers.search_providers import search_providers

        # Create a mock response with provider hits
        mock_hit = self._create_mock_provider_hit()
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [mock_hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_providers(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual(
            {
                'providers': [
                    {
                        'birthMonthDay': '06-15',
                        'compact': 'aslp',
                        'compactEligibility': 'eligible',
                        'dateOfExpiration': '2025-12-31',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'familyName': 'Doe',
                        'givenName': 'John',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseJurisdiction': 'oh',
                        'licenseStatus': 'active',
                        'privilegeJurisdictions': [],
                        'providerId': '00000000-0000-0000-0000-000000000001',
                        'type': 'provider',
                    }
                ],
                'total': {'relation': 'eq', 'value': 1},
            },
            body,
        )

    @patch('handlers.search_providers.OpenSearchClient')
    def test_search_response_includes_last_sort_for_pagination(self, mock_opensearch_client):
        """Test that lastSort is included in response for search_after pagination."""
        from handlers.search_providers import search_providers

        # Create hits with sort values
        mock_hit = self._create_mock_provider_hit(sort_values=['provider-uuid-123', '2024-01-15T10:30:00+00:00'])
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
                'sort': [{'providerId': 'asc'}, {'dateOfUpdate': 'asc'}],
            },
        )

        response = search_providers(event, self.mock_context)

        body = json.loads(response['body'])
        self.assertIn('lastSort', body)
        self.assertEqual(['provider-uuid-123', '2024-01-15T10:30:00+00:00'], body['lastSort'])

    @patch('handlers.search_providers.OpenSearchClient')
    def test_search_uses_correct_index_for_compact(self, mock_opensearch_client):
        """Test that the correct index name is used based on the compact parameter."""
        from handlers.search_providers import search_providers

        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Test with different compacts
        for compact in ['aslp', 'octp', 'coun']:
            mock_client_instance.reset_mock()

            event = self._create_api_event(compact, body={'query': {'match_all': {}}})
            search_providers(event, self.mock_context)

            call_args = mock_client_instance.search.call_args
            self.assertEqual(f'compact_{compact}_providers', call_args.kwargs['index_name'])
